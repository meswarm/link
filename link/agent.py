"""Agent 核心编排器 — 协调 Matrix、LLM 和工具三层"""

import json
import logging
import mimetypes
import re
from pathlib import Path
from typing import Any

from link.config import AgentConfig
from link.llm_engine import LLMEngine
from link import r2_protocol
from link.matrix_client import MatrixClient
from link.media_store import R2MediaStore
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

        # 初始化 R2 媒体存储（如果启用）
        self._media_store: R2MediaStore | None = None
        if config.media_storage == "r2" and config._r2_config and config._r2_config.enabled:
            self._media_store = R2MediaStore(
                config._r2_config, config.resolved_media_cache_root
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
            f"  媒体缓存根目录: {self._config.resolved_media_cache_root}\n"
            f"  文件接收: {'✅ 已启用' if self._config.work_dir else '❌ 未设置 work_dir'}\n"
            f"  图像分析: {'✅ 已启用' if self._config.resolved_vision else '❌ 模型不支持'}\n"
            f"  R2 图片转多模态: {'✅ 是' if self._config.pass_r2_images_to_llm else '❌ 否'}\n"
            f"  媒体存储: {self._config.media_storage.upper()}{' (✅ R2 已连接)' if self._media_store else ''}\n"
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

        # 将消息中的 r2:// 图片引用下载到本地，转换为 [image:path:mime] 格式
        # 这样 LLMEngine 的 vision 逻辑就能正确处理多模态内容
        content = await self._resolve_r2_markdown_links(content)

        # 如果启用 R2，将用户发来的本地媒体文件存档到 R2
        if self._media_store and "[image:" in content:
            await self._archive_media_to_r2(room_id, content)

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
            elif reply.strip():
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

        R2 模式：将回复中的本地路径上传到 R2，替换为 r2:// 引用，
                 整体发送完整 Markdown — 客户端用自身 R2 凭据渲染图片。

        Matrix 模式：分别发送每个文件（m.file 事件），再发文字部分。
        """
        if self._media_store:
            room_prefix = await self._matrix_client.get_r2_room_prefix(room_id)
            modified_reply = reply
            if not room_prefix:
                logger.warning(
                    f"房间 {room_id} 未配置 com.talk.r2_prefix，R2 上传改为 Matrix 直传"
                )
                for fp in file_paths:
                    path = Path(fp)
                    if path.exists() and path.is_file():
                        await self._send_file_to_room(room_id, fp)
                    else:
                        logger.warning(f"回复中的文件不存在: {fp}")
                clean_reply = _FILE_PATH_PATTERN.sub("", reply).strip()
                if clean_reply:
                    await self._matrix_client.send_text(room_id, clean_reply)
                return

            for fp in file_paths:
                path = Path(fp)
                if not path.exists():
                    logger.warning(f"回复中的文件不存在: {fp}")
                    continue
                mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
                try:
                    r2_uri = await self._media_store.upload(
                        path, room_prefix=room_prefix, mime=mime
                    )
                    modified_reply = _replace_file_links_with_r2(
                        modified_reply, fp, r2_uri, path
                    )
                    logger.info(f"本地文件已替换为 R2 引用: {path.name} → {r2_uri}")
                except Exception as e:
                    logger.error(f"上传到 R2 失败，将移除该路径: {fp}, {e}")

            clean_reply = _FILE_PATH_PATTERN.sub("", modified_reply).strip()
            if clean_reply:
                await self._matrix_client.send_text(room_id, clean_reply)

        else:
            # Matrix 模式：逐文件发送，再发纯文本
            for fp in file_paths:
                path = Path(fp)
                if path.exists() and path.is_file():
                    logger.info(f"检测到回复中的文件: {fp}，自动上传")
                    await self._send_file_to_room(room_id, fp)
                else:
                    logger.warning(f"回复中的文件不存在: {fp}")

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
                await self._send_file_to_room(room_id, file_path, caption)
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
                await self._matrix_client.send_text(room_id, message)
            else:
                await self._matrix_client.send_notice(room_id, message)

    async def _send_file_to_room(
        self, room_id: str, file_path: str, caption: str = ""
    ) -> None:
        """发送文件到房间（自动选择 R2 或 Matrix 通道）

        R2 模式：上传到 R2 → 发送含链接的 Markdown 文本
        Matrix 模式：上传到 Matrix 媒体仓库 → 发送 m.file 事件
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"文件不存在，跳过发送: {file_path}")
            return

        if self._media_store:
            try:
                room_prefix = await self._matrix_client.get_r2_room_prefix(room_id)
                if not room_prefix:
                    raise RuntimeError("房间未配置 com.talk.r2_prefix")
                mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
                r2_uri = await self._media_store.upload(
                    path, room_prefix=room_prefix, mime=mime
                )
                kind = r2_protocol.media_kind_from_mime(mime)
                alt = caption or path.name
                md = r2_protocol.outbound_markdown_for_r2(kind, alt, r2_uri)
                public_url = self._media_store.resolve_url(r2_uri)

                if public_url:
                    msg = f"📎 {md}\n{public_url}"
                else:
                    msg = f"📎 {md}"

                await self._matrix_client.send_text(room_id, msg)

            except Exception as e:
                logger.error(f"R2 上传失败，回退到 Matrix: {e}")
                await self._matrix_client.send_file(room_id, file_path, caption)
        else:
            # Matrix 模式
            success = await self._matrix_client.send_file(room_id, file_path, caption)
            if success and caption:
                await self._matrix_client.send_text(room_id, caption)

    async def _archive_media_to_r2(self, room_id: str, content: str) -> None:
        """将消息中引用的媒体文件存档到 R2（后台操作，不影响主流程）"""
        if not self._media_store:
            return

        import re
        room_prefix = await self._matrix_client.get_r2_room_prefix(room_id)
        if not room_prefix:
            logger.debug("跳过 R2 存档：房间无有效 prefix")
            return

        # 解析 [image:path:mime] 标记
        matches = re.findall(r'\[image:(.+?):(.+?)\]', content)
        for file_path, mime in matches:
            try:
                path = Path(file_path)
                if path.exists():
                    r2_uri = await self._media_store.upload(
                        path, room_prefix=room_prefix, mime=mime
                    )
                    logger.info(f"媒体已存档到 R2: {path.name} → {r2_uri}")
            except Exception as e:
                logger.warning(f"R2 存档失败（不影响主流程）: {e}")

    async def _resolve_r2_markdown_links(self, content: str) -> str:
        """将消息中的 r2:// Markdown 链接下载到本地；图片在 pass_r2_images_to_llm 时转为 [image:path:mime]。

        与移动端对齐：按 object key 目录段与扩展名判断类型，不依赖 ?mime=。
        """
        matches = list(r2_protocol.iter_r2_markdown_links(content))
        if not matches:
            return content

        result = content
        for match in matches:
            alt_text = match.group("alt")
            r2_uri = match.group("uri")
            original = match.group(0)

            clean_uri = r2_protocol.strip_r2_query(r2_uri)
            parsed = r2_protocol.parse_r2_uri(clean_uri)
            if not parsed:
                continue
            _bucket, object_key = parsed
            kind = r2_protocol.infer_media_kind_from_object_key(object_key)
            mime_guess = r2_protocol.guess_mime_from_object_key(object_key)

            local_path = await self._download_r2_attachment(clean_uri)

            if not local_path:
                replacement = f"[附件无法加载: {alt_text or object_key}]"
                result = result.replace(original, replacement)
                logger.warning(f"r2:// 下载失败，退化为文字描述: {clean_uri}")
                continue

            if kind == "image" and self._config.pass_r2_images_to_llm:
                tag = f"[image:{local_path}:{mime_guess}]"
                replacement = f"{tag} {alt_text}" if alt_text else tag
                result = result.replace(original, replacement)
                logger.info(f"r2:// 图片已解析: {alt_text} → {local_path}")
            else:
                replacement = (
                    f"[用户附件:{kind} 名称:{alt_text or object_key} "
                    f"本地路径:{local_path} 类型:{mime_guess}]"
                )
                result = result.replace(original, replacement)

        return result

    async def _download_r2_attachment(self, r2_uri: str) -> str | None:
        """从 r2:// URI 下载文件到本地缓存。

        优先使用 R2MediaStore（已配置时），否则尝试 public_url 直接下载。
        """
        clean_uri = r2_protocol.strip_r2_query(r2_uri)

        if self._media_store:
            local_path = await self._media_store.download(clean_uri)
            if local_path:
                return str(local_path)

        if self._config._r2_config and self._config._r2_config.public_url:
            parsed = r2_protocol.parse_r2_uri(clean_uri)
            key = parsed[1] if parsed else None
            if key:
                url = f"{self._config._r2_config.public_url.rstrip('/')}/{key}"
                return await self._http_download(url, key)

        logger.warning(f"无法下载 r2://（未配置 R2 凭据和 public_url）: {r2_uri}")
        return None

    async def _http_download(self, url: str, object_key: str) -> str | None:
        """通过 HTTP 下载到与 R2 相同的本地缓存路径（去掉 room prefix 后分层）。"""
        import aiohttp

        if ".." in object_key.split("/") or object_key.startswith("/"):
            logger.error(f"非法 object key，拒绝缓存: {object_key!r}")
            return None

        cache_root = self._config.resolved_media_cache_root
        local_path = cache_root / r2_protocol.local_cache_relative_path(object_key)
        if local_path.exists():
            logger.debug(f"HTTP 缓存命中: {object_key}")
            return str(local_path)

        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        import aiofiles

                        async with aiofiles.open(local_path, "wb") as f:
                            await f.write(await resp.read())
                        return str(local_path)
                    else:
                        logger.error(f"HTTP 下载失败 [{resp.status}]: {url}")
                        if local_path.exists():
                            local_path.unlink()
                        return None
        except Exception as e:
            logger.error(f"HTTP 下载异常: {e}")
            if local_path.exists():
                local_path.unlink()
            return None


def _replace_file_links_with_r2(
    reply: str, fp: str, r2_uri: str, path: Path
) -> str:
    """将回复中的 file:// 引用替换为与移动端一致的 r2:// Markdown。"""
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    kind = r2_protocol.media_kind_from_mime(mime)
    pat_img = re.compile(r"!\[([^\]]*)\]\(" + re.escape(f"file://{fp}") + r"\)")
    m = pat_img.search(reply)
    if m:
        alt = m.group(1)
        md = r2_protocol.outbound_markdown_for_r2(kind, alt, r2_uri)
        return reply.replace(m.group(0), md)
    pat_link = re.compile(r"\[([^\]]*)\]\(" + re.escape(f"file://{fp}") + r"\)")
    m2 = pat_link.search(reply)
    if m2:
        alt = m2.group(1)
        md = r2_protocol.outbound_markdown_for_r2(kind, alt, r2_uri)
        return reply.replace(m2.group(0), md)
    return reply.replace(
        f"file://{fp}",
        r2_protocol.outbound_markdown_for_r2(kind, path.name, r2_uri),
    )

