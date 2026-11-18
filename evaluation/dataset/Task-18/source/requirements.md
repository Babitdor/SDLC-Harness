# Requirements Specification — Substation Battery Energy Storage System

Document: SPEC-BESS-018
Revision: B
Status: Issued for concept design
Scope: A 1 MW / 2 MWh lithium iron phosphate (LFP) battery energy storage system at
a distribution substation, providing energy shifting and frequency regulation under
utility SCADA dispatch. Covers the battery, BMS, power conversion, protection,
thermal management and grid interface.

---

## 1. Functional Requirements

**REQ-001 — Charging**
The system shall charge the battery from the grid when the dispatch signal commands
energy absorption.
*Verification:* Test — dispatch step to −1 MW.

**REQ-002 — Discharging**
The system shall discharge the battery to the grid when the dispatch signal commands
energy injection.
*Verification:* Test — dispatch step to +1 MW.

**REQ-003 — Frequency regulation**
The system shall modulate real-power output in response to measured grid frequency.
*Verification:* Test — injected frequency deviation on the controller.

**REQ-004 — Module monitoring**
The BMS shall monitor the voltage, current and temperature of every battery module.
*Verification:* Inspection — BMS channel list; test — sensor fault injection.

**REQ-005 — Module isolation**
The system shall isolate any battery module that exceeds its safe operating limits.
*Verification:* Test — simulated module over-temperature.

**REQ-006 — Over-current trip**
The protection system shall open the main contactor on over-current.
*Verification:* Test — secondary injection of fault current.

**REQ-007 — Over-temperature trip**
The protection system shall open the main contactor on over-temperature.
*Verification:* Test — simulated rack over-temperature.

**REQ-008 — SCADA reporting**
The system shall report state of charge, power output and fault status to the
utility SCADA system.
*Verification:* Test — point-to-point SCADA check.

**REQ-009 — Dispatch acceptance**
The system shall accept power set-points from the utility SCADA system.
*Verification:* Test — set-point sequence from SCADA.

**REQ-010 — Event recording**
The system shall record every protection trip and module isolation event.
*Verification:* Inspection — event log after tests REQ-005 to REQ-007.

---

## 2. Non-Functional Requirements

**REQ-NF-001 — Usable energy**
The system shall provide at least 2 MWh of usable energy within the SOC window.
*Verification:* Test — full discharge at 1 MW from 95 % to 10 % SOC.

**REQ-NF-002 — Continuous power**
The system shall sustain 1 MW continuous output at the point of common coupling.
*Verification:* Test — 2 h discharge at 1 MW.

**REQ-NF-003 — Frequency response time**
The frequency-regulation response shall reach the commanded set-point within 500 ms.
*Verification:* Test — step response measurement.

**REQ-NF-004 — Round-trip efficiency**
AC-to-AC round-trip efficiency, including auxiliaries, shall be at least 85 %.
*Verification:* Test — full cycle energy metering.

**REQ-NF-005 — Fault clearing**
The protection system shall clear an over-current fault within 100 ms.
*Verification:* Test — relay and breaker timing.

---

## 3. Top-Level Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Battery module operating temperature | 15–35 °C | REQ-004, REQ-007 |
| C2 | Per-module state of charge | 10–95 % | REQ-NF-001 |
| C3 | Voltage at the point of connection | ±5 % of nominal | REQ-003 |

Further constraints are in the constraints register (CON-BESS-018).

---

## 4. Open Points

- The UL 9540A test data for the selected modules, which sets the NFPA 855
  separation distances, is not yet available.
- The frequency-regulation droop characteristic is not specified by the utility.
