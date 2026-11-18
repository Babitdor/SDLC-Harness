---
name: implementation-plan
description: Order BACKLOG.md items into dependency-safe delivery order and map every acceptance criterion to a test case in TEST_PLAN.md. Use whenever planning/BACKLOG.md or planning/TEST_PLAN.md is written or repaired.
source: https://github.com/github/awesome-copilot/blob/main/skills/create-implementation-plan/SKILL.md
license: MIT
---

## When to use

You are @Planning and `requirements/USER_STORIES.md` and
`requirements/ACCEPTANCE_CRITERIA.md` exist. Nothing else yet: no endpoint
design, no duration estimates.

## Rules

- One item is one unit a single engineer finishes without coordinating anyone —
  if it needs "and", split it.
- Order is dependency order, not importance order. An item may only depend on
  items above it; a cycle means the split is wrong.
- Every item traces to a US-NNN (or to a REQ when no story covers it) and every
  story has at least one item.
- Priority (P0..P3) expresses the consequence of its absence, never the sequence —
  a P0 item can be scheduled last if nothing else can be built before it.
- Estimates are relative sizes (XS..XL). No hours, no days, no story points.
- Every AC-NNN appears in at least one TC. Uncovered criteria are listed under
  `# Coverage Gaps`, never dropped silently.
- A test case names its level (unit | integration | contract | e2e) and the one
  observable outcome it asserts.
- Do not plan work no story asks for: no refactors, no tooling upgrades, no
  "nice to have" items.

## Minimal worked example

```
| ID | Item | Epic | Priority | Estimate | Depends on | Traces to |
|----|------|------|----------|----------|------------|-----------|
| BI-001 | Order persistence | EP-001 | P1 | M | — | US-001 |
| BI-002 | Reorder endpoint | EP-001 | P1 | M | BI-001 | US-001 |
```

```
## TC-001: Reorder copies line items

Level: integration
Verifies: AC-001
Given / When / Then: delivered order / reorder it / a new draft order with the same 3 items
Expected result: 201 and 3 line items in the response
```

## Common failure modes

- Items sorted by priority so BI-004 depends on BI-007 further down the table.
- One test case verifying two criteria: a failure then names neither.
- TEST_PLAN.md that closes every criterion but plans no case for the story whose
  criteria were never written.
- Estimates in hours or points — they are wrong the moment the team changes and
  they imply a commitment this pipeline cannot make.
