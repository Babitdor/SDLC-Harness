# Functional Requirements

REQ-001: The warehouse management system shall receive incoming goods at designated receiving docks.
REQ-002: The system shall verify received goods against purchase orders.
REQ-003: The system shall assign storage locations based on product size, weight, and hazard class.
REQ-004: The system shall support put-away operations from receiving to storage zones.
REQ-005: The system shall manage picking operations for outgoing orders.
REQ-006: The system shall support wave, batch, and zone picking strategies.
REQ-007: The system shall manage packing and shipping operations.
REQ-008: The system shall integrate with external ERP systems via a REST API.
REQ-009: The system shall record barcode scans for every inventory movement.
REQ-010: The system shall report real-time inventory levels per storage location.

# Non-Functional Requirements

REQ-NF-001: The system shall manage at least 10,000 distinct SKUs.
REQ-NF-002: The system shall sustain an order throughput of 500 orders per hour.
REQ-NF-003: The system shall maintain 99.9 percent service availability.
REQ-NF-004: The system shall keep hazardous-material storage physically segregated from general storage.
REQ-NF-005: The system shall enforce role-based access control for administrator, operator, and viewer roles.

# Constraints

C1: The warehouse floor area shall not exceed 5,000 square metres.
C2: The maximum rack height shall not exceed 12 metres.
C3: General storage shall be held between 15 and 25 degrees Celsius; cold storage between 2 and 8 degrees Celsius.
