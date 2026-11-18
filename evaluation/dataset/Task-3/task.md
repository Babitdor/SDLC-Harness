Hi — I need you to build a block definition diagram (BDD) for a smart home energy management system. The requirements are attached.

The system has the following components with their specifications:

- **SolarPanels**: 5 kW peak power, 22% conversion efficiency
- **ChargeController**: 98% efficiency, regulates solar-to-battery charging
- **BatteryStorage**: 13.5 kWh usable capacity
- **Inverter**: 6 kW rated power, 96% conversion efficiency, 240 V AC output
- **GridConnection**: 240 V utility connection
- **HomeLoad**: 4 kW peak demand
- **SmartMeter**: 1 Hz sampling rate
- **CloudDashboard**: Remote monitoring and analytics

Use generalization hierarchies where appropriate — for instance, SolarPanel and GridConnection are both types of PowerSource. Include an enum def for battery chemistry types (Li-Ion, LeadAcid) with specialization (:>) for LiIonBattery and LeadAcidBattery as variants of BatteryStorage.

Please produce a proper SysML v2 BDD with part definitions, typed attributes using SI units, enumerations, generalizations, and composition structure. Follow the definition-usage pattern: define part defs first, then compose them in a top-level system part def.
