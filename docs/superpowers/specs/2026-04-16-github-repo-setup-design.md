---
title: github-repo-setup Cursor skill design
date: 2026-04-16
status: draft-approved
---

# github-repo-setup Cursor Skill Design

## Goal

Create a personal Cursor skill named `github-repo-setup` at
`~/.cursor/skills/github-repo-setup/` by adapting and improving the existing
repository skill in `github-repo-setup/`.

The new skill should help Cursor safely prepare repositories for GitHub by:

- detecting the project stack
- auditing and improving `.gitignore`
- generating or updating bilingual `README.md` and `README_EN.md`
- explicitly filtering personal privacy files and directories before anything is
  pushed to GitHub

## Why this variant is needed

The existing skill has useful domain content, but it is not yet optimized for
Cursor skill discovery and reuse:

- the `description` mixes capability and workflow details
- the workflow is longer than needed for repeated agent use
- the content assumes repository-relative references instead of a standalone
  personal-skill layout
- privacy protection should be elevated from a generic `.gitignore` concern to a
  first-class safety rule

## Output Layout

Create this personal skill structure:

```text
~/.cursor/skills/github-repo-setup/
├── SKILL.md
├── assets/
│   ├── README-TEMPLATE.md
│   └── README_EN-TEMPLATE.md
└── references/
    └── GITIGNORE-RULES.md
```

## Design Decisions

### 1. Skill identity

- Skill name remains `github-repo-setup`
- This is a personal Cursor skill, not a project skill
- The skill must be self-contained and must not depend on files inside the
  current repository after installation

### 2. Cursor-oriented discovery

`SKILL.md` frontmatter will be rewritten so the `description` focuses on when to
use the skill, not how it works.

Target trigger scenarios:

- new repository initialization
- first GitHub push
- repository cleanup before publishing
- README or `.gitignore` improvement requests
- requests involving privacy-sensitive files, local config, secrets, or machine-
  specific directories

### 3. Workflow simplification

The Cursor skill will keep a compact four-step workflow:

1. Detect stack and repository shape
2. Audit `.gitignore` with privacy-first filtering
3. Create or sync bilingual README files
4. Verify safety and output consistency

### 4. Privacy-first safety rules

This is the main enhancement requested by the user.

The skill must explicitly require the agent to check for and filter personal or
sensitive content before GitHub publication. This includes:

- secret files such as `.env`, `.env.*`, private keys, tokens, credentials, and
  local database files where applicable
- personal configuration files that are not intended for sharing
- local IDE or editor state that may contain private paths or machine-specific
  metadata
- machine-specific folders, caches, logs, runtime outputs, and temporary files
- user-private documents or notes accidentally stored in the repository

The skill should instruct the agent to prefer:

- adding ignore rules
- preserving safe templates such as `.env.example`
- warning the user when an already-tracked private file should not be published
- avoiding blanket rules that would hide legitimate project files

The skill should also include a strong warning that privacy filtering is
mandatory even if the user only asks for README or GitHub cleanup help.

### 5. README behavior

The new skill will preserve the bilingual README concept:

- `README.md` as Chinese default
- `README_EN.md` as English counterpart
- synchronized technical content across both files
- language-switch badges in both files
- placeholders allowed when `OWNER/REPO` is unknown

### 6. Supporting files

Reuse the existing repository materials with light cleanup only:

- `assets/README-TEMPLATE.md`
- `assets/README_EN-TEMPLATE.md`
- `references/GITIGNORE-RULES.md`

If wording changes are needed, they should support the new privacy-first rules
and standalone Cursor skill packaging.

## Implementation Boundaries

In scope:

- create the personal Cursor skill directory
- rewrite `SKILL.md` for Cursor-oriented discovery and execution
- copy and lightly refine the template/reference files
- add explicit privacy filtering guidance

Out of scope:

- publishing the skill externally
- creating multiple related skills
- changing repository-wide project files outside the design/spec work unless
  explicitly requested later

## Verification Plan

Before claiming completion:

1. Confirm the personal skill directory and all expected files exist
2. Review `SKILL.md` for concise frontmatter and clear trigger wording
3. Confirm privacy filtering rules are explicit and prominent
4. Confirm all internal references point to files inside the skill directory
5. Check the new/edited files for lint-style issues only if relevant

## Risks and Mitigations

- Risk: overly broad ignore rules hide legitimate project files
  Mitigation: require stack-aware filtering and preserve examples/templates
- Risk: privacy guidance is too vague to be actionable
  Mitigation: include concrete examples of sensitive files and directories
- Risk: the skill remains too repo-specific
  Mitigation: remove assumptions tied to the current repository layout
