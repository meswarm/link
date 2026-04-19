"""R2 带外媒体存储层 — 管理 R2/S3 上传、下载与本地缓存"""

import logging
import time
from pathlib import Path

from link.config import R2Config
from link import r2_protocol

logger = logging.getLogger(__name__)


def _human_size(size_bytes: int) -> str:
    """将字节数转为可读格式"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


class R2MediaStore:
    """R2 带外媒体存储层

    负责：
    - 上传：本地文件 → R2，返回 r2:// 引用
    - 下载：r2:// 引用 → 本地缓存文件
    - 缓存：已下载文件持久化到配置的缓存根目录（与 object key 分层），避免重复拉取

    不配置 R2 时不应实例化此类（由 Agent 层控制）。
    """

    def __init__(self, config: R2Config, media_cache_root: Path):
        self._config = config
        self._cache_dir = Path(media_cache_root)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # 惰性导入 aioboto3（仅 R2 模式下才需要）
        try:
            import aioboto3 as _aioboto3
        except ImportError:
            raise ImportError(
                "media_storage='r2' 需要安装 aioboto3。\n"
                "请运行: pip install aioboto3\n"
                "若使用 pipx 安装的 ltool: pipx inject link aioboto3"
            ) from None

        self._session = _aioboto3.Session(
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
        )
        logger.info(
            f"R2MediaStore 已初始化: "
            f"endpoint={config.endpoint}, "
            f"bucket={config.bucket}, "
            f"cache={self._cache_dir}"
        )

    # ─── 上传 ───────────────────────

    async def upload(
        self,
        local_path: Path | str,
        *,
        room_prefix: str,
        mime: str,
    ) -> str:
        """上传文件到 R2（与移动端一致的 object key：prefix/dir/ts-name）

        Args:
            local_path: 本地文件路径
            room_prefix: 房间共享前缀（来自 Matrix state com.talk.r2_prefix）
            mime: 用于 Content-Type 与目录 imgs/videos/audios/files

        Returns:
            r2://bucket/key 格式的引用（无查询参数）
        """
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"文件不存在: {local_path}")

        key = r2_protocol.build_object_key(
            room_prefix,
            mime,
            local_path.name,
        )

        file_size = local_path.stat().st_size
        logger.info(f"正在上传到 R2: {local_path.name} ({_human_size(file_size)})")

        extra = {"ContentType": mime}

        async with self._session.client(
            "s3", endpoint_url=self._config.endpoint
        ) as s3:
            await s3.upload_file(
                str(local_path),
                self._config.bucket,
                key,
                ExtraArgs=extra,
            )

        r2_uri = f"r2://{self._config.bucket}/{key}"
        logger.info(f"上传完成: {r2_uri}")

        # 同时缓存到本地（key 可含子目录）
        cache_path = self._cache_dir / key
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if not cache_path.exists():
            import shutil
            shutil.copy2(str(local_path), str(cache_path))

        return r2_uri

    # ─── 下载 ───────────────────────

    async def download(self, r2_uri: str) -> Path | None:
        """下载 R2 文件到本地缓存

        优先使用本地缓存，未命中则从 R2 拉取。

        Args:
            r2_uri: r2://bucket/key 格式的引用

        Returns:
            本地文件路径，失败返回 None
        """
        key = self._parse_key(r2_uri)
        if not key:
            logger.error(f"无效的 R2 URI: {r2_uri}")
            return None

        # 缓存命中
        cache_path = self._cache_dir / key
        if cache_path.exists():
            logger.debug(f"缓存命中: {key}")
            return cache_path

        # 从 R2 下载
        logger.info(f"正在从 R2 下载: {key}")
        try:
            async with self._session.client(
                "s3", endpoint_url=self._config.endpoint
            ) as s3:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                await s3.download_file(self._config.bucket, key, str(cache_path))

            file_size = cache_path.stat().st_size
            logger.info(f"下载完成: {key} ({_human_size(file_size)})")
            return cache_path

        except Exception as e:
            logger.error(f"R2 下载失败 [{key}]: {e}")
            if cache_path.exists():
                cache_path.unlink()
            return None

    # ─── URL 解析 ───────────────────

    def resolve_url(self, r2_uri: str) -> str | None:
        """将 r2:// 引用转为公开 HTTP URL

        仅当配置了 public_url 时返回，否则返回 None。
        """
        if not self._config.public_url:
            return None
        key = self._parse_key(r2_uri)
        if not key:
            return None
        base = self._config.public_url.rstrip("/")
        return f"{base}/{key}"

    # ─── 工具方法 ───────────────────

    @staticmethod
    def _parse_key(r2_uri: str) -> str | None:
        """从 r2://bucket/key 解析出 key 部分（忽略 query）"""
        parsed = r2_protocol.parse_r2_uri(r2_uri)
        if not parsed:
            return None
        return parsed[1]

    @staticmethod
    def is_r2_uri(text: str) -> bool:
        """检查文本中是否包含 r2:// 引用"""
        return "r2://" in text

    def extract_r2_uris(self, text: str) -> list[str]:
        """从文本中提取所有 r2:// 引用"""
        import re
        return re.findall(r'r2://\S+', text)
