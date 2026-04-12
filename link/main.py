"""Link Agent 启动入口

使用方式：
  # 标准：使用配置文件
  ltool start agents/todo.yaml

  # 快速：CLI 参数覆盖配置
  ltool start agents/todo.yaml --skills ./my-skills --room '!roomid'
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

from link.agent import Agent
from link.config import load_config, list_available_models

# 加载 .env 文件（从当前工作目录或项目根目录查找）
load_dotenv(Path(__file__).parent.parent / ".env")  # link/../.env = 项目根目录
load_dotenv()  # 也支持从 CWD 加载


def setup_logging(verbose: bool = False) -> None:
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO

    # 始终压制第三方库的噪音日志
    logging.getLogger("nio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="ltool",
        description="Link — 智能工具中间件",
    )

    sub = parser.add_subparsers(dest="command", help="可用命令")

    # ltool start <config> [overrides]
    start_parser = sub.add_parser("start", help="启动 Agent")
    start_parser.add_argument(
        "config", help="工具配置文件路径 (YAML)"
    )
    start_parser.add_argument(
        "-v", "--verbose", action="store_true", help="详细日志"
    )

    # CLI 覆盖参数（优先于配置文件）
    overrides = start_parser.add_argument_group("配置覆盖（优先于配置文件）")
    overrides.add_argument("--name", help="Agent 名称")
    overrides.add_argument("--prompt", help="系统提示词")
    overrides.add_argument("--skills", dest="skills_dir", help="技能目录")
    overrides.add_argument("--room", dest="rooms", action="append", help="Matrix 房间 ID（可多次指定）")
    overrides.add_argument("--model", help="模型名称（引用 models/ 目录中的配置）")
    overrides.add_argument("--matrix-user", help="Matrix 用户 ID")
    overrides.add_argument("--matrix-pass", dest="matrix_password", help="Matrix 密码")
    overrides.add_argument("--work-dir", dest="work_dir", help="工具工作目录")
    overrides.add_argument("--webhook-port", type=int, help="Webhook 端口")

    # ltool models — 列出可用模型
    sub.add_parser("models", help="列出可用的模型配置")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "start":
        _run_start(args)
    elif args.command == "models":
        _list_models()


def _run_start(args):
    """执行 start 命令"""
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # 加载配置
    logger.info(f"正在加载配置: {args.config}")
    config = load_config(args.config)

    # CLI 参数覆盖配置
    overrides = {
        "name", "prompt", "skills_dir", "rooms",
        "model", "matrix_user", "matrix_password", "work_dir",
    }
    for field_name in overrides:
        cli_value = getattr(args, field_name, None)
        if cli_value is not None:
            setattr(config, field_name, cli_value)

    # 如果 CLI 指定了不同的模型，重新加载模型配置
    if args.model and args.model != config.model:
        from link.config import load_model_config
        config._model_config = load_model_config(args.model)
        config.model = args.model

    if args.webhook_port:
        config.webhook.port = args.webhook_port

    # 创建并启动 Agent
    agent = Agent(config)
    _stopping = False

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 优雅关闭（第一次 Ctrl+C 优雅退出，第二次强制退出）
    def _shutdown(sig, frame):
        nonlocal _stopping
        if _stopping:
            logger.info("再次收到信号，强制退出")
            import os
            os._exit(1)
        _stopping = True
        logger.info("正在优雅关闭...")
        loop.call_soon_threadsafe(loop.create_task, agent.stop())

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(agent.start())
    except KeyboardInterrupt:
        if not _stopping:
            loop.run_until_complete(agent.stop())
    finally:
        loop.close()


def _list_models():
    """列出所有可用的模型配置"""
    from link.config import load_model_config

    models = list_available_models()
    if not models:
        print("未找到模型配置。请在 models/ 目录下创建模型配置文件。")
        return

    ready = []
    not_ready = []
    for name in models:
        try:
            cfg = load_model_config(name)
            ready.append((name, cfg))
        except Exception as e:
            not_ready.append((name, str(e)))

    if ready:
        print("✅ 可用模型:")
        for name, cfg in ready:
            print(f"   {name:20s} → {cfg.model}")
            print(f"   {'':20s}   {cfg.base_url}")

    if not_ready:
        print("\n⚠️  未配置 (需在 .env 中添加 API Key):")
        for name, err in not_ready:
            print(f"   {name:20s} → {err}")


if __name__ == "__main__":
    main()
