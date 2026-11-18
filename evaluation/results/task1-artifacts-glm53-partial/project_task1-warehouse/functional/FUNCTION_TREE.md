---
type: Function Tree Document
title: Functional Decomposition Hierarchy
description: Hierarchical decomposition of system functions and sub-functions mapped to activities.
tags: [functional, decomposition, mbse]
timestamp: 2026-09-08T18:48:32Z
resource: functional/FUNCTION_TREE.md
---

# Function Tree

Rooted in the top-level function **Operate Warehouse Goods Flow**, decomposed into the six functions of the morphological box (Receive Goods, Store Goods, Pick Goods, Pack Goods, Ship Goods, Manage Inventory — `requirements/BOX.md`) plus the two enabling functions for barcode scan recording (REQ-009) and real-time inventory reporting (REQ-010). Leaf functions map to the activities ACT-001..ACT-012 defined in `functional/ACTIVITIES.md`. Behavior only — no solution options (AS/RS, conveyors, RFID, etc.) are carried into this tree; those are Logical-phase content per `requirements/BOX.md`.

- **Operate Warehouse Goods Flow** (top-level function; REQ-001..REQ-010; UC-001..UC-010)
  - **Receive Goods** (UC-001, UC-002; REQ-001, REQ-002)
    - **Register Goods Arrival and Create Receipt** (UC-001 steps 1–2; REQ-001)
      - Receive Incoming Goods at Receiving Dock (ACT-001) — REQ-001
    - **Verify Goods Against Purchase Order** (UC-002; REQ-002)
      - Verify Received Goods Against Purchase Order (ACT-002) — REQ-002
  - **Store Goods** (UC-003, UC-004; REQ-003, REQ-004; REQ-NF-004, C3)
    - **Assign Storage Location** (UC-003; REQ-003; REQ-NF-004, C3)
      - Assign Storage Location (ACT-003) — REQ-003
    - **Put Away Goods to Storage Zone** (UC-004; REQ-004)
      - Put Away Goods from Receiving to Storage Zone (ACT-004) — REQ-004
  - **Pick Goods** (UC-005, UC-006; REQ-005, REQ-006)
    - **Select and Execute Picking Strategy** (UC-006; REQ-006)
      - Execute Picking Strategy (Wave, Batch, Zone) (ACT-006) — REQ-006
    - **Pick Items for Outgoing Order** (UC-005; REQ-005)
      - Pick Items for Outgoing Order (ACT-005) — REQ-005
  - **Pack Goods** (UC-007 steps 1–3; REQ-007)
    - **Pack Picked Items** (UC-007 steps 1–3; REQ-007)
      - Pack Picked Items for Outgoing Order (ACT-007) — REQ-007
  - **Ship Goods** (UC-007 steps 4–6; REQ-007)
    - **Ship Packed Order** (UC-007 steps 4–6; REQ-007)
      - Ship Packed Order (ACT-008) — REQ-007
  - **Manage Inventory** (UC-008, UC-009, UC-010; REQ-008, REQ-009, REQ-010)
    - **Integrate with External ERP System** (UC-008; REQ-008)
      - Process External ERP Request via REST API (ACT-009) — REQ-008
    - **Record Barcode Scans for Inventory Movements** (UC-009; REQ-009)
      - Record Barcode Scan for Inventory Movement (ACT-010) — REQ-009
    - **Maintain and Report Real-Time Inventory Levels** (UC-010; REQ-010)
      - Update Real-Time Inventory Levels per Storage Location (ACT-011) — REQ-010
      - Compile and Report Real-Time Inventory Levels per Storage Location (ACT-012) — REQ-010
  - **Record Barcode Scans (Enabling Function)** (UC-009; REQ-009) — cross-cutting, invoked by Receive Goods (ACT-001), Store Goods (ACT-004), Pick Goods (ACT-005), Pack Goods (ACT-007), Ship Goods (ACT-008)
    - **Record Scan per Inventory Movement** (UC-009; REQ-009)
      - Record Barcode Scan for Inventory Movement (ACT-010) — REQ-009
  - **Report Real-Time Inventory (Enabling Function)** (UC-010; REQ-010) — cross-cutting, fed by completed movements of Receive/Store/Pick/Pack/Ship
    - **Report Inventory Levels on Request** (UC-010; REQ-010)
      - Compile and Report Real-Time Inventory Levels per Storage Location (ACT-012) — REQ-010

## Notes

- **Hierarchy depth**: 4 levels (Level 1 root → Level 2 functions → Level 3 sub-functions → Level 4 activity leaves).
- **Leaf count**: 15 activity leaf placements covering 12 distinct activities (ACT-010 and ACT-012 each appear twice — once under Manage Inventory, once under their enabling function — reflecting their cross-cutting character; each activity traces to exactly one use case and its requirement IDs).
- **Parent-child rule**: every activity leaf has exactly one parent sub-function per placement; the dual placement of ACT-010 and ACT-012 is an explicit cross-cutting annotation, not a decomposition ambiguity.
- **Traceability**: each leaf names its activity (ACT-NNN) and direct requirement IDs; sub-function headers name their use case(s) and requirements. Full activity detail, decision points, inputs, and outputs are in `functional/ACTIVITIES.md`.
- **Behavior only**: no logical blocks, technologies, or equipment are identified here; the morphological box solution options (e.g., AS/RS, RF-scan picking, automated sortation) remain Logical-phase content per `requirements/BOX.md`.
- **Gaps carried forward** (see `functional/ACTIVITIES.md` Gaps section): REQ-008 interface detail, REQ-NF-005 permission matrix, REQ-006 strategy semantics, C3 cold-storage trigger attribute and tolerance band, purchase order origin (REQ-002/REQ-008), sortation (UC-007 steps 4–6 only), REQ-NF-003 measurement window.

## Rules:
- Document parent-child functional relationships hierarchically.
- Leaf nodes should correspond to activities (ACT-NNN) defined in ACTIVITIES.md.
- Ensure every activity is placed under exactly one parent function.