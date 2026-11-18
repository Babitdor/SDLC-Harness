package WarehouseManagementSystemRequirements {
    public import ScalarValues::*;

    /* Subject part definition — the warehouse management system that every
       requirement applies to. Attributes declared here mirror the quantitative
       bounds cited by the formal `require constraint` predicates below. */
    part def WarehouseManagementSystem {
        attribute maxSkus : Integer = 10000;
        attribute minOrderThroughput : Real = 500.0;
        attribute minAvailabilityPercent : Real = 99.9;
        attribute maxFloorArea : Real = 5000.0;
        attribute maxRackHeight : Real = 12.0;
        attribute generalStorageMinTemp : Real = 15.0;
        attribute generalStorageMaxTemp : Real = 25.0;
        attribute coldStorageMinTemp : Real = 2.0;
        attribute coldStorageMaxTemp : Real = 8.0;
    }

    /* ======================================================================
       Functional Requirements
       Source: sources/requirements.md (section "Functional Requirements")
       Requirement text is carried in `doc` comments; auxiliary attribute
       names are suffixed with the requirement ID so that no two requirement
       usages declare same-named features.
       ====================================================================== */

    requirement <'REQ-001'> {
        doc /* The warehouse management system shall receive incoming goods at designated receiving docks. */
        attribute classificationReq001 : String = "Functional";
        attribute verifyMethodReq001 : String = "functional test / demonstration at designated receiving docks.";
    }

    requirement <'REQ-002'> {
        doc /* The system shall verify received goods against purchase orders. */
        attribute classificationReq002 : String = "Functional";
        attribute verifyMethodReq002 : String = "functional test with matching and mismatching goods vs. purchase order.";
    }

    requirement <'REQ-003'> {
        doc /* The system shall assign storage locations based on product size, weight, and hazard class. */
        attribute classificationReq003 : String = "Functional";
        attribute verifyMethodReq003 : String = "functional test of location-assignment logic with inputs size, weight, hazard class.";
    }

    requirement <'REQ-004'> {
        doc /* The system shall support put-away operations from receiving to storage zones. */
        attribute classificationReq004 : String = "Functional";
        attribute verifyMethodReq004 : String = "functional test / demonstration of a put-away process flow from receiving to storage zones.";
    }

    requirement <'REQ-005'> {
        doc /* The system shall manage picking operations for outgoing orders. */
        attribute classificationReq005 : String = "Functional";
        attribute verifyMethodReq005 : String = "functional test / demonstration of picking for outgoing orders.";
    }

    requirement <'REQ-006'> {
        doc /* The system shall support wave, batch, and zone picking strategies. */
        attribute classificationReq006 : String = "Functional";
        attribute verifyMethodReq006 : String = "functional test exercising each of the three named strategies (wave, batch, zone).";
    }

    /* Process flow note: picking (REQ-005, REQ-006) feeds packing and
       shipping (REQ-007). Containment is documented here rather than by
       nesting REQ-005/REQ-006 inside REQ-007, because re-declaring the same
       requirement IDs as nested usages would duplicate their definitions. */
    requirement <'REQ-007'> {
        doc /* The system shall manage packing and shipping operations. */
        attribute classificationReq007 : String = "Functional";
        attribute verifyMethodReq007 : String = "functional test / demonstration of packing and shipping process flow.";
    }

    requirement <'REQ-008'> {
        doc /* The system shall integrate with external ERP systems via a REST API. */
        attribute classificationReq008 : String = "Functional (interface)";
        attribute verifyMethodReq008 : String = "integration test against an external ERP via the REST API.";
        attribute gapReq008 : String = "the source specifies no API endpoints, data formats, or ERP systems; interface detail is not defined in the input.";
    }

    requirement <'REQ-009'> {
        doc /* The system shall record barcode scans for every inventory movement. */
        attribute classificationReq009 : String = "Functional";
        attribute verifyMethodReq009 : String = "functional test verifying a scan record exists for each inventory movement (completeness check).";
    }

    requirement <'REQ-010'> {
        doc /* The system shall report real-time inventory levels per storage location. */
        attribute classificationReq010 : String = "Functional";
        attribute verifyMethodReq010 : String = "functional test comparing reported levels against actual per-location inventory.";
    }

    /* ======================================================================
       Non-Functional Requirements
       Source: sources/requirements.md (section "Non-Functional Requirements")
       ====================================================================== */

    requirement <'REQ-NF-001'> {
        doc /* The system shall manage at least 10,000 distinct SKUs. */
        attribute classificationReqNF001 : String = "Non-functional (capacity)";
        attribute verifyMethodReqNF001 : String = "capacity test with a 10,000-SKU dataset.";
        attribute minSkus : Integer = 10000;
        require constraint { minSkus >= 10000 }
    }

    requirement <'REQ-NF-002'> {
        doc /* The system shall sustain an order throughput of 500 orders per hour. */
        attribute classificationReqNF002 : String = "Non-functional (performance)";
        attribute verifyMethodReqNF002 : String = "load/performance test measuring sustained orders per hour.";
        attribute minOrderThroughput : Real = 500.0;
        require constraint { minOrderThroughput >= 500.0 }
    }

    requirement <'REQ-NF-003'> {
        doc /* The system shall maintain 99.9 percent service availability. */
        attribute classificationReqNF003 : String = "Non-functional (availability/reliability)";
        attribute verifyMethodReqNF003 : String = "availability measurement over the service period (monitoring/uptime reporting).";
        attribute gapReqNF003 : String = "the source does not define the measurement window (e.g., monthly vs. annual) or planned-downtime handling.";
        attribute minAvailabilityPercent : Real = 99.9;
        require constraint { minAvailabilityPercent >= 99.9 }
    }

    requirement <'REQ-NF-004'> {
        doc /* The system shall keep hazardous-material storage physically segregated from general storage. */
        attribute classificationReqNF004 : String = "Non-functional (safety)";
        attribute verifyMethodReqNF004 : String = "physical inspection/audit of storage segregation.";
    }

    requirement <'REQ-NF-005'> {
        doc /* The system shall enforce role-based access control for administrator, operator, and viewer roles. */
        attribute classificationReqNF005 : String = "Non-functional (security)";
        attribute verifyMethodReqNF005 : String = "access-control test for each of the three named roles (administrator, operator, viewer).";
        attribute gapReqNF005 : String = "the source defines the role names but no permission matrix per role.";
    }

    /* ======================================================================
       Constraints (modelled as requirement elements per task directive)
       Source: sources/requirements.md (section "Constraints")
       ====================================================================== */

    requirement <'C1'> {
        doc /* The warehouse floor area shall not exceed 5,000 square metres. */
        attribute classificationC1 : String = "Constraint (physical)";
        attribute verifyMethodC1 : String = "measurement of the warehouse layout/floor plan against 5,000 m2.";
        attribute maxFloorArea : Real = 5000.0;
        require constraint { maxFloorArea <= 5000.0 }
    }

    requirement <'C2'> {
        doc /* The maximum rack height shall not exceed 12 metres. */
        attribute classificationC2 : String = "Constraint (physical)";
        attribute verifyMethodC2 : String = "inspection/measurement of rack height against 12 m.";
        attribute maxRackHeight : Real = 12.0;
        require constraint { maxRackHeight <= 12.0 }
    }

    requirement <'C3'> {
        doc /* General storage shall be held between 15 and 25 degrees Celsius; cold storage between 2 and 8 degrees Celsius. */
        attribute classificationC3 : String = "Constraint (physical/environmental)";
        attribute verifyMethodC3 : String = "continuous temperature monitoring per storage zone against the stated ranges.";
        attribute gapC3 : String = "the source specifies no tolerance band, monitoring granularity, or humidity limits.";
        attribute generalStorageMinTemp : Real = 15.0;
        attribute generalStorageMaxTemp : Real = 25.0;
        attribute coldStorageMinTemp : Real = 2.0;
        attribute coldStorageMaxTemp : Real = 8.0;
        require constraint { generalStorageMinTemp <= 20.0 and generalStorageMaxTemp >= 20.0 and coldStorageMinTemp <= 5.0 and coldStorageMaxTemp >= 5.0 }
    }
}