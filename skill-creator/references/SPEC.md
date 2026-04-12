# Agent Skills 规范速查

本文件是 Agent Skills specification 的精简速查版。创建技能时按需查阅。

---

## Frontmatter 字段

| 字段 | 必填 | 约束 |
|------|------|------|
| `name` | 是 | 1-64 字符，仅小写字母 `a-z`、数字、连字符 `-`。不得以 `-` 开头/结尾，不得有连续 `--`。必须与目录名一致。 |
| `description` | 是 | 1-1024 字符，非空。描述技能做什么 + 何时使用。 |
| `license` | 否 | 许可证名称或引用文件。 |
| `compatibility` | 否 | ≤ 500 字符。环境要求（运行时、系统包、网络等）。 |
| `metadata` | 否 | 任意键值对（string → string）。 |
| `allowed-tools` | 否 | 空格分隔的预授权工具列表（实验性）。 |

---

## 目录结构

```
skill-name/
├── SKILL.md          # 必需：元数据 + 指令
├── scripts/          # 可选：可执行脚本
├── references/       # 可选：参考文档
└── assets/           # 可选：模板、资源
```

---

## 关键约束

- **SKILL.md 正文** < 500 行 / ~5000 tokens
- **文件引用**一层深度（SKILL.md → references/X.md，不要 references/X.md → references/Y.md）
- **渐进式披露**：name + description 在启动时加载（~100 tokens）；SKILL.md 正文在激活时加载；references/assets 按需加载

---

## Description 写作公式

```
[具体动词 + 对象] + [触发场景]
```

要求：
- 第三人称（"Generates..." 而非 "I generate..."）
- 包含 WHAT（做什么）+ WHEN（何时用）
- 包含用户可能说出的具体关键词
- 宁可积极匹配（pushy），也不要遗漏

---

## Name 命名规范

有效示例：
- `pdf-processing`
- `code-review`
- `deploy-staging`

无效示例：
- `PDF-Processing`（大写）
- `-pdf`（以 `-` 开头）
- `pdf--processing`（连续 `--`）
- `helper`、`utils`（过于模糊）

---

## 脚本规范

脚本放在 `scripts/` 目录下，要求：

1. **非交互式** — 不得等待 TTY 输入，所有输入通过参数/环境变量/stdin
2. **`--help` 输出** — 简短描述 + 可用参数 + 示例
3. **依赖内联声明** — Python 用 PEP 723、Node 用 npx/bunx、Go 用 `go run`
4. **结构化输出** — 优先 JSON/CSV 而非自由文本，数据发 stdout，诊断发 stderr
5. **有意义的退出码** — 区分错误类型
6. **幂等性** — "不存在则创建" 优于 "创建并在重复时报错"
7. **可控输出量** — 大输出支持 `--output FILE` 或分页参数

---

## 指令模式速查

| 模式 | 适用场景 | 核心元素 |
|------|---------|---------|
| Checklist | 有依赖的多步骤工作流 | `- [ ] Step N:` 进度条 |
| Template | 输出必须遵循特定格式 | `assets/` 中的具体结构 |
| Gotchas | 领域有反直觉的陷阱 | "agent 会搞错这个" 的事实列表 |
| Validation loop | 质量关键型输出 | 做 → 验证 → 修 → 重复 |
| Conditional | 多路径决策 | `→` 箭头的决策树 |
| Plan-validate-execute | 批量/破坏性操作 | 先生成计划文件，验证后执行 |

---

## 存储位置

| 类型 | 路径 | 范围 |
|------|------|------|
| 个人 | `~/.cursor/skills/skill-name/` | 所有项目通用 |
| 项目 | `.cursor/skills/skill-name/` | 仅当前仓库 |

**禁止**在 `~/.cursor/skills-cursor/` 中创建技能。
