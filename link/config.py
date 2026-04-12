"""Link 配置加载与数据模型

配置分三层：
- 全局基础设施：.env（Matrix 服务器地址等）
- 模型配置：models/*.yaml（每个模型一份）
- 工具配置：agents/*.yaml（每个工具一份）
"""

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 模型配置目录（项目根目录下的 models/）
_PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = _PROJECT_ROOT / "models"


# ═══════════════════════════════════════
# 模型配置
# ═══════════════════════════════════════

class ModelConfig(BaseModel):
    """LLM 模型配置"""

    name: str
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.7
    enable_thinking: bool = False
    vision: bool = False  # 是否支持图像输入（多模态）


def load_model_config(model_name: str) -> ModelConfig:
    """从 models/ 目录加载模型配置

    Args:
        model_name: 模型引用名（对应 models/<name>.yaml）

    Returns:
        ModelConfig 实例
    """
    model_path = MODELS_DIR / f"{model_name}.yaml"
    if not model_path.exists():
        available = [f.stem for f in MODELS_DIR.glob("*.yaml") if not f.stem.startswith("_")]
        raise FileNotFoundError(
            f"模型配置不存在: {model_path}\n"
            f"可用模型: {available}"
        )

    with open(model_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    resolved = _resolve_env_recursive(raw)
    logger.info(f"已加载模型配置: {model_name} ({resolved.get('model', '?')})")
    return ModelConfig(**resolved)


def list_available_models() -> list[str]:
    """列出所有可用的模型配置"""
    if not MODELS_DIR.exists():
        return []
    return sorted(f.stem for f in MODELS_DIR.glob("*.yaml") if not f.stem.startswith("_"))


# ═══════════════════════════════════════
# 工具配置模型
# ═══════════════════════════════════════

class ToolParamConfig(BaseModel):
    """工具参数定义"""

    type: str = "string"
    description: str = ""
    required: bool = False
    default: Any = None
    enum: list[str] | None = None


class ToolConfig(BaseModel):
    """单个工具配置"""

    type: str  # "api", "cli", "builtin"
    name: str
    description: str
    # API 工具专用
    endpoint: str | None = None
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    body_template: dict[str, Any] | None = None
    # CLI 工具专用
    command: str | None = None
    # 通用
    parameters: dict[str, ToolParamConfig] = Field(default_factory=dict)


class WebhookEndpointConfig(BaseModel):
    """Webhook 端点配置"""

    path: str
    urgent: bool = False
    description: str = ""


class WebhookConfig(BaseModel):
    """Webhook 接收配置

    当配置了 endpoints 时自动启用，无需手动设置 enabled。
    """

    host: str = "0.0.0.0"
    port: int = 9001
    endpoints: list[WebhookEndpointConfig] = Field(default_factory=list)

    @property
    def enabled(self) -> bool:
        """有端点配置时自动启用"""
        return len(self.endpoints) > 0


class ContextHookConfig(BaseModel):
    """预置上下文钩子配置

    在 LLM 调用前自动执行指定工具，
    将结果注入到 prompt 的 {name} 占位符中。

    refresh 策略:
      once   — 首次对话时获取，后续使用缓存（默认）
      always — 每条消息都重新获取（适合时间等快速变化的数据）
    """

    name: str          # 占位符名称（对应 prompt 中的 {name}）
    tool: str          # 要调用的工具名称
    params: dict[str, Any] = Field(default_factory=dict)  # 工具参数（可选）
    refresh: str = "once"  # 刷新策略: "once" | "always"


# ═══════════════════════════════════════
# Agent 完整配置
# ═══════════════════════════════════════

class AgentConfig(BaseModel):
    """Agent 完整配置（运行时使用）"""

    # 基本信息
    name: str = "Link Agent"
    description: str = ""
    prompt: str = "你是一个智能助手。"

    # 模型引用名（指向 models/<name>.yaml）
    model: str = "qwen-plus"

    # Matrix
    homeserver: str = ""
    matrix_user: str = ""
    matrix_password: str = ""
    rooms: list[str] = Field(default_factory=list)

    # LLM 参数（可覆盖模型配置中的默认值）
    temperature: float | None = None
    max_history: int = 20
    enable_thinking: bool | None = None
    vision: bool | None = None  # 是否启用图像分析（None=跟随模型, false=关闭, true=强制开启）

    # 工具
    tools: list[ToolConfig] = Field(default_factory=list)
    skills_dir: str | None = None
    work_dir: str | None = None
    webhook: WebhookConfig = Field(default_factory=WebhookConfig)

    # 预置上下文钩子
    context: list[ContextHookConfig] = Field(default_factory=list)
    context_ttl: int = 30  # 上下文缓存过期时间（分钟），超过后视为新会话

    # ── 运行时填充（由 load_config 设置）──
    _model_config: ModelConfig | None = None

    model_config = {"arbitrary_types_allowed": True}

    @property
    def llm_base_url(self) -> str:
        return self._model_config.base_url if self._model_config else ""

    @property
    def llm_api_key(self) -> str:
        return self._model_config.api_key if self._model_config else ""

    @property
    def llm_model(self) -> str:
        return self._model_config.model if self._model_config else self.model

    @property
    def resolved_temperature(self) -> float:
        if self.temperature is not None:
            return self.temperature
        return self._model_config.temperature if self._model_config else 0.7

    @property
    def resolved_enable_thinking(self) -> bool:
        if self.enable_thinking is not None:
            return self.enable_thinking
        return self._model_config.enable_thinking if self._model_config else False

    @property
    def resolved_vision(self) -> bool:
        """是否启用图像分析：Agent 配置优先，否则跟随模型能力"""
        if self.vision is not None:
            return self.vision
        return self._model_config.vision if self._model_config else False


# ═══════════════════════════════════════
# 环境变量解析
# ═══════════════════════════════════════

def _resolve_env_vars(value: str) -> str:
    """解析配置中的环境变量引用 ${VAR_NAME}"""

    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            raise ValueError(f"环境变量 {var_name} 未设置")
        return env_value

    return re.sub(r"\$\{(\w+)}", _replace, value)


def _resolve_env_recursive(obj: Any) -> Any:
    """递归解析所有字符串中的环境变量"""
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    elif isinstance(obj, dict):
        return {k: _resolve_env_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_recursive(item) for item in obj]
    return obj


# ═══════════════════════════════════════
# 配置加载入口
# ═══════════════════════════════════════

def load_config(config_path: str | Path) -> AgentConfig:
    """加载 Agent 配置

    合并策略：
    1. 从 .env 读取全局默认值
    2. 从 YAML 读取工具配置
    3. 从 models/ 加载模型配置
    4. Agent YAML 中的参数可覆盖模型默认值
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # 解析环境变量引用
    resolved = _resolve_env_recursive(raw)

    # 从 .env 提供默认值
    defaults = {
        "homeserver": os.environ.get("MATRIX_HOMESERVER", ""),
    }

    # 合并
    merged = {**defaults, **resolved}
    config = AgentConfig(**merged)

    # 加载模型配置
    try:
        model_cfg = load_model_config(config.model)
        config._model_config = model_cfg
    except FileNotFoundError as e:
        logger.error(f"模型加载失败: {e}")
        raise

    return config
