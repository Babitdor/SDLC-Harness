---
name: adr
description: Record each significant architecture decision as an ADR-NNN entry in design/ADR.md with its forces, the choice, the alternatives rejected and both consequences. Use whenever design/ADR.md is written or repaired.
source: https://github.com/github/awesome-copilot/blob/main/skills/create-architectural-decision-record/SKILL.md
license: MIT
---

## When to use

You are @Architecture and about to choose a technology, a decomposition or a
data-ownership boundary. Anything a maintainer could later ask "why this and not
that?" about is a record.

## Rules

- One decision per record. "Use Postgres and Redis" is two records.
- Status is exactly one of `proposed`, `accepted`, `superseded by ADR-NNN`.
- Context names the forces with the REQ / REQ-NF IDs that create them. A decision
  with no requirement behind it is a preference, not an architecture.
- Alternatives names at least one rejected option and why it lost. A record with
  no alternative reads as a justification, not a decision.
- Consequences name what gets easier and what gets harder. A record with only
  benefits is unfinished.
- Supersede, never rewrite: an accepted record is history. Write the new record,
  point it at the old one and flip the old one's Status.
- No implementation detail beyond the interfaces the decision fixes — line-level
  design belongs to the code, not here.
- ADR numbers are append-only, and one number per decision is the only way a
  later reversal stays legible.
- Recording the decision *and* its rationale is what ISO/IEC/IEEE 42010 §6.10
  requires of an architecture description. A record with consequences but no
  rejected alternative fails that clause; it is a justification, not a decision.

## Minimal worked example

```
# ADR-002: Own pricing in a single service

Status: accepted
Context: REQ-NF-003 caps price-change propagation at 5 minutes; two services
  reading separate price tables cannot meet it.
Alternatives: shared price table — rejected, it couples both release cycles;
  event bus with no owner — rejected, REQ-NF-003 allows no lag window.
Decision: the pricing service is the only writer of price records; every other
  component reads through its API.
Consequences: price changes propagate in one call and one cache window. The
  service becomes a single point of failure, so its availability target rises to
  99.9% and its release gate gets a smoke test.
Traces to: REQ-NF-003, REQ-011
```

## Common failure modes

- `Consequences: better performance` — no cost named, so nobody ever re-examines
  the choice.
- Context that restates the chosen option, hiding the forces that made it win.
- Three small choices bundled into one record, so a later reversal supersedes
  all three at once.
- ADR.md used as a design document: component tables and data flow belong in
  ARCHITECTURE.md, entities in DATA_MODEL.md.
