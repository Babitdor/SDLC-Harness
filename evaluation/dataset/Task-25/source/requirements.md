# Requirements — Minimal Warehouse Management System

Document: SPEC-WMS-MIN-001
Status: Released for modelling
Scope: A deliberately minimal warehouse — one receiving zone, one storage zone and
one shipping zone joined by a single conveyor. Intended as the smallest complete
model build, so that the cost of a full RFLP pass can be measured on the least
possible content.

---

## 1. Functional Requirements

**REQ-001 — Receiving**
The warehouse shall provide one receiving zone at which inbound goods are
accepted.
*Verification:* Demonstration — inbound delivery accepted at the receiving zone.

**REQ-002 — Storage**
The warehouse shall provide one storage zone in which received goods are held
until dispatch.
*Verification:* Inspection — layout shows one storage zone.

**REQ-003 — Shipping**
The warehouse shall provide one shipping zone from which outbound goods are
dispatched.
*Verification:* Demonstration — outbound dispatch from the shipping zone.

**REQ-004 — Material transport**
The warehouse shall move goods between the receiving, storage and shipping zones
by a single conveyor connecting all three zones.
*Verification:* Inspection — layout shows one conveyor joining all three zones.

**REQ-005 — Hazardous goods handling**
The warehouse shall store hazardous goods in a location isolated from the main
storage aisle.
*Verification:* Inspection — hazardous storage location separated from the main aisle.

---

## 2. Constraints

| ID | Constraint | Value |
|---|---|---|
| C1 | Total floor area | ≤ 2000 m² |
| C2 | Receiving zones | exactly 1 |
| C3 | Storage zones | exactly 1 |
| C4 | Shipping zones | exactly 1 |
| C5 | Conveyors | exactly 1, connecting all three zones |
| C6 | Hazardous goods | isolated from the main storage aisle |

---

## 3. Open Points

Throughput, rack height, storage technology and the dimensions of each zone are
not specified. Where a model element needs one of these values, it is to be
stated as an assumption rather than presented as a requirement.
