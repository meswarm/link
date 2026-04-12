"""LLM 决策引擎 — Function Calling 循环"""

import base64
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from link.config import ContextHookConfig
from link.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

# Function Calling 最大循环次数（防止无限循环）
MAX_TOOL_CALL_ROUNDS = 10

# 图片标记格式: [image:/path/to/file:image/jpeg]
_IMAGE_TAG_PATTERN = re.compile(r'\[image:(.+?):(.+?)\]')


class LLMEngine:
    """LLM 决策引擎

    管理对话历史，实现完整的 Function Calling 循环：
    用户消息 → LLM → (可能多次工具调用) → 最终文本回复
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        system_prompt: str,
        tool_registry: ToolRegistry,
        skills_prompt: str = "",
        context_hooks: list[ContextHookConfig] | None = None,
        context_ttl: int = 30,
        temperature: float = 0.7,
        max_history: int = 20,
        enable_thinking: bool = False,
        vision: bool = False,
    ):
        self._model = model
        self._system_prompt = system_prompt
        self._skills_prompt = skills_prompt
        self._context_hooks = context_hooks or []
        self._context_ttl = context_ttl  # 缓存过期时间（分钟）
        self._temperature = temperature
        self._max_history = max_history
        self._enable_thinking = enable_thinking
        self._vision = vision  # 是否支持图像输入
        self._tool_registry = tool_registry
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        # 对话历史（按房间隔离）
        self._histories: dict[str, list[dict[str, Any]]] = {}

        # 上下文缓存（按房间隔离）
        self._context_cache: dict[str, dict[str, str]] = {}
        self._context_last_active: dict[str, float] = {}  # 每个房间最后活跃时间

    def _get_history(self, room_id: str) -> list[dict[str, Any]]:
        """获取指定房间的对话历史"""
        if room_id not in self._histories:
            self._histories[room_id] = []
        return self._histories[room_id]

    def _trim_history(self, room_id: str) -> None:
        """修剪对话历史，保持在最大长度内"""
        history = self._get_history(room_id)
        max_len = self._max_history * 2
        if len(history) > max_len:
            self._histories[room_id] = history[-max_len:]

    def _build_messages(self, room_id: str, context_data: dict[str, str] | None = None) -> list[dict[str, Any]]:
        """构建发送给 LLM 的完整消息列表"""
        # 组合 system prompt
        system_content = self._system_prompt

        # 替换预置上下文占位符
        if context_data:
            try:
                system_content = system_content.format(**context_data)
            except KeyError as e:
                logger.warning(f"上下文占位符未匹配: {e}")

        # 拼接 skills
        if self._skills_prompt:
            system_content += "\n\n" + self._skills_prompt

        messages = [
            {"role": "system", "content": system_content}
        ]
        messages.extend(self._get_history(room_id))
        return messages

    def _build_user_content(self, user_message: str) -> str | list[dict[str, Any]]:
        """构建用户消息内容

        如果模型支持图像且消息中包含图片标记 [image:path:mime]，
        将图片编码为 base64 并构建多模态消息格式。
        否则返回纯文本。
        """
        # 检查是否有图片标记
        matches = _IMAGE_TAG_PATTERN.findall(user_message)

        if not matches or not self._vision:
            # 无图片或模型不支持视觉 → 保持纯文本
            if matches and not self._vision:
                # 模型不支持视觉，将标记替换为文字描述
                for file_path, mimetype in matches:
                    tag = f"[image:{file_path}:{mimetype}]"
                    user_message = user_message.replace(
                        tag, f"[用户发送了一张图片: {Path(file_path).name}]"
                    )
            return user_message

        # 模型支持视觉 → 构建多模态消息
        content_parts: list[dict[str, Any]] = []

        # 提取文本部分（去除图片标记）
        text_part = _IMAGE_TAG_PATTERN.sub("", user_message).strip()
        if not text_part:
            text_part = "请分析这张图片"

        # 添加图片部分
        for file_path, mimetype in matches:
            try:
                image_data = Path(file_path).read_bytes()
                b64_data = base64.b64encode(image_data).decode("utf-8")
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mimetype};base64,{b64_data}"
                    }
                })
                logger.info(f"图片已编码: {Path(file_path).name} ({len(image_data)} bytes)")
            except Exception as e:
                logger.error(f"图片编码失败 {file_path}: {e}")
                text_part += f"\n[图片加载失败: {Path(file_path).name}]"

        # 添加文本部分
        content_parts.append({"type": "text", "text": text_part})

        return content_parts

    async def _resolve_context(self, room_id: str) -> dict[str, str]:
        """执行预置上下文钩子，获取动态数据

        缓存策略:
          - refresh=once 的 hook：首次获取后缓存
          - 如果距上次对话超过 context_ttl 分钟，清空缓存（视为新会话）
          - refresh=always 的 hook：每次都重新获取
        """
        if not self._context_hooks:
            return {}

        now = time.time()

        # 检查是否超时（新会话），清空该房间的缓存
        last_active = self._context_last_active.get(room_id, 0)
        if now - last_active > self._context_ttl * 60:
            if room_id in self._context_cache:
                logger.info(f"上下文缓存已过期 (>{self._context_ttl}分钟)，重新获取")
                self._context_cache[room_id] = {}

        self._context_last_active[room_id] = now

        # 确保房间有缓存字典
        if room_id not in self._context_cache:
            self._context_cache[room_id] = {}

        cache = self._context_cache[room_id]
        context = {}

        for hook in self._context_hooks:
            # refresh=once 且已有缓存，直接复用
            if hook.refresh == "once" and hook.name in cache:
                context[hook.name] = cache[hook.name]
                continue

            # 需要调用工具
            try:
                result = await self._tool_registry.execute_tool(
                    hook.tool, **hook.params
                )
                context[hook.name] = result
                cache[hook.name] = result
                logger.debug(f"上下文钩子 [{hook.name}] (refresh={hook.refresh}): 已获取")
            except Exception as e:
                logger.error(f"上下文钩子 [{hook.name}] 执行失败: {e}")
                context[hook.name] = cache.get(hook.name, f"(获取失败: {e})")

        return context

    async def chat(self, room_id: str, user_message: str) -> str:
        """执行一轮完整对话（可能包含多次工具调用）

        Args:
            room_id: Matrix 房间 ID（用于隔离对话历史）
            user_message: 用户消息

        Returns:
            LLM 的最终文本回复
        """
        history = self._get_history(room_id)

        # 解析图片标记，构建多模态消息
        user_content = self._build_user_content(user_message)
        history.append({"role": "user", "content": user_content})

        # 执行预置上下文钩子
        context_data = await self._resolve_context(room_id)

        messages = self._build_messages(room_id, context_data)
        tools = self._tool_registry.get_all_definitions() if self._tool_registry.has_tools() else None

        # Function Calling 循环
        for round_num in range(MAX_TOOL_CALL_ROUNDS):
            logger.debug(f"LLM 调用 (round {round_num + 1}), 消息数: {len(messages)}")

            kwargs: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "temperature": self._temperature,
            }
            if tools:
                kwargs["tools"] = tools
            if not self._enable_thinking:
                kwargs["extra_body"] = {"enable_thinking": False}

            try:
                completion = await self._client.chat.completions.create(**kwargs)
            except Exception as e:
                error_msg = f"LLM 调用失败: {e}"
                logger.error(error_msg)
                history.pop()
                return f"抱歉，我遇到了一些问题: {error_msg}"

            choice = completion.choices[0]
            assistant_message = choice.message

            # 如果没有工具调用，返回最终回复
            if not assistant_message.tool_calls:
                content = assistant_message.content or ""
                history.append({"role": "assistant", "content": content})
                self._trim_history(room_id)
                return content

            # 有工具调用，执行每个工具
            tool_calls_msg: dict[str, Any] = {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_message.tool_calls
                ],
            }
            messages.append(tool_calls_msg)

            for tool_call in assistant_message.tool_calls:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}

                logger.info(f"执行工具调用: {func_name}({func_args})")
                result = await self._tool_registry.execute_tool(func_name, **func_args)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        # 超过最大轮次
        logger.warning(f"Function Calling 循环超过最大轮次 ({MAX_TOOL_CALL_ROUNDS})")
        final_content = "抱歉，操作步骤过多，我需要简化处理方式。请重新描述你的需求。"
        history.append({"role": "assistant", "content": final_content})
        self._trim_history(room_id)
        return final_content

    async def format_notification(self, event_data: dict[str, Any]) -> str:
        """使用 LLM 格式化工具推送的通知信息"""
        prompt = (
            f"以下是一条工具推送的通知信息，请将其整理为简洁友好的中文消息：\n\n"
            f"```json\n{json.dumps(event_data, ensure_ascii=False, indent=2)}\n```"
        )

        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "你是一个通知整理助手。将工具推送的原始数据整理为简洁友好的消息。不要使用代码块，直接输出消息内容。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                extra_body={"enable_thinking": False},
            )
            return completion.choices[0].message.content or str(event_data)
        except Exception as e:
            logger.error(f"通知格式化失败: {e}")
            return json.dumps(event_data, ensure_ascii=False, indent=2)
