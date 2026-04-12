![构建状态](https://img.shields.io/github/actions/workflow/status/meswarm/link/ci.yml?branch=main&label=构建状态)
![最新版本](https://img.shields.io/github/v/release/meswarm/link?label=最新版本)
![许可证](https://img.shields.io/github/license/meswarm/link?label=许可证)

[![语言-中文](https://img.shields.io/badge/语言-中文-red)](README.md)
[![Language-English](https://img.shields.io/badge/Language-English-blue)](README_EN.md)

# Link (智能工具中间件)

> 智能工具中间件 - 通过 Matrix 协议连接用户与工具的 Agent 框架

Link 是一个个人智能助手中间件系统，旨在通过构建一个能够理解上下文、具备多模态能力（包含图像分析）并能自主进行工具调用的智能助理，连接日常数字生活的各种自动化工具和服务。它基于 Matrix 协议通信，让你可以利用诸如 Element 等成熟的聊天客户端跨设备无缝与后端各类自定义服务交互。

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python (>= 3.11) |
| 通信协议 | Matrix (`matrix-nio`) |
| LLM 推理引擎 | OpenAI Compatible API, 支撑 Function Calling 及图文多模态 |
| 异步通信 | HTTP / Webhooks (`aiohttp`) |
| 配置与校验 | YAML, Pydantic (`pydantic`) |

## 快速开始

### 前置要求

- Python >= 3.11
- 包管理工具 (如：`pipx` 或 `pip`)
- 准备一个独立的 Matrix 账号与 Homeserver 节点 (由于该账号将被 Bot 接管，请勿使用个人常用聊天账号)

### 安装

推荐使用 `pipx` 以可编辑的方式进行全局安全隔离安装：

```bash
git clone https://github.com/meswarm/link.git
cd link

# 全局安装 ltool 命令
pipx install -e .
```

### 配置

拷贝并配置环境变量（主要是你的 Matrix 服务器与相关大模型的 API Keys）：

```bash
cp .env.example .env
# 编辑 .env 文件，填入所需配置信息
```

中间件的配置可以通过书写独立 YAML 的方式按需组合，模板文件可参考 `agents/config-template.yaml`。

### 本地运行

安装并配置完毕后，你可以在任意目录下利用 `ltool` 快速拉起专属的中间件 Agent：

```bash
# 启动特定 Agent 实例
ltool start path/to/your-agent-config.yaml
```

## 项目结构

```
.
├── link/               # 框架核心代码
│   ├── llm_engine.py   # LLM 决策与 Function Calling 引擎
│   ├── matrix_client.py# Matrix 客户端 (收发内容及媒体下载处理)
│   ├── agent.py        # 生命周期与事件编排流
│   └── tools/          # 内置与外部 API 工具适配器
├── models/             # LLM 模型库配置 (按供应商隔离隔离 Keys)
├── agents/             # Agent 组装配置模板示例
├── docs/               # 技术文档资源
└── pyproject.toml      # 项目构建定义与依赖管理
```

## 使用方法

Link 工具链统一提供了入口 CLI 命令：

```bash
# 获取命令帮助
ltool --help

# 校验并列出当前支持和配置完备的 LLM 模型
ltool models

# 拉起指定的中间件进行工作
ltool start ./agents/example.yaml
```

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feat/your-feature`)
3. 提交更改 (`git commit -m 'feat: add your feature'`)
4. 推送分支 (`git push origin feat/your-feature`)
5. 发起 Pull Request

## 许可证

MIT License — 详见 [LICENSE](LICENSE)。
