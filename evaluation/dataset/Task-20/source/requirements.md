# Requirements Specification — Propulsion and Machinery Control System

Document: SPEC-NAV-020
Revision: B
Status: Issued for concept design
Scope: Integrated propulsion, electrical power and machinery control for a naval
surface combatant with a combined diesel-electric and gas turbine plant:
propulsion control, generation and distribution, damage control, auxiliary systems
and centralised monitoring from the engineering control room (ECR) and the bridge.

---

## 1. Functional Requirements

**REQ-001 — Plant configuration**
The system shall manage the propulsion plant configuration, including diesel
generators, gas turbine and propulsion motors.
*Verification:* Test — each plant line-up during harbour acceptance trials.

**REQ-002 — Power distribution**
The system shall distribute electrical power from the generators to ship service
loads through automated switchboards.
*Verification:* Test — load transfer between switchboards.

**REQ-003 — Centralised control**
The system shall provide monitoring and control of all machinery from the ECR
console.
*Verification:* Demonstration — ECR operation of every controlled system.

**REQ-004 — Standby generation**
The system shall start a standby generator automatically on loss of the primary
power source.
*Verification:* Test — trip of the online generator.

**REQ-005 — Zone isolation**
The system shall isolate a damaged electrical zone and keep power to essential loads
in the remaining zones.
*Verification:* Test — simulated zone fault on the shore-based test site.

**REQ-006 — Auxiliary control**
The system shall control bilge, fire main and seawater cooling pumps according to
demand.
*Verification:* Test — demand changes for each pump system.

**REQ-007 — Machinery alarms**
The system shall monitor machinery temperature, pressure and vibration and raise
alarms on limit exceedance.
*Verification:* Test — simulated sensor limit exceedance.

**REQ-008 — Recording**
The system shall log all machinery parameters, alarms and operator actions for
post-casualty analysis.
*Verification:* Inspection — log after a trial sequence.

**REQ-009 — Bridge control**
The system shall allow propulsion control from the bridge during manoeuvring.
*Verification:* Test — control transfer ECR ↔ bridge at sea.

**REQ-010 — Emergency shutdown**
The system shall execute the pre-programmed emergency shutdown sequence on detection
of collision or fire.
*Verification:* Test — simulated fire detection in a machinery space.

---

## 2. Non-Functional Requirements

**REQ-NF-001 — Throttle response**
The propulsion control loop shall respond to a throttle command within 2 s.
*Verification:* Test — step command during sea trials.

**REQ-NF-002 — Bus voltage**
Bus voltage shall stay within ±5 % of nominal under all load conditions.
*Verification:* Test — load steps per MIL-STD-1399.

**REQ-NF-003 — Fault tolerance**
No single failure shall cause loss of essential machinery monitoring.
*Verification:* Analysis — FMECA; test — server and network fault injection.

**REQ-NF-004 — Temperature**
The system shall operate from −10 °C to +50 °C ambient.
*Verification:* Test — MIL-STD-810 temperature procedures.

**REQ-NF-005 — Data capacity**
The data bus shall carry at least 500 sensor points refreshed once per second.
*Verification:* Test — full point load on the integration rig.

---

## 3. Top-Level Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Emergency generator start | ≤ 45 s to rated speed and voltage | REQ-004 |
| C2 | Sustained speed | ≥ 28 knots in sea state 4 | REQ-001 |
| C3 | Electromagnetic compatibility | MIL-STD-461 for below-deck equipment | — |

Further constraints are in the constraints register (CON-NAV-020).

---

## 4. Open Points

- The load-shedding priority list for essential loads is not yet defined.
- Whether the ECR console software is shared with the bridge repeater or separate
  is not decided.
