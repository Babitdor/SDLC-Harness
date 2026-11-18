# Domain Knowledge Base — Naval Standards & Design Rules

## Applicable Standards

| Standard | Title | Scope |
|---|---|---|
| MIL-STD-461 | Requirements for the Control of Electromagnetic Interference | EMC/EMI for all below-deck and topside equipment; CE101–CE106, RE101–RE103 limits |
| MIL-STD-810 | Environmental Engineering Considerations and Laboratory Tests | Temperature, humidity, vibration, shock, salt fog, immersion, and fungus resistance |
| IEEE 45 | Recommended Practice for Electrical Installations on Shipboard | Cable sizing, switchboard design, generator protection, grounding, and load shedding |
| MIL-STD-1399 | Interface Standard for Shipboard Systems | Electrical power quality (voltage, frequency, harmonics), propulsion shaft interface |
| MIL-STD-1472 | Human Engineering | Console layout, display brightness, alarm prioritisation, reach envelopes |
| ABS Naval Vessel Rules | American Bureau of Shipping — Naval Vessel Rules | Classification, structural fire protection, damage stability, machinery surveys |
| MIL-DTL-901E | Shock tests, high-impact, shipboard machinery, equipment and systems | Shock qualification of mission-essential equipment |
| STANAG 1008 | Characteristics of Shipboard Electrical Power Systems | Power quality, transient limits, harmonic distortion for NATO vessels |

## Design Rules

- **Survivability (RULE-SURV-001)**: No single-point failure shall result in loss of more than 50 % of propulsion power or total loss of ship service electrical power.
- **Redundancy (RULE-RED-001)**: All mission-essential machinery shall have N+1 redundancy; standby auxiliary machinery (pumps, fans) shall auto-start within 10 seconds of primary failure. Generator start times are set separately (C1).
- **Separation (RULE-SEP-001)**: Redundant machinery and cabling runs shall be physically separated by at least one watertight compartment or fire zone.
- **Shock (RULE-SHOCK-001)**: All mission-essential equipment shall be shock-qualified per MIL-DTL-901E (Grade A, lightweight or heavyweight).
- **EMC (RULE-EMC-001)**: Sensitive control circuits shall be physically and electrically isolated from power cables; shielded twisted-pair or fibre-optic cabling required for data buses.
- **Zonal Electrical (RULE-ZONE-001)**: The electrical plant shall be divided into at least three damage-control zones, each with independent generation or stored-energy backup.
- **Human Factors (RULE-HF-001)**: The ECR console shall present no more than 3 alarm priorities; critical alarms must be acknowledged within 5 seconds.
