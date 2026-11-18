# Domain Knowledge Base — Automotive ADAS

## Applicable Standards

| Standard | Title | Relevance |
|---|---|---|
| ISO 26262 (2018) | Road vehicles — Functional safety | ASIL-D target for braking/steering command path; ASIL-B/C for perception and HMI |
| ISO 21448 (2022) | Safety of the intended functionality (SOTIF) | Hazard-triggering scenarios, ODD definition, unknown-unknown reduction |
| ISO 21434 (2021) | Road vehicles — Cybersecurity engineering | Threat analysis (TARA), secure OTA updates, CAN/Ethernet message authentication |
| ISO 34501–34503 (2022) | Road vehicles — Test scenarios for automated driving | Scenario taxonomy, logical/ concrete scenario representation |
| UN R157 | Uniform provisions concerning ALKS | Type-approval for automated lane-keeping systems; mandatory DDT fallback, EDR, data storage |
| ISO 15622 (2018) | Adaptive cruise control systems — Performance requirements and test procedures | ACC time gap, deceleration and target-selection behaviour |
| ISO 11270 (2014) | Lane keeping assistance systems — Performance requirements and test procedures | Lane-keeping function |
| SAE J3016 (2021) | Taxonomy and definitions for driving automation | Levels 0–5; ODD, fallback-ready user, minimal-risk condition |
| NHTSA — Automated Vehicles 4.0 | Voluntary guidance for AV safety | Safety self-assessments, 12 safety design elements |

## Design Rules

1. **Safe handover (TOR → driver):** The take-over request (TOR) must be issued at least 4 s before the ODD boundary is crossed. The transition time (TOR to driver in the loop) shall not exceed 4 s. If the driver does not respond, the system shall execute a minimal-risk manoeuvre (MRM) — decelerate at ≤ 0.6 g and come to a stop in the current lane.

2. **ODD boundaries:** The system must continuously monitor all ODD attributes (speed, road type, weather, lane-marking quality, map availability). Degradation of any attribute below the minimum threshold triggers a TOR. The ODD shall be formally documented as a set of measurable parameters with min/max ranges.

3. **Sensor redundancy:** At least two independent sensing modalities shall cover each ODD-relevant perception task (e.g., camera + radar for object detection). A single-point sensor failure shall not cause a loss of the safety-critical perception function.

4. **ASIL decomposition:** Where a safety requirement is allocated to sufficiently independent elements, ISO 26262-9 permits ASIL-D to be decomposed as D(D) + QM(D), C(D) + A(D) or B(D) + B(D).

5. **Fault-tolerant time interval (FTTI):** The system shall detect any single-point fault and initiate a safe state within the FTTI (≤ 200 ms for braking path, ≤ 500 ms for steering path).

6. **Cybersecurity by design:** All external communication (V2X, OTA, telemetry) shall be authenticated and encrypted. A TARA shall be performed at each architecture iteration.

7. **Human-machine interface (HMI) transparency:** The system shall continuously display its automation state (engaged / disengaged / fault / TOR) and the detected lead vehicle. The driver must never be uncertain about who is driving.
