"""工具基类定义"""

from abc import ABC, abstractmethod
from typing import Any


class ToolBase(ABC):
    """所有工具的抽象基类

    每个工具需要实现：
    1. definition 属性 — 返回 OpenAI Function Calling 格式的工具定义
    2. execute 方法 — 执行工具操作并返回结果字符串
    """

    @property
    @abstractmethod
    def definition(self) -> dict[str, Any]:
        """返回 OpenAI 格式的 tool 定义

        返回格式:
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "工具描述",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        }
        """

    @property
    def name(self) -> str:
        """工具名称，从 definition 中提取"""
        return self.definition["function"]["name"]

    @abstractmethod
    async def execute(self, **params: Any) -> str:
        """执行工具操作

        Args:
            **params: 工具参数，由 LLM Function Calling 传入

        Returns:
            工具执行结果的字符串表示
        """
