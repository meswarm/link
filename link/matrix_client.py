"""Matrix 连接层 — 管理 Matrix 连接、消息收发（含文件）"""

import logging
import mimetypes
import time
from pathlib import Path
from typing import Callable, Awaitable, Any

import aiofiles
from nio import (
    AsyncClient,
    LoginResponse,
    RoomMessageText,
    RoomMessageImage,
    RoomMessageVideo,
    RoomMessageAudio,
    RoomMessageFile,
    DownloadResponse,
    UploadResponse,
)

logger = logging.getLogger(__name__)

# 消息回调类型：(room_id, sender, body) -> None
MessageCallback = Callable[[str, str, str], Awaitable[None]]


def _human_size(size_bytes: int) -> str:
    """将字节数转为可读格式"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


# 媒体消息类型映射
_MEDIA_EVENTS = (RoomMessageImage, RoomMessageVideo, RoomMessageAudio, RoomMessageFile)
_MEDIA_TYPE_NAMES = {
    RoomMessageImage: "image",
    RoomMessageVideo: "video",
    RoomMessageAudio: "audio",
    RoomMessageFile: "file",
}


class MatrixClient:
    """Matrix 连接客户端

    基于 matrix-nio 的异步客户端封装，负责：
    - 登录和保持同步
    - 接收并分发文本和媒体消息
    - 发送文本消息和文件
    """

    def __init__(
        self,
        homeserver: str,
        user: str,
        password: str,
        rooms: list[str],
        download_dir: str | None = None,
    ):
        self._user = user
        self._password = password
        self._rooms = rooms
        self._client = AsyncClient(homeserver, user)
        self._homeserver = homeserver
        self._message_callback: MessageCallback | None = None
        self._first_sync_done = False
        self._download_dir = Path(download_dir) if download_dir else None
        self._should_stop = False

    def on_message(self, callback: MessageCallback) -> None:
        """注册消息回调"""
        self._message_callback = callback

    async def login(self) -> bool:
        """登录 Matrix 服务器"""
        response = await self._client.login(self._password)
        if isinstance(response, LoginResponse):
            logger.info(
                f"Matrix 登录成功: {self._user} "
                f"(device: {response.device_id})"
            )
            return True
        else:
            logger.error(f"Matrix 登录失败: {response}")
            return False

    async def _join_rooms(self) -> None:
        """加入配置中指定的房间"""
        for room_id in self._rooms:
            try:
                result = await self._client.join(room_id)
                logger.info(f"已加入房间: {room_id} -> {result}")
            except Exception as e:
                logger.error(f"加入房间 {room_id} 失败: {e}")

    # ─── 消息接收 ───────────────────────

    async def _on_room_message(self, room, event) -> None:
        """处理收到的文本消息"""
        if event.sender == self._client.user_id:
            return
        if not self._first_sync_done:
            return

        room_id = room.room_id
        sender = event.sender
        body = event.body

        logger.info(f"收到消息: [{room_id}] {sender}: {body}")

        if self._message_callback:
            try:
                await self._message_callback(room_id, sender, body)
            except Exception as e:
                logger.error(f"消息处理回调异常: {e}")

    async def _on_media_message(self, room, event) -> None:
        """处理收到的媒体消息（图片/视频/音频/文件）"""
        if event.sender == self._client.user_id:
            return
        if not self._first_sync_done:
            return

        room_id = room.room_id
        sender = event.sender
        media_type = _MEDIA_TYPE_NAMES.get(type(event), "file")
        filename = getattr(event, "body", "unknown")

        # 获取文件信息
        file_info = getattr(event, "source", {}).get("content", {}).get("info", {})
        file_size = file_info.get("size", 0)
        mimetype = file_info.get("mimetype", "application/octet-stream")

        logger.info(
            f"收到媒体: [{room_id}] {sender}: "
            f"{media_type} {filename} ({_human_size(file_size)})"
        )

        # 下载到本地
        local_path = await self._download_media(event, filename)

        if local_path and self._message_callback:
            # 图片类型：传递特殊标记，让 LLM 引擎构建多模态消息
            if mimetype.startswith("image/"):
                file_desc = (
                    f"[image:{local_path}:{mimetype}]"
                )
                # 如果用户在图片上加了文字说明（body 不是文件名时）
                user_text = getattr(event, "body", "")
                if user_text and user_text != filename:
                    file_desc += f" {user_text}"
            else:
                # 非图片文件：纯文本描述
                file_desc = (
                    f"[用户发送了{media_type}] "
                    f"文件名: {filename}, "
                    f"类型: {mimetype}, "
                    f"大小: {_human_size(file_size)}, "
                    f"本地路径: {local_path}"
                )
            try:
                await self._message_callback(room_id, sender, file_desc)
            except Exception as e:
                logger.error(f"媒体消息处理回调异常: {e}")

    async def _download_media(self, event, filename: str) -> str | None:
        """下载媒体文件到本地 inbox 目录

        Returns:
            本地文件路径，失败返回 None
        """
        if not self._download_dir:
            logger.warning("未配置下载目录 (work_dir)，跳过文件下载")
            return None

        # 获取 mxc:// URL
        mxc_url = getattr(event, "url", None)
        if not mxc_url:
            logger.error("媒体消息中没有 URL")
            return None

        # 创建 inbox 目录
        inbox = self._download_dir / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名
        timestamp = int(time.time())
        safe_name = filename.replace("/", "_").replace("..", "_")
        local_path = inbox / f"{timestamp}_{safe_name}"

        try:
            response = await self._client.download(mxc_url)

            if isinstance(response, DownloadResponse):
                async with aiofiles.open(local_path, "wb") as f:
                    await f.write(response.body)
                logger.info(f"文件已下载: {local_path} ({_human_size(len(response.body))})")
                return str(local_path)
            else:
                logger.error(f"文件下载失败: {response}")
                return None
        except Exception as e:
            logger.error(f"文件下载异常: {e}")
            return None

    # ─── 消息发送 ───────────────────────

    async def send_text(self, room_id: str, text: str) -> None:
        """发送文本消息"""
        try:
            response = await self._client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": text,
                },
            )
            # 检查是否发送成功
            from nio import RoomSendError
            if isinstance(response, RoomSendError):
                logger.error(f"消息发送失败: {response.message}")
            else:
                logger.info(f"消息已发送到 {room_id}")
        except Exception as e:
            logger.error(f"发送消息异常: {e}")

    async def set_typing(self, room_id: str, typing: bool, timeout: int = 30000) -> None:
        """设置「正在输入」指示器

        Args:
            room_id: 房间 ID
            typing: True=显示正在输入, False=取消
            timeout: 自动取消时间（毫秒），防止卡死后一直显示
        """
        try:
            await self._client.room_typing(room_id, typing, timeout=timeout)
        except Exception:
            pass  # 不影响主流程

    async def send_notice(self, room_id: str, text: str) -> None:
        """发送通知消息（不触发通知提醒）"""
        try:
            await self._client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.notice",
                    "body": text,
                },
            )
        except Exception as e:
            logger.error(f"发送通知失败: {e}")

    async def send_file(self, room_id: str, file_path: str, caption: str = "") -> bool:
        """上传并发送文件到 Matrix 房间

        自动根据文件类型选择消息类型（图片/视频/音频/文件）。

        Args:
            room_id: 目标房间
            file_path: 本地文件路径
            caption: 可选的说明文字

        Returns:
            是否成功
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"文件不存在: {file_path}")
            return False

        # 读取文件内容
        async with aiofiles.open(path, "rb") as f:
            data = await f.read()

        file_size = len(data)
        mimetype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        filename = path.name

        logger.info(f"正在上传文件: {filename} ({_human_size(file_size)}, {mimetype})")

        try:
            # 上传到 Matrix 媒体仓库
            upload_resp, _keys = await self._client.upload(
                data,
                content_type=mimetype,
                filename=filename,
            )

            if not isinstance(upload_resp, UploadResponse):
                logger.error(f"文件上传失败: {upload_resp}")
                return False

            mxc_url = upload_resp.content_uri

            # 根据文件类型选择 msgtype
            msgtype = self._detect_msgtype(mimetype)

            content: dict[str, Any] = {
                "msgtype": msgtype,
                "body": caption or filename,
                "url": mxc_url,
                "info": {
                    "mimetype": mimetype,
                    "size": file_size,
                },
            }

            # 图片和视频可以带宽高信息（暂不实现）
            if msgtype == "m.image":
                content["info"]["w"] = 0
                content["info"]["h"] = 0

            await self._client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content=content,
            )

            logger.info(f"文件已发送到 {room_id}: {filename}")
            return True

        except Exception as e:
            logger.error(f"发送文件异常: {e}")
            return False

    @staticmethod
    def _detect_msgtype(mimetype: str) -> str:
        """根据 MIME 类型判断 Matrix 消息类型"""
        if mimetype.startswith("image/"):
            return "m.image"
        elif mimetype.startswith("video/"):
            return "m.video"
        elif mimetype.startswith("audio/"):
            return "m.audio"
        else:
            return "m.file"

    # ─── 同步控制 ───────────────────────

    async def start_sync(self) -> None:
        """开始同步，持续监听消息"""
        # 注册文本消息回调
        self._client.add_event_callback(self._on_room_message, RoomMessageText)
        # 注册媒体消息回调
        for event_type in _MEDIA_EVENTS:
            self._client.add_event_callback(self._on_media_message, event_type)

        await self._join_rooms()

        logger.info("执行首次同步...")
        await self._client.sync(timeout=10000)
        self._first_sync_done = True
        logger.info("首次同步完成，开始监听新消息")

        # 使用短超时轮询，以便检查 _should_stop 标志
        while not self._should_stop:
            try:
                await self._client.sync(timeout=5000)
            except Exception as e:
                if self._should_stop:
                    break
                logger.error(f"Matrix 同步异常: {e}")
                break

    async def stop(self) -> None:
        """停止同步并关闭连接"""
        self._should_stop = True
        try:
            await self._client.close()
            logger.info("Matrix 连接已关闭")
        except Exception as e:
            logger.error(f"关闭 Matrix 连接异常: {e}")

    @property
    def user_id(self) -> str:
        return self._client.user_id or self._user

    @property
    def rooms(self) -> list[str]:
        return self._rooms
