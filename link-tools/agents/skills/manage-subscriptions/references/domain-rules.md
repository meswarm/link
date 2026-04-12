# Domain Rules

Read this file when the user uses relative dates, omits `billing_cycle`, asks to infer `next_billing_date`, or the target subscription is ambiguous.

## Relative date defaults

- “今天”“刚才” → current date
- “昨天” → current date minus 1 day
- “X天前” → current date minus X days
- If the user gives an explicit date, use it directly

## `next_billing_date` defaults

Only infer `next_billing_date` when the user did not provide it explicitly.

- `monthly` → start date + 1 natural month
- `yearly` → start date + 1 year
- `weekly` → start date + 7 days
- `daily` → start date + 1 day
- `permanent` → `null`
- `custom` → ask a follow-up; do not infer

## Missing-field rules

- Missing `currency` → ask
- Missing `billing_cycle` → ask
- Missing `account` or `payment_channel` → ask, and prefer values seen in context when offering choices
- `notes` may be empty

## Report mode selection

Use `mode=actual` for:
- 本月花了多少
- 本月实际扣了多少
- 本月实际支出

Use `mode=budget` for:
- 月报
- 预算
- 每月总费用
- 每个月大概花多少

## Ambiguity handling

For update or delete:

1. Query first
2. If zero matches, tell the user nothing matched
3. If multiple matches exist, ask the user to choose one
4. Prefer `id` for the final write operation
