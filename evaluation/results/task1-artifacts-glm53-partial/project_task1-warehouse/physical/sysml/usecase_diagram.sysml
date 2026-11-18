package WarehouseManagementSystemUseCases {
    public import ScalarValues::*;

    // =====================================================================
    // System under consideration
    // =====================================================================
    // Warehouse Management System - the system under consideration; secondary
    // actor in every use case: it records receipts and movements, assigns
    // storage locations, directs and confirms picking, confirms packing and
    // shipping, provides the REST API, records barcode scans, and reports
    // inventory levels.
    part def 'Warehouse Management System';

    // =====================================================================
    // External actors
    // =====================================================================
    // Operator - role-based access control role named in REQ-NF-005; primary
    // actor of all warehouse process use cases. Specialized by process area:
    part def 'Operator';
    part def OperatorReceiving :> 'Operator';        // Operator (receiving) per REQ-001/REQ-002
    part def OperatorPutAway :> 'Operator';          // Operator (put-away) per REQ-003/REQ-004
    part def OperatorPicking :> 'Operator';          // Operator (picking) per REQ-005/REQ-006
    part def OperatorPackingShipping :> 'Operator';  // Operator (packing & shipping) per REQ-007

    // Viewer - RBAC role named in REQ-NF-005; primary actor of the inventory
    // reporting use case (UC-010), which is read access.
    part def 'Viewer';

    // Administrator - RBAC role named in REQ-NF-005; no functional requirement
    // REQ-001..REQ-010 assigns a distinct goal to the administrator role, so it
    // is not the primary actor of any derived use case; it accesses the system
    // under RBAC like the other roles.
    part def 'Administrator';

    // ERP System - external system that integrates with the warehouse
    // management system via a REST API (REQ-008); primary actor of UC-008.
    part def 'ERP System';

    // =====================================================================
    // Requirement trace anchors (primary requirements per traceability matrix)
    // =====================================================================
    requirement def 'REQ-001' { doc /* Primary requirement of UC-001 - Receive Incoming Goods at Receiving Dock. */ }
    requirement def 'REQ-002' { doc /* Primary requirement of UC-002 - Verify Received Goods Against Purchase Order. */ }
    requirement def 'REQ-003' { doc /* Primary requirement of UC-003 - Assign Storage Location. */ }
    requirement def 'REQ-004' { doc /* Primary requirement of UC-004 - Put Away Goods from Receiving to Storage Zone. */ }
    requirement def 'REQ-005' { doc /* Primary requirement of UC-005 - Pick Items for Outgoing Order. */ }
    requirement def 'REQ-006' { doc /* Primary requirement of UC-006 - Execute Picking Strategy (Wave, Batch, Zone). */ }
    requirement def 'REQ-007' { doc /* Primary requirement of UC-007 - Pack and Ship Outgoing Order. */ }
    requirement def 'REQ-008' { doc /* Primary requirement of UC-008 - Integrate with External ERP System via REST API. */ }
    requirement def 'REQ-009' { doc /* Primary requirement of UC-009 - Record Barcode Scan for Inventory Movement. */ }
    requirement def 'REQ-010' { doc /* Primary requirement of UC-010 - Report Real-Time Inventory Levels per Storage Location. */ }

    // =====================================================================
    // Use cases
    // =====================================================================

    use case def 'UC-001' {
        subject uc001System : 'Warehouse Management System';
        actor uc001Operator : OperatorReceiving;

        objective 'Receive Incoming Goods at Receiving Dock' {
            doc /* Trigger: incoming goods arrive at a designated receiving dock (REQ-001).
                   The Operator registers the arrival of the incoming goods at the receiving
                   dock; the system creates a receipt record for the incoming goods at the
                   dock. The Operator scans the barcodes of the received goods and the system
                   records the scans for the inventory movement (includes UC-009). The system
                   verifies the received goods against the purchase order (includes UC-002)
                   and confirms completion of the receiving operation to the Operator.
                   Alternate flows: a verification mismatch is recorded and the receipt is not
                   confirmed as verified (UC-002 alternate flow); a barcode scan that cannot
                   be captured blocks recording the movement as completed (REQ-009). */
        }

        include use case 'UC-002';
        include use case 'UC-009';

        satisfy requirement req001 : 'REQ-001';
    }

    use case def 'UC-002' {
        subject uc002System : 'Warehouse Management System';
        actor uc002Operator : OperatorReceiving;

        objective 'Verify Received Goods Against Purchase Order' {
            doc /* Trigger: received goods are presented for verification during receiving (REQ-002).
                   The Operator selects the receipt to be verified; the system retrieves the
                   purchase order associated with the receipt, compares the received goods
                   against the purchase order, confirms that the goods match, and records the
                   verification result (match). Alternate flow: the goods do not match the
                   purchase order - the system records the verification result (mismatch) and
                   does not confirm the goods as verified. */
        }

        satisfy requirement req002 : 'REQ-002';
    }

    use case def 'UC-003' {
        subject uc003System : 'Warehouse Management System';
        actor uc003Operator : OperatorPutAway;

        objective 'Assign Storage Location' {
            doc /* Trigger: received and verified goods require a storage location (follows
                   UC-001/UC-002; REQ-003). The Operator requests a storage location for the
                   received and verified goods; the system retrieves the product's size,
                   weight, and hazard class, assigns a storage location based on them, and
                   communicates the assigned storage location to the Operator. Alternate
                   flows: hazardous material is assigned a location in the physically
                   segregated hazardous-material storage (REQ-NF-004); if no storage location
                   satisfies the size, weight, and hazard class criteria, the system reports
                   that no location can be assigned. */
        }

        satisfy requirement req003 : 'REQ-003';
    }

    use case def 'UC-004' {
        subject uc004System : 'Warehouse Management System';
        actor uc004Operator : OperatorPutAway;

        objective 'Put Away Goods from Receiving to Storage Zone' {
            doc /* Trigger: goods have an assigned storage location and are ready for
                   put-away (follows UC-003; REQ-004). The Operator retrieves the assigned
                   storage location for the goods from the system and transfers the goods
                   from receiving to the assigned storage zone; the Operator scans the
                   barcodes for the movement and the system records the scans (includes
                   UC-009). The system confirms the put-away, records the goods at the
                   assigned storage location, and the put-away movement is reflected in the
                   real-time inventory levels per storage location (REQ-010). Alternate
                   flows: hazardous material is put away in the physically segregated
                   hazardous-material storage (REQ-NF-004); if the put-away cannot be
                   completed, the system does not confirm it and the movement is not recorded
                   as completed (REQ-009). */
        }

        include use case 'UC-003';
        include use case 'UC-009';

        satisfy requirement req004 : 'REQ-004';
    }

    use case def 'UC-005' {
        subject uc005System : 'Warehouse Management System';
        actor uc005Operator : OperatorPicking;

        objective 'Pick Items for Outgoing Order' {
            doc /* Trigger: an outgoing order is released for picking (REQ-005). The system
                   creates a picking task for the outgoing order and provides the Operator
                   with the storage locations of the items to be picked; the Operator
                   retrieves the items from the storage locations and scans the item
                   barcodes, and the system records the scans for the movement (includes
                   UC-009) and confirms the picked items against the outgoing order.
                   Alternate flow: an item is not available at the indicated storage
                   location - the system records the discrepancy and does not confirm the
                   pick for that item (REQ-010). */
        }

        include use case 'UC-009';

        satisfy requirement req005 : 'REQ-005';
    }

    use case def 'UC-006' {
        subject uc006System : 'Warehouse Management System';
        actor uc006Operator : OperatorPicking;

        objective 'Execute Picking Strategy (Wave, Batch, Zone)' {
            doc /* Trigger: outgoing orders are due for picking and a picking strategy is
                   applied (REQ-006). The system groups the outgoing orders for picking
                   according to the applicable strategy - wave, batch, or zone - and the
                   Operator executes picking for the grouped orders (includes UC-005); the
                   system confirms completion of picking for each order in the group.
                   Alternate flows: wave - the outgoing orders are released as waves and
                   picking is executed wave by wave; batch - items of multiple outgoing
                   orders are combined into batch picks; zone - picking is organized by
                   storage zones and executed zone by zone (REQ-006). */
        }

        include use case 'UC-005';

        satisfy requirement req006 : 'REQ-006';
    }

    use case def 'UC-007' {
        subject uc007System : 'Warehouse Management System';
        actor uc007Operator : OperatorPackingShipping;

        objective 'Pack and Ship Outgoing Order' {
            doc /* Trigger: picked items of an outgoing order are ready for packing (follows
                   UC-005; REQ-007). The Operator packs the picked items for the outgoing
                   order and scans the barcodes for the packing movement; the system records
                   the scans (includes UC-009) and confirms completion of packing. The
                   Operator ships the packed order and scans the barcodes for the shipping
                   movement; the system records the scans (includes UC-009) and confirms
                   shipment of the order. Alternate flow: packing cannot be completed - the
                   order is not shipped and the movement is not recorded as completed
                   (REQ-009). */
        }

        include use case 'UC-009';

        satisfy requirement req007 : 'REQ-007';
    }

    use case def 'UC-008' {
        subject uc008System : 'Warehouse Management System';
        actor uc008ErpSystem : 'ERP System';

        objective 'Integrate with External ERP System via REST API' {
            doc /* Trigger: the external ERP system sends a request to the system's REST API
                   (REQ-008). The external ERP system sends a request to the system's REST
                   API; the system processes the request and returns a response to the ERP
                   system via the REST API. Alternate flow: the request cannot be processed -
                   the system returns an error response to the ERP system via the REST API. */
        }

        satisfy requirement req008 : 'REQ-008';
    }

    use case def 'UC-009' {
        subject uc009System : 'Warehouse Management System';
        actor uc009Operator : 'Operator';

        objective 'Record Barcode Scan for Inventory Movement' {
            doc /* Trigger: an inventory movement is performed in any process area -
                   receiving, put-away, picking, packing, shipping (REQ-009). The Operator
                   (the role performing the movement: receiving, put-away, picking, or
                   packing & shipping) scans the barcode(s) associated with the inventory
                   movement; the system records the scan, associates it with the inventory
                   movement, and stores the scan record such that a scan record exists for
                   every inventory movement (REQ-009 completeness). Alternate flow: the
                   barcode cannot be read - no scan is recorded and the movement is not
                   recorded as completed until a scan is captured. */
        }

        satisfy requirement req009 : 'REQ-009';
    }

    use case def 'UC-010' {
        subject uc010System : 'Warehouse Management System';
        actor uc010Viewer : 'Viewer';

        objective 'Report Real-Time Inventory Levels per Storage Location' {
            doc /* Trigger: the user requests current inventory levels (REQ-010). The Viewer
                   requests real-time inventory levels; the system compiles the current
                   inventory levels per storage location and reports the levels to the
                   Viewer in real time (REQ-010), fed by the recorded inventory movements
                   (REQ-009). Alternate flow: a storage location holds no inventory - the
                   system reports an empty level for that location. */
        }

        satisfy requirement req010 : 'REQ-010';
    }
}