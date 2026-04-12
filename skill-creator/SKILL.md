---
name: skill-creator
description: >
  Create, scaffold, and refine Agent Skills from scratch. Use when the user
  wants to create a new skill, write a SKILL.md, scaffold a skill directory,
  or asks about skill structure, best practices, or Agent Skills format — even
  if they only describe a workflow or capability they want to automate.
---

# Skill Creator

You are the **造物主** — the meta-skill that creates other skills. Every new
skill you produce must be production-ready: well-scoped, concise, and
following the Agent Skills specification precisely.

## When to use this skill

- User asks to "create a skill", "write a skill", "make a new skill"
- User describes a repeatable workflow they want to automate
- User wants to package domain knowledge for agent reuse
- User asks about SKILL.md format, skill structure, or best practices

---

## Workflow

```
Task Progress:
- [ ] Phase 1: Gather requirements
- [ ] Phase 2: Design the skill
- [ ] Phase 3: Scaffold and write files
- [ ] Phase 4: Validate the output
```

---

## Phase 1: Gather requirements

Before writing anything, establish these six dimensions. Infer from context
when possible; ask only for what's missing.

| Dimension | Question | Default |
|-----------|----------|---------|
| **Purpose** | What task or workflow does this skill automate? | — (required) |
| **Location** | Personal (`~/.cursor/skills/`) or project (`.cursor/skills/`)? | Personal |
| **Triggers** | When should the agent activate this skill? | — (required) |
| **Domain knowledge** | What does the agent need to know that it wouldn't already? | — |
| **Output format** | Any required templates, formats, or styles? | None |
| **Supporting files** | Does the skill need scripts, references, or assets? | None |

Use the AskQuestion tool for structured gathering when available:

```
Suggested questions:
- "技能存放位置？" → ["个人 (~/.cursor/skills/)", "项目 (.cursor/skills/)", "当前目录"]
- "是否需要附带脚本？" → ["是", "否"]
- "是否需要模板文件？" → ["是", "否"]
```

### Inferring from conversation

If the user just completed a hands-on task and says "把这个做成 skill", extract
the pattern from the conversation: what steps worked, what corrections were
made, what domain facts were provided. These are the highest-value inputs.

---

## Phase 2: Design the skill

### 2a. Name

Rules (see [references/SPEC.md](references/SPEC.md) for full spec):

- 1-64 characters, lowercase `a-z`, digits, hyphens only
- No leading/trailing/consecutive hyphens
- Directory name must match the `name` field

Pick a name that describes the **action**, not the domain. Prefer
`review-pull-request` over `github-helper`.

### 2b. Description

The description is the **single most important line** — it determines whether
the skill gets activated. Follow this formula:

```
[What it does — 1-2 specific verbs and objects] + [When to use — trigger scenarios]
```

Rules:
- Max 1024 characters
- Third person ("Generates..." not "I generate...")
- Include specific trigger keywords the user might say
- Be pushy: explicitly list when it applies, even edge cases

**Test your description:** would an agent reading only this line know to
activate it for the target tasks? If not, rewrite.

### 2c. Structure plan

Decide the directory layout based on complexity:

```
# Minimal (instructions only)
skill-name/
└── SKILL.md

# Standard (with references)
skill-name/
├── SKILL.md
└── references/
    └── REFERENCE.md

# Full (templates + references + scripts)
skill-name/
├── SKILL.md
├── assets/
│   └── TEMPLATE.md
├── references/
│   └── REFERENCE.md
└── scripts/
    └── validate.sh
```

**Decision rule:** start minimal. Only add directories when the content would
push `SKILL.md` past ~300 lines or the skill needs reusable assets.

---

## Phase 3: Scaffold and write files

### 3a. Create directory structure

Create the planned directories. Never create empty placeholder files.

### 3b. Write SKILL.md

Use [assets/SKILL-TEMPLATE.md](assets/SKILL-TEMPLATE.md) as the structural
starting point, then apply these principles:

**Conciseness above all else.** Every line must earn its place. Ask:
"Would the agent get this wrong without this instruction?" If no, cut it.

**Add what the agent lacks, omit what it knows.** Focus on project-specific
conventions, domain-specific procedures, non-obvious edge cases. Don't explain
general knowledge (what a PDF is, how HTTP works, etc.).

**Provide defaults, not menus.** When multiple approaches work, pick one and
mention alternatives briefly:

```markdown
<!-- Bad -->
You can use A, B, or C...

<!-- Good -->
Use A for this task. For [edge case], use B instead.
```

**Favor procedures over declarations.** Teach *how to approach* a class of
problems, not *what to produce* for a single instance.

### 3c. Choose instruction patterns

Select patterns that fit the skill's nature (mix as needed):

| Pattern | When to use | Key element |
|---------|------------|-------------|
| **Checklist** | Multi-step workflows with dependencies | `- [ ] Step N:` progress tracker |
| **Template** | Output must follow a specific format | Concrete structure in `assets/` |
| **Gotchas** | Domain has non-obvious pitfalls | Bulleted list of "the agent will get this wrong" facts |
| **Validation loop** | Quality-critical output | Do → validate → fix → repeat |
| **Conditional** | Multiple paths based on input | Decision tree with `→` arrows |

### 3d. Write supporting files

- **`references/`** — detailed rules, specs, or lookup tables the agent loads
  on demand. Tell the agent *when* to load each file explicitly.
- **`assets/`** — templates, example outputs. Short ones can be inline in
  `SKILL.md`; move to files if >30 lines.
- **`scripts/`** — tested, reusable logic. Must be self-contained, non-
  interactive, with `--help` output. See [references/SPEC.md](references/SPEC.md)
  § Scripts for requirements.

---

## Phase 4: Validate the output

Run through this checklist before declaring the skill complete:

### Metadata
- [ ] `name` is lowercase, hyphens only, 1-64 chars, matches directory name
- [ ] `description` is ≤ 1024 chars, includes WHAT + WHEN, third person
- [ ] `description` contains specific trigger keywords

### Content quality
- [ ] `SKILL.md` body is < 500 lines
- [ ] No general knowledge the agent already has
- [ ] Provides defaults, not menus of equal options
- [ ] Examples are concrete, not abstract
- [ ] Consistent terminology throughout (one term per concept)

### Structure
- [ ] File references are one level deep from `SKILL.md`
- [ ] Progressive disclosure: heavy content in `references/` or `assets/`
- [ ] Each reference file has explicit load condition ("Read X when Y")
- [ ] No Windows-style paths (`\`), always use `/`

### If including scripts
- [ ] Scripts are non-interactive (no prompts)
- [ ] Scripts have `--help` output
- [ ] Dependencies declared inline (PEP 723, npm specifiers, etc.)
- [ ] Error messages are actionable

---

## Anti-patterns

Avoid these common mistakes when creating skills:

| Anti-pattern | Why it's bad | Fix |
|-------------|-------------|-----|
| Vague name (`helper`, `utils`) | Doesn't convey purpose | Use action-based names (`review-code`, `deploy-app`) |
| Description says "Helps with X" | Too vague to trigger correctly | State specific verbs + trigger scenarios |
| Explaining general knowledge | Wastes context tokens | Cut anything the agent already knows |
| Listing 5+ equal options | Agent wastes time choosing | Pick a default, mention 1 alternative |
| All content in SKILL.md | Bloated context on every run | Move reference material to separate files |
| Deeply nested file references | Agent may not follow chains | Keep references one level deep |
| Time-sensitive instructions | Will become stale | Use "Current method" / "Legacy" pattern |

---

## Gotchas

- **Never** create skills in `~/.cursor/skills-cursor/` — that directory is
  reserved for Cursor's internal built-in skills.
- If the user describes a task conversationally, you should still produce a
  complete, structured skill — don't just echo their description back.
- When extracting a skill from a conversation, prioritize **corrections the
  user made** and **domain facts they provided** — those are the highest-value
  content for the skill.
- Keep the `description` field under 1024 chars. Descriptions grow during
  iteration — check the length after every edit.
