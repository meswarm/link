![Build Status](https://img.shields.io/github/actions/workflow/status/meswarm/link/ci.yml?branch=main)
![Version](https://img.shields.io/github/v/release/meswarm/link)
![License](https://img.shields.io/github/license/meswarm/link)

[![语言-中文](https://img.shields.io/badge/语言-中文-red)](README.md)
[![Language-English](https://img.shields.io/badge/Language-English-blue)](README_EN.md)

# Link (Intelligent Tool Middleware)

> Intelligent tool middleware - an Agent framework connecting users and tools via the Matrix protocol

Link is a personal intelligent assistant middleware system designed to connect everyday digital and automated tools. By building a smart assistant capable of understanding context, possessing multi-modal capabilities (including image analysis), and autonomously orchestrating tool usage (Function Calling), it enables cross-device interaction seamlessly with custom backend services using mature clients like Element through the robust Matrix protocol.

## Tech Stack

| Category       | Technology                       |
| -------------- | -------------------------------- |
| Language       | Python (>= 3.11)                 |
| Protocol       | Matrix (`matrix-nio`)            |
| LLM Engine     | API Compatible with OpenAI (Function Calling & text-to-vision capabilities) |
| Async Network  | HTTP / Webhooks (`aiohttp`)      |
| Configuration  | YAML, Pydantic (`pydantic`)      |

## Getting Started

### Prerequisites

* Python >= 3.11
* Package manager (e.g. `pipx` or `pip`)
* A dedicated Matrix account and Homeserver (Since this account will be operated by the bot, please do not use your personal daily account)

### Installation

We recommend using `pipx` for an isolated and global installation:

```bash
git clone https://github.com/meswarm/link.git
cd link

# Install globally in editable mode
pipx install -e .
```

### Configuration

Copy and configure your environment variables (primarily your Matrix server and the respective Large Language Model API keys):

```bash
cp .env.example .env
# Edit the .env configuration file according to your needs
```

Agent configurations can be composed by writing standalone YAML files. You can find a complete configuration template in `agents/config-template.yaml`.

### Running locally

After installation and configuration, you can quickly spin up an exclusive middleware Agent anywhere using the `ltool` command:

```bash
# Start a specific Agent instance
ltool start path/to/your-agent-config.yaml
```

## Project Structure

```
.
├── link/               # Middleware core codebase
│   ├── llm_engine.py   # LLM orchestration & Function Calling engine
│   ├── matrix_client.py# Matrix client (messaging & media downloads)
│   ├── agent.py        # Lifecycle and event dispatcher
│   └── tools/          # Core & external API adapters
├── models/             # Isolated LLM configurations
├── agents/             # Agent YAML configurations & examples
├── docs/               # Manual and technical reference docs
└── pyproject.toml      # Project dependencies and configurations
```

## Usage

The Link toolchain provides a unified Command Line Interface:

```bash
# Get help options
ltool --help

# Verify and list strictly-configured LLM models
ltool models

# Bring the specified middleware workflow to life
ltool start ./agents/example.yaml
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Commit your changes (`git commit -m 'feat: add your feature'`)
4. Push to the branch (`git push origin feat/your-feature`)
5. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.
