Hi — I've attached the requirements for our automated warehouse order fulfillment process in the source folder. Please review source/requirements.md for the full specification.

Build a SysML v2 activity diagram for the order fulfillment process. The process flow is:

1. Receive Order → Check Inventory → Route to Picking (if in stock) or Generate Backorder (if out of stock) → Collect Items → Verify Items → Pack and Label → Route to Shipping

If items are out of stock, the system should generate a backorder and notify the supplier instead of proceeding to picking.

Respect the constraints in the requirements doc (throughput, accuracy, temperature zones, hazmat segregation). Use proper SysML v2 textual notation with item definitions for data types, action definitions for each step, and a top-level composite action that composes all sub-actions with successions and decision branching.