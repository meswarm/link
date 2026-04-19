# github-repo-setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a personal Cursor skill named `github-repo-setup` that safely prepares repositories for GitHub publication, with bilingual README support and mandatory privacy filtering guidance.

**Architecture:** Package the skill as a standalone directory under `~/.cursor/skills/github-repo-setup/`. Keep the main workflow concise in `SKILL.md`, store reusable README templates in `assets/`, and keep stack-specific ignore guidance in `references/GITIGNORE-RULES.md`.

**Tech Stack:** Markdown files, Cursor personal skills, local filesystem

---

### Task 1: Capture the baseline failures

**Files:**
- Modify: `docs/superpowers/specs/2026-04-16-github-repo-setup-design.md`
- Test: baseline subagent outputs captured in session

- [ ] **Step 1: Record the baseline failures**

Write down the concrete gaps found during baseline testing:

```markdown
- The draft description focused on what the skill does instead of when to use it.
- The baseline workflow omitted standalone skill packaging details.
- Privacy filtering appeared as generic advice instead of a mandatory safety rule.
- Bilingual README synchronization was treated as a minor checklist item.
```

- [ ] **Step 2: Verify the failures are specific enough**

Run: manual review of the baseline subagent outputs in session
Expected: each failure maps to a change in the final skill

### Task 2: Draft the optimized skill content

**Files:**
- Create: `~/.cursor/skills/github-repo-setup/SKILL.md`
- Create: `~/.cursor/skills/github-repo-setup/assets/README-TEMPLATE.md`
- Create: `~/.cursor/skills/github-repo-setup/assets/README_EN-TEMPLATE.md`
- Create: `~/.cursor/skills/github-repo-setup/references/GITIGNORE-RULES.md`

- [ ] **Step 1: Write the frontmatter and overview**

```markdown
---
name: github-repo-setup
description: Use when preparing a repository for its first GitHub push, cleaning up a repo before publishing, improving README or .gitignore files, or checking for private local files and machine-specific config that should not be exposed.
---
```

- [ ] **Step 2: Write the compact workflow**

```markdown
1. Detect the stack and repository shape
2. Audit `.gitignore` with privacy-first filtering
3. Create or sync `README.md` and `README_EN.md`
4. Verify publish safety and bilingual consistency
```

- [ ] **Step 3: Add mandatory privacy rules**

```markdown
- Treat private or machine-local files as a blocking safety concern.
- Preserve safe templates such as `.env.example`.
- Warn the user if a tracked file appears private or secret-bearing.
- Do not silently remove legitimate project files with overly broad ignore rules.
```

### Task 3: Create the personal skill package

**Files:**
- Create: `~/.cursor/skills/github-repo-setup/SKILL.md`
- Create: `~/.cursor/skills/github-repo-setup/assets/README-TEMPLATE.md`
- Create: `~/.cursor/skills/github-repo-setup/assets/README_EN-TEMPLATE.md`
- Create: `~/.cursor/skills/github-repo-setup/references/GITIGNORE-RULES.md`

- [ ] **Step 1: Create directories**

Run:

```bash
mkdir -p ~/.cursor/skills/github-repo-setup/assets ~/.cursor/skills/github-repo-setup/references
```

Expected: the skill directory tree exists

- [ ] **Step 2: Write the final files**

Copy the templates and rules into the new skill package, with privacy-first wording updates and standalone references.

- [ ] **Step 3: Verify the files exist**

Run:

```bash
ls ~/.cursor/skills/github-repo-setup
ls ~/.cursor/skills/github-repo-setup/assets
ls ~/.cursor/skills/github-repo-setup/references
```

Expected: `SKILL.md`, both templates, and the `.gitignore` reference file are present

### Task 4: Verify usability and quality

**Files:**
- Modify: `~/.cursor/skills/github-repo-setup/SKILL.md` if needed

- [ ] **Step 1: Review the skill for discovery quality**

Check:

```markdown
- The description starts with "Use when..."
- The description focuses on trigger conditions, not workflow summary
- Internal links point only to files inside the skill directory
```

- [ ] **Step 2: Review the skill for privacy emphasis**

Check:

```markdown
- Privacy filtering is presented as mandatory
- Examples include secrets, local config, logs, caches, and machine-specific files
- The skill warns about already-tracked private files
```

- [ ] **Step 3: Verify the final package**

Run:

```bash
wc -l ~/.cursor/skills/github-repo-setup/SKILL.md
```

Expected: reasonable size for repeated loading, with no missing supporting files
