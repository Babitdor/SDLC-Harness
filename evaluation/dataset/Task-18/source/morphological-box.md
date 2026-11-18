# Morphological Box — Grid-Scale Battery Energy Storage System

Document: MB-BESS-018
Status: For evaluation — no option selected

| Function | Option 1 | Option 2 | Option 3 |
|---|---|---|---|
| Energy conversion (AC↔DC) | Bi-directional 4-quadrant IGBT inverter | Multi-level MMC converter | SiC MOSFET 2-level VSI |
| Thermal management | Liquid cold-plate with chiller loop | Forced-air HVAC with ducted plenum | Immersion cooling (dielectric fluid) |
| Grid interface | Step-up transformer (480 V → 13.8 kV) | Direct MV connection via solid-state transformer | Pad-mounted transformer with LTC |
| Battery management system (BMS) | Distributed BMS (per-module) | Centralized BMS with daisy-chain CAN | Hybrid master-slave BMS |
| Protection | High-speed DC breaker + fused contactor | Solid-state circuit breaker (SSCB) | Hybrid electromechanical + pyro switch |
| SCADA integration | DNP3 over TCP/IP | IEC 61850 (GOOSE + MMS) | Modbus TCP with OPC-UA gateway |

## Option Characteristics

**Conversion — 4-quadrant IGBT inverter.** Mature at 1 MW, supports frequency and
reactive-power control. **MMC.** Very low harmonics; economic only at much higher
voltages and powers. **SiC 2-level VSI.** Highest efficiency and switching speed;
newer at MW scale.

**Thermal — liquid cold-plate.** Tight cell temperature spread, compact; introduces
coolant that needs leak containment. **Forced air.** Simple, no liquid; wider cell
temperature spread. **Immersion.** Best thermal uniformity and fire suppression;
least field experience.

**Grid interface — step-up transformer to 13.8 kV.** Standard at distribution
substations. **Solid-state transformer.** Compact and controllable; limited field
experience at this rating.

**SCADA — DNP3.** The common utility SCADA protocol; supports DNP3 Secure
Authentication. **IEC 61850.** Substation-native with fast GOOSE messaging.
**Modbus + OPC-UA.** Widely supported; Modbus has no native security.

## Known Incompatibilities

- An MMC converter is not economic at 1 MW on a low-voltage battery bus.
- Liquid cold-plate or immersion cooling requires containment of 110 % of the
  liquid volume (C18); forced air does not.
- Modbus TCP without a security layer cannot meet the authenticated, encrypted
  SCADA rule in the knowledge base.
- A centralised BMS on a daisy-chain bus conflicts with the dual-redundant BMS
  communication rule unless a second bus is added.
