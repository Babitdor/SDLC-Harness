---
name: deployment-diagram
description: Write a Mermaid deployment view — runtime nodes, the services on them and the protocol between them — from design/ARCHITECTURE.md. Use for "what runs where, and how it talks".
license: proprietary
---

## When to use

You are asked for a `deployment` diagram. Read `design/ARCHITECTURE.md`: each
component becomes a node, each interface an edge.

## Rules

- Mermaid has no native deployment diagram: use `flowchart LR` with one
  `subgraph` per deployment node (host, cluster, environment).
- Every subgraph declares a display label: `subgraph app[Application]`.
- Every subgraph is closed with `end` on its own line.
- Every edge is labelled with the protocol: `LB -->|HTTPS| API`.
- Node names match component names in ARCHITECTURE.md.
- Show only nodes the architecture names. A database that appears in
  DATA_MODEL.md but not in ARCHITECTURE.md is a gap to report, not to fill.

## Minimal worked example

```mermaid
flowchart LR
    subgraph edge[Edge]
        LB[Load balancer]
    end
    subgraph app[Application]
        API[API service]
    end
    LB -->|HTTPS| API
```

## Common failure modes

- Unclosed `subgraph` → the rest of the diagram nests inside it.
- Unlabelled edges: a deployment view without protocols answers nothing.
- Drawing cloud regions or replicas the architecture never mentions.
