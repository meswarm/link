"""Webhook 接收器 — 接收外部工具的主动推送"""

import json
import logging
from typing import Any, Callable, Awaitable

from aiohttp import web

from link.config import WebhookConfig

logger = logging.getLogger(__name__)

# Webhook 回调类型：(endpoint_path, data, urgent) -> None
WebhookCallback = Callable[[str, dict[str, Any], bool], Awaitable[None]]


class WebhookReceiver:
    """轻量 HTTP 服务器，接收外部工具的 webhook 推送

    接收到推送后，通过回调通知 Agent：
    - urgent=True: 直接发送给用户（bypass LLM）
    - urgent=False: 经 LLM 整理后发送
    """

    def __init__(self, config: WebhookConfig, callback: WebhookCallback):
        self._config = config
        self._callback = callback
        self._app = web.Application()
        self._runner: web.AppRunner | None = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        """根据配置注册 webhook 端点"""
        for endpoint in self._config.endpoints:
            urgent = endpoint.urgent

            async def handler(
                request: web.Request, _urgent: bool = urgent, _path: str = endpoint.path
            ) -> web.Response:
                try:
                    if request.content_type == "application/json":
                        data = await request.json()
                    else:
                        text = await request.text()
                        data = {"raw": text}

                    logger.info(
                        f"Webhook 收到推送: {_path} (urgent={_urgent})"
                    )
                    await self._callback(_path, data, _urgent)
                    return web.json_response({"status": "ok"})

                except Exception as e:
                    logger.error(f"Webhook 处理失败: {e}")
                    return web.json_response(
                        {"status": "error", "message": str(e)}, status=500
                    )

            self._app.router.add_post(endpoint.path, handler)
            logger.info(
                f"Webhook 端点已注册: POST {endpoint.path} (urgent={urgent})"
            )

    async def start(self) -> None:
        """启动 webhook HTTP 服务器"""
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(
            self._runner, self._config.host, self._config.port
        )
        await site.start()
        logger.info(
            f"Webhook 服务器已启动: {self._config.host}:{self._config.port}"
        )

    async def stop(self) -> None:
        """停止 webhook HTTP 服务器"""
        if self._runner:
            await self._runner.cleanup()
            logger.info("Webhook 服务器已停止")
