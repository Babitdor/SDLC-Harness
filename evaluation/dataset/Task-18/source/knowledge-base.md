# Domain Knowledge Base — Grid-Scale Battery Storage

## Applicable Standards

| Standard | Scope |
|---|---|
| **IEC 62933** | Electrical energy storage (EES) systems — safety, performance, environmental |
| **IEEE 1547** | Interconnection and interoperability of distributed energy resources |
| **UL 9540** | Safety of energy storage systems and equipment |
| **UL 9540A** | Test method for evaluating thermal runaway fire propagation in battery energy storage systems |
| **ANSI C84.1** | Electric power systems — voltage ratings (60 Hz) |
| **NFPA 855** | Installation of stationary energy storage systems (fire safety) |
| **IEC 62619** | Safety of large-format secondary lithium cells and batteries |
| **IEEE C37.90** | Protective relaying for power systems |

## Design Rules

- **Thermal runaway prevention**: Maintain per-module temperature ≤ 35 °C; deploy gas detection (CO, H₂) and venting; use flame-retardant separators.
- **Battery safety**: Enforce voltage, current, and temperature trip limits at the cell level; provide galvanic isolation between battery bank and grid.
- **State-of-charge management**: Never exceed 95 % SOC (overcharge risk) or drop below 10 % SOC (deep-discharge damage); balance cells within ±2 % SOC.
- **Fault coordination**: Protection must discriminate between internal module faults (isolate module) and external grid faults (ride-through or trip at PCC).
- **Cybersecurity**: SCADA communication must use authenticated, encrypted protocols (TLS 1.3, DNP3-SA); deny all non-essential ports.
- **Redundancy**: N+1 cooling pumps; dual-redundant BMS communication buses; backup power for control electronics.
