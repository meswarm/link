# Link 接入说明

本目录包含 SubHub 接入 Link 中间件所需的配置。

## 文件说明

- [link/agents/subhub.yaml](agents/subhub.yaml)：SubHub 的正式 Agent 配置
- [link/agents/skills/manage-subscriptions/SKILL.md](agents/skills/manage-subscriptions/SKILL.md)：规范化 Skill 主文件
- [link/agents/skills/manage-subscriptions/references/domain-rules.md](agents/skills/manage-subscriptions/references/domain-rules.md)：日期、计费周期、报表模式等领域规则
- [link/config-template.yaml](config-template.yaml)：Link 官方接入模板

## 启动顺序

1. 启动 SubHub API

   `uv run subhub`

   如果 [config.toml](../config.toml) 已配置 `webhook.url`，这个进程会同时启用主动提醒，无需再单独启动一次。

   API 监听地址默认读取 [config.toml](../config.toml) 中的 `[server]` 配置。

2. 检查 [link/agents/subhub.yaml](agents/subhub.yaml) 中的 API 地址

   当前默认写死为 `http://127.0.0.1:58000`。

   如果你修改了 [config.toml](../config.toml) 中 `[server].host` 或 `[server].port`，需要同步修改该文件里的各个 `endpoint`。

3. 填写 [link/agents/subhub.yaml](agents/subhub.yaml) 中的 Matrix 账号、密码、房间 ID

4. 启动 Link

   `ltool start link/agents/subhub.yaml`

## 主动提醒

SubHub 的主动提醒通过 Link 的 webhook 接收，且已并入 API 进程：

- 端口：`9001`
- 路径：`/alert`
- 模式：`urgent: true`

SubHub API 进程检测到即将扣款时，会向该端点发送文本消息。
