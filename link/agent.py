"""Agent 核心编排器 — 协调 Matrix、LLM 和工具三层"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from link.config import AgentConfig
from link.llm_engine import LLMEngine
from link.matrix_client import MatrixClient
from link.skills import load_skills_from_dir, format_skills_for_prompt, Skill
from link.tool_registry import ToolRegistry
from link.tools.webhook import WebhookReceiver

logger = logging.getLogger(__name__)

# 匹配工具返回中的文件路径（file:///path 或 [file:/path]）
_FILE_PATH_PATTERN = re.compile(r"file://(/.+?)(?:\s|$|[)\]\"'])")


class Agent:
    """Agent 核心

    编排三层之间的交互：
    1. 用户消息 → LLM 决策 → 工具调用 → 回复用户
    2. 工具推送 → (LLM 格式化 | 直通) → 通知用户
    3. 用户文件 → 下载到 inbox → LLM 决策 → 工具处理
    4. 工具返回文件路径 → 自动上传到 Matrix
    """

    def __init__(self, config: AgentConfig):
        self._config = config

        # 初始化工具注册中心
        self._tool_registry = ToolRegistry.from_configs(config.tools, work_dir=config.work_dir)

        # 加载技能
        self._skills: list[Skill] = []
        skills_prompt = ""
        if config.skills_dir:
            self._skills = load_skills_from_dir(config.skills_dir)
            skills_prompt = format_skills_for_prompt(self._skills)

        # 初始化 LLM 引擎（扁平参数）
        self._llm_engine = LLMEngine(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            model=config.llm_model,
            system_prompt=config.prompt,
            tool_registry=self._tool_registry,
            skills_prompt=skills_prompt,
            context_hooks=config.context,
            context_ttl=config.context_ttl,
            temperature=config.resolved_temperature,
            max_history=config.max_history,
            enable_thinking=config.resolved_enable_thinking,
            vision=config.resolved_vision,
        )

        # 初始化 Matrix 客户端（传入 work_dir 作为文件下载目录）
        self._matrix_client = MatrixClient(
            homeserver=config.homeserver,
            user=config.matrix_user,
            password=config.matrix_password,
            rooms=config.rooms,
            download_dir=config.work_dir,
        )
        self._matrix_client.on_message(self._handle_user_message)

        # 初始化 Webhook 接收器（如果启用）
        self._webhook: WebhookReceiver | None = None
        if config.webhook.enabled:
            self._webhook = WebhookReceiver(
                config.webhook, self._handle_tool_event
            )

    async def start(self) -> None:
        """启动 Agent"""
        logger.info(f"正在启动 Agent: {self._config.name}")

        # 登录 Matrix
        if not await self._matrix_client.login():
            raise RuntimeError("Matrix 登录失败，Agent 无法启动")

        # 启动 Webhook（如果启用）
        if self._webhook:
            await self._webhook.start()

        # 报告状态
        tool_names = self._tool_registry.tool_names
        skill_names = [s.name for s in self._skills]
        context_names = [h.name for h in self._config.context]
        logger.info(
            f"Agent '{self._config.name}' 已就绪\n"
            f"  Matrix 用户: {self._matrix_client.user_id}\n"
            f"  监听房间: {self._matrix_client.rooms}\n"
            f"  已注册工具: {tool_names if tool_names else '(无)'}\n"
            f"  已加载技能: {skill_names if skill_names else '(无)'}\n"
            f"  预置上下文: {context_names if context_names else '(无)'}\n"
            f"  工作目录: {self._config.work_dir or '(未设置)'}\n"
            f"  文件接收: {'✅ 已启用' if self._config.work_dir else '❌ 未设置 work_dir'}\n"
            f"  图像分析: {'✅ 已启用' if self._config.resolved_vision else '❌ 模型不支持'}\n"
            f"  Webhook: {'已启用' if self._webhook else '未启用'}"
        )

        # 开始 Matrix 同步（阻塞）
        await self._matrix_client.start_sync()

    async def stop(self) -> None:
        """优雅关闭 Agent（防止重复调用）"""
        if getattr(self, '_stopped', False):
            return
        self._stopped = True

        logger.info(f"正在停止 Agent: {self._config.name}")

        if self._webhook:
            await self._webhook.stop()

        await self._matrix_client.stop()
        logger.info(f"Agent '{self._config.name}' 已停止")

    async def _handle_user_message(
        self, room_id: str, sender: str, content: str
    ) -> None:
        """处理用户消息（文本或媒体描述）"""
        logger.info(f"处理消息: [{room_id}] {sender}: {content}")

        # 显示「正在输入」状态
        await self._matrix_client.set_typing(room_id, True)

        try:
            reply = await self._llm_engine.chat(room_id, content)

            # 取消「正在输入」状态
            await self._matrix_client.set_typing(room_id, False)

            # 检测回复中是否包含文件路径，自动上传
            file_paths = _FILE_PATH_PATTERN.findall(reply)
            if file_paths:
                await self._send_reply_with_files(room_id, reply, file_paths)
            else:
                await self._matrix_client.send_text(room_id, reply)

        except Exception as e:
            await self._matrix_client.set_typing(room_id, False)
            logger.error(f"处理消息异常: {e}", exc_info=True)
            await self._matrix_client.send_text(
                room_id, "抱歉，处理你的消息时出现了问题。"
            )

    async def _send_reply_with_files(
        self, room_id: str, reply: str, file_paths: list[str]
    ) -> None:
        """发送包含文件的回复

        先发送文件，再发送去掉文件路径后的文本。
        """
        # 发送所有文件
        for fp in file_paths:
            path = Path(fp)
            if path.exists() and path.is_file():
                logger.info(f"检测到回复中的文件: {fp}，自动上传")
                await self._matrix_client.send_file(room_id, fp)
            else:
                logger.warning(f"回复中的文件不存在: {fp}")

        # 清理文本中的 file:// 路径，发送纯文本
        clean_reply = _FILE_PATH_PATTERN.sub("", reply).strip()
        if clean_reply:
            await self._matrix_client.send_text(room_id, clean_reply)

    async def _handle_tool_event(
        self, endpoint: str, data: dict[str, Any], urgent: bool
    ) -> None:
        """处理工具主动推送的事件（支持文件推送）"""
        rooms = self._matrix_client.rooms
        if not rooms:
            logger.warning("没有可用的房间来发送通知")
            return

        # 检查是否是文件推送
        if data.get("type") == "file" and data.get("path"):
            file_path = data["path"]
            caption = data.get("caption", "")
            for room_id in rooms:
                success = await self._matrix_client.send_file(
                    room_id, file_path, caption
                )
                if success and caption:
                    await self._matrix_client.send_text(room_id, caption)
            return

        # 常规通知处理
        if urgent:
            message = data.get("message") or json.dumps(
                data, ensure_ascii=False, indent=2
            )
            logger.info(f"[紧急通知] {endpoint}: {message}")
        else:
            message = await self._llm_engine.format_notification(data)
            logger.info(f"[通知] {endpoint}: {message}")

        for room_id in rooms:
            logger.info(f"正在发送通知到房间: {room_id}")
            if urgent:
                await self._matrix_client.send_text(room_id, f"⚠️ {message}")
            else:
                await self._matrix_client.send_notice(room_id, message)
