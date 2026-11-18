# Morphological Box — Warehouse Management System

Document: MB-WMS-001
Status: Concept selected

## 1. Function / Option Matrix

| Function | Option A | Option B | Option C |
|---|---|---|---|
| Receive goods | Manual dock with forklift | Automated unloading conveyor | — |
| Store goods | Selective pallet racking | Automated storage and retrieval system (AS/RS) | Push-back racking |
| Pick goods | Pick-to-light | Voice-directed picking | RF barcode scanning |
| Pack goods | Manual pack station | Semi-automated packing line | — |
| Ship goods | Stretch wrapping and manual dock loading | Automated sortation and loading | — |
| Manage inventory | Periodic cycle counting | Real-time RFID tracking | Perpetual WMS inventory |

## 2. Option Characteristics

**Store — selective racking.** Lowest cost, every pallet directly accessible, lowest
density. **AS/RS.** Highest density and throughput, fully automated; under the
12 m height limit its density advantage over racking is reduced, and it has the
highest capital cost. **Push-back.** Dense for few-SKU, high-volume stock; poor
selectivity for 10,000 SKUs.

**Pick — pick-to-light.** Fastest for high-velocity SKUs in fixed locations; costly
to cover many SKUs. **Voice.** Hands-free, good for cases; weaker item-level
verification. **RF scanning.** Verifies every pick by barcode, which directly
satisfies the scan-per-movement requirement.

**Ship — automated sortation.** Needed at high order rates across many carriers;
requires conveyor infrastructure from packing. **Manual loading.** Adequate at low
volume only.

**Inventory — RFID.** Real-time without scanning, but tag cost per item.
**Perpetual WMS.** Real-time from transaction records, depends on scan discipline.

## 3. Known Incompatibilities

- Automated sortation requires an automated or semi-automated packing line
  feeding it by conveyor; it is incompatible with manual pack stations.
- Push-back racking is incompatible with 10,000 SKUs at item-level selectivity.
- Periodic cycle counting alone cannot satisfy real-time inventory reporting
  (REQ-010).

## 4. Selected Concept

| Function | Selected | Reason |
|---|---|---|
| Receive | Automated unloading conveyor | Feeds AS/RS directly |
| Store | AS/RS | Throughput and density within 5,000 m² |
| Pick | RF barcode scanning | Scan per movement (REQ-009) |
| Pack | Semi-automated packing line | Feeds automated sortation |
| Ship | Automated sortation and loading | 500 orders/h across carriers |
| Inventory | Perpetual WMS | Real-time reporting from scans (REQ-010) |
