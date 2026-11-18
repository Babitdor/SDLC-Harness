---
type: Use Case Document
title: Actors and Use Cases
description: Use cases and actors derived from requirements, with triggers, preconditions, and success scenarios.
tags: [use-cases, mbse]
timestamp: 2026-09-08T18:48:32Z
resource: requirements/USECASES.md
---

# Actors

- **Operator** — Role-based access control role named in REQ-NF-005. Primary actor of all warehouse process use cases. The source names no person roles beyond the RBAC roles, so the operator is specialized by the process area named in the respective requirement: Operator (receiving) per REQ-001/REQ-002, Operator (put-away) per REQ-003/REQ-004, Operator (picking) per REQ-005/REQ-006, Operator (packing & shipping) per REQ-007. Per-role permissions are not defined in the source (see Gaps).
- **Viewer** — Role-based access control role named in REQ-NF-005. Primary actor of the inventory reporting use case (UC-010), which is read access. Per-role permissions are not defined in the source (see Gaps).
- **Administrator** — Role-based access control role named in REQ-NF-005. No functional requirement REQ-001..REQ-010 assigns a distinct goal to the administrator role, so the administrator is not the primary actor of any derived use case; it accesses the system under RBAC like the other roles. Per-role permissions are not defined in the source (see Gaps).
- **ERP System** — External system that integrates with the warehouse management system via a REST API (REQ-008). Primary actor of UC-008.
- **Warehouse Management System** — The system under consideration. Secondary actor in every use case: it records receipts and movements, assigns storage locations, directs and confirms picking, confirms packing and shipping, provides the REST API, records barcode scans, and reports inventory levels.

# Use Cases

UC-001: Receive Incoming Goods at Receiving Dock
  Actor: Operator (receiving)
  Supporting Actors: Warehouse Management System
  Trigger: Incoming goods arrive at a designated receiving dock (REQ-001).
  Precondition: A designated receiving dock is available (REQ-001); the operator is authenticated and authorized under role-based access control (REQ-NF-005).
  Related Requirements: REQ-001 (primary); REQ-002, REQ-009 via included use cases.
  Constraints / Quality Attributes: REQ-NF-005 (RBAC); REQ-NF-003 (system availability during operation).
  Main Success Scenario:
    1. The Operator registers the arrival of the incoming goods at the receiving dock in the system.
    2. The system creates a receipt record for the incoming goods at the dock.
    3. The Operator scans the barcodes of the received goods; the system records the scans for the inventory movement (Includes UC-009).
    4. The system verifies the received goods against the purchase order (Includes UC-002).
    5. The system confirms completion of the receiving operation to the Operator.
  Alternate Flows:
    - A1: Verification returns a mismatch (goods do not match the purchase order) — the system records the mismatch and the receipt is not confirmed as verified; continue per UC-002 alternate flow.
    - A2: A barcode scan cannot be captured for the movement — the system does not record the movement as completed until a scan is captured (REQ-009).
  Includes: UC-002, UC-009
  Postconditions: The receipt of the goods at the receiving dock is recorded in the system; barcode scans for the movement exist; a verification result (match/mismatch) is recorded.

UC-002: Verify Received Goods Against Purchase Order
  Actor: Operator (receiving)
  Supporting Actors: Warehouse Management System
  Trigger: Received goods are presented for verification during receiving (REQ-002).
  Precondition: Goods have been received at a dock (UC-001); purchase order data for the expected goods is available in the system.
  Related Requirements: REQ-002 (primary).
  Constraints / Quality Attributes: REQ-NF-005 (RBAC).
  Main Success Scenario:
    1. The Operator selects the receipt to be verified in the system.
    2. The system retrieves the purchase order associated with the receipt.
    3. The system compares the received goods against the purchase order.
    4. The system confirms that the goods match the purchase order.
    5. The system records the verification result (match).
  Alternate Flows:
    - A1: The goods do not match the purchase order — the system records the verification result (mismatch) and does not confirm the goods as verified (REQ-002 verification covers matching and mismatching goods).
  Includes: —
  Postconditions: A verification result (match or mismatch) is recorded for the received goods.

UC-003: Assign Storage Location
  Actor: Operator (put-away)
  Supporting Actors: Warehouse Management System
  Trigger: Received and verified goods require a storage location (follows UC-001/UC-002; REQ-003).
  Precondition: The product's size, weight, and hazard class are available to the system as assignment inputs (REQ-003); the operator is authenticated and authorized under RBAC (REQ-NF-005).
  Related Requirements: REQ-003 (primary).
  Constraints / Quality Attributes: REQ-NF-004 (hazardous-material storage physically segregated from general storage); REQ-NF-001 (system manages at least 10,000 SKUs — assignment operates on the SKU portfolio); C1 (floor area ≤ 5,000 m²), C2 (rack height ≤ 12 m), C3 (general storage 15–25 °C, cold storage 2–8 °C) bound the storage locations that can be assigned; REQ-NF-005 (RBAC).
  Main Success Scenario:
    1. The Operator requests a storage location for the received and verified goods.
    2. The system retrieves the product's size, weight, and hazard class.
    3. The system assigns a storage location based on the product's size, weight, and hazard class (REQ-003).
    4. The system communicates the assigned storage location to the Operator.
  Alternate Flows:
    - A1: The hazard class identifies the goods as hazardous material — the system assigns a location in the physically segregated hazardous-material storage (REQ-NF-004).
    - A2: No storage location satisfies the size, weight, and hazard class criteria — the system reports that no location can be assigned.
  Includes: —
  Postconditions: A storage location consistent with the product's size, weight, and hazard class is assigned and communicated to the operator.

UC-004: Put Away Goods from Receiving to Storage Zone
  Actor: Operator (put-away)
  Supporting Actors: Warehouse Management System
  Trigger: Goods have an assigned storage location and are ready for put-away (follows UC-003; REQ-004).
  Precondition: A storage location has been assigned (UC-003); the goods are present at receiving; the operator is authenticated and authorized under RBAC (REQ-NF-005).
  Related Requirements: REQ-004 (primary); REQ-003, REQ-009 via included use cases; REQ-010 (movement is reflected in per-location levels).
  Constraints / Quality Attributes: REQ-NF-004 (hazardous materials are put away in physically segregated storage); C3 (storage zones are held at general 15–25 °C or cold 2–8 °C); REQ-NF-005 (RBAC).
  Main Success Scenario:
    1. The Operator retrieves the assigned storage location for the goods from the system.
    2. The Operator transfers the goods from receiving to the assigned storage zone.
    3. The Operator scans the barcodes for the movement; the system records the scans (Includes UC-009).
    4. The system confirms the put-away and records the goods at the assigned storage location.
    5. The put-away movement is reflected in the real-time inventory levels per storage location (REQ-010).
  Alternate Flows:
    - A1: The goods are hazardous material — the put-away destination is the physically segregated hazardous-material storage (REQ-NF-004).
    - A2: The put-away cannot be completed — the system does not confirm the put-away and the movement is not recorded as completed (REQ-009).
  Includes: UC-003, UC-009
  Postconditions: The goods are stored in the assigned storage zone; barcode scans for the movement exist; the inventory level of the destination storage location reflects the put-away.

UC-005: Pick Items for Outgoing Order
  Actor: Operator (picking)
  Supporting Actors: Warehouse Management System
  Trigger: An outgoing order is released for picking (REQ-005).
  Precondition: An outgoing order exists and is released for picking; the storage locations of the ordered items are known to the system (REQ-003, REQ-010); the operator is authenticated and authorized under RBAC (REQ-NF-005).
  Related Requirements: REQ-005 (primary); REQ-009 via included use case; REQ-010 (per-location levels identify pick sources).
  Constraints / Quality Attributes: REQ-NF-002 (sustained order throughput of 500 orders per hour); REQ-NF-005 (RBAC).
  Main Success Scenario:
    1. The system creates a picking task for the outgoing order.
    2. The system provides the Operator with the storage locations of the items to be picked.
    3. The Operator retrieves the items from the storage locations.
    4. The Operator scans the item barcodes; the system records the scans for the movement (Includes UC-009).
    5. The system confirms the picked items against the outgoing order.
  Alternate Flows:
    - A1: An item is not available at the indicated storage location — the system records the discrepancy and does not confirm the pick for that item (consistent with REQ-010 verification of reported vs. actual per-location levels).
  Includes: UC-009
  Postconditions: The picked items are confirmed against the outgoing order; barcode scans for the movement exist; the inventory levels of the pick locations reflect the removal.

UC-006: Execute Picking Strategy (Wave, Batch, Zone)
  Actor: Operator (picking)
  Supporting Actors: Warehouse Management System
  Trigger: Outgoing orders are due for picking and a picking strategy is applied (REQ-006).
  Precondition: Outgoing orders are available for picking (REQ-005); the operator is authenticated and authorized under RBAC (REQ-NF-005).
  Related Requirements: REQ-006 (primary); REQ-005, REQ-009 via included use cases.
  Constraints / Quality Attributes: REQ-NF-002 (sustained order throughput of 500 orders per hour); REQ-NF-005 (RBAC).
  Main Success Scenario:
    1. The system groups the outgoing orders for picking according to the applicable strategy — wave, batch, or zone (REQ-006).
    2. The Operator executes picking for the grouped orders (Includes UC-005).
    3. The system confirms completion of picking for each order in the group.
  Alternate Flows:
    - A1 (Wave): The system releases the outgoing orders as waves; picking is executed wave by wave (REQ-006).
    - A2 (Batch): The system combines items of multiple outgoing orders into batch picks (REQ-006).
    - A3 (Zone): The system organizes picking by storage zones; picking is executed zone by zone (REQ-006).
  Includes: UC-005
  Postconditions: All outgoing orders in the strategy group are picked and confirmed per order; barcode scans for the picking movements exist.

UC-007: Pack and Ship Outgoing Order
  Actor: Operator (packing & shipping)
  Supporting Actors: Warehouse Management System
  Trigger: Picked items of an outgoing order are ready for packing (follows UC-005; REQ-007).
  Precondition: The items of the outgoing order have been picked (UC-005); the operator is authenticated and authorized under RBAC (REQ-NF-005).
  Related Requirements: REQ-007 (primary); REQ-009 via included use case; REQ-010 (shipping is reflected in per-location levels).
  Constraints / Quality Attributes: REQ-NF-002 (sustained order throughput of 500 orders per hour); REQ-NF-005 (RBAC).
  Main Success Scenario:
    1. The Operator packs the picked items for the outgoing order.
    2. The Operator scans the barcodes for the packing movement; the system records the scans (Includes UC-009).
    3. The system confirms completion of packing.
    4. The Operator ships the packed order.
    5. The Operator scans the barcodes for the shipping movement; the system records the scans (Includes UC-009).
    6. The system confirms shipment of the order.
  Alternate Flows:
    - A1: Packing cannot be completed — the order is not shipped and the movement is not recorded as completed (REQ-009).
  Includes: UC-009
  Postconditions: The order is packed and shipped; barcode scans for the packing and shipping movements exist; the inventory levels of the affected storage locations reflect the shipped goods.

UC-008: Integrate with External ERP System via REST API
  Actor: ERP System
  Supporting Actors: Warehouse Management System
  Trigger: The external ERP system sends a request to the system's REST API (REQ-008).
  Precondition: The system's REST API is reachable by the external ERP system (REQ-008); the service is available (REQ-NF-003).
  Related Requirements: REQ-008 (primary).
  Constraints / Quality Attributes: REQ-NF-003 (99.9 percent service availability of the integration interface).
  Main Success Scenario:
    1. The external ERP system sends a request to the system's REST API.
    2. The system processes the request.
    3. The system returns a response to the ERP system via the REST API.
  Alternate Flows:
    - A1: The request cannot be processed — the system returns an error response to the ERP system via the REST API.
  Includes: —
  Postconditions: The ERP request has been processed and a response has been returned via the REST API.

UC-009: Record Barcode Scan for Inventory Movement
  Actor: Operator (receiving / put-away / picking / packing & shipping — the role performing the movement)
  Supporting Actors: Warehouse Management System
  Trigger: An inventory movement is performed in any process area (receiving, put-away, picking, packing, shipping) (REQ-009).
  Precondition: The movement is executed under the system; a barcode is present for the goods/movement being scanned.
  Related Requirements: REQ-009 (primary).
  Constraints / Quality Attributes: REQ-NF-005 (RBAC).
  Main Success Scenario:
    1. The Operator scans the barcode(s) associated with the inventory movement.
    2. The system records the scan and associates it with the inventory movement.
    3. The system stores the scan record such that a scan record exists for every inventory movement (REQ-009 completeness).
  Alternate Flows:
    - A1: The barcode cannot be read — no scan is recorded and the movement is not recorded as completed until a scan is captured (REQ-009 completeness).
  Includes: —
  Postconditions: A scan record exists for the inventory movement.

UC-010: Report Real-Time Inventory Levels per Storage Location
  Actor: Viewer
  Supporting Actors: Warehouse Management System
  Trigger: The user requests current inventory levels (REQ-010).
  Precondition: The user is authenticated and authorized under role-based access control (REQ-NF-005); inventory movements are recorded in the system (REQ-009).
  Related Requirements: REQ-010 (primary); REQ-009 (movement records feed the reported levels).
  Constraints / Quality Attributes: REQ-NF-005 (RBAC — viewer role); REQ-NF-001 (reporting spans the managed SKU portfolio of at least 10,000 SKUs).
  Main Success Scenario:
    1. The Viewer requests real-time inventory levels.
    2. The system compiles the current inventory levels per storage location.
    3. The system reports the levels to the Viewer in real time (REQ-010).
  Alternate Flows:
    - A1: A storage location holds no inventory — the system reports an empty level for that location (REQ-010 covers levels per storage location).
  Includes: —
  Postconditions: The reported per-location inventory levels correspond to the actual inventory per storage location (REQ-010 verification basis).

# Traceability Matrix

| Use Case | Primary Actor | Supporting Actors | Traced Requirements (direct) | Traced Requirements (via Includes) | Constraints / NFRs Referenced |
|---|---|---|---|---|---|
| UC-001 | Operator (receiving) | Warehouse Management System | REQ-001 | REQ-002 (UC-002), REQ-009 (UC-009) | REQ-NF-005, REQ-NF-003 |
| UC-002 | Operator (receiving) | Warehouse Management System | REQ-002 | — | REQ-NF-005 |
| UC-003 | Operator (put-away) | Warehouse Management System | REQ-003 | — | REQ-NF-004, REQ-NF-001, C1, C2, C3, REQ-NF-005 |
| UC-004 | Operator (put-away) | Warehouse Management System | REQ-004 | REQ-003 (UC-003), REQ-009 (UC-009) | REQ-NF-004, C3, REQ-NF-005, REQ-010 |
| UC-005 | Operator (picking) | Warehouse Management System | REQ-005 | REQ-009 (UC-009) | REQ-NF-002, REQ-NF-005, REQ-010 |
| UC-006 | Operator (picking) | Warehouse Management System | REQ-006 | REQ-005 (UC-005), REQ-009 (via UC-005) | REQ-NF-002, REQ-NF-005 |
| UC-007 | Operator (packing & shipping) | Warehouse Management System | REQ-007 | REQ-009 (UC-009) | REQ-NF-002, REQ-NF-005, REQ-010 |
| UC-008 | ERP System | Warehouse Management System | REQ-008 | — | REQ-NF-003 |
| UC-009 | Operator (movement-performing role) | Warehouse Management System | REQ-009 | — | REQ-NF-005 |
| UC-010 | Viewer | Warehouse Management System | REQ-010 | — | REQ-NF-005, REQ-NF-001 |

Coverage check: REQ-001 → UC-001; REQ-002 → UC-002 (included in UC-001); REQ-003 → UC-003 (included in UC-004); REQ-004 → UC-004; REQ-005 → UC-005 (included in UC-006); REQ-006 → UC-006; REQ-007 → UC-007; REQ-008 → UC-008; REQ-009 → UC-009 (included in UC-001, UC-004, UC-005, UC-007); REQ-010 → UC-010 (referenced in UC-004, UC-005, UC-007). All 10 functional requirements are covered; every use case traces to at least one requirement ID.

# Quality Attributes and Constraints (not use cases)

The following are non-functional requirements and constraints from REQUIREMENTS.md / RULES.md. They are not use cases; they are referenced as quality attributes or constraints on the use cases listed.

- REQ-NF-005 / C8 (RBAC, roles: administrator, operator, viewer): applies to every use case involving system access (UC-001..UC-010). Permission matrix per role is not defined in the source (see Gaps).
- REQ-NF-004 / C4 (hazardous-material storage physically segregated): applies to UC-003 (hazard-class-based assignment) and UC-004 (put-away destination).
- REQ-NF-001 / C7 (at least 10,000 distinct SKUs): system-wide capacity attribute; directly exercised where SKU master data and the SKU portfolio are used (UC-003, UC-010).
- REQ-NF-002 / C5 (500 orders per hour sustained): performance attribute on the order-driven use cases UC-005, UC-006, UC-007.
- REQ-NF-003 / C6 (99.9 percent service availability): system-wide availability attribute; directly relevant to UC-008 (REST API integration) and to all operator use cases during operation.
- C1 (floor area ≤ 5,000 m²) and C2 (rack height ≤ 12 m): physical constraints bounding the storage locations assigned in UC-003 and used in UC-004.
- C3 (general storage 15–25 °C, cold storage 2–8 °C): environmental constraint on the storage zones referenced in UC-003 and UC-004.

Note: the solution options and selections recorded in `requirements/BOX.md` (e.g., AS/RS, RF-scan picking, packing line) are solution-side content and were deliberately not used as a basis for any use case; use cases are derived exclusively from REQ-001..REQ-010.

# Gaps and Ambiguities (flagged, not filled)

- REQ-008 (declared in source): no API endpoints, data formats, or ERP systems are specified. UC-008 is therefore kept at the abstraction level of "request/response via REST API"; no interface detail is invented.
- REQ-NF-005 (declared in source): role names administrator, operator, viewer are defined, but no permission matrix per role exists. Use cases name the roles but cannot state per-role permissions; the mapping of Viewer to UC-010 reflects the read orientation of reporting and remains subject to the undefined permission matrix.
- REQ-NF-003 (declared in source): no measurement window or planned-downtime handling is defined; availability is referenced as a quality attribute only.
- C3 (declared in source): no tolerance band, monitoring granularity, or humidity limits are defined; temperature ranges are referenced as a constraint only.
- REQ-006: the wave, batch, and zone strategies are named but not defined in the source. The alternate flows A1–A3 of UC-006 restate the named strategies without adding semantics (grouping/release rules are unspecified).
- Purchase order origin: REQ-002 requires verification against purchase orders, but the source does not state which system provides purchase orders. UC-002 therefore assumes only that purchase order data is available in the system; the supply path is part of the REQ-008 interface gap.