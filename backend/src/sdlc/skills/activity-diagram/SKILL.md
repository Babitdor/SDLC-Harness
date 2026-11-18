---
name: activity-diagram
description: Write a Mermaid flowchart that models a process or activity flow — steps, decisions and their branches. Use for "what happens, step by step" where ordering matters more than message senders.
license: proprietary
---

## When to use

You are asked for an `activity` diagram. Read `requirements/USER_STORIES.md`
for the actor goal, and `requirements/ACCEPTANCE_CRITERIA.md` for the decision
points the criteria imply.

## Rules

- Mermaid has no `activityDiagram` keyword: use `flowchart TD` for a
  top-down process.
- Node shapes: `[step]` process, `{decision}` decision, `([start])` / `([end])`
  for the terminals.
- Decision nodes have one outgoing edge per branch, each labelled:
  `B -->|yes| C`.
- Every `subgraph` (a phase or actor swimlane) is closed with `end`.
- Every step traces to a story or criterion; do not invent steps.

## Minimal worked example

```mermaid
flowchart TD
    A([Start]) --> B[Validate input]
    B --> C{Valid?}
    C -->|yes| D[Persist]
    C -->|no| E[Return 400]
    D --> F([End])
    E --> F
```

## Common failure modes

- A cycle with no exit — the reader cannot tell where the process ends.
- Unlabelled decision branches → rejected by the structural check.
- Using a sequence diagram for a single-actor process: no messages, no sequence.
