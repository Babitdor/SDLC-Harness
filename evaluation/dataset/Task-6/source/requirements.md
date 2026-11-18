# Requirements Specification — Warehouse Order Fulfilment Process

Document: SPEC-WOF-006
Revision: B
Status: Released for process modelling
Scope: The fulfilment process of a single distribution centre, from receipt of a
customer order to hand-over at the shipping dock. Covers ambient and chilled
goods and a segregated hazardous-materials area.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| GS1 General Specifications | GS1-128 barcode and SSCC identification | Shipping labels |
| 49 CFR Parts 172 and 177 | Hazardous materials marking, labelling and segregation (US DOT) | Hazmat packing and loading |
| NFPA 400 | Hazardous Materials Code | Hazmat storage area |
| ISO 9001 | Quality management systems | Process control |

---

## 2. Functional Requirements

**REQ-001 — Order reception**
The system shall receive customer orders from the order management interface and
reject any order that fails structural validation.
*Verification:* Test — submit valid and malformed orders.

**REQ-002 — Inventory check**
The system shall check available inventory for every order line against the
warehouse management database before release to picking.
*Verification:* Test — orders against known stock levels.

**REQ-003 — Pick routing**
The system shall route each in-stock order line to the picking zone that holds
the item and generate a pick list with storage locations.
*Verification:* Test — multi-zone order; inspect generated pick lists.

**REQ-004 — Backorder creation**
The system shall create a backorder record for each order line that cannot be
filled from available inventory.
*Verification:* Test — order containing an out-of-stock line.

**REQ-005 — Supplier notification**
The system shall notify the supplier through its API within 15 minutes of a
backorder being created, stating the item and the quantity required.
*Verification:* Test — backorder creation with API trace.

**REQ-006 — Item collection**
Pickers shall collect each order line from its pick location and confirm the pick
by scanning the location and item barcodes.
*Verification:* Demonstration — pick cycle with scanner log.

**REQ-007 — Item verification**
The system shall verify every collected item against the order line by barcode
scan before packing and shall route any mismatch to an exception station.
*Verification:* Test — inject a wrong-item pick.

**REQ-008 — Packing and labelling**
The system shall pack verified items and apply a GS1-128 shipping label carrying
the shipment's SSCC.
*Verification:* Inspection — label verification against GS1 specification.

**REQ-009 — Shipping hand-over**
The system shall route each labelled package to the shipping lane of its assigned
carrier.
*Verification:* Test — packages for three carriers.

---

## 3. Non-Functional Requirements

**REQ-NF-001 — Throughput**
The process shall fulfil at least 500 orders per hour at peak.
*Verification:* Test — peak-hour simulation with live pick crews.

**REQ-NF-002 — Picking accuracy**
The process shall achieve a picking accuracy of at least 99.5 %.
*Verification:* Analysis — verification-scan exception rate over 30 days.

**REQ-NF-003 — Cycle time**
The process shall complete each order from receipt to shipping hand-over within
30 minutes.
*Verification:* Analysis — timestamps over 30 days, 95th percentile.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Ambient picking zone temperature | 15–25 °C | REQ-003 |
| C2 | Chilled picking zone temperature | 2–8 °C | REQ-003 |
| C3 | Hazardous materials | Picked and packed only in the segregated hazmat area | REQ-006, REQ-008 |
| C4 | Shipping label | GS1-128 with SSCC | REQ-008 |
| C5 | Supplier notification delay | ≤ 15 min | REQ-005 |

---

## 5. Open Points

- For an order with some lines in stock and some backordered, it is not decided
  whether the in-stock lines ship immediately (split shipment) or wait for the
  backordered lines.
- The exception-handling process at the exception station is out of scope.
