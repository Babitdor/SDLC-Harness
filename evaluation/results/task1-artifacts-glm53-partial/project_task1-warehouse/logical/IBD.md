---
type: Internal Block Diagram
title: Internal Block — Connections and Ports
description: Internal wiring of block instances showing connections, ports, and flow relationships between parts.
tags: [ibd, mbse, structural]
timestamp: 2026-09-08T18:48:32Z
resource: logical/IBD.md
---

# Internal Block: Warehouse Management System

Internal wiring of the WMS. All parts are the subsystem blocks declared in `logical/BDD.md`. Three flow families are wired: the **goods flow** (receiving → storage → picking → packing → sortation/shipping), the **data/inventory flow** (scan records → perpetual inventory → reporting/ERP API), and the **control flow** (orchestration, RBAC gating). The hazmat and temperature-zone routing of ACT-003/ACT-004 appear as flow constraints on the storage connections.

## Goods Flow Connections

- Receiving Subsystem ─[VerifiedReceivedGoods]→ Storage Subsystem
  - Source port: ReceivingSubsystem.verifiedGoodsOut : VerifiedGoods — released only on the ACT-002 match path; a mismatch (ACT-002 A1) blocks downstream storage assignment.
  - Target port: StorageSubsystem.goodsIn : ReceivedGoodsForPutaway
  - Direction: unidirectional (receiving → storage)
  - Traced activities: ACT-001 (receiving completion), ACT-002 (verification gate), feeding ACT-003/ACT-004
  - Traced rules: REQ-001, REQ-002, C5

- Receiving Subsystem ─[InductedGoods]→ Receiving Subsystem (internal conveyor induction)
  - Source port: ReceivingSubsystem.conveyorInductionOut : InductedGoodsStream — the selected Automated Unloading Conveyor capability presents goods to the scan/verification point without manual forklift transfer.
  - Target port: ReceivingSubsystem.scanPointIn : GoodsAtScanPoint
  - Direction: internal to the receiving part (declared as a self-connection of the part)
  - Traced activities: ACT-001 (steps 1–3)
  - Traced rules: REQ-001, REQ-009 (scan gate at induction), C1, C5

- Storage Subsystem ─[PickedItems]→ Picking Subsystem
  - Source port: StorageSubsystem.pickSourceOut : PickSourceLocationSet — storage locations of ordered items, derived from per-location levels (REQ-010).
  - Target port: PickingSubsystem.pickGuidanceIn : LocationReference
  - Direction: unidirectional (storage → picking)
  - Traced activities: ACT-003 (location portfolio), ACT-005 (step 2: locations provided to the Operator)
  - Traced rules: REQ-003, REQ-005, REQ-010, C7

- Picking Subsystem ─[PickedOrderItems]→ Packing Subsystem
  - Source port: PickingSubsystem.pickedItemsOut : PickedOrderItems — items confirmed against the outgoing order (ACT-005 step 5); a per-item discrepancy (ACT-005 A1) is recorded and the affected pick is not confirmed.
  - Target port: PackingSubsystem.itemsToPackIn : PickedOrderItems
  - Direction: unidirectional (picking → packing)
  - Traced activities: ACT-005 (completion), ACT-006 (per-order completion), feeding ACT-007
  - Traced rules: REQ-005, REQ-006, REQ-007, C5

- Packing Subsystem ─[PackedOrder]→ Shipping Subsystem
  - Source port: PackingSubsystem.packedOrderOut : PackedOrder — released only with the packing completion confirmation (ACT-007 step 3 gate).
  - Target port: ShippingSubsystem.sortationIn : PackedOrderForDispatch
  - Direction: unidirectional (packing → shipping)
  - Traced activities: ACT-007 (completion), feeding ACT-008
  - Traced rules: REQ-007, C5

- Shipping Subsystem ─[ShippedOrder]→ External Environment (outbound goods flow terminus)
  - Source port: ShippingSubsystem.loadingOut : ShippedOrder — automated sortation routes the packed order to a loading lane and dispatches it.
  - Target port: (system boundary — outbound goods to carrier)
  - Direction: output (system → external)
  - Traced activities: ACT-008 (ship packed order, confirm shipment)
  - Traced rules: REQ-007, C1 (sortation/loading footprint within floor budget), C5

## Storage Flow Constraints (hazmat and temperature-zone routing)

The following constraints apply to every connection that crosses into or out of the Storage Subsystem (InductedGoods → put-away, VerifiedReceivedGoods → storage, PickedItems → picking):

- **Hazmat segregation constraint (C4 / REQ-NF-004)**: if the goods' hazard class identifies hazardous material (ACT-003 A1), the put-away flow is routed exclusively to the physically segregated hazmat zone of the Storage Subsystem (Hazmat Segregation Management → StorageSubsystem routing constraint); hazmat goods never enter general or cold zone circulation (ACT-004 A1).
- **Temperature-zone routing constraint (C3)**: non-hazardous goods are routed to the general zone (15–25 °C) or the cold zone (2–8 °C) per the ACT-003 zone-type decision; the put-away destination zone is held at the assigned band (ACT-004). Gap: no product attribute triggers the cold branch in the source — routing is bounded to the two C3 zone types, trigger flagged not filled.
- **Location-bound constraint (C1, C2)**: every assigned location is drawn from the Storage Location Registry portfolio bounded by C1 (≤ 5,000 m² floor area) and the AS/RS rack-height envelope of C2 (≤ 12 m); if no location satisfies size/weight/hazard criteria, the no-location branch reports unassignability (ACT-003 A2) and the goods flow does not proceed into storage.

## Data / Inventory Flow Connections

- Scan Recording Service ─[ScanRecord]→ Inventory Management Subsystem
  - Source port: ScanRecordingService.scanRecordOut : BarcodeScanRecord — stored scan record per inventory movement (REQ-009 completeness).
  - Target port: InventoryManagementSubsystem.movementRecordIn : CompletedMovementRecord — a completed movement with its scan record is the only accepted input to the perpetual ledger (ACT-011 decision point: no scan → no level update).
  - Direction: unidirectional (scan recording → inventory)
  - Traced activities: ACT-010 (invoked by ACT-001, ACT-004, ACT-005, ACT-007, ACT-008), ACT-011
  - Traced rules: REQ-009, REQ-010, C6

- Receiving Subsystem ─[ReceivingScanEvent]→ Scan Recording Service
  - Source port: ReceivingSubsystem.scanEventOut : ScanEvent — barcode scans captured at receiving (ACT-001 step 3).
  - Target port: ScanRecordingService.scanCaptureIn : BarcodeReadRequest
  - Direction: unidirectional (receiving → scan recording)
  - Traced activities: ACT-001 → ACT-010
  - Traced rules: REQ-009

- Storage Subsystem ─[PutawayScanEvent]→ Scan Recording Service
  - Source port: StorageSubsystem.scanOut : ScanEvent — barcode scans captured at put-away (ACT-004 step 3).
  - Target port: ScanRecordingService.scanCaptureIn : BarcodeReadRequest
  - Direction: unidirectional (storage → scan recording)
  - Traced activities: ACT-004 → ACT-010
  - Traced rules: REQ-009

- Picking Subsystem ─[PickScanEvent]→ Scan Recording Service
  - Source port: PickingSubsystem.scanOut : ScanEvent — barcode scans captured per picked item (ACT-005 step 4).
  - Target port: ScanRecordingService.scanCaptureIn : BarcodeReadRequest
  - Direction: unidirectional (picking → scan recording)
  - Traced activities: ACT-005 → ACT-010
  - Traced rules: REQ-009

- Packing Subsystem ─[PackingScanEvent]→ Scan Recording Service
  - Source port: PackingSubsystem.scanOut : ScanEvent — barcode scans captured at packing (ACT-007 step 2).
  - Target port: ScanRecordingService.scanCaptureIn : BarcodeReadRequest
  - Direction: unidirectional (packing → scan recording)
  - Traced activities: ACT-007 → ACT-010
  - Traced rules: REQ-009

- Shipping Subsystem ─[ShippingScanEvent]→ Scan Recording Service
  - Source port: ShippingSubsystem.scanOut : ScanEvent — barcode scans captured at shipping (ACT-008 step 2).
  - Target port: ScanRecordingService.scanCaptureIn : BarcodeReadRequest
  - Direction: unidirectional (shipping → scan recording)
  - Traced activities: ACT-008 → ACT-010
  - Traced rules: REQ-009

- Inventory Management Subsystem ─[LevelUpdateRequest]→ Storage Subsystem
  - Source port: InventoryManagementSubsystem.levelBasisOut : PerLocationLevelSet — updated per-location levels made available for identifying pick sources (ACT-011 step 3).
  - Target port: StorageSubsystem.levelRegistryIn : PerLocationLevelSet — maintained by the Storage Location Registry; the pick-source view (StorageSubsystem.pickSourceOut) is derived from it.
  - Direction: bidirectional (levels published to storage; completed movements returned via the scan-record path above)
  - Traced activities: ACT-011 (steps 2–3), ACT-005 (step 2)
  - Traced rules: REQ-010, REQ-003, C7

- Inventory Management Subsystem ─[InventoryReport]→ External Environment (Viewer)
  - Source port: InventoryManagementSubsystem.reportOut : RealTimeInventoryReport — compiled per-location levels, including empty levels (ACT-012 A1).
  - Target port: (system boundary — report to the Viewer actor)
  - Direction: output (system → external Viewer)
  - Traced activities: ACT-012
  - Traced rules: REQ-010, REQ-009, C7, C8 (viewer authorization gate)

- Inventory Management Subsystem ─[InventoryData]→ ERP REST API Interface
  - Source port: InventoryManagementSubsystem.apiDataOut : InventoryQueryResult — inventory and movement data served to API requests.
  - Target port: ErpRestApiInterface.requestDataIn : ERPRequestPayload
  - Direction: bidirectional (query data to the API processor; responses returned to the ERP through the same interface)
  - Traced activities: ACT-009
  - Traced rules: REQ-008, C6

- ERP REST API Interface ─[ERPResponse]→ External Environment (ERP System)
  - Source port: ErpRestApiInterface.responseOut : RESTResponse — processing response or error response (ACT-009 A1).
  - Target port: (system boundary — REST API to the external ERP System actor)
  - Direction: output (system → external ERP)
  - Traced activities: ACT-009
  - Traced rules: REQ-008, C6

## Control Flow Connections

- Process Orchestration Service ─[StageSequenceControl]→ Receiving Subsystem
  - Source port: ProcessOrchestrationService.stageControlOut : StageCommand — initiates the receiving stage (ACT-001) and enforces the verification and scan gates before storage entry.
  - Target port: ReceivingSubsystem.controlIn : StageCommand
  - Direction: bidirectional (command out; stage-completion status returned)
  - Traced activities: ACT-001, ACT-002 (control flow)
  - Traced rules: C5, C6

- Process Orchestration Service ─[StageSequenceControl]→ Storage Subsystem
  - Source port: ProcessOrchestrationService.stageControlOut : StageCommand — sequences storage assignment (ACT-003) and put-away (ACT-004); carries the hazmat and temperature-zone routing constraints onto the storage connections.
  - Target port: StorageSubsystem.controlIn : StageCommand
  - Direction: bidirectional (command out; put-away confirmation returned)
  - Traced activities: ACT-003, ACT-004
  - Traced rules: C3, C4, C5

- Process Orchestration Service ─[StageSequenceControl]→ Picking Subsystem
  - Source port: ProcessOrchestrationService.stageControlOut : StageCommand — releases strategy groups (wave/batch/zone) and paces picking against the 500 orders/h budget.
  - Target port: PickingSubsystem.controlIn : StageCommand
  - Direction: bidirectional (command out; per-order completion status returned)
  - Traced activities: ACT-005, ACT-006
  - Traced rules: C5, C6

- Process Orchestration Service ─[StageSequenceControl]→ Packing Subsystem
  - Source port: ProcessOrchestrationService.stageControlOut : StageCommand — initiates packing and enforces the packing-confirmation gate into shipping.
  - Target port: PackingSubsystem.controlIn : StageCommand
  - Direction: bidirectional (command out; packing confirmation returned)
  - Traced activities: ACT-007
  - Traced rules: C5, C6

- Process Orchestration Service ─[StageSequenceControl]→ Shipping Subsystem
  - Source port: ProcessOrchestrationService.stageControlOut : StageCommand — initiates shipping and triggers the shipment-level reflection (ACT-011).
  - Target port: ShippingSubsystem.controlIn : StageCommand
  - Direction: bidirectional (command out; shipment confirmation returned)
  - Traced activities: ACT-008
  - Traced rules: C5, C6

- Process Orchestration Service ─[MovementGateControl]→ Scan Recording Service
  - Source port: ProcessOrchestrationService.gateControlOut : GateCommand — enforces the REQ-009 completeness gate: a movement is completed only when its scan record exists (ACT-010 A1, ACT-011 decision point).
  - Target port: ScanRecordingService.gateControlIn : GateCommand
  - Direction: bidirectional (gate command out; scan-record existence status returned)
  - Traced activities: ACT-010, ACT-011
  - Traced rules: REQ-009, C5, C6

- RBAC Access Control ─[AuthorizationVerdict]→ Process Orchestration Service
  - Source port: RBACAccessControl.verdictOut : AuthorizationDecision — authorization verdict for the authenticated role (administrator, operator, viewer) before any activity is executed.
  - Target port: ProcessOrchestrationService.rbacGateIn : AuthorizationDecision
  - Direction: unidirectional (RBAC → orchestration)
  - Traced activities: ACT-001..ACT-012 (authorization precondition), explicit gate in ACT-012
  - Traced rules: C8, REQ-NF-005

- RBAC Access Control ─[AuthorizationVerdict]→ Inventory Management Subsystem
  - Source port: RBACAccessControl.verdictOut : AuthorizationDecision — viewer-role gate for real-time inventory reporting (ACT-012 decision point: unauthorized → levels not reported).
  - Target port: InventoryManagementSubsystem.rbacGateIn : AuthorizationDecision
  - Direction: unidirectional (RBAC → inventory reporting)
  - Traced activities: ACT-012
  - Traced rules: C8, REQ-NF-005

- Temperature-Zone Management ─[ZoneRoutingConstraint]→ Storage Subsystem
  - Source port: TemperatureZoneManagement.zoneRoutingOut : ZoneAssignment — eligible zone type (general 15–25 °C vs. cold 2–8 °C) determined for non-hazardous goods (ACT-003 step 3).
  - Target port: StorageSubsystem.zoneRoutingIn : ZoneAssignment — bounds the assigned location and the put-away destination band (ACT-004).
  - Direction: unidirectional (zone management → storage)
  - Traced activities: ACT-003, ACT-004
  - Traced rules: C3

- Hazmat Segregation Management ─[HazmatRoutingConstraint]→ Storage Subsystem
  - Source port: HazmatSegregationManagement.hazmatRoutingOut : HazmatZoneAssignment — hazmat determination from the product hazard class (ACT-003 step 2–3); hazardous goods are routed exclusively to the physically segregated hazmat zone (ACT-003 A1).
  - Target port: StorageSubsystem.hazmatRoutingIn : HazmatZoneAssignment — overrides general/cold routing and excludes hazmat goods from general and cold circulation (ACT-004 A1).
  - Direction: unidirectional (hazmat management → storage)
  - Traced activities: ACT-003, ACT-004
  - Traced rules: C4, REQ-NF-004, REQ-003

## Ports

- ReceivingSubsystem.conveyorInductionOut : InductedGoodsStream
- ReceivingSubsystem.scanPointIn : GoodsAtScanPoint
- ReceivingSubsystem.verifiedGoodsOut : VerifiedGoods
- ReceivingSubsystem.scanEventOut : ScanEvent
- ReceivingSubsystem.controlIn : StageCommand
- StorageSubsystem.goodsIn : ReceivedGoodsForPutaway
- StorageSubsystem.pickSourceOut : PickSourceLocationSet
- StorageSubsystem.levelRegistryIn : PerLocationLevelSet
- StorageSubsystem.scanOut : ScanEvent
- StorageSubsystem.controlIn : StageCommand
- StorageSubsystem.zoneRoutingIn : ZoneAssignment
- StorageSubsystem.hazmatRoutingIn : HazmatZoneAssignment
- PickingSubsystem.pickGuidanceIn : LocationReference
- PickingSubsystem.pickedItemsOut : PickedOrderItems
- PickingSubsystem.scanOut : ScanEvent
- PickingSubsystem.controlIn : StageCommand
- PackingSubsystem.itemsToPackIn : PickedOrderItems
- PackingSubsystem.packedOrderOut : PackedOrder
- PackingSubsystem.scanOut : ScanEvent
- PackingSubsystem.controlIn : StageCommand
- ShippingSubsystem.sortationIn : PackedOrderForDispatch
- ShippingSubsystem.loadingOut : ShippedOrder
- ShippingSubsystem.scanOut : ScanEvent
- ShippingSubsystem.controlIn : StageCommand
- InventoryManagementSubsystem.movementRecordIn : CompletedMovementRecord
- InventoryManagementSubsystem.levelBasisOut : PerLocationLevelSet
- InventoryManagementSubsystem.reportOut : RealTimeInventoryReport
- InventoryManagementSubsystem.apiDataOut : InventoryQueryResult
- InventoryManagementSubsystem.rbacGateIn : AuthorizationDecision
- ScanRecordingService.scanCaptureIn : BarcodeReadRequest
- ScanRecordingService.scanRecordOut : BarcodeScanRecord
- ScanRecordingService.gateControlIn : GateCommand
- ErpRestApiInterface.requestDataIn : ERPRequestPayload
- ErpRestApiInterface.responseOut : RESTResponse
- ProcessOrchestrationService.stageControlOut : StageCommand
- ProcessOrchestrationService.gateControlOut : GateCommand
- ProcessOrchestrationService.rbacGateIn : AuthorizationDecision
- RBACAccessControl.verdictOut : AuthorizationDecision
- TemperatureZoneManagement.zoneRoutingOut : ZoneAssignment
- HazmatSegregationManagement.hazmatRoutingOut : HazmatZoneAssignment

## Rules:
- Every connection references two blocks declared in BDD.md.
- Flow names are nouns (material or information).
- All referenced blocks must exist in BDD.md.