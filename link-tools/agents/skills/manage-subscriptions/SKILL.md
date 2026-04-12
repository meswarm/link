---
name: manage-subscriptions
description: Queries, creates, updates, deletes, reports on, and dismisses reminders for subscription records when users ask to 查看订阅、添加订阅、修改订阅、删除订阅、生成月报、统计本月花费、确认扣款提醒，或需要先查后改、先查后删的订阅管理对话。
---

# Manage Subscriptions

Use this skill for subscription-management requests handled through the Link tools in ../../subhub.yaml.

Read references/domain-rules.md when the user uses relative dates, omits `billing_cycle`, asks to infer `next_billing_date`, or the target subscription is ambiguous.

## Task Progress

- [ ] Step 1: Classify the request as query, create, update, delete, report, or reminder confirmation
- [ ] Step 2: Gather required fields or identify the target subscription
- [ ] Step 3: Call the safest tool sequence
- [ ] Step 4: Return the tool result in concise Chinese

## Defaults

- Use `list_subscriptions` first for update or delete unless a unique `id` is already known.
- Use `generate_monthly_report` with `mode=actual` for “本月花了多少/本月实际扣了多少”.
- Use `generate_monthly_report` with `mode=budget` for “月报/预算/每月总费用”.
- Use `get_today_reminders` for “最近要扣款/快到期/有哪些要提醒”.
- Use `dismiss_reminder` when the user says “知道了”“已处理”“我会取消”.

## Required fields for create

Do not call `create_subscription` until these are known:

- `name`
- `account`
- `payment_channel`
- `amount`
- `currency`
- `billing_cycle`
- `next_billing_date` unless `billing_cycle=permanent`

`notes` is optional.

## Safe tool sequences

### Query

- General lookup → `list_subscriptions`
- Upcoming charge check → `get_today_reminders`
- Monthly spending or budget → `generate_monthly_report`

### Create

1. Collect missing fields
2. Apply the defaults in references/domain-rules.md when inference is allowed
3. Call `create_subscription`

### Update

1. Query with `list_subscriptions`
2. If multiple matches exist, ask the user to confirm one target
3. Call `update_subscription`, preferring `id` over `selector_name`

### Delete

1. Query with `list_subscriptions`
2. If multiple matches exist, ask the user to confirm one target
3. Call `delete_subscription`, preferring `id` over `name`

### Reminder confirmation

- One subscription confirmed → `dismiss_reminder` with that `id` or name
- User confirms all reminders → `dismiss_reminder` with `target=all`

## Response rules

- Always reply in Chinese.
- Prefer markdown returned by tools for tables and reports.
- Do not invent subscriptions, dates, amounts, or currencies.
- If key information is missing, ask a focused follow-up instead of acting.
- If a destructive action is ambiguous, query first and confirm.
