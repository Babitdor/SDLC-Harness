---
name: mermaid-v2-reference
description: Index of supported Mermaid diagram types and the syntax facts that most often break a model: headers, block closing, cardinality tokens, label rules and what Mermaid cannot express. Read when a diagram type or construct is unclear.
license: proprietary
---

## When to use

When you need the exact header keyword, a construct the per-diagram skill does
not cover, or a reminder of a Mermaid limitation before you design around it.
The `mermaid_syntax_reference_tool` returns the same rules for one type.

## Supported diagrams in this harness

| Need | Header | Skill |
|------|--------|-------|
| Ordered messages between participants | `sequenceDiagram` | `sequence-diagram` |
| Types, fields, associations | `classDiagram` | `class-diagram` |
| Tables and foreign keys | `erDiagram` | `erd` |
| One entity lifecycle | `stateDiagram-v2` | `state-machine-diagram` |
| Process with decisions | `flowchart TD` | `activity-diagram` |
| Runtime nodes and protocols | `flowchart LR` + subgraphs | `deployment-diagram` |
| Scope and boundaries | `flowchart LR` | `c4-context` |

## Facts that break models

- The header keyword must be the first content line — a leading blank line or
  prose becomes a parse error.
- `end` closes exactly one `subgraph`; nesting needs one `end` per level.
- `classDiagram` class blocks need their `}`; an unclosed block swallows the file.
- ER cardinality is limited to `||--o{`, `||--|{`, `}o--||`, `|o--||`, `||--||`.
- Every edge/transition needs a label after `:` (the `[*]` pseudo-state is the
  only exemption).
- No HTML tags in labels; no parentheses inside labels.
- There is no native deployment, C4 or activity diagram — use flowcharts.

## Common failure modes

- Mixing two diagram families in one file (an `erDiagram` for a class view, or
  vice versa) because the picture "looks close enough".
- Using a flowchart where ordering between senders matters: that is a sequence.
