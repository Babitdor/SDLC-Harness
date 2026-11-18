Hi — I've attached the requirements for our satellite communication system architecture.

Please build a **SysML v2 package diagram** for the satellite communication system. The top-level package is **SatelliteComSystem** with the following sub-packages:

- **GroundSegment**: Imports AntennaSystems and DataProcessing.
- **SpaceSegment**: Imports PowerSystems and ThermalControl.
- **CommunicationProtocols**: Imports FrequencyAllocation and EncryptionStandards.

Each sub-package must contain `part def` declarations for its key components with realistic attributes using SI units. Use `public import` for cross-package references. Respect the constraints in the requirements doc (frequency bands, encryption standards, power budget, thermal limits).

Produce the complete SysML v2 package model.