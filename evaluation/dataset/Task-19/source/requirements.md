# Requirements Specification — Metro CBTC Signalling System

Document: SPEC-CBTC-019
Revision: B
Status: Issued for concept design
Scope: Communications-based train control for a 25 km double-track metro line with
20 stations: onboard automatic train protection (ATP), zone controllers issuing
movement authorities, interlocking, train detection, door supervision and the
radio network between train and wayside.

---

## 1. Functional Requirements

**REQ-001 — Position reporting**
Each train shall report its position, speed and direction to the zone controller at
least once per second.
*Verification:* Test — radio trace during a line run.

**REQ-002 — Movement authority**
The zone controller shall compute a movement authority for each train from track
occupancy and switch positions.
*Verification:* Test — simulated occupancy scenarios on the zone controller.

**REQ-003 — Authority transmission**
The zone controller shall transmit each movement authority to its train over the
radio link.
*Verification:* Test — radio trace.

**REQ-004 — Authority enforcement**
The onboard ATP shall apply the service brake when the train approaches the limit of
its movement authority.
*Verification:* Test — approach to authority limit at line speed.

**REQ-005 — Emergency brake intervention**
The onboard ATP shall apply the emergency brake if the train would otherwise exceed
its movement authority or a speed limit.
*Verification:* Test — overspeed and overrun attempts.

**REQ-006 — Train detection**
The system shall detect track occupancy with axle counters and report it to the
zone controller.
*Verification:* Test — axle counter section occupation and clearance.

**REQ-007 — Switch locking**
The interlocking shall prevent a switch from moving while its track section is
occupied.
*Verification:* Test — switch command with section occupied.

**REQ-008 — Door supervision**
The system shall prevent train departure while any train or platform door is open.
*Verification:* Test — traction request with one door open.

**REQ-009 — Event logging**
The system shall log every movement authority, brake command and occupancy change.
*Verification:* Inspection — log after a test run.

**REQ-010 — Degraded mode**
The system shall support line-of-sight operation at restricted speed when CBTC is
unavailable.
*Verification:* Demonstration — radio failure on a section.

---

## 2. Non-Functional Requirements

**REQ-NF-001 — Authority latency**
Latency from a train's position report to receipt of its movement authority shall
not exceed 2 s.
*Verification:* Test — timestamp analysis over 10,000 cycles.

**REQ-NF-002 — Safety integrity**
The ATP and interlocking functions shall achieve SIL 4 per EN 50129.
*Verification:* Analysis — safety case with independent assessment.

**REQ-NF-003 — Radio reliability**
The radio link shall achieve a connection success rate of at least 99.99 %.
*Verification:* Test — link statistics over a 30-day trial.

**REQ-NF-004 — Line capacity**
The system shall support at least 30 trains operating simultaneously.
*Verification:* Test — full-line simulation.

**REQ-NF-005 — Availability**
The system shall be available for at least 99.9 % of scheduled revenue service.
*Verification:* Analysis — RAMS model and 6-month demonstration.

---

## 3. Top-Level Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Minimum headway | 90 s | REQ-002 |
| C2 | Emergency braking distance from 80 km/h | ≤ 300 m, including on the 4 % down-gradient | REQ-005 |
| C3 | Radio handover time | ≤ 100 ms | REQ-003 |

Further constraints, including the braking-rate check behind C2, are in the
constraints register (CON-CBTC-019).

---

## 4. Open Points

- The rolling stock supplier has not yet confirmed a guaranteed emergency brake rate
  of 1.4 m/s² (C21); without it C2 cannot be met on the steepest gradient.
- Whether the line has platform screen doors throughout is not decided.
