"""CLI 命令行工具适配器"""

import asyncio
import logging
import shlex
from typing import Any

from link.config import ToolConfig
from link.tools.base import ToolBase

logger = logging.getLogger(__name__)

# CLI 命令执行超时（秒）
DEFAULT_TIMEOUT = 30


class CLITool(ToolBase):
    """将命令行工具包装为 LLM 可调用的工具

    配置中的 command 支持 {param_name} 占位符，执行时替换为实际参数。
    """

    def __init__(self, config: ToolConfig, work_dir: str | None = None, timeout: int = DEFAULT_TIMEOUT):
        self._config = config
        self._work_dir = work_dir
        self._timeout = timeout
        self._build_definition()

    def _build_definition(self) -> None:
        """从配置构建 OpenAI tool definition"""
        properties = {}
        required = []

        for param_name, param_config in self._config.parameters.items():
            prop: dict[str, Any] = {
                "type": param_config.type,
                "description": param_config.description,
            }
            if param_config.enum:
                prop["enum"] = param_config.enum
            properties[param_name] = prop

            if param_config.required:
                required.append(param_name)

        self._definition = {
            "type": "function",
            "function": {
                "name": self._config.name,
                "description": self._config.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    @property
    def definition(self) -> dict[str, Any]:
        return self._definition

    async def execute(self, **params: Any) -> str:
        """执行 CLI 命令"""
        from link.safety import check_command_safety, check_param_safety, check_path_in_workdir

        command_template = self._config.command
        if not command_template:
            return "错误: 未配置 command"

        # 先检查参数安全性
        is_safe, reason = check_param_safety(params)
        if not is_safe:
            return (
                f"⛔ 安全拦截: {reason}。"
                f"请使用安全的参数重试，不要包含命令注入。"
            )

        # 安全地替换参数（对参数值做 shell 转义）
        safe_params = {k: shlex.quote(str(v)) for k, v in params.items()}
        try:
            command = command_template.format(**safe_params)
        except KeyError as e:
            return f"命令模板参数缺失: {e}"

        # 检查最终命令的安全性
        is_safe, reason = check_command_safety(command)
        if not is_safe:
            return (
                f"⛔ 安全拦截: {reason}。"
                f"该命令可能对系统造成破坏，已被阻止。"
                f"请换一种安全的方式完成任务。"
            )

        # 检查参数路径是否在工作目录内
        if self._work_dir:
            is_safe, reason = check_path_in_workdir(params, self._work_dir)
            if not is_safe:
                return (
                    f"⛔ 路径安全拦截: {reason}。"
                    f"命令只允许在工作目录内执行。"
                )

        logger.info(f"工具 {self.name} 执行命令: {command}"
                    + (f" (cwd: {self._work_dir})" if self._work_dir else ""))

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._work_dir,  # 在工作目录中执行
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )

            output = stdout.decode("utf-8", errors="replace").strip()
            errors = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                result = f"命令执行失败 (退出码 {proc.returncode})"
                if errors:
                    result += f"\n错误: {errors}"
                if output:
                    result += f"\n输出: {output}"
                return result

            # 截断过长输出
            if len(output) > 4000:
                output = output[:4000] + "\n... (输出已截断)"

            return output if output else "(无输出)"

        except asyncio.TimeoutError:
            return f"命令执行超时（{self._timeout}秒）"
        except Exception as e:
            error_msg = f"命令执行异常: {e}"
            logger.error(f"工具 {self.name} {error_msg}")
            return error_msg
