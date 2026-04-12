"""工具注册中心"""

import logging
from typing import Any

from link.config import ToolConfig
from link.tools.base import ToolBase
from link.tools.api_tool import APITool
from link.tools.cli_tool import CLITool
from link.tools.builtin import GetTimeTool, SystemInfoTool

logger = logging.getLogger(__name__)

# 工具类型到适配器类的映射
TOOL_TYPE_MAP: dict[str, type[ToolBase]] = {
    "api": APITool,
    "cli": CLITool,
}

# 内置工具映射：name -> 工具类（无需配置参数）
BUILTIN_TOOLS: dict[str, type[ToolBase]] = {
    "get_current_time": GetTimeTool,
    "get_system_info": SystemInfoTool,
}


class ToolRegistry:
    """工具注册中心

    管理所有已注册的工具，提供：
    - 从配置批量创建和注册工具
    - 按名称查找工具
    - 导出所有工具的 OpenAI Function Calling 定义
    """

    def __init__(self):
        self._tools: dict[str, ToolBase] = {}

    def register(self, tool: ToolBase) -> None:
        """注册一个工具实例"""
        if tool.name in self._tools:
            logger.warning(f"工具 {tool.name} 已存在，将被覆盖")
        self._tools[tool.name] = tool
        logger.info(f"已注册工具: {tool.name}")

    def get_tool(self, name: str) -> ToolBase | None:
        """按名称获取工具"""
        return self._tools.get(name)

    def get_all_definitions(self) -> list[dict[str, Any]]:
        """获取所有工具的 OpenAI Function Calling 定义"""
        return [tool.definition for tool in self._tools.values()]

    def has_tools(self) -> bool:
        """是否注册了任何工具"""
        return len(self._tools) > 0

    @property
    def tool_names(self) -> list[str]:
        """获取所有已注册的工具名称"""
        return list(self._tools.keys())

    async def execute_tool(self, tool_name: str, **params: Any) -> str:
        """执行指定工具

        Args:
            tool_name: 工具名称
            **params: 工具参数

        Returns:
            工具执行结果字符串
        """
        tool = self.get_tool(tool_name)
        if tool is None:
            return f"错误: 未找到工具 '{tool_name}'"

        logger.info(f"执行工具: {tool_name}, 参数: {params}")
        result = await tool.execute(**params)
        logger.info(f"工具 {tool_name} 执行完成")
        return result

    @classmethod
    def from_configs(cls, tool_configs: list[ToolConfig], work_dir: str | None = None) -> "ToolRegistry":
        """从配置列表批量创建工具并注册

        Args:
            tool_configs: 工具配置列表
            work_dir: CLI 工具的工作目录

        Returns:
            包含所有工具的 ToolRegistry 实例
        """
        registry = cls()

        for config in tool_configs:
            if config.type == "builtin":
                # 内置工具通过 name 查找
                builtin_class = BUILTIN_TOOLS.get(config.name)
                if builtin_class is None:
                    logger.error(
                        f"未知内置工具 '{config.name}'，"
                        f"可用: {list(BUILTIN_TOOLS.keys())}"
                    )
                    continue
                try:
                    tool = builtin_class()
                    registry.register(tool)
                except Exception as e:
                    logger.error(f"创建内置工具 '{config.name}' 失败: {e}")
                continue

            if config.type == "cli":
                # CLI 工具传入 work_dir
                try:
                    tool = CLITool(config, work_dir=work_dir)
                    registry.register(tool)
                except Exception as e:
                    logger.error(f"创建工具 '{config.name}' 失败: {e}")
                continue

            tool_class = TOOL_TYPE_MAP.get(config.type)
            if tool_class is None:
                logger.error(
                    f"未知工具类型 '{config.type}'，跳过工具 '{config.name}'"
                )
                continue

            try:
                tool = tool_class(config)
                registry.register(tool)
            except Exception as e:
                logger.error(f"创建工具 '{config.name}' 失败: {e}")

        return registry

