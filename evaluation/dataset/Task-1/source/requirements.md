# Requirements Specification — Warehouse Management System

Document: SPEC-WMS-001
Revision: B
Status: Released for architecture
Scope: A single-site distribution warehouse of up to 5,000 m² handling general,
chilled and hazardous goods: receiving, storage, picking, packing, shipping and
inventory management, with integration to the enterprise ERP. Excludes
transport beyond the shipping dock.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| EN 15512 | Steel static storage systems — Adjustable pallet racking — Structural design | Rack design |
| EN 528 | Rail dependent storage and retrieval equipment — Safety requirements | AS/RS cranes |
| NFPA 30 | Flammable and Combustible Liquids Code | Hazmat storage area |
| NFPA 400 | Hazardous Materials Code | Hazmat segregation |
| GS1 General Specifications | Barcode identification and SSCC | Scanning and labelling |

---

## 2. Functional Requirements

**REQ-001 — Receiving**
The system shall receive inbound goods at designated receiving docks.
*Verification:* Demonstration — inbound truck unload.

**REQ-002 — Receipt verification**
The system shall verify received goods against the purchase order and flag every
quantity or item discrepancy.
*Verification:* Test — receipts with matching and mismatching quantities.

**REQ-003 — Location assignment**
The system shall assign each received item a storage location based on its size,
weight and hazard class.
*Verification:* Test — items of each hazard class and size band.

**REQ-004 — Put-away**
The system shall direct put-away from receiving to the assigned storage location.
*Verification:* Test — put-away task generation and confirmation.

**REQ-005 — Picking**
The system shall generate and manage pick tasks for outbound orders.
*Verification:* Test — pick task lifecycle.

**REQ-006 — Picking strategies**
The system shall support wave, batch and zone picking strategies.
*Verification:* Demonstration — each strategy on a sample order set.

**REQ-007 — Packing and shipping**
The system shall direct packing and assign each package to a shipping lane.
*Verification:* Test — package routing to three carriers.

**REQ-008 — ERP integration**
The system shall exchange orders, receipts and inventory with the ERP through a
REST API.
*Verification:* Test — interface test suite.

**REQ-009 — Movement recording**
The system shall record a barcode scan for every inventory movement.
*Verification:* Inspection — audit trail completeness over one shift.

**REQ-010 — Inventory reporting**
The system shall report current inventory for every storage location in real time.
*Verification:* Test — report after a movement, within 5 s.

---

## 3. Non-Functional Requirements

**REQ-NF-001 — SKU capacity**
The system shall manage at least 10,000 distinct SKUs.
*Verification:* Test — load 10,000 SKUs.

**REQ-NF-002 — Throughput**
The warehouse shall process at least 500 outbound orders per hour at peak.
*Verification:* Test — peak-hour simulation.

**REQ-NF-003 — Availability**
The system shall be available at least 99.9 % of scheduled operating time.
*Verification:* Analysis — architecture redundancy and operating data.

**REQ-NF-004 — Hazmat segregation**
Hazardous materials shall be stored in an area physically separated from general
storage by a 2-hour fire-rated barrier.
*Verification:* Inspection — layout and barrier certification.

**REQ-NF-005 — Access control**
The system shall enforce role-based access for administrator, operator and viewer
roles.
*Verification:* Test — permission matrix for each role.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Warehouse floor area | ≤ 5,000 m² | REQ-003 |
| C2 | Rack height | ≤ 12 m | REQ-003 |
| C3 | General storage temperature | 15–25 °C | REQ-003 |
| C4 | Chilled storage temperature | 2–8 °C | REQ-003 |
| C5 | Hazmat area separation | 2-hour fire-rated barrier | REQ-NF-004 |
| C6 | Peak outbound throughput | ≥ 500 orders/h | REQ-NF-002 |

---

## 5. Open Points

- The split of floor area between general, chilled and hazmat storage is not
  given.
- Receiving dock count and door dimensions are not specified.
