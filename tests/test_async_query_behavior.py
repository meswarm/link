import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from link.agent import Agent
from link.llm_engine import LLMEngine


class _FakeToolRegistry:
    def __init__(self, result: str):
        self._result = result
        self.execute_tool = AsyncMock(return_value=result)

    def has_tools(self) -> bool:
        return True

    def get_all_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "query_note",
                    "description": "query note",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                        },
                        "required": ["query"],
                    },
                },
            }
        ]


def _tool_completion() -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[
                        SimpleNamespace(
                            id="call_1",
                            function=SimpleNamespace(
                                name="query_note",
                                arguments=json.dumps({"query": "docker compose"}),
                            ),
                        )
                    ],
                )
            )
        ]
    )


def _final_completion(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=text,
                    tool_calls=None,
                )
            )
        ]
    )


class TestAsyncQueryBehavior(unittest.IsolatedAsyncioTestCase):
    async def test_query_note_async_acceptance_short_circuits_llm_loop(self):
        registry = _FakeToolRegistry(
            json.dumps(
                {
                    "accepted": True,
                    "request_id": "req_1",
                    "status": "processing",
                },
                ensure_ascii=False,
            )
        )
        engine = LLMEngine(
            base_url="http://unused",
            api_key="unused",
            model="test-model",
            system_prompt="你是助手",
            tool_registry=registry,
            temperature=0.0,
        )
        create = AsyncMock(
            side_effect=[
                _tool_completion(),
                _final_completion("不应再追加这条文本"),
            ]
        )
        engine._client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create)
            )
        )

        reply = await engine.chat("room-1", "docker compose 常用命令")

        self.assertEqual(reply, "")
        self.assertEqual(create.await_count, 1)
        registry.execute_tool.assert_awaited_once()

    async def test_urgent_webhook_message_has_no_forced_emoji_prefix(self):
        agent = Agent.__new__(Agent)
        matrix = SimpleNamespace(
            rooms=["!room:localhost"],
            send_text=AsyncMock(),
            send_notice=AsyncMock(),
        )
        agent._matrix_client = matrix
        agent._send_file_to_room = AsyncMock()

        await Agent._handle_tool_event(
            agent,
            "/phonelinknote/notify",
            {"message": "2026年04月03日\nDocker Compose 常用命令指南"},
            True,
        )

        matrix.send_text.assert_awaited_once_with(
            "!room:localhost",
            "2026年04月03日\nDocker Compose 常用命令指南",
        )

    async def test_agent_does_not_send_empty_reply_after_async_query_dispatch(self):
        agent = Agent.__new__(Agent)
        agent._config = SimpleNamespace(pass_r2_images_to_llm=False)
        agent._media_store = None
        agent._resolve_r2_markdown_links = AsyncMock(return_value="docker compose 是什么")
        agent._llm_engine = SimpleNamespace(chat=AsyncMock(return_value=""))
        agent._send_reply_with_files = AsyncMock()
        matrix = SimpleNamespace(
            set_typing=AsyncMock(),
            send_text=AsyncMock(),
        )
        agent._matrix_client = matrix

        await Agent._handle_user_message(
            agent,
            "!room:localhost",
            "@user:localhost",
            "docker compose 是什么",
        )

        matrix.send_text.assert_not_awaited()
