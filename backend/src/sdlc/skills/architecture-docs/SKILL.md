---
name: architecture-docs
description: Write ARCHITECTURE.md, DATA_MODEL.md and ADR.md from requirements and constraints — component decomposition, entity model and decision records. Use whenever the design phase is being produced or audited.
license: proprietary
---

## When to use

You are @Architecture. Inputs: `requirements/REQUIREMENTS.md` (required),
`requirements/CONSTRAINTS.md` and `requirements/GLOSSARY.md` (when present).

## Rules

- Every component traces to at least one REQ id; every functional requirement
  is served by a component or listed under Risks as uncovered.
- One responsibility per component. If it needs "and" in the description, it
  is two components.
- Every entity has a primary identifier and every relationship an explicit
  cardinality (1, 0..1, 1..*, *).
- Every technology choice is an ADR with both the gain and the cost. A choice
  argued inline in ARCHITECTURE.md is an undocumented decision.
- A quality attribute with no target in the requirements is written as
  "no target specified in REQUIREMENTS.md" — never invent an SLA.

## Architecture description checklist — ISO/IEC/IEEE 42010:2022, Clause 6

ARCHITECTURE.md *is* an architecture description, so it is measured against the
clause that specifies one:

- Entity of interest and its scope (§6.1).
- Stakeholders (§6.2), and their concerns (§6.4) — named, one line each.
- Viewpoints (§6.6) and views (§6.7): every view names the viewpoint governing
  it, and every concern is addressed by at least one viewpoint.
- Correspondences (§6.9): the table stating how elements in different views
  relate. A element that appears in two views with two names is a correspondence
  defect, not a formatting one.
- Decisions and rationale (§6.10): point at `ADR-NNN`. An inline choice in a
  component row is an unrecorded decision.

The standard concedes it does not address completeness or correctness, and says
they can be *partially* checked through consistency, transitivity, and whether
elements appear in the views. Do exactly that much and claim no more.

## Minimal worked example

```markdown
## ADR-001: PostgreSQL for order storage

Status: accepted
Context: REQ-004 needs transactional order writes; C2 caps infrastructure cost.
Decision: a single PostgreSQL instance.
Consequences: strong consistency and simple backups; one instance is a single
point of failure until a replica is added.
Traces to: REQ-004, C2
```

## Common failure modes

- A component invented to fill an architectural gap the requirements never
  describe.
- ADRs with no Consequences section.
- Data-model fields that do not match the names later used in openapi.yaml.
