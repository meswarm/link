"""安全检查器 — 拦截危险命令和参数"""

import logging
import re

logger = logging.getLogger(__name__)

# 危险命令模式（CLI 工具执行前检查）
DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    # 删除操作
    (r"\brm\s+(-[a-zA-Z]*[rfR])", "检测到危险的递归/强制删除命令"),
    (r"\brm\s+.*(?:/\*|~|\$HOME|\$\{HOME\})", "检测到危险的删除路径"),
    (r"\brmdir\s+/", "检测到删除根目录下的目录"),
    # 格式化/磁盘操作
    (r"\bmkfs\b", "检测到磁盘格式化命令"),
    (r"\bfdisk\b", "检测到磁盘分区命令"),
    (r"\bdd\s+.*\bof=/dev/", "检测到直接写入设备的 dd 命令"),
    (r"\bformat\b", "检测到格式化命令"),
    # 系统破坏
    (r">\s*/dev/sd[a-z]", "检测到覆盖磁盘设备"),
    (r">\s*/dev/null.*<", "检测到危险的重定向"),
    (r":\(\)\{.*\|.*&\}", "检测到 fork bomb"),
    # 权限操作
    (r"\bchmod\s+(-[a-zA-Z]*\s+)?777\s+/", "检测到对根目录设置 777 权限"),
    (r"\bchown\s+.*\s+/\s", "检测到对根目录更改所有者"),
    # 系统控制
    (r"\bshutdown\b", "检测到关机命令"),
    (r"\breboot\b", "检测到重启命令"),
    (r"\binit\s+[06]\b", "检测到切换运行级别命令"),
    (r"\bsystemctl\s+(poweroff|halt|reboot)", "检测到系统电源控制命令"),
    # 危险覆盖
    (r">\s*/etc/", "检测到覆盖系统配置文件"),
    (r"\bmv\s+.*\s+/dev/null", "检测到将文件移至 /dev/null"),
    # 网络下载执行
    (r"\bcurl\b.*\|\s*(bash|sh)\b", "检测到从网络下载并直接执行脚本"),
    (r"\bwget\b.*\|\s*(bash|sh)\b", "检测到从网络下载并直接执行脚本"),
]

# 编译正则（提升性能）
_COMPILED_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(pattern, re.IGNORECASE), reason)
    for pattern, reason in DANGEROUS_PATTERNS
]


def check_command_safety(command: str) -> tuple[bool, str]:
    """检查命令是否安全

    Args:
        command: 要执行的命令字符串

    Returns:
        (is_safe, reason) — 如果安全返回 (True, "")，
        否则返回 (False, "拦截原因")
    """
    for pattern, reason in _COMPILED_PATTERNS:
        if pattern.search(command):
            logger.warning(f"危险命令被拦截: {reason}\n  命令: {command}")
            return False, reason

    return True, ""


def check_param_safety(params: dict) -> tuple[bool, str]:
    """检查工具调用参数中是否包含危险内容

    主要检查参数值中的路径注入、命令注入等。

    Args:
        params: 工具调用参数

    Returns:
        (is_safe, reason)
    """
    for key, value in params.items():
        if not isinstance(value, str):
            continue
        # 检查命令注入（分号、反引号、管道到危险命令）
        if re.search(r";\s*(rm|mkfs|dd|shutdown|reboot)\b", value, re.IGNORECASE):
            reason = f"参数 '{key}' 中检测到命令注入"
            logger.warning(f"危险参数被拦截: {reason}\n  值: {value}")
            return False, reason
        # 检查反引号执行
        if re.search(r"`[^`]*`", value):
            reason = f"参数 '{key}' 中检测到反引号命令执行"
            logger.warning(f"危险参数被拦截: {reason}\n  值: {value}")
            return False, reason
        # 检查 $() 命令替换
        if re.search(r"\$\([^)]*\)", value):
            reason = f"参数 '{key}' 中检测到命令替换"
            logger.warning(f"危险参数被拦截: {reason}\n  值: {value}")
            return False, reason

    return True, ""


def check_path_in_workdir(params: dict, work_dir: str) -> tuple[bool, str]:
    """检查参数中的路径是否在工作目录内

    防止通过 ../、绝对路径等方式逃逸出工作目录。

    Args:
        params: 工具调用参数
        work_dir: 允许的工作目录（绝对路径）

    Returns:
        (is_safe, reason)
    """
    from pathlib import Path

    work_path = Path(work_dir).resolve()

    for key, value in params.items():
        if not isinstance(value, str):
            continue

        # 检查看起来像路径的参数值
        if "/" in value or ".." in value:
            # 尝试解析为路径
            try:
                target = Path(value)
                # 相对路径：基于工作目录解析
                if not target.is_absolute():
                    target = (work_path / target).resolve()
                else:
                    target = target.resolve()

                # 检查是否在工作目录内
                if not str(target).startswith(str(work_path)):
                    reason = (
                        f"参数 '{key}' 的路径 '{value}' "
                        f"超出工作目录 '{work_dir}'"
                    )
                    logger.warning(f"路径逃逸被拦截: {reason}")
                    return False, reason
            except (ValueError, OSError):
                pass

    return True, ""

