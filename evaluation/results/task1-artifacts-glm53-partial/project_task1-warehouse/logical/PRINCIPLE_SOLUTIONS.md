---
type: Principle Solutions Document
title: Principle Solutions — Morphological Combinations
description: Selected solution combinations from the morphological box with rationale for each selection.
tags: [principle-solutions, mbse]
timestamp: 2026-09-08T18:48:32Z
resource: logical/PRINCIPLE_SOLUTIONS.md
---

# Solution A — Automated Goods Flow with Perpetual WMS Inventory (CS-001)

**Concept ID**: CS-001
**Status**: Selected concept — adopted verbatim as the user's authoritative selection from `requirements/BOX.md`. The selection is recorded as given; it is not re-evaluated, re-scored, or substituted in this phase. Unselected options in the morphological box are out of scope for this synthesis.

| Function     | Selected Option |
|--------------|-----------------|
| Receive Goods   | Automated Unloading Conveyor |
| Store Goods     | Automated Storage & Retrieval System (AS/RS) |
| Pick Goods      | RF-Scan Barcode Picking |
| Pack Goods      | Semi-Automated Packing Line |
| Ship Goods      | Automated Sortation & Loading |
| Manage Inventory | Perpetual WMS Inventory |

Rationale: The six selections form one coherent end-to-end goods flow: the automated unloading conveyor induces incoming goods to the receiving scan/verification point without manual forklift transfer (ACT-001, ACT-002); the AS/RS stores and retrieves unit loads under logical location assignment (ACT-003, ACT-004); RF-scan barcode picking executes strategy-grouped picks with operator guidance (ACT-005, ACT-006); the semi-automated packing line closes picked orders (ACT-007); automated sortation and loading dispatch packed orders (ACT-008). The perpetual WMS inventory backbone (ACT-009, ACT-011, ACT-012) reflects every completed movement — gated by barcode scan completeness (ACT-010) — into real-time per-location levels and exposes them to the ERP via the REST API. No option combination is invented: every row is taken verbatim from the BOX.md selected-concept table.

## Function Selections — Activities Served and Rules to Satisfy

### F1 — Receive Goods: Automated Unloading Conveyor
- **Serves activities**: ACT-001 (register arrival, create receipt record, record scans, confirm completion), ACT-002 (verify against purchase order; match/mismatch branch).
- **Realized functions**: Receive Goods → Register Goods Arrival and Create Receipt; Verify Goods Against Purchase Order.
- **Rules to satisfy**: C1 (dock and induction footprint within the 5,000 m² floor area), C5 (receiving pace contributes to 500 orders/h), C6 (availability during operation), C8 (operator session authorized under RBAC).
- **Design constraints introduced by the option**: goods are presented to the scan point by the conveyor, so the REQ-009 completeness gate (ACT-010: no scan → movement not completed) must be enforced at the induction/scan interface; a verification mismatch (ACT-002 A1) must block downstream storage assignment because ACT-003 requires received *and verified* goods.

### F2 — Store Goods: Automated Storage & Retrieval System (AS/RS)
- **Serves activities**: ACT-003 (assign location from size, weight, hazard class; hazmat branch; temperature-zone routing; no-location branch), ACT-004 (put-away to assigned zone; scans; level update).
- **Realized functions**: Store Goods → Assign Storage Location; Put Away Goods to Storage Zone.
- **Rules to satisfy**: C1 (location portfolio within 5,000 m²), C2 (rack height ≤ 12 m), C3 (general 15–25 °C, cold 2–8 °C), C4/REQ-NF-004 (physically segregated hazardous-material storage), C7 (location addressing for ≥ 10,000 SKUs), C8.
- **Design constraints introduced by the option**: the AS/RS configuration is bounded by C2 — storage/retrieval machine aisles and rack structure must stay within 12 m; the zone topology served by the AS/RS must physically realize three zone types (general, cold, segregated hazmat) inside the C1 floor budget; the cold-storage branch of ACT-003 has no triggering product attribute in the source (flagged gap — routing is bounded to the two C3 zone types, not filled).

### F3 — Pick Goods: RF-Scan Barcode Picking
- **Serves activities**: ACT-005 (pick task, location guidance, retrieval, scans, per-item confirm/discrepancy), ACT-006 (wave/batch/zone grouping and release).
- **Realized functions**: Pick Goods → Select and Execute Picking Strategy; Pick Items for Outgoing Order.
- **Rules to satisfy**: C5 (500 orders/h — the RF-guided, operator-executed picks are the manual element of an otherwise automated flow and therefore the throughput-critical stage), C7 (pick sources across ≥ 10,000 SKUs), C8.
- **Design constraints introduced by the option**: pick confirmation is scan-based, so the ACT-010 gate applies to every pick; strategy grouping (wave/batch/zone) is the pacing lever against C5, but REQ-006 defines no grouping or release rules (flagged gap — no semantics invented).

### F4 — Pack Goods: Semi-Automated Packing Line
- **Serves activities**: ACT-007 (pack picked items, record scans, confirm packing).
- **Realized function**: Pack Goods → Pack Picked Items.
- **Rules to satisfy**: C5 (line pacing must sustain the shared 500 orders/h budget), C8.
- **Design constraints introduced by the option**: the packing completion confirmation (ACT-007 step 3) is the hard gate into shipping (ACT-008); packing scan records feed the perpetual ledger via ACT-010/ACT-011.

### F5 — Ship Goods: Automated Sortation & Loading
- **Serves activities**: ACT-008 (ship packed order, record scans, confirm shipment, reflect shipment in per-location levels).
- **Realized function**: Ship Goods → Ship Packed Order.
- **Rules to satisfy**: C1 (sortation loop and loading lanes compete for the 5,000 m² floor budget alongside AS/RS, conveyor, and packing line), C5, C8.
- **Design constraints introduced by the option**: no use-case step describes a sortation action — sortation exists only as the selected Ship Goods option, so the sortation routing capability is a solution-side elaboration realized *within* ACT-008 (consistent with the ACTIVITIES.md modeling note; no separate activity is created).

### F6 — Manage Inventory: Perpetual WMS Inventory
- **Serves activities**: ACT-011 (real-time level update per storage location after each completed movement), ACT-012 (real-time reporting to the Viewer), ACT-009 (ERP REST API request/response).
- **Realized functions**: Manage Inventory → Maintain and Report Real-Time Inventory Levels; Integrate with External ERP System.
- **Rules to satisfy**: C6 (99.9 % availability of ledger, reporting, and API), C7 (levels and reports span ≥ 10,000 SKUs), C8 (viewer/administrator/operator authorization; explicit gate in ACT-012).
- **Design constraints introduced by the option**: perpetual levels are only as correct as the movement records — the REQ-009 scan-completeness gate (ACT-010 → ACT-011: no scan, no level update) is a structural dependency, not an optional feature; the REQ-008 API contract (endpoints, formats, ERP systems) is unspecified (flagged gap — kept at request/response abstraction).

## Cross-Cutting Capabilities Required by the Selected Concept

- **Barcode scan recording** (ACT-010, REQ-009): invoked at every inventory movement of the selected automated flow — receiving (ACT-001), put-away (ACT-004), picking (ACT-005), packing (ACT-007), shipping (ACT-008); a movement is complete only with a captured scan.
- **RBAC access control** (REQ-NF-005 / C8): authorization precondition of all activities ACT-001..ACT-012 for the administrator, operator, and viewer roles.
- **Temperature-zone management** (C3): routes goods between the general zone (15–25 °C) and the cold zone (2–8 °C) during storage assignment (ACT-003) and bounds put-away destinations (ACT-004).
- **Hazmat segregation management** (C4 / REQ-NF-004): routes hazardous-material goods to the physically segregated hazmat storage and keeps them out of general and cold zones (ACT-003 A1, ACT-004 A1).
- **Process orchestration**: realizes the sequential control flow and completion gates of ACT-001..ACT-008 (verification gate, scan gate, packing gate) required to keep the automated stages consistent with C5 and C6.

## Selection Constraints on the Design (adopted, not re-opened)

| Constraint interaction | Consequence for the logical architecture |
|---|---|
| AS/RS vs. C2 (rack height ≤ 12 m) | Storage/retrieval control and the location registry are bounded to a ≤ 12 m rack envelope; ACT-003 candidate locations inherit the bound. |
| Automated sortation + conveyor + packing line vs. C1 (≤ 5,000 m²) | The material-flow stages share one floor budget; the storage location/zone registry is the authoritative spatial model and must keep the total footprint within C1. |
| RF-scan picking (operator-executed) vs. C5 (500 orders/h) | Picking is the manual stage between two automated stages; strategy grouping (ACT-006) and per-location level accuracy (ACT-011 → ACT-005 step 2) are the design levers for throughput. |
| Perpetual WMS inventory vs. C6 (99.9 %) and REQ-009 | Ledger, reporting, and ERP API availability targets are carried as first-class properties; scan completeness gates every level update. |
| AS/RS zone topology vs. C3/C4 | The AS/RS must serve general (15–25 °C), cold (2–8 °C), and physically segregated hazmat zones; hazmat goods never enter general/cold circulation (flow constraint on all storage connections). |

Trade-offs: Per the directive, the selection is not re-opened and no alternative option combination is evaluated or scored; the constraints above are recorded as accepted design bounds that the logical architecture (BDD.md, IBD.md) must satisfy.

Traceability: This concept realises the activities ACT-001..ACT-012 through the functions of `functional/FUNCTION_TREE.md` (Receive Goods, Store Goods, Pick Goods, Pack Goods, Ship Goods, Manage Inventory, plus the enabling functions Record Barcode Scans and Report Real-Time Inventory), under the rules C1–C8 of `requirements/RULES.md`.

## Rules:
- Each solution selects one option per function from the Morphological Box.
- Provide rationale for each selection.
- Solutions must satisfy all constraints in RULES.md.