"""内置工具 — 用于测试和通用功能"""

import datetime
import platform
from typing import Any

from link.tools.base import ToolBase


class GetTimeTool(ToolBase):
    """获取当前时间"""

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "获取当前的日期和时间",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

    async def execute(self, **params: Any) -> str:
        now = datetime.datetime.now()
        return now.strftime("%Y年%m月%d日 %H:%M:%S (星期%w)")


class SystemInfoTool(ToolBase):
    """获取系统信息"""

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_system_info",
                "description": "获取当前系统的基本信息，包括操作系统、主机名等",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

    async def execute(self, **params: Any) -> str:
        info = {
            "系统": platform.system(),
            "主机名": platform.node(),
            "版本": platform.version(),
            "架构": platform.machine(),
            "Python": platform.python_version(),
        }
        return "\n".join(f"{k}: {v}" for k, v in info.items())
