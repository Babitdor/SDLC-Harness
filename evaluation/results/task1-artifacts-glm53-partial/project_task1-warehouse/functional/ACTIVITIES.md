---
type: Activities Document
title: System Activities and Decision Points
description: Behavioral model of system activities derived from use cases, with sequential steps and decision logic.
tags: [activities, mbse]
timestamp: 2026-09-08T18:48:32Z
resource: functional/ACTIVITIES.md
---

# End-to-End Activity Flow

Main goods flow, in sequence (each step traces to its use case):

1. **Receiving** — ACT-001 (UC-001; REQ-001): register arrival, create receipt record, record scans (ACT-010), verify against purchase order (ACT-002), confirm completion.
2. **Verification** — ACT-002 (UC-002; REQ-002): compare received goods against purchase order; record match or mismatch.
3. **Storage assignment** — ACT-003 (UC-003; REQ-003): assign location from size, weight, hazard class; hazardous-material branch (REQ-NF-004); temperature-zone routing (C3); no-location branch.
4. **Put-away** — ACT-004 (UC-004; REQ-004): transfer goods to the assigned storage zone, record scans (ACT-010), confirm, reflect movement in per-location levels (ACT-011).
5. **Picking strategy selection** — ACT-006 (UC-006; REQ-006): group outgoing orders by wave, batch, or zone strategy.
6. **Picking** — ACT-005 (UC-005; REQ-005): create picking task, provide pick locations, retrieve items, record scans (ACT-010), confirm picks; executed per order within ACT-006.
7. **Packing** — ACT-007 (UC-007 steps 1–3; REQ-007): pack picked items, record scans (ACT-010), confirm packing.
8. **Shipping** — ACT-008 (UC-007 steps 4–6; REQ-007): ship packed order, record scans (ACT-010), confirm shipment, reflect shipment in per-location levels (ACT-011).

Cross-cutting activities:

- **ACT-010** (UC-009; REQ-009): barcode scan recording — invoked at every inventory movement (receiving ACT-001, put-away ACT-004, picking ACT-005, packing ACT-007, shipping ACT-008).
- **ACT-011** (REQ-010; REQ-009): real-time inventory level update per storage location — invoked after each completed movement.
- **ACT-012** (UC-010; REQ-010): real-time inventory reporting to the Viewer on request.
- **ACT-009** (UC-008; REQ-008): ERP REST API request/response integration (external actor: ERP System).

Modeling notes (traceability, not invented content):

- UC-007 is modeled as two activities — ACT-007 (packing) and ACT-008 (shipping) — because Pack Goods and Ship Goods are separate key functions of the goods flow.
- UC-010's movement-to-level reflection is modeled as the cross-cutting activity ACT-011, derived from UC-004 step 5 and the UC-005/UC-007 postconditions; the Viewer-facing report of UC-010 is ACT-012.
- No activity is derived from solution-side content; `requirements/BOX.md` options are excluded from behavioral derivation (see USECASES.md note).

## Activity Traceability Matrix

| Activity | Source Use Case(s) | Requirements (direct) | Requirements (via includes) |
|---|---|---|---|
| ACT-001 | UC-001 | REQ-001 | REQ-002 (UC-002), REQ-009 (UC-009) |
| ACT-002 | UC-002 | REQ-002 | — |
| ACT-003 | UC-003 | REQ-003 | — |
| ACT-004 | UC-004 | REQ-004 | REQ-003 (UC-003), REQ-009 (UC-009) |
| ACT-005 | UC-005 | REQ-005 | REQ-009 (UC-009) |
| ACT-006 | UC-006 | REQ-006 | REQ-005 (UC-005), REQ-009 (via UC-005) |
| ACT-007 | UC-007 (steps 1–3) | REQ-007 | REQ-009 (UC-009) |
| ACT-008 | UC-007 (steps 4–6) | REQ-007 | REQ-009 (UC-009) |
| ACT-009 | UC-008 | REQ-008 | — |
| ACT-010 | UC-009 | REQ-009 | — |
| ACT-011 | UC-004 (step 5), UC-005, UC-007, UC-010 | REQ-010 | REQ-009 |
| ACT-012 | UC-010 | REQ-010 | REQ-009 |

---

# Activity: Receive Incoming Goods at Receiving Dock

- **ID**: ACT-001
- **Source use case(s)**: UC-001 (main success scenario steps 1, 2, 5; steps 3–4 delegate to ACT-010 and ACT-002 per the Includes of UC-001)
- **Traced requirements**: REQ-001 (primary); REQ-009 (via UC-009), REQ-002 (via UC-002); REQ-NF-005 (RBAC), REQ-NF-003 (availability during operation)
- **Inputs**: incoming goods arriving at a designated receiving dock (UC-001 trigger; REQ-001); operator session authenticated and authorized under role-based access control (REQ-NF-005)
- **Outputs**: receipt record for the incoming goods at the dock (UC-001 step 2); receiving completion confirmation to the Operator (UC-001 step 5); verification result (match/mismatch) via ACT-002; barcode scan records via ACT-010
- **Preconditions**: a designated receiving dock is available (REQ-001); the operator is authenticated and authorized under role-based access control (REQ-NF-005)
- **Postconditions**: the receipt of the goods at the receiving dock is recorded in the system; barcode scans for the movement exist; a verification result (match/mismatch) is recorded (UC-001 postconditions)
- **Control flow**: sequential steps 1→5; step 3 invokes ACT-010 (UC-009); step 4 invokes ACT-002 (UC-002); step 5 executes only after a verification result exists and scans are captured.

Steps:
1. The Operator registers the arrival of the incoming goods at the receiving dock in the system (UC-001 step 1).
2. The system creates a receipt record for the incoming goods at the dock (UC-001 step 2; REQ-001).
3. The Operator scans the barcodes of the received goods and the system records the scans for the inventory movement — invoke ACT-010 (UC-001 step 3; includes UC-009; REQ-009).
4. The system verifies the received goods against the purchase order — invoke ACT-002 (UC-001 step 4; includes UC-002; REQ-002).
5. The system confirms completion of the receiving operation to the Operator (UC-001 step 5).

Decision Points:
- If verification returns a mismatch (goods do not match the purchase order) → the system records the mismatch and the receipt is not confirmed as verified; processing continues per the UC-002 alternate flow (UC-001 A1; ACT-002).
- If a barcode scan cannot be captured for the movement → the system does not record the movement as completed until a scan is captured (UC-001 A2; REQ-009).

---

# Activity: Verify Received Goods Against Purchase Order

- **ID**: ACT-002
- **Source use case(s)**: UC-002 (included in UC-001)
- **Traced requirements**: REQ-002 (primary); REQ-NF-005 (RBAC)
- **Inputs**: receipt selected for verification (UC-002 step 1); purchase order data for the expected goods (UC-002 precondition); received goods presented for verification (from ACT-001 / UC-001)
- **Outputs**: verification result (match or mismatch) recorded for the received goods (UC-002 steps 4–5, A1); match confirmation for matching goods (UC-002 step 4)
- **Preconditions**: goods have been received at a dock (UC-001); purchase order data for the expected goods is available in the system (UC-002 precondition)
- **Postconditions**: a verification result (match or mismatch) is recorded for the received goods (UC-002 postcondition)
- **Control flow**: sequential steps 1→5 with a match/mismatch branch at step 4; on the mismatch path the confirmation of step 4 is skipped and the mismatch result is recorded.

Steps:
1. The Operator selects the receipt to be verified in the system (UC-002 step 1).
2. The system retrieves the purchase order associated with the receipt (UC-002 step 2).
3. The system compares the received goods against the purchase order (UC-002 step 3; REQ-002).
4. The system confirms that the goods match the purchase order (UC-002 step 4) — executed only on the match path.
5. The system records the verification result, match or mismatch (UC-002 step 5 / A1).

Decision Points:
- If the goods match the purchase order → the system confirms the match and records the verification result (match) (UC-002 steps 4–5).
- If the goods do not match the purchase order → the system records the verification result (mismatch) and does not confirm the goods as verified (UC-002 A1; REQ-002 covers verification of matching and mismatching goods).

---

# Activity: Assign Storage Location

- **ID**: ACT-003
- **Source use case(s)**: UC-003 (included in UC-004)
- **Traced requirements**: REQ-003 (primary); REQ-NF-004 (hazardous-material segregation), REQ-NF-001 (SKU portfolio capacity), C1, C2, C3, REQ-NF-005 (RBAC)
- **Inputs**: storage location request for received and verified goods (UC-003 step 1); product size, weight, and hazard class (UC-003 step 2; REQ-003); storage location portfolio bounded by C1 (floor area ≤ 5,000 m²), C2 (rack height ≤ 12 m), C3 (general 15–25 °C, cold 2–8 °C), and REQ-NF-004 (physically segregated hazardous-material storage)
- **Outputs**: assigned storage location communicated to the Operator (UC-003 step 4); report that no location can be assigned (UC-003 A2)
- **Preconditions**: the product's size, weight, and hazard class are available to the system as assignment inputs (REQ-003); the operator is authenticated and authorized under RBAC (REQ-NF-005)
- **Postconditions**: a storage location consistent with the product's size, weight, and hazard class is assigned and communicated to the operator (UC-003 postcondition)
- **Control flow**: sequential steps 1→5; the eligible zone type (hazardous vs. general; general vs. cold temperature zone) is determined at step 3 before the location is assigned at step 4.

Steps:
1. The Operator requests a storage location for the received and verified goods (UC-003 step 1).
2. The system retrieves the product's size, weight, and hazard class (UC-003 step 2; REQ-003).
3. The system determines the eligible storage zone type for the goods: hazardous-material storage (physically segregated from general storage, REQ-NF-004) versus general storage, and — within non-hazardous goods — general storage (15–25 °C) versus cold storage (2–8 °C) (C3).
4. The system assigns a storage location based on the product's size, weight, and hazard class within the eligible zone type (UC-003 step 3; REQ-003); candidate locations are bounded by C1 (floor area ≤ 5,000 m²) and C2 (rack height ≤ 12 m).
5. The system communicates the assigned storage location to the Operator (UC-003 step 4).

Decision Points:
- If the hazard class identifies the goods as hazardous material → the system assigns a location in the physically segregated hazardous-material storage (UC-003 A1; REQ-NF-004); else → the system assigns within general storage, segregated from hazardous-material storage (REQ-NF-004).
- If the goods require cold storage → the system assigns a location in a cold-storage zone held at 2–8 °C; else → the system assigns a location in a general-storage zone held at 15–25 °C (C3). [Gap: the source defines no product attribute that triggers the cold-storage branch; REQ-003 names only size, weight, and hazard class as assignment inputs — flagged, not filled.]
- If no storage location satisfies the size, weight, and hazard class criteria → the system reports that no location can be assigned (UC-003 A2).

---

# Activity: Put Away Goods from Receiving to Storage Zone

- **ID**: ACT-004
- **Source use case(s)**: UC-004 (includes UC-003, UC-009)
- **Traced requirements**: REQ-004 (primary); REQ-003 (via UC-003), REQ-009 (via UC-009), REQ-010; REQ-NF-004, C3, REQ-NF-005 (RBAC)
- **Inputs**: assigned storage location (output of ACT-003 / UC-003); goods present at receiving (UC-004 precondition); operator authorization (REQ-NF-005)
- **Outputs**: put-away confirmation with the goods recorded at the assigned storage location (UC-004 step 4); barcode scan records for the movement (UC-004 step 3 / ACT-010); updated real-time inventory level of the destination location (UC-004 step 5; REQ-010 via ACT-011)
- **Preconditions**: a storage location has been assigned (UC-003); the goods are present at receiving; the operator is authenticated and authorized under RBAC (REQ-NF-005)
- **Postconditions**: the goods are stored in the assigned storage zone; barcode scans for the movement exist; the inventory level of the destination storage location reflects the put-away (UC-004 postconditions)
- **Control flow**: sequential steps 1→5; step 3 invokes ACT-010; step 5 invokes ACT-011; steps 4–5 execute only when the put-away is completed.

Steps:
1. The Operator retrieves the assigned storage location for the goods from the system (UC-004 step 1).
2. The Operator transfers the goods from receiving to the assigned storage zone (UC-004 step 2; REQ-004).
3. The Operator scans the barcodes for the movement and the system records the scans — invoke ACT-010 (UC-004 step 3; includes UC-009; REQ-009).
4. The system confirms the put-away and records the goods at the assigned storage location (UC-004 step 4).
5. The put-away movement is reflected in the real-time inventory levels per storage location — invoke ACT-011 (UC-004 step 5; REQ-010).

Decision Points:
- If the goods are hazardous material → the put-away destination is the physically segregated hazardous-material storage (UC-004 A1; REQ-NF-004); else → the destination is the assigned general-storage location from ACT-003.
- If the assigned location is in a cold-storage zone → the destination zone is held at 2–8 °C; if in a general-storage zone → held at 15–25 °C (C3).
- If the put-away cannot be completed → the system does not confirm the put-away and the movement is not recorded as completed (UC-004 A2; REQ-009).

---

# Activity: Pick Items for Outgoing Order

- **ID**: ACT-005
- **Source use case(s)**: UC-005 (includes UC-009); executed per outgoing order within ACT-006
- **Traced requirements**: REQ-005 (primary); REQ-009 (via UC-009), REQ-010; REQ-NF-002 (500 orders per hour), REQ-NF-005 (RBAC)
- **Inputs**: outgoing order released for picking (UC-005 trigger; REQ-005); storage locations of the ordered items known to the system (UC-005 precondition; REQ-003, REQ-010); operator authorization (REQ-NF-005)
- **Outputs**: picking task for the outgoing order (UC-005 step 1); storage-location information provided to the Operator (UC-005 step 2); pick confirmation of the picked items against the outgoing order (UC-005 step 5); discrepancy record for unavailable items (UC-005 A1); barcode scan records (ACT-010); updated pick-location levels (postcondition via ACT-011)
- **Preconditions**: an outgoing order exists and is released for picking; the storage locations of the ordered items are known to the system (REQ-003, REQ-010); the operator is authenticated and authorized under RBAC (REQ-NF-005)
- **Postconditions**: the picked items are confirmed against the outgoing order; barcode scans for the movement exist; the inventory levels of the pick locations reflect the removal (UC-005 postconditions)
- **Control flow**: sequential steps 1→5; step 4 invokes ACT-010; step 5 executes per item with a confirmed/not-confirmed branch; the activity runs once per outgoing order (iteration is controlled by ACT-006 over the strategy group).

Steps:
1. The system creates a picking task for the outgoing order (UC-005 step 1; REQ-005).
2. The system provides the Operator with the storage locations of the items to be picked (UC-005 step 2; REQ-010 per-location levels identify pick sources).
3. The Operator retrieves the items from the storage locations (UC-005 step 3).
4. The Operator scans the item barcodes and the system records the scans for the movement — invoke ACT-010 (UC-005 step 4; includes UC-009; REQ-009).
5. The system confirms the picked items against the outgoing order (UC-005 step 5).

Decision Points:
- If an item is available at the indicated storage location → the pick for that item is confirmed against the outgoing order (UC-005 step 5).
- If an item is not available at the indicated storage location → the system records the discrepancy and does not confirm the pick for that item (UC-005 A1; consistent with REQ-010 verification of reported versus actual per-location levels).

---

# Activity: Execute Picking Strategy (Wave, Batch, Zone)

- **ID**: ACT-006
- **Source use case(s)**: UC-006 (includes UC-005)
- **Traced requirements**: REQ-006 (primary); REQ-005 (via UC-005), REQ-009 (via UC-005); REQ-NF-002 (500 orders per hour), REQ-NF-005 (RBAC)
- **Inputs**: outgoing orders due for picking (UC-006 trigger; REQ-005, REQ-006); the applicable picking strategy — wave, batch, or zone (REQ-006); operator authorization (REQ-NF-005)
- **Outputs**: strategy group of outgoing orders (UC-006 step 1); executed picks per grouped order (UC-006 step 2 via ACT-005); per-order picking completion confirmations (UC-006 step 3); barcode scan records for the picking movements (UC-006 postcondition)
- **Preconditions**: outgoing orders are available for picking (REQ-005); the operator is authenticated and authorized under RBAC (REQ-NF-005)
- **Postconditions**: all outgoing orders in the strategy group are picked and confirmed per order; barcode scans for the picking movements exist (UC-006 postconditions)
- **Control flow**: step 1 executes once per strategy group; steps 2–3 iterate over each order in the group; step 2 invokes ACT-005 per order; the strategy branch (wave/batch/zone) is selected at step 1.

Steps:
1. The system groups the outgoing orders for picking according to the applicable strategy — wave, batch, or zone (UC-006 step 1; REQ-006).
2. The Operator executes picking for the grouped orders — invoke ACT-005 for each order in the group (UC-006 step 2; includes UC-005).
3. The system confirms completion of picking for each order in the group (UC-006 step 3).

Decision Points (picking strategy selection, REQ-006):
- If the applicable strategy is wave → the system releases the outgoing orders as waves and picking is executed wave by wave (UC-006 A1; REQ-006).
- If the applicable strategy is batch → the system combines items of multiple outgoing orders into batch picks (UC-006 A2; REQ-006).
- If the applicable strategy is zone → the system organizes picking by storage zones and picking is executed zone by zone (UC-006 A3; REQ-006).

Note: REQ-006 names the three strategies but the source defines no grouping or release rules (USECASES.md Gaps); the decision points restate the named strategies without added semantics.

---

# Activity: Pack Picked Items for Outgoing Order

- **ID**: ACT-007
- **Source use case(s)**: UC-007 (main success scenario steps 1–3; includes UC-009)
- **Traced requirements**: REQ-007 (primary); REQ-009 (via UC-009), REQ-010; REQ-NF-002 (500 orders per hour), REQ-NF-005 (RBAC)
- **Inputs**: picked items of the outgoing order (output of ACT-005 / UC-005); operator authorization (REQ-NF-005)
- **Outputs**: packed order for the outgoing order (UC-007 step 1); barcode scan records for the packing movement (UC-007 step 2 / ACT-010); packing completion confirmation (UC-007 step 3)
- **Preconditions**: the items of the outgoing order have been picked (UC-005); the operator is authenticated and authorized under RBAC (REQ-NF-005)
- **Postconditions**: packing is completed and confirmed; barcode scans for the packing movement exist (UC-007 postconditions, packing part)
- **Control flow**: sequential steps 1→3; step 2 invokes ACT-010; the packing confirmation of step 3 gates entry to ACT-008 (shipping).

Steps:
1. The Operator packs the picked items for the outgoing order (UC-007 step 1; REQ-007).
2. The Operator scans the barcodes for the packing movement and the system records the scans — invoke ACT-010 (UC-007 step 2; includes UC-009; REQ-009).
3. The system confirms completion of packing (UC-007 step 3).

Decision Points:
- If packing is completed → the system confirms completion of packing and the order becomes ready for shipping (ACT-008) (UC-007 step 3).
- If packing cannot be completed → the order is not shipped and the movement is not recorded as completed (UC-007 A1; REQ-009).

---

# Activity: Ship Packed Order

- **ID**: ACT-008
- **Source use case(s)**: UC-007 (main success scenario steps 4–6; includes UC-009)
- **Traced requirements**: REQ-007 (primary); REQ-009 (via UC-009), REQ-010; REQ-NF-002 (500 orders per hour), REQ-NF-005 (RBAC)
- **Inputs**: packed order with packing completion confirmation (output of ACT-007); operator authorization (REQ-NF-005)
- **Outputs**: shipment confirmation of the order (UC-007 step 6); barcode scan records for the shipping movement (UC-007 step 5 / ACT-010); updated real-time inventory levels of the affected storage locations reflecting the shipped goods (UC-007 postcondition; REQ-010 via ACT-011)
- **Preconditions**: the items of the outgoing order have been picked (UC-005) and packed with confirmation (UC-007 steps 1–3); the operator is authenticated and authorized under RBAC (REQ-NF-005)
- **Postconditions**: the order is packed and shipped; barcode scans for the shipping movement exist; the inventory levels of the affected storage locations reflect the shipped goods (UC-007 postconditions)
- **Control flow**: sequential steps 1→3; step 2 invokes ACT-010; step 3 triggers ACT-011 for the per-location level update; entry requires the packing confirmation of ACT-007.

Steps:
1. The Operator ships the packed order (UC-007 step 4; REQ-007).
2. The Operator scans the barcodes for the shipping movement and the system records the scans — invoke ACT-010 (UC-007 step 5; includes UC-009; REQ-009).
3. The system confirms shipment of the order (UC-007 step 6).

Decision Points:
- If packing was completed (ACT-007 confirmation exists) → the Operator ships the packed order and the system confirms shipment (UC-007 steps 4, 6).
- If packing was not completed → the order is not shipped and the movement is not recorded as completed (UC-007 A1; REQ-009).

Note: no separate sortation activity is derived — no step of UC-001..UC-010 describes a sortation action; sortation appears only as a solution option in `requirements/BOX.md` (Ship Goods), which is excluded from behavioral derivation. Shipping is modeled per UC-007 steps 4–6.

---

# Activity: Process External ERP Request via REST API

- **ID**: ACT-009
- **Source use case(s)**: UC-008
- **Traced requirements**: REQ-008 (primary); REQ-NF-003 (99.9 percent service availability of the integration interface)
- **Inputs**: request sent by the external ERP system to the system's REST API (UC-008 trigger; REQ-008); service availability (REQ-NF-003)
- **Outputs**: response returned to the ERP system via the REST API (UC-008 step 3) — processing response or error response (UC-008 A1)
- **Preconditions**: the system's REST API is reachable by the external ERP system (REQ-008); the service is available (REQ-NF-003)
- **Postconditions**: the ERP request has been processed and a response has been returned via the REST API (UC-008 postcondition)
- **Control flow**: sequential steps 1→3 with a processable/not-processable branch at step 2; one cycle per incoming ERP request (iteration over incoming requests).

Steps:
1. The external ERP system sends a request to the system's REST API (UC-008 step 1; REQ-008).
2. The system processes the request (UC-008 step 2).
3. The system returns a response to the ERP system via the REST API (UC-008 step 3).

Decision Points:
- If the request can be processed → the system returns the processing response to the ERP system via the REST API (UC-008 steps 2–3).
- If the request cannot be processed → the system returns an error response to the ERP system via the REST API (UC-008 A1).

Note: REQ-008 specifies no API endpoints, data formats, or ERP systems (USECASES.md Gaps); the activity is kept at the abstraction level of request/response via the REST API.

---

# Activity: Record Barcode Scan for Inventory Movement

- **ID**: ACT-010
- **Source use case(s)**: UC-009 (cross-cutting; included in UC-001, UC-004, UC-005, UC-007)
- **Traced requirements**: REQ-009 (primary); REQ-NF-005 (RBAC)
- **Inputs**: barcode(s) associated with the inventory movement (UC-009 step 1); the inventory movement being performed in any process area — receiving, put-away, picking, packing, shipping (UC-009 trigger; REQ-009)
- **Outputs**: scan record associated with the inventory movement (UC-009 step 2); stored scan record such that a scan record exists for every inventory movement (UC-009 step 3; REQ-009 completeness); movement-completion gate for the invoking activity
- **Preconditions**: the movement is executed under the system; a barcode is present for the goods/movement being scanned (UC-009 precondition)
- **Postconditions**: a scan record exists for the inventory movement (UC-009 postcondition)
- **Control flow**: invoked (included) at every inventory movement — ACT-001 step 3 (receiving), ACT-004 step 3 (put-away), ACT-005 step 4 (picking), ACT-007 step 2 (packing), ACT-008 step 2 (shipping); sequential steps 1→3 per scan.

Steps:
1. The Operator scans the barcode(s) associated with the inventory movement (UC-009 step 1).
2. The system records the scan and associates it with the inventory movement (UC-009 step 2; REQ-009).
3. The system stores the scan record such that a scan record exists for every inventory movement (UC-009 step 3; REQ-009 completeness).

Decision Points:
- If the barcode can be read → the scan is recorded, associated with the movement, and stored (UC-009 steps 2–3).
- If the barcode cannot be read → no scan is recorded and the movement is not recorded as completed until a scan is captured (UC-009 A1; REQ-009 completeness).

---

# Activity: Update Real-Time Inventory Levels per Storage Location

- **ID**: ACT-011
- **Source use case(s)**: UC-004 (step 5), UC-005 (postcondition), UC-007 (postcondition), UC-010 (precondition) — cross-cutting movement-to-level reflection
- **Traced requirements**: REQ-010 (primary); REQ-009 (movement records feed the reported levels)
- **Inputs**: completed inventory movement records with their scan records — put-away into a storage location (UC-004 steps 4–5), pick removal from a storage location (UC-005 step 5), shipping of goods (UC-007 step 6) (REQ-009)
- **Outputs**: current real-time inventory level per affected storage location (UC-004 step 5; REQ-010); level basis for identifying pick sources of outgoing orders (UC-005 step 2) and for real-time reporting (ACT-012 / UC-010)
- **Preconditions**: the movement is recorded as completed with an existing scan record (REQ-009; UC-009 postcondition)
- **Postconditions**: the inventory level of each affected storage location reflects the movement (UC-004 step 5; UC-005 and UC-007 postconditions)
- **Control flow**: invoked after each completed inventory movement (put-away, picking removal, shipping); sequential steps 1→3 per movement.

Steps:
1. The system takes up the completed inventory movement — put-away, pick removal, or shipping — together with its scan record (UC-004 steps 3–5, UC-005 steps 4–5, UC-007 steps 2–6; REQ-009).
2. The system updates the real-time inventory level of the affected storage location(s) to reflect the movement (UC-004 step 5; REQ-010).
3. The updated per-location levels are made available for identifying pick sources of outgoing orders (UC-005 step 2; REQ-003, REQ-010) and for real-time inventory reporting (UC-010; ACT-012).

Decision Points:
- If the movement is recorded as completed (a scan record exists for the movement) → the real-time inventory level of the affected storage location is updated (UC-004 step 5; REQ-009, REQ-010).
- If the movement is not recorded as completed (no scan captured) → the inventory level is not updated and the movement is not confirmed (UC-004 A2; UC-009 A1; REQ-009).

---

# Activity: Compile and Report Real-Time Inventory Levels per Storage Location

- **ID**: ACT-012
- **Source use case(s)**: UC-010
- **Traced requirements**: REQ-010 (primary); REQ-009 (movement records feed the reported levels); REQ-NF-005 (RBAC — viewer role), REQ-NF-001 (reporting spans the managed portfolio of at least 10,000 SKUs)
- **Inputs**: real-time inventory level request from the Viewer (UC-010 trigger; REQ-010); recorded inventory movements and per-location levels (UC-010 precondition; REQ-009; ACT-011)
- **Outputs**: real-time report of inventory levels per storage location (UC-010 step 3), including an empty level for locations without inventory (UC-010 A1)
- **Preconditions**: the user is authenticated and authorized under role-based access control (REQ-NF-005); inventory movements are recorded in the system (REQ-009)
- **Postconditions**: the reported per-location inventory levels correspond to the actual inventory per storage location (UC-010 postcondition; REQ-010 verification basis)
- **Control flow**: executed on each Viewer request; step 2 iterates over the storage locations; step 3 reports the compiled levels.

Steps:
1. The Viewer requests real-time inventory levels (UC-010 step 1).
2. The system compiles the current inventory levels per storage location (UC-010 step 2; REQ-010).
3. The system reports the levels to the Viewer in real time (UC-010 step 3; REQ-010).

Decision Points:
- If a storage location holds no inventory → the system reports an empty level for that location (UC-010 A1; REQ-010 covers levels per storage location).
- If the requester is not authenticated and authorized under RBAC → the levels are not reported (REQ-NF-005 enforcement). [Gap: the source defines the role names administrator, operator, viewer but no permission matrix per role — the authorization check is modeled as the RBAC gate only; see Gaps.]

---

## Gaps and Ambiguities (flagged, not filled)

- **REQ-008** (ACT-009): no API endpoints, data formats, or ERP systems are specified in the source; the activity is kept at the request/response abstraction level (USECASES.md Gaps).
- **REQ-NF-005** (all activities): role names administrator, operator, viewer are defined, but no permission matrix per role exists; RBAC is therefore modeled as preconditions and an authorization gate only (ACT-012 decision point).
- **REQ-006** (ACT-006): the wave, batch, and zone strategies are named but not defined; grouping and release rules are unspecified, so the strategy decision points restate the named strategies without added semantics (USECASES.md Gaps).
- **C3 temperature-zone routing** (ACT-003, ACT-004): the source defines the two zone temperature ranges (general 15–25 °C, cold 2–8 °C) but no product attribute that triggers the cold-storage branch; REQ-003 names only size, weight, and hazard class as assignment inputs. The routing decision is bounded to the two C3 zone types; the triggering input is flagged, not filled. C3 also defines no tolerance band, monitoring granularity, or humidity limits.
- **Purchase order origin** (ACT-002): REQ-002 requires verification against purchase orders, but the source does not state which system provides them; UC-002 assumes only that purchase order data is available in the system — the supply path is part of the REQ-008 interface gap (USECASES.md Gaps).
- **Sortation** (ACT-008): no use case step describes a sortation action; sortation appears only as a solution option in `requirements/BOX.md` (Ship Goods), which is solution-side content excluded from behavioral derivation. Shipping is modeled per UC-007 steps 4–6.
- **REQ-NF-003** (ACT-001, ACT-009): no measurement window or planned-downtime handling is defined; availability is carried as a quality attribute only (USECASES.md Gaps).
- **Administrator role**: no functional requirement REQ-001..REQ-010 assigns a distinct goal to the administrator role, so no administrator-specific activity is derived (USECASES.md Actors).

## Rules:
- One activity per use case (or per key system function).
- Number all steps sequentially.
- Capture decision points with if-then logic.
- Reference requirement IDs where applicable: (REQ-NNN).