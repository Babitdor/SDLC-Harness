---
name: requirements-spec
description: Turn REQUIREMENTS.md and CONSTRAINTS.md into actor-centred USER_STORIES.md and testable Given/When/Then ACCEPTANCE_CRITERIA.md. Use whenever requirements/USER_STORIES.md or requirements/ACCEPTANCE_CRITERIA.md is written or repaired.
source: https://github.com/github/awesome-copilot/blob/main/skills/create-specification/SKILL.md
license: MIT
---

## When to use

You are @Requirements and `sources/REQUIREMENTS.md` exists. Read it and
`sources/CONSTRAINTS.md` first. You add no scope: every story traces to a REQ
ID that already exists.

## Rules

- One actor per story, named as the sources name it — two roles are two stories.
- One capability per story. A second "and" in `I want:` is a second story.
- Every story traces to at least one REQ-NNN; every criterion to one REQ and the
  story that needs it.
- A criterion is observable: a tester passes or fails it without asking anyone.
  "fast", "robust", "user-friendly" are not criteria — write the number or the state.
- One outcome per criterion. If `Then:` needs "and", split it.
- Do not restate a requirement as a story; a story states the value, the
  requirement states the system behaviour.
- A requirement the sources cannot support stays unwritten. Record it under
  `## Open Questions` with its REQ ID instead of inventing an answer.
- IDs are append-only: US- and AC- numbers are never reused or renumbered,
  because BACKLOG.md, TEST_PLAN.md and the diagram tasks reference them.
- No technology, endpoint or schema in this phase — that is @Architecture and
  @API territory.
- Every requirement carries a `Source:` — INCOSE A3, trace to source. A
  requirement whose source is unrecorded cannot be audited later.

## Requirement language — INCOSE GtWR v4 closed word lists

Apply to every `Then:` you write and every requirement you quote (ISO/IEC/IEEE
29148 §5.2.7 language criteria). A hit is a candidate defect, not a proven one:
fix it or justify it, never silently pass it.

- **Vague terms (R7):** some, any, several, approximately, sufficient, adequate,
  appropriate, efficient, effective, reasonable, fast, robust, friendly.
- **Escape clauses (R8):** where possible, as appropriate, if necessary, to the
  extent practical, when required.
- **Open-ended (R9):** including but not limited to, etc., and so on.
- **Negation (R16) / slash (R17):** a criterion written as "no X" or "and/or".
  Write the positive case; split the alternative into its own criterion.
- **Combinators (R19):** one `and`, `or`, `unless` joining two behaviours means
  it is two criteria.
- **Pronouns (R24) / absolutes (R26):** "it", "they", "the system" with no
  antecedent; all, every, always, never, 100%.
- **Temporal (R35) / units (R6):** ideally, eventually, quickly, soon; and every
  number without its unit.

## Minimal worked example

```
# Actors
- Customer

# User Stories

US-001: Reorder a previous order
  As a: Customer
  I want: to reorder a previous order in one action
  So that: I do not rebuild a basket I already built
  Traces to: REQ-004
  Acceptance: AC-001
```

```
AC-001: Reorder copies the previous line items
  Given: a delivered order with 3 line items
  When: the customer reorders it
  Then: a new draft order exists with the same 3 line items
  Verifies: REQ-004
  Test: TC-001
```

## Common failure modes

- A story with no `Traces to:` — the traceability report then shows a story
  nobody asked for.
- `Then: the order is handled correctly` — unobservable, so TEST_PLAN.md cannot
  close it.
- Criteria written per requirement instead of per story: coverage looks complete
  while the stories stay untested.
- Two roles collapsed into "the user": their criteria then contradict each other
  on permissions.
