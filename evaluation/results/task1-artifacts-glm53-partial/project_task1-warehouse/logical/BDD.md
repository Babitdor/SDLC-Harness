---
type: Block Definition Diagram
title: Block Definition — Structural Types
description: Structural type declarations including part definitions, attributes, ports, generalization, and composition relationships.
tags: [bdd, mbse, structural]
timestamp: 2026-09-08T18:48:32Z
resource: logical/BDD.md
---

# Block Definition

Logical block hierarchy of the warehouse management system, decomposed per the selected concept (PRINCIPLE_SOLUTIONS.md, CS-001). All blocks are solution-agnostic logical capabilities: they name what the system must do and own, not physical products or vendor technologies. The selected options (automated unloading conveyor, AS/RS, RF-scan picking, semi-automated packing line, automated sortation & loading, perpetual WMS inventory) are represented as the logical capabilities those options require.

## Warehouse Management System (System root block)
- Subsystems: Receiving Subsystem, Storage Subsystem, Picking Subsystem, Packing Subsystem, Shipping Subsystem, Inventory Management Subsystem, Scan Recording Service, ERP REST API Interface, RBAC Access Control, Temperature-Zone Management, Hazmat Segregation Management, Process Orchestration Service
- Properties:
  - managedSkuPortfolio: Integer — at least 10,000 distinct SKUs (C7)
  - orderThroughput: Integer — sustained 500 orders per hour (C5)
  - serviceAvailability: Percent — 99.9 % (C6)
  - floorAreaBudget: Area — ≤ 5,000 m² (C1)
  - maxRackHeight: Length — ≤ 12 m (C2)
  - zoneTemperatureBands: Map — general 15–25 °C, cold 2–8 °C (C3)

## Receiving Subsystem
- Parts: Automated Unloading Conveyor Capability[1], Receipt Verification Capability[1]
- Properties:
  - dockAssignment: DockIdentifier — designated receiving dock (REQ-001)
  - receiptRecord: ReceiptRecord — created per arrival (REQ-001)
  - verificationResult: Enumeration {match, mismatch} — ACT-002 decision point
  - scanGateEnforced: Boolean — movement completes only with a captured scan (REQ-009)
- Realized functions: Receive Goods → Register Goods Arrival and Create Receipt; Verify Goods Against Purchase Order
- Served activities: ACT-001, ACT-002 (scan capture via ACT-010)
- Satisfied rules: C1 (footprint within floor budget), C5, C6, C8, REQ-001, REQ-002, REQ-009

## Storage Subsystem
- Parts: AS/RS Storage & Retrieval Capability[1], Storage Location Registry[1]
- Properties:
  - rackHeightEnvelope: Length — ≤ 12 m, bounding all S/R machine aisles (C2)
  - locationPortfolio: LocationSet — addressing capacity for ≥ 10,000 SKUs (C7), bounded by C1
  - zoneTopology: ZoneSet {general, cold, hazmatSegregated} — physically realizes the three zone types (C3, C4)
  - noLocationBranch: Boolean — reports when no location satisfies size/weight/hazard criteria (ACT-003 A2)
- Realized functions: Store Goods → Assign Storage Location; Put Away Goods to Storage Zone
- Served activities: ACT-003, ACT-004 (scan capture via ACT-010, level update via ACT-011)
- Satisfied rules: C1, C2, C3, C4/REQ-NF-004, C7, C8, REQ-003, REQ-004

## Picking Subsystem
- Parts: RF-Scan Picking Capability[1], Picking Strategy Selector[1]
- Properties:
  - strategyModes: Enumeration {wave, batch, zone} — grouping and release of outgoing orders (REQ-006)
  - pickTaskQueue: TaskSet — one picking task per released order (REQ-005)
  - pickConfirmation: Enumeration {confirmed, discrepancy} — per-item branch (ACT-005 A1)
  - pickGuidance: LocationReference — storage locations of items to be picked, from per-location levels (REQ-010)
- Realized functions: Pick Goods → Select and Execute Picking Strategy; Pick Items for Outgoing Order
- Served activities: ACT-005, ACT-006 (scan capture via ACT-010)
- Satisfied rules: C5 (throughput-critical, operator-executed stage), C7, C8, REQ-005, REQ-006, REQ-009, REQ-010

## Packing Subsystem
- Parts: Semi-Automated Packing Line Capability[1]
- Properties:
  - packingConfirmation: Boolean — gates entry to shipping (ACT-007 step 3)
  - linePacing: Rate — sustains the shared 500 orders/h budget (C5)
  - scanGateEnforced: Boolean — packing movement completes only with a captured scan (REQ-009)
- Realized function: Pack Goods → Pack Picked Items
- Served activities: ACT-007 (scan capture via ACT-010)
- Satisfied rules: C5, C8, REQ-007, REQ-009

## Shipping Subsystem
- Parts: Automated Sortation & Loading Capability[1]
- Properties:
  - shipmentConfirmation: Boolean — confirms shipment of the packed order (ACT-008 step 3)
  - sortationRouting: RouteSet — solution-side routing capability realized within ACT-008 (no separate sortation activity exists in ACTIVITIES.md)
  - footprintShare: Area — sortation loop and loading lanes within the C1 floor budget
- Realized function: Ship Goods → Ship Packed Order
- Served activities: ACT-008 (scan capture via ACT-010, level update via ACT-011)
- Satisfied rules: C1, C5, C8, REQ-007, REQ-009, REQ-010

## Inventory Management Subsystem
- Parts: Perpetual Inventory Ledger[1], Inventory Reporting Capability[1]
- Properties:
  - levelGranularity: LocationLevel — real-time level per storage location (REQ-010)
  - portfolioCoverage: Integer — levels and reports span ≥ 10,000 SKUs (C7)
  - emptyLevelReporting: Boolean — reports empty levels for locations without inventory (ACT-012 A1)
  - availabilityTarget: Percent — 99.9 % for ledger and reporting (C6)
- Realized functions: Manage Inventory → Maintain and Report Real-Time Inventory Levels; Report Real-Time Inventory (enabling function)
- Served activities: ACT-011, ACT-012
- Satisfied rules: C6, C7, C8, REQ-009 (movement records feed levels), REQ-010

## Scan Recording Service (cross-cutting)
- Parts: Barcode Scan Capture[1], Scan Record Store[1]
- Properties:
  - completenessRule: Boolean — a scan record exists for every inventory movement (REQ-009)
  - invocationPoints: Enumeration {receiving, put-away, picking, packing, shipping} — ACT-001, ACT-004, ACT-005, ACT-007, ACT-008
  - unreadableBarcodePolicy: Gate — no scan captured → movement not recorded as completed (ACT-010 A1)
- Realized functions: Record Barcode Scans (enabling function) → Record Scan per Inventory Movement
- Served activities: ACT-010, invoked by ACT-001, ACT-004, ACT-005, ACT-007, ACT-008
- Satisfied rules: C8, REQ-009

## ERP REST API Interface (cross-cutting)
- Parts: Request Processor[1], Response Builder[1]
- Properties:
  - interfaceContract: RESTRequestResponse — request/response abstraction only; endpoints, data formats, and ERP systems unspecified (REQ-008 gap, flagged not filled)
  - errorResponsePath: Boolean — returns error response when request is not processable (ACT-009 A1)
  - availabilityTarget: Percent — 99.9 % of the integration interface (C6)
- Realized function: Manage Inventory → Integrate with External ERP System
- Served activities: ACT-009
- Satisfied rules: C6, REQ-008

## RBAC Access Control (cross-cutting)
- Parts: Authentication Gate[1], Authorization Policy[1]
- Properties:
  - roleModel: Enumeration {administrator, operator, viewer} (C8 / REQ-NF-005)
  - permissionMatrix: Undefined — role names defined, no per-role permission matrix in source (flagged gap, not filled)
  - enforcementScope: AllActivities — authorization precondition of ACT-001..ACT-012
- Realized functions: cross-cutting enabler of all functions in FUNCTION_TREE.md
- Served activities: ACT-001..ACT-012 (authorization precondition and gate, explicit in ACT-012)
- Satisfied rules: C8, REQ-NF-005

## Temperature-Zone Management (cross-cutting, C3)
- Parts: Zone Routing Logic[1], Zone Condition Monitor[1]
- Properties:
  - generalZoneBand: TemperatureRange — 15–25 °C (C3)
  - coldZoneBand: TemperatureRange — 2–8 °C (C3)
  - coldTriggerAttribute: Undefined — no product attribute triggering the cold branch is defined in the source (flagged gap, not filled); routing bounded to the two C3 zone types
  - toleranceBand: Undefined — no tolerance band, monitoring granularity, or humidity limits stated (flagged gap, not filled)
- Realized functions: Store Goods (C3 zone routing within Assign Storage Location and Put Away)
- Served activities: ACT-003, ACT-004
- Satisfied rules: C3

## Hazmat Segregation Management (cross-cutting, C4 / REQ-NF-004)
- Parts: Hazard Routing Logic[1], Segregation Policy[1]
- Properties:
  - hazmatZone: ZoneIdentifier — physically segregated hazardous-material storage (C4)
  - hazmatTrigger: HazardClass — product hazard class from ACT-003 step 2 (REQ-003)
  - exclusionPolicy: Boolean — hazmat goods never enter general or cold zone circulation (ACT-003 A1, ACT-004 A1)
- Realized functions: Store Goods (hazard branch within Assign Storage Location and Put Away)
- Served activities: ACT-003, ACT-004
- Satisfied rules: C4, REQ-NF-004, REQ-003

## Process Orchestration Service (cross-cutting)
- Parts: Flow Sequencer[1], Completion Gate Manager[1]
- Properties:
  - goodsFlowSequence: Enumeration {receiving → verification → storage assignment → put-away → picking → packing → shipping} — ACT-001..ACT-008 control flow
  - completionGates: GateSet {verificationResult (ACT-002), scanCaptured (ACT-010), packingConfirmation (ACT-007)} — gates that must pass before the next stage is entered
  - throughputCoordination: Rate — paces the stages against the shared 500 orders/h budget (C5)
- Realized functions: Operate Warehouse Goods Flow (top-level sequencing of all Level-2 functions)
- Served activities: ACT-001..ACT-008 (control flow), gating ACT-010/ACT-011 invocation
- Satisfied rules: C5, C6

## Rules:
- Every block has a name and at least one property or part.
- Reference types from the constraint / requirement layer.
- Decomposition must be consistent with ACTIVITIES.md.