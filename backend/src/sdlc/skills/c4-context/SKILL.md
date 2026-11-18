---
name: c4-context
description: Write a C4-style system-context view in Mermaid — the system as one box, its users and its external systems. Use when the reader needs scope and boundaries, not internals.
license: proprietary
---

## When to use

You are asked for a `context` or `c4` diagram. Read
`design/ARCHITECTURE.md` section "System Context" and the actors in
`requirements/USER_STORIES.md`.

## Rules

- Mermaid has no C4 renderer: use `flowchart LR` with labelled subgraphs for
  the boundary — `[Person]` and `[External system]` nodes around a single
  `[System]` box.
- Show ONLY the system, its people and its external systems. Internal
  components belong in `deployment.mmd`, not here.
- Every edge is labelled with what flows across it (`uses`, `posts orders to`).
- If the architecture names no external system, the context view has no
  external nodes — do not invent integrations.

## Minimal worked example

```mermaid
flowchart LR
    User[Person: Customer]
    System[System: Order service]
    Pay[External: Payment provider]
    User -->|places orders| System
    System -->|charges card| Pay
```

## Common failure modes

- Drifting into a component diagram: the context view has exactly one system box.
- Inventing external systems to make the picture look complete.
