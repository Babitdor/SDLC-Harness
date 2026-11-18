# Requirements Specification — Residential Solar-plus-Storage Energy System

Document: SPEC-HEMS-003
Revision: A
Status: Released for architecture
Scope: Grid-tied residential photovoltaic system with DC-coupled battery storage,
home energy monitoring and cloud reporting, for a single-family home on a
240 V split-phase service.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| IEEE 1547-2018 | Interconnection of distributed energy resources with the grid | Grid support, anti-islanding |
| UL 1741 (SB) | Inverters, converters and controllers for distributed energy | Inverter certification |
| UL 9540 | Energy storage systems and equipment | Battery system safety |
| UL 1973 | Batteries for stationary applications | Battery module safety |
| IEC 61215 / IEC 61730 | PV module design qualification / safety | PV modules |
| NFPA 70 (NEC) Art. 690, 705, 706 | PV systems, interconnected sources, energy storage | Installation |
| IEEE 2030.5 | Smart energy profile application protocol | Utility communications |

---

## 2. Functional Requirements

**REQ-001 — PV generation**
The system shall generate up to 5 kW peak DC power from photovoltaic modules at
standard test conditions (1000 W/m², 25 °C).
*Verification:* Test — array I-V curve trace, corrected to STC.

**REQ-002 — PV module efficiency**
The photovoltaic modules shall have a rated conversion efficiency of at least 22 %.
*Verification:* Inspection — module datasheet and IEC 61215 certificate.

**REQ-003 — Charge regulation**
The system shall regulate PV-to-battery charging through a charge controller with
a conversion efficiency of at least 98 %.
*Verification:* Test — input/output power at 25 %, 50 % and 100 % load.

**REQ-004 — Energy storage**
The system shall store energy in a battery with a usable capacity of at least
13.5 kWh.
*Verification:* Test — full charge/discharge cycle at rated power.

**REQ-005 — Battery power**
The battery shall deliver at least 5 kW continuous discharge power.
*Verification:* Test — 1 h discharge at 5 kW.

**REQ-006 — Inversion**
The system shall convert DC power to 240 V AC through an inverter rated at 6 kW
continuous with a weighted conversion efficiency of at least 96 %.
*Verification:* Test — CEC weighted efficiency measurement.

**REQ-007 — Grid import**
The system shall import power from the utility grid when PV generation and
battery discharge together are insufficient to supply the home load.
*Verification:* Demonstration — load step with PV and battery unavailable.

**REQ-008 — Home load supply**
The system shall supply a home load demand of up to 4 kW peak.
*Verification:* Test — 4 kW resistive load step.

**REQ-009 — Anti-islanding**
The system shall cease energising the grid within 2 s of loss of utility supply.
*Verification:* Test per IEEE 1547.1 unintentional islanding procedure.

**REQ-010 — Energy metering**
The system shall measure consumption, generation and storage state at a sampling
rate of 1 Hz.
*Verification:* Test — compare against a reference meter over 24 h.

**REQ-011 — Cloud reporting**
The system shall upload metered data to a cloud dashboard at intervals not
exceeding 5 minutes.
*Verification:* Demonstration — dashboard update timing over 1 h.

**REQ-012 — Battery chemistry support**
The system shall support lithium-ion and lead-acid battery chemistries through
chemistry-specific charge profiles.
*Verification:* Inspection — charge controller configuration for each chemistry.

---

## 3. Non-Functional Requirements

**REQ-NF-001 — Round-trip efficiency**
The storage system shall achieve an AC-to-AC round-trip efficiency of at least 89 %.
*Verification:* Test — measured over a full cycle at rated power.

**REQ-NF-002 — Operating temperature**
Outdoor-mounted equipment shall operate from −20 °C to +50 °C.
*Verification:* Test — climatic chamber at both limits.

**REQ-NF-003 — Service life**
The battery shall retain at least 70 % of usable capacity after 10 years of daily
cycling.
*Verification:* Analysis — manufacturer cycle-life data.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Service voltage | 240 V split-phase, 60 Hz | REQ-006 |
| C2 | Available south-facing roof area | 30 m² | REQ-001, REQ-002 |
| C3 | Minimum PV array area at 22 % efficiency | 22.7 m² | REQ-001, REQ-002 |
| C4 | Inverter continuous rating | 6 kW | REQ-006 |
| C5 | Export limit set by the utility | 5 kW | REQ-006 |
| C6 | Anti-islanding clearing time | ≤ 2 s | REQ-009 |

---

## 5. Open Points

- Backup operation during a grid outage (whole-home or critical loads only) is
  not specified.
- Battery chemistry for the initial installation is not selected; both
  lithium-ion and lead-acid must be supported by the architecture.
