Hi — I need you to build a complete SysML v2 model for a smart irrigation system.

The system should include:

1. A requirement diagram capturing:
   - REQ-001: The system shall reduce water consumption by 30% compared to scheduled irrigation.
   - REQ-002: The system shall sample soil moisture every 5 minutes.

2. A Block Definition Diagram (BDD) showing the system structure with these components:
   - SoilMoistureSensor: Measures soil moisture content
   - RainSensor: Detects rainfall presence
   - TemperatureSensor: Measures ambient temperature
   - ValveController: Controls the irrigation valve (open/close)
   - CentralController: Processes sensor data and commands the valve

3. An Internal Block Diagram (IBD) showing connections between all components with item flows for:
   - Moisture readings from SoilMoistureSensor to CentralController
   - Rain status from RainSensor to CentralController
   - Temperature data from TemperatureSensor to CentralController
   - Valve commands from CentralController to ValveController

Please model this as a proper SysML v2 model with requirement definitions, part definitions, port definitions, item definitions, and connection definitions.
