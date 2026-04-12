"""REST API 工具适配器"""

import json
import logging
from typing import Any

import aiohttp

from link.config import ToolConfig
from link.tools.base import ToolBase

logger = logging.getLogger(__name__)


class APITool(ToolBase):
    """将 REST API 端点包装为 LLM 可调用的工具"""

    def __init__(self, config: ToolConfig):
        self._config = config
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
        """执行 HTTP 请求调用 API"""
        endpoint = self._config.endpoint
        if not endpoint:
            return "错误: 未配置 API endpoint"

        method = self._config.method.upper()
        headers = {**self._config.headers}

        try:
            async with aiohttp.ClientSession() as session:
                kwargs: dict[str, Any] = {"headers": headers}

                if method == "GET":
                    kwargs["params"] = params
                else:
                    # POST/PUT/PATCH: 使用 body_template 或直接传参
                    if self._config.body_template:
                        body = {}
                        # 只保留 LLM 实际传入的参数，忽略未填充的模板字段
                        for key, template_val in self._config.body_template.items():
                            if key in params:
                                body[key] = params[key]
                            elif isinstance(template_val, str) and '{' in template_val:
                                # 跳过未填充的占位符（如 "{name}"）
                                continue
                            else:
                                # 保留硬编码的非占位符值
                                body[key] = template_val
                        # 添加模板中未定义但 LLM 传入的额外参数
                        for key, value in params.items():
                            if key not in body:
                                body[key] = value
                        kwargs["json"] = body
                    else:
                        kwargs["json"] = params
                    if "Content-Type" not in headers:
                        headers["Content-Type"] = "application/json"

                logger.debug(f"工具 {self.name} 请求: {method} {endpoint}, body={kwargs.get('json', kwargs.get('params', {}))}")

                async with session.request(method, endpoint, **kwargs) as resp:
                    status = resp.status
                    try:
                        result = await resp.json()
                        result_str = json.dumps(result, ensure_ascii=False, indent=2)
                    except (json.JSONDecodeError, aiohttp.ContentTypeError):
                        result_str = await resp.text()

                    if status >= 400:
                        return f"API 调用失败 (HTTP {status}): {result_str}"

                    logger.info(f"工具 {self.name} 执行成功: HTTP {status}")
                    return result_str

        except aiohttp.ClientError as e:
            error_msg = f"API 连接错误: {e}"
            logger.error(f"工具 {self.name} {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"工具执行异常: {e}"
            logger.error(f"工具 {self.name} {error_msg}")
            return error_msg
