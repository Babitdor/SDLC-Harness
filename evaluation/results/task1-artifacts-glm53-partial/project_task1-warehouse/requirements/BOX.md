---
type: Morphological Box
title: Morphological Box — Solution Principles
description: Function-to-solution mapping table for morphological analysis, with alternative solution options per function.
tags: [morphological-box, mbse]
timestamp: 2026-09-08T18:48:32Z
resource: requirements/BOX.md
---

# Morphological Box

Source: `sources/morphological-box.md`. The selected concept below is the user's explicit selection as stated in the source file; it is recorded as given, not evaluated by this phase.

| Function          | Option A                    | Option B                                    | Option C                    |
|-------------------|-----------------------------|---------------------------------------------|-----------------------------|
| Receive Goods     | Manual Dock with Forklift   | Automated Unloading Conveyor                | —                           |
| Store Goods       | Pallet Racking              | Automated Storage & Retrieval System (AS/RS) | Push-Back Racking           |
| Pick Goods        | Pick-to-Light System        | Voice-Directed Picking                      | RF-Scan Barcode Picking     |
| Pack Goods        | Manual Pack Station         | Semi-Automated Packing Line                 | —                           |
| Ship Goods        | Stretch Wrapping & Dock Loading | Automated Sortation & Loading           | —                           |
| Manage Inventory  | Periodic Cycle Counting     | Real-Time RFID Tracking                     | Perpetual WMS Inventory     |

## Selected Concept (user selection, as stated in the source)

| Function          | Selected Option                              |
|-------------------|----------------------------------------------|
| Receive Goods     | Automated Unloading Conveyor                 |
| Store Goods       | Automated Storage & Retrieval System (AS/RS) |
| Pick Goods        | RF-Scan Barcode Picking                      |
| Pack Goods        | Semi-Automated Packing Line                  |
| Ship Goods        | Automated Sortation & Loading                |
| Manage Inventory  | Perpetual WMS Inventory                      |

## Notes

- Option cells marked "—" mean the source lists no third option for that function (Receive Goods, Pack Goods, Ship Goods have only two options each).
- The source file contains no evaluation rationale or scoring for the selection; none is added here.