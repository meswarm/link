---
name: github-repo-setup
description: >
  Initialize and maintain GitHub repositories — audit .gitignore rules,
  generate a standardized README.md with badges, tech stack, and project
  overview. Use when the user creates a new project, pushes to GitHub for the
  first time, or asks to clean up repository configuration, even if they don't
  explicitly mention "GitHub" or "repo setup."
---

# GitHub Repo Setup

## When to use this skill

Apply this skill **every time** a project is being initialized or prepared for
GitHub. Triggers include:

- User creates a new project or repository
- User asks to "set up" or "initialize" a project
- User wants to improve their `.gitignore` or `README.md`
- User is about to push code to GitHub for the first time

## Workflow

Copy this checklist and track progress:

```
Task Progress:
- [ ] Step 1: Scan project files and detect tech stack
- [ ] Step 2: Audit and optimize .gitignore
- [ ] Step 3: Generate or update README.md + README_EN.md
- [ ] Step 4: Verify outputs
```

---

## Step 1: Scan project and detect tech stack

Examine the project root to determine:

1. **Language / framework** — look for `package.json`, `pyproject.toml`,
   `Cargo.toml`, `go.mod`, `pom.xml`, `Gemfile`, `mix.exs`, etc.
2. **Build tools** — webpack, vite, esbuild, gradle, make, cmake, etc.
3. **Package managers** — npm, pnpm, yarn, pip, uv, cargo, etc.
4. **Infrastructure** — Docker, Terraform, Kubernetes manifests, etc.
5. **CI/CD** — `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, etc.

Record the detected stack — it drives both the `.gitignore` rules and the
README tech-stack section.

---

## Step 2: Audit and optimize .gitignore

### 2a. If `.gitignore` exists

1. Read the current `.gitignore`.
2. Compare against the rules in [references/GITIGNORE-RULES.md](references/GITIGNORE-RULES.md) for the detected stack.
3. **Add** any missing critical patterns (build artifacts, secrets, OS files).
4. **Remove** rules that are clearly outdated or irrelevant to the project.
5. **Organize** entries into labeled sections for readability.

### 2b. If `.gitignore` does not exist

1. Create `.gitignore` from scratch using the stack-specific rules in
   [references/GITIGNORE-RULES.md](references/GITIGNORE-RULES.md).

### .gitignore structure

Always organize the file with section headers:

```gitignore
# === OS files ===
.DS_Store
Thumbs.db

# === Editor / IDE ===
.vscode/
.idea/
*.swp

# === Dependencies ===
node_modules/

# === Build output ===
dist/
build/

# === Environment & secrets ===
.env
.env.*
!.env.example

# === Logs ===
*.log
```

### Gotchas

- **Never ignore lockfiles** (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`,
  `Cargo.lock` in applications, `poetry.lock`, `uv.lock`). They should be committed.
- Always provide an `.env.example` exclusion pattern (`!.env.example`) so
  template env files are tracked.
- For monorepos, ensure nested build outputs are captured (`**/dist/`,
  `**/build/`).

---

## Step 3: Generate or update README files

Generate **two separate files**: `README.md`（中文，默认）and `README_EN.md`
（English）. Use the corresponding templates as structural baselines:

- [assets/README-TEMPLATE.md](assets/README-TEMPLATE.md) → `README.md`
- [assets/README_EN-TEMPLATE.md](assets/README_EN-TEMPLATE.md) → `README_EN.md`

### Dual-file bilingual structure

```
project-root/
├── README.md          ← 中文（GitHub 默认展示）
└── README_EN.md       ← English
```

Both files share the same **language-switch badges** at the top, right below
the project badges. This gives readers a one-click jump between versions:

```markdown
[![语言-中文](https://img.shields.io/badge/语言-中文-red)](README.md)
[![Language-English](https://img.shields.io/badge/Language-English-blue)](README_EN.md)
```

### Badge layout (both files)

The top of each file follows this exact order:

1. **Project badges** — build status, version, license (use shields.io)
2. **Language-switch badges** — 中文 (red) + English (blue), linking to the
   other file

```markdown
![构建状态](https://img.shields.io/github/actions/workflow/status/OWNER/REPO/ci.yml?branch=main&label=构建状态)
![最新版本](https://img.shields.io/github/v/release/OWNER/REPO?label=最新版本)
![许可证](https://img.shields.io/github/license/OWNER/REPO?label=许可证)

[![语言-中文](https://img.shields.io/badge/语言-中文-red)](README.md)
[![Language-English](https://img.shields.io/badge/Language-English-blue)](README_EN.md)
```

In `README.md`, project badge labels should be in Chinese (构建状态, 最新版本,
许可证). In `README_EN.md`, use English labels (Build Status, Version,
License).

Replace `OWNER/REPO` with the actual GitHub owner and repository name. If
unknown, use placeholders and tell the user to replace them.

### Required sections (both files)

Both files **must** include these sections, properly translated:

| README.md (中文) | README_EN.md (English) | Purpose |
|-----------------|----------------------|---------|
| 项目名称 & 简介 | Project title & description | One-liner + short paragraph |
| 技术栈 | Tech Stack | Languages, frameworks, key libraries |
| 快速开始 | Getting Started | Prerequisites, installation, running locally |
| 项目结构 | Project Structure | Key directories and files |
| 使用方法 | Usage | Core commands or API examples |
| 贡献指南 | Contributing | How to contribute |
| 许可证 | License | License type |

### Sync rules

- When **creating** READMEs, generate both files in the same step.
- When **updating** an existing README, always update **both** files
  simultaneously. Never leave one out of sync.
- Technical content (commands, code blocks, table data) must be **identical**
  across both files. Only natural-language prose should differ.

### Writing style

- `README.md`: 使用简洁的技术中文，避免过度口语化
- `README_EN.md`: clear, concise technical English
- Both: write for developers seeing the project for the first time;
  include actual runnable commands
- Keep each file under 200 lines

---

## Step 4: Verify outputs

After generating files, perform these checks:

1. **`.gitignore`** — confirm no lockfiles are ignored; confirm secrets
   patterns are present; confirm build output patterns match the detected stack.
2. **`README.md` + `README_EN.md`** structural check:
   - Both files exist in the project root.
   - Both files contain project badges + language-switch badges at the top.
   - Language-switch badge links are correct (`README.md` ↔ `README_EN.md`).
   - All required sections are present in **both** files.
   - Installation commands are runnable in both versions.
3. **Content sync check**:
   - Compare the section headings of both files — they must be one-to-one.
   - Technical content (commands, code blocks, table data) must be identical.
   - Only natural-language prose should differ between the two files.

---

## Gotchas

- If the repo already has a monolingual `README.md`, keep its content as the
  basis for the matching language file, then generate the other language
  version. Do not overwrite existing user content.
- Do not add badges for services that aren't configured (e.g., no coverage
  badge if there's no coverage tool set up).
- When uncertain about the GitHub owner/repo name, use `OWNER/REPO` as
  placeholder and tell the user to replace it.
- **Never** update only one file. Every README change must be applied to
  both `README.md` and `README_EN.md` to keep them in sync.
