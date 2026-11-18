---
type: Constraints Document
title: Design Constraints and Rules
description: Quantifiable or verifiable constraints that bound the design space, categorized by type.
tags: [constraints, mbse]
timestamp: 2026-09-08T18:48:32Z
resource: requirements/RULES.md
---

# Constraints

Sources: `sources/requirements.md` (Constraints C1–C3 and Non-Functional Requirements REQ-NF-001..REQ-NF-005). Each rule cites its source requirement ID verbatim in intent; no values are added beyond the source text.

## Physical Constraints

C1: The warehouse floor area shall not exceed 5,000 square metres. (Source: C1)
C2: The maximum rack height shall not exceed 12 metres. (Source: C2)
C3: General storage shall be held between 15 and 25 degrees Celsius; cold storage between 2 and 8 degrees Celsius. (Source: C3)

## Safety Constraints

C4: Hazardous-material storage shall be physically segregated from general storage. (Source: REQ-NF-004)

## Performance Constraints

C5: The system shall sustain an order throughput of 500 orders per hour. (Source: REQ-NF-002)
C6: The system shall maintain 99.9 percent service availability. (Source: REQ-NF-003)

## Capacity Constraints

C7: The system shall manage at least 10,000 distinct SKUs. (Source: REQ-NF-001)

## Security Constraints

C8: The system shall enforce role-based access control for administrator, operator, and viewer roles. (Source: REQ-NF-005)

## Data Gaps (noted, not filled)

- C3: no tolerance band, monitoring granularity, or humidity limits are stated in the source.
- C5/C6 (REQ-NF-002/REQ-NF-003): no measurement window or duty-cycle definition is stated in the source.
- C8 (REQ-NF-005): role names are defined, but no permission matrix per role is stated in the source.