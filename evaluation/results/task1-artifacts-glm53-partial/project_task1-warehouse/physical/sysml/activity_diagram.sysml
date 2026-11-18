package WarehouseGoodsFlowActivities {
    public import ScalarValues::*;

    /* ===== Item definitions (data exchanged between activities) ===== */

    item def GoodsItem {
        attribute itemId : String = "";
        attribute quantity : Integer = 0;
        attribute sizeValue : Real = 0.0;
        attribute weightValue : Real = 0.0;
        attribute hazardClass : String = "";
    }

    item def PurchaseOrder {
        attribute poId : String = "";
    }

    item def ReceiptRecord {
        attribute receiptId : String = "";
        attribute verified : Boolean = false;
    }

    item def StorageLocation {
        attribute locationId : String = "";
        attribute zoneType : String = "";
        attribute temperatureRange : String = "";
    }

    item def OutgoingOrder {
        attribute orderId : String = "";
    }

    item def ScanRecord {
        attribute scanId : String = "";
        attribute movementType : String = "";
    }

    item def ErpRequest {
        attribute requestId : String = "";
    }

    item def ErpResponse {
        attribute responseContent : String = "";
        attribute isError : Boolean = false;
    }

    item def InventoryReport {
        attribute reportContent : String = "";
    }

    /* ===== Leaf actions (atomic steps traced to ACTIVITIES.md) ===== */

    /* ACT-001 steps 1-2 (UC-001; REQ-001): register arrival, create receipt record. */
    action def doRegisterGoodsArrival {
        in goods : GoodsItem;
        out receipt : ReceiptRecord;
        first start;
        then done;
    }

    /* ACT-001 step 5 (UC-001 step 5): confirm completion of receiving to the Operator. */
    action def doConfirmReceivingCompletion {
        in receipt : ReceiptRecord;
        first start;
        then done;
    }

    /* ACT-001 A1 / UC-002 A1: record the mismatch; receipt not confirmed as verified. */
    action def doRecordReceivingMismatch {
        in receipt : ReceiptRecord;
        first start;
        then done;
    }

    /* ACT-002 step 2 (UC-002 step 2): retrieve the purchase order for the receipt. */
    action def doRetrievePurchaseOrder {
        in receipt : ReceiptRecord;
        out purchaseOrder : PurchaseOrder;
        first start;
        then done;
    }

    /* ACT-002 step 3 (UC-002 step 3; REQ-002): compare received goods against purchase order. */
    action def doCompareGoodsWithPurchaseOrder {
        in goods : GoodsItem;
        in purchaseOrder : PurchaseOrder;
        out matches : Boolean = false;
        first start;
        then done;
    }

    /* ACT-002 step 4 (UC-002 step 4): confirm goods match the purchase order (match path). */
    action def doConfirmMatchedGoods {
        in goods : GoodsItem;
        first start;
        then done;
    }

    /* ACT-002 step 5 / A1 (UC-002 A1; REQ-002): record verification result mismatch. */
    action def doRecordVerificationMismatch {
        in goods : GoodsItem;
        first start;
        then done;
    }

    /* ACT-003 step 2 (UC-003 step 2; REQ-003): retrieve product size, weight, hazard class. */
    action def doRetrieveProductCharacteristics {
        in goods : GoodsItem;
        out characteristicsRetrieved : Boolean = false;
        first start;
        then done;
    }

    /* ACT-003 steps 2-3 (UC-003; REQ-003, REQ-NF-004, C3): determine eligible zone type -
       hazardous vs general (REQ-NF-004), general 15-25 degC vs cold 2-8 degC (C3) -
       and whether a location satisfying size, weight and hazard class exists (UC-003 A2). */
    action def doDetermineEligibleZoneType {
        in goods : GoodsItem;
        out isHazardous : Boolean = false;
        out isColdZone : Boolean = false;
        out locationAvailable : Boolean = false;
        first start;
        then done;
    }

    /* ACT-003 A1 (REQ-NF-004): assign location in physically segregated hazardous-material storage. */
    action def doAssignHazardousStorageLocation {
        in goods : GoodsItem;
        out location : StorageLocation;
        out locationFound : Boolean = false;
        first start;
        then done;
    }

    /* ACT-003 C3 cold branch: assign location in cold-storage zone held at 2-8 degC. */
    action def doAssignColdStorageLocation {
        in goods : GoodsItem;
        out location : StorageLocation;
        out locationFound : Boolean = false;
        first start;
        then done;
    }

    /* ACT-003 C3 general branch: assign location in general-storage zone held at 15-25 degC. */
    action def doAssignGeneralStorageLocation {
        in goods : GoodsItem;
        out location : StorageLocation;
        out locationFound : Boolean = false;
        first start;
        then done;
    }

    /* ACT-003 step 4 (UC-003 step 4): communicate assigned storage location to the Operator. */
    action def doCommunicateAssignedLocation {
        in location : StorageLocation;
        first start;
        then done;
    }

    /* ACT-003 A2 (UC-003 A2): report that no location can be assigned. */
    action def doReportNoLocationAvailable {
        in goods : GoodsItem;
        first start;
        then done;
    }

    /* ACT-004 step 2 (UC-004 step 2; REQ-004): transfer goods from receiving to assigned zone. */
    action def doTransferGoodsToStorageZone {
        in goods : GoodsItem;
        in location : StorageLocation;
        first start;
        then done;
    }

    /* ACT-004 step 4 (UC-004 step 4): confirm put-away, record goods at assigned location. */
    action def doConfirmPutAway {
        in goods : GoodsItem;
        in location : StorageLocation;
        first start;
        then done;
    }

    /* ACT-005 step 1 (UC-005 step 1; REQ-005): create picking task for the outgoing order. */
    action def doCreatePickingTask {
        in order : OutgoingOrder;
        first start;
        then done;
    }

    /* ACT-005 step 2 (UC-005 step 2; REQ-010): provide storage locations of items to pick. */
    action def doProvidePickLocations {
        in order : OutgoingOrder;
        first start;
        then done;
    }

    /* ACT-005 step 3 (UC-005 step 3): retrieve items from the storage locations. */
    action def doRetrieveItemsFromStorage {
        in order : OutgoingOrder;
        out itemAvailable : Boolean = false;
        first start;
        then done;
    }

    /* ACT-005 step 5 (UC-005 step 5): confirm picked items against the outgoing order. */
    action def doConfirmPick {
        in order : OutgoingOrder;
        first start;
        then done;
    }

    /* ACT-005 A1 (UC-005 A1; REQ-010): record discrepancy for unavailable item. */
    action def doRecordPickDiscrepancy {
        in order : OutgoingOrder;
        first start;
        then done;
    }

    /* ACT-006 step 1 (UC-006 step 1; REQ-006): group outgoing orders by wave, batch or zone. */
    action def doGroupOrdersByStrategy {
        in outgoingOrder : OutgoingOrder;
        out isWave : Boolean = false;
        out isBatch : Boolean = false;
        first start;
        then done;
    }

    /* ACT-006 A1 (UC-006 A1; REQ-006): release outgoing orders as waves. */
    action def doPickByWave {
        in outgoingOrder : OutgoingOrder;
        first start;
        then done;
    }

    /* ACT-006 A2 (UC-006 A2; REQ-006): combine items of multiple orders into batch picks. */
    action def doPickByBatch {
        in outgoingOrder : OutgoingOrder;
        first start;
        then done;
    }

    /* ACT-006 A3 (UC-006 A3; REQ-006): organize picking by storage zones. */
    action def doPickByZone {
        in outgoingOrder : OutgoingOrder;
        first start;
        then done;
    }

    /* ACT-006 step 3 (UC-006 step 3): confirm completion of picking per order. */
    action def doConfirmOrderPickingCompletion {
        in outgoingOrder : OutgoingOrder;
        first start;
        then done;
    }

    /* ACT-007 step 1 (UC-007 step 1; REQ-007): pack picked items for the outgoing order. */
    action def doPackItemsForOrder {
        in order : OutgoingOrder;
        first start;
        then done;
    }

    /* ACT-007 step 3 (UC-007 step 3): confirm completion of packing. */
    action def doConfirmPackingCompletion {
        in order : OutgoingOrder;
        first start;
        then done;
    }

    /* ACT-008 step 1 (UC-007 step 4; REQ-007): ship the packed order. */
    action def doShipOrder {
        in order : OutgoingOrder;
        first start;
        then done;
    }

    /* ACT-008 step 3 (UC-007 step 6): confirm shipment of the order. */
    action def doConfirmShipment {
        in order : OutgoingOrder;
        first start;
        then done;
    }

    /* ACT-009 step 1 (UC-008 step 1; REQ-008): ERP system sends request to the REST API. */
    action def doReceiveErpRequest {
        out erpRequest : ErpRequest;
        first start;
        then done;
    }

    /* ACT-009 step 2 (UC-008 step 2; REQ-008): process the ERP request. */
    action def doProcessErpRequest {
        in erpRequest : ErpRequest;
        out processable : Boolean = false;
        first start;
        then done;
    }

    /* ACT-009 steps 2-3 (UC-008 steps 2-3): return processing response via REST API. */
    action def doReturnProcessingResponse {
        in erpRequest : ErpRequest;
        out erpResponse : ErpResponse;
        first start;
        then done;
    }

    /* ACT-009 A1 (UC-008 A1): return error response via REST API. */
    action def doReturnErrorResponse {
        in erpRequest : ErpRequest;
        out erpResponse : ErpResponse;
        first start;
        then done;
    }

    /* ACT-010 step 1 (UC-009 step 1; REQ-009): Operator scans the movement barcode(s). */
    action def doReadBarcode {
        out readable : Boolean = false;
        first start;
        then done;
    }

    /* ACT-010 steps 2-3 (UC-009 steps 2-3; REQ-009): record and store the scan record. */
    action def doStoreScanRecord {
        out scanRecord : ScanRecord;
        first start;
        then done;
    }

    /* ACT-010 A1 / UC-001 A2 (REQ-009): movement not completed until a scan is captured. */
    action def doWithholdMovementCompletion {
        first start;
        then done;
    }

    /* ACT-011 step 1 (UC-004 steps 3-5, UC-005 steps 4-5, UC-007 steps 2-6; REQ-009):
       take up the completed inventory movement together with its scan record. */
    action def doTakeUpCompletedMovement {
        in movementType : String;
        out movementCompleted : Boolean = false;
        first start;
        then done;
    }

    /* ACT-011 step 2 (UC-004 step 5; REQ-010): update real-time level of affected location. */
    action def doApplyInventoryLevelUpdate {
        in movementType : String;
        first start;
        then done;
    }

    /* ACT-011 decision (UC-004 A2; UC-009 A1; REQ-009): level not updated without completed movement. */
    action def doWithholdLevelUpdate {
        in movementType : String;
        first start;
        then done;
    }

    /* ACT-012 RBAC gate (REQ-NF-005): check viewer authorization before reporting. */
    action def doCheckViewerAuthorization {
        out authorized : Boolean = false;
        first start;
        then done;
    }

    /* ACT-012 step 2 (UC-010 step 2; REQ-010): compile current levels per storage location. */
    action def doCompileInventoryLevels {
        out locationEmpty : Boolean = false;
        first start;
        then done;
    }

    /* ACT-012 A1 (UC-010 A1; REQ-010): report empty level for location without inventory. */
    action def doReportEmptyLocationLevel {
        first start;
        then done;
    }

    /* ACT-012 step 3 (UC-010 step 3; REQ-010): report levels to the Viewer in real time. */
    action def doReportLocationLevel {
        first start;
        then done;
    }

    /* ACT-012 RBAC enforcement (REQ-NF-005): levels not reported without authorization. */
    action def doWithholdInventoryReport {
        first start;
        then done;
    }

    /* ===== Composite actions (ACT-NNN control flow) ===== */

    /* ACT-003 (UC-003; REQ-003): non-hazardous branch - C3 temperature-zone routing
       between cold storage (2-8 degC) and general storage (15-25 degC). */
    action def doAssignNonHazardousStorageLocation {
        action evaluateTemperatureZone : doDetermineEligibleZoneType;
        action coldAssignment : doAssignColdStorageLocation;
        action generalAssignment : doAssignGeneralStorageLocation;

        first start;
        then evaluateTemperatureZone;
        then decide;
            if evaluateTemperatureZone.isColdZone then coldAssignment;
            else generalAssignment;
        then done;
    }

    /* ACT-003 (UC-003; REQ-003, REQ-NF-004): eligible-zone assignment - hazardous-material
       branch (REQ-NF-004) vs non-hazardous branch, then communicate the location (step 4). */
    action def doAssignLocationInEligibleZone {
        action determineZoneType : doDetermineEligibleZoneType;
        action hazmatAssignment : doAssignHazardousStorageLocation;
        action nonHazmatAssignment : doAssignNonHazardousStorageLocation;
        action communicateLocation : doCommunicateAssignedLocation;

        first start;
        then determineZoneType;
        then decide;
            if determineZoneType.isHazardous then hazmatAssignment;
            else nonHazmatAssignment;
        then communicateLocation;
        then done;
    }

    /* ACT-010 (UC-009; REQ-009): record barcode scan for the inventory movement;
       the movement is not recorded as completed until a scan is captured (UC-009 A1).
       Invoked at every inventory movement: ACT-001 step 3, ACT-004 step 3,
       ACT-005 step 4, ACT-007 step 2, ACT-008 step 2. */
    action def doRecordBarcodeScan {
        action readBarcode : doReadBarcode;
        action storeScan : doStoreScanRecord;
        action withholdCompletion : doWithholdMovementCompletion;

        first start;
        then readBarcode;
        then decide;
            if readBarcode.readable then storeScan;
            else withholdCompletion;
        then done;
    }

    /* ACT-011 (REQ-010; REQ-009): update real-time inventory levels per storage location
       after each completed movement; no update without a completed movement (UC-004 A2). */
    action def doUpdateInventoryLevels {
        action takeUpMovement : doTakeUpCompletedMovement;
        action applyUpdate : doApplyInventoryLevelUpdate;
        action withholdUpdate : doWithholdLevelUpdate;

        first start;
        then takeUpMovement;
        then decide;
            if takeUpMovement.movementCompleted then applyUpdate;
            else withholdUpdate;
        then done;
    }

    /* ACT-002 (UC-002; REQ-002): verify received goods against the purchase order;
       match/mismatch branch at step 4 (UC-002 A1). */
    action def doVerifyGoodsAgainstPurchaseOrder {
        action retrievePurchaseOrder : doRetrievePurchaseOrder;
        action compareGoods : doCompareGoodsWithPurchaseOrder;
        action confirmMatch : doConfirmMatchedGoods;
        action recordMismatch : doRecordVerificationMismatch;

        first start;
        then retrievePurchaseOrder;
        then compareGoods;
        then decide;
            if compareGoods.matches then confirmMatch;
            else recordMismatch;
        then done;
    }

    /* ACT-001 (UC-001; REQ-001): receive incoming goods at the receiving dock;
       step 3 invokes ACT-010, step 4 invokes ACT-002, mismatch branch per UC-001 A1. */
    action def doReceiveIncomingGoods {
        action registerArrival : doRegisterGoodsArrival;
        action recordScans : doRecordBarcodeScan;
        action verifyGoods : doVerifyGoodsAgainstPurchaseOrder;
        action confirmReceiving : doConfirmReceivingCompletion;
        action recordMismatch : doRecordReceivingMismatch;

        first start;
        then registerArrival;
        then recordScans;
        then verifyGoods;
        then decide;
            if verifyGoods.matches then confirmReceiving;
            else recordMismatch;
        then done;
    }

    /* ACT-003 (UC-003; REQ-003): assign storage location from size, weight, hazard class;
       no-location branch per UC-003 A2, hazmat branch per REQ-NF-004, C3 routing. */
    action def doAssignStorageLocation {
        action retrieveCharacteristics : doRetrieveProductCharacteristics;
        action determineZoneType : doDetermineEligibleZoneType;
        action assignLocation : doAssignLocationInEligibleZone;
        action reportNoLocation : doReportNoLocationAvailable;

        first start;
        then retrieveCharacteristics;
        then determineZoneType;
        then decide;
            if determineZoneType.locationAvailable then assignLocation;
            else reportNoLocation;
        then done;
    }

    /* ACT-004 (UC-004; REQ-004): put away goods from receiving to the assigned storage zone;
       step 3 invokes ACT-010, step 5 invokes ACT-011. */
    action def doPutAwayGoodsInStorageZone {
        action transferGoods : doTransferGoodsToStorageZone;
        action recordScans : doRecordBarcodeScan;
        action confirmPutAway : doConfirmPutAway;
        action updateLevels : doUpdateInventoryLevels;

        first start;
        then transferGoods;
        then recordScans;
        then confirmPutAway;
        then updateLevels;
        then done;
    }

    /* ACT-005 (UC-005; REQ-005): pick items for the outgoing order;
       step 4 invokes ACT-010, availability branch per UC-005 A1, level update via ACT-011. */
    action def doPickItemsForOutgoingOrder {
        action createPickingTask : doCreatePickingTask;
        action providePickLocations : doProvidePickLocations;
        action retrieveItems : doRetrieveItemsFromStorage;
        action recordScans : doRecordBarcodeScan;
        action confirmPick : doConfirmPick;
        action recordDiscrepancy : doRecordPickDiscrepancy;
        action updateLevels : doUpdateInventoryLevels;

        first start;
        then createPickingTask;
        then providePickLocations;
        then retrieveItems;
        then recordScans;
        then decide;
            if retrieveItems.itemAvailable then confirmPick;
            else recordDiscrepancy;
        then updateLevels;
        then done;
    }

    /* ACT-006 (UC-006; REQ-006): non-wave strategies - batch (UC-006 A2) vs zone (UC-006 A3). */
    action def doExecuteNonWavePicking {
        action groupOrders : doGroupOrdersByStrategy;
        action batchPicking : doPickByBatch;
        action zonePicking : doPickByZone;

        first start;
        then groupOrders;
        then decide;
            if groupOrders.isBatch then batchPicking;
            else zonePicking;
        then done;
    }

    /* ACT-006 (UC-006; REQ-006): execute picking strategy - wave (UC-006 A1), batch (A2)
       or zone (A3); step 2 invokes ACT-005 for each order in the strategy group. */
    action def doExecutePickingStrategy {
        action groupOrders : doGroupOrdersByStrategy;
        action wavePicking : doPickByWave;
        action nonWavePicking : doExecuteNonWavePicking;
        action pickOrder : doPickItemsForOutgoingOrder;
        action confirmCompletion : doConfirmOrderPickingCompletion;

        first start;
        then groupOrders;
        then decide;
            if groupOrders.isWave then wavePicking;
            else nonWavePicking;
        then pickOrder;
        then confirmCompletion;
        then done;
    }

    /* ACT-007 (UC-007 steps 1-3; REQ-007): pack picked items for the outgoing order;
       step 2 invokes ACT-010; packing confirmation gates ACT-008. */
    action def doPackPickedItems {
        action packItems : doPackItemsForOrder;
        action recordScans : doRecordBarcodeScan;
        action confirmPacking : doConfirmPackingCompletion;

        first start;
        then packItems;
        then recordScans;
        then confirmPacking;
        then done;
    }

    /* ACT-008 (UC-007 steps 4-6; REQ-007): ship the packed order;
       step 2 invokes ACT-010, step 3 triggers ACT-011 for the per-location level update. */
    action def doShipPackedOrder {
        action shipOrder : doShipOrder;
        action recordScans : doRecordBarcodeScan;
        action confirmShipment : doConfirmShipment;
        action updateLevels : doUpdateInventoryLevels;

        first start;
        then shipOrder;
        then recordScans;
        then confirmShipment;
        then updateLevels;
        then done;
    }

    /* ACT-009 (UC-008; REQ-008): process external ERP request via REST API;
       processable/not-processable branch per UC-008 A1. */
    action def doProcessErpRestApiRequest {
        action receiveRequest : doReceiveErpRequest;
        action processRequest : doProcessErpRequest;
        action returnProcessingResponse : doReturnProcessingResponse;
        action returnErrorResponse : doReturnErrorResponse;

        first start;
        then receiveRequest;
        then processRequest;
        then decide;
            if processRequest.processable then returnProcessingResponse;
            else returnErrorResponse;
        then done;
    }

    /* ACT-012 (UC-010; REQ-010): compile and report real-time inventory levels per
       storage location to the Viewer; RBAC gate (REQ-NF-005), empty-level branch (UC-010 A1). */
    action def doReportInventoryLevels {
        action checkAuthorization : doCheckViewerAuthorization;
        action compileLevels : doCompileInventoryLevels;
        action reportEmptyLevel : doReportEmptyLocationLevel;
        action reportLocationLevel : doReportLocationLevel;
        action withholdReport : doWithholdInventoryReport;

        first start;
        then checkAuthorization;
        then decide;
            if checkAuthorization.authorized then compileLevels;
            else withholdReport;
        then decide;
            if compileLevels.locationEmpty then reportEmptyLevel;
            else reportLocationLevel;
        then done;
    }

    /* End-to-end goods flow (ACTIVITIES.md): ACT-001 -> ACT-002 -> ACT-003 -> ACT-004
       -> ACT-006 -> ACT-005 -> ACT-007 -> ACT-008, with cross-cutting ACT-010 scan
       recording and ACT-011 level updates invoked at their documented movement points.
       ACT-009 (ERP REST API) and ACT-012 (inventory reporting) are standalone activities. */
    action def doExecuteWarehouseGoodsFlow {
        action receiveGoods : doReceiveIncomingGoods;
        action assignStorage : doAssignStorageLocation;
        action putAwayGoods : doPutAwayGoodsInStorageZone;
        action executePicking : doExecutePickingStrategy;
        action packOrder : doPackPickedItems;
        action shipGoods : doShipPackedOrder;

        first start;
        then receiveGoods;
        then assignStorage;
        then putAwayGoods;
        then executePicking;
        then packOrder;
        then shipGoods;
        then done;
    }
}