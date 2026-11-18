---
type: Requirements Document
title: Functional and Non-Functional Requirements
description: Structured requirements derived from raw user input, organized by category with unique IDs.
tags: [requirements, mbse]
timestamp: 2026-09-08T18:48:32Z
resource: requirements/REQUIREMENTS.md
---

# Functional Requirements

Source: `sources/requirements.md` (section "Functional Requirements"). Classification: functional.

REQ-001
The warehouse management system shall receive incoming goods at designated receiving docks.
Classification: Functional. Verification: functional test / demonstration at designated receiving docks.

REQ-002
The system shall verify received goods against purchase orders.
Classification: Functional. Verification: functional test with matching and mismatching goods vs. purchase order.

REQ-003
The system shall assign storage locations based on product size, weight, and hazard class.
Classification: Functional. Verification: functional test of location-assignment logic with inputs size, weight, hazard class.

REQ-004
The system shall support put-away operations from receiving to storage zones.
Classification: Functional. Verification: functional test / demonstration of a put-away process flow from receiving to storage zones.

REQ-005
The system shall manage picking operations for outgoing orders.
Classification: Functional. Verification: functional test / demonstration of picking for outgoing orders.

REQ-006
The system shall support wave, batch, and zone picking strategies.
Classification: Functional. Verification: functional test exercising each of the three named strategies (wave, batch, zone).

REQ-007
The system shall manage packing and shipping operations.
Classification: Functional. Verification: functional test / demonstration of packing and shipping process flow.

REQ-008
The system shall integrate with external ERP systems via a REST API.
Classification: Functional (interface). Verification: integration test against an external ERP via the REST API.
Gap: the source specifies no API endpoints, data formats, or ERP systems; interface detail is not defined in the input.

REQ-009
The system shall record barcode scans for every inventory movement.
Classification: Functional. Verification: functional test verifying a scan record exists for each inventory movement (completeness check).

REQ-010
The system shall report real-time inventory levels per storage location.
Classification: Functional. Verification: functional test comparing reported levels against actual per-location inventory.

# Non-Functional Requirements

Source: `sources/requirements.md` (section "Non-Functional Requirements"). Classification: non-functional.

REQ-NF-001
The system shall manage at least 10,000 distinct SKUs.
Classification: Non-functional (capacity). Verification: capacity test with a 10,000-SKU dataset.

REQ-NF-002
The system shall sustain an order throughput of 500 orders per hour.
Classification: Non-functional (performance). Verification: load/performance test measuring sustained orders per hour.

REQ-NF-003
The system shall maintain 99.9 percent service availability.
Classification: Non-functional (availability/reliability). Verification: availability measurement over the service period (monitoring/uptime reporting).
Gap: the source does not define the measurement window (e.g., monthly vs. annual) or planned-downtime handling.

REQ-NF-004
The system shall keep hazardous-material storage physically segregated from general storage.
Classification: Non-functional (safety). Verification: physical inspection/audit of storage segregation.

REQ-NF-005
The system shall enforce role-based access control for administrator, operator, and viewer roles.
Classification: Non-functional (security). Verification: access-control test for each of the three named roles (administrator, operator, viewer).
Gap: the source defines the role names but no permission matrix per role.

# Constraints

Source: `sources/requirements.md` (section "Constraints"). Classification: constraint. Also carried into `requirements/RULES.md` with rule IDs.

C1
The warehouse floor area shall not exceed 5,000 square metres.
Classification: Constraint (physical). Verification: measurement of the warehouse layout/floor plan against 5,000 m².

C2
The maximum rack height shall not exceed 12 metres.
Classification: Constraint (physical). Verification: inspection/measurement of rack height against 12 m.

C3
General storage shall be held between 15 and 25 degrees Celsius; cold storage between 2 and 8 degrees Celsius.
Classification: Constraint (physical/environmental). Verification: continuous temperature monitoring per storage zone against the stated ranges.
Gap: the source specifies no tolerance band, monitoring granularity, or humidity limits.