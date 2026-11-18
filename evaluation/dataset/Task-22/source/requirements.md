# Requirements Specification — Broadband LEO Communications Satellite

Document: SPEC-SAT-022
Revision: B
Status: Issued for concept design
Scope: One satellite of a broadband constellation in a 550 km sun-synchronous orbit:
multi-beam phased-array payload, onboard digital channeliser and packet switch,
intersatellite laser links, attitude control, electrical power, thermal control and
propulsion. Design life 7 years.

---

## 1. Functional Requirements

**REQ-001 — Subscriber reception**
The satellite shall receive subscriber signals through the multi-beam phased-array
antenna in the assigned frequency band.
*Verification:* Test — payload end-to-end test in the compact antenna range.

**REQ-002 — Packet routing**
The satellite shall route packets between subscriber beams and the intersatellite
laser terminals.
*Verification:* Test — traffic generator through the channeliser.

**REQ-003 — Laser links**
The satellite shall maintain laser links to the two adjacent satellites in its
orbital plane.
*Verification:* Test — terminal acquisition in the optical ground test; in-orbit
demonstration.

**REQ-004 — Antenna pointing**
The attitude control system shall point the antenna boresight within 0.1° of the
commanded ground target.
*Verification:* Analysis — pointing budget; test — star tracker and wheel
closed-loop simulation.

**REQ-005 — Sun pointing**
The attitude control system shall keep the solar arrays sun-pointed during nominal
operations.
*Verification:* Simulation — full orbit with eclipse transitions.

**REQ-006 — Power regulation**
The electrical power system shall regulate the bus from the solar arrays in sunlight
and from the batteries in eclipse, recharging them in sunlight.
*Verification:* Test — power subsystem with solar array simulator.

**REQ-007 — Collision avoidance**
The satellite shall execute a collision-avoidance manoeuvre when commanded after a
conjunction is detected on the ground.
*Verification:* Analysis — delta-v budget; test — thruster firing sequence.

**REQ-008 — Telemetry**
The satellite shall report bus voltage, temperatures and pointing error to the ground
segment.
*Verification:* Test — telemetry database check.

**REQ-009 — In-orbit updates**
The satellite shall accept software patches and configuration updates via the ground
uplink.
*Verification:* Test — patch upload and rollback.

**REQ-010 — Safe mode**
On any unrecoverable fault the satellite shall switch the payload to a safe state and
adopt a sun-pointing safe attitude.
*Verification:* Test — fault injection on the flat-sat.

---

## 2. Non-Functional Requirements

**REQ-NF-001 — Throughput**
The satellite shall provide a total throughput of at least 20 Gbps.
*Verification:* Analysis — link budget; test — channeliser capacity.

**REQ-NF-002 — Latency**
One-way latency through the satellite shall not exceed 5 ms.
*Verification:* Test — packet timing through the payload.

**REQ-NF-003 — Design life**
The satellite shall achieve a design life of at least 7 years at 550 km.
*Verification:* Analysis — reliability, radiation and propellant budgets.

**REQ-NF-004 — Eclipse operation**
The battery shall supply the full payload load through eclipses of up to 35 minutes.
*Verification:* Analysis — energy balance; test — battery cycling at 30 % DoD.

**REQ-NF-005 — Attitude knowledge**
Attitude determination shall be accurate to 0.01° (3σ) in all axes.
*Verification:* Test — star tracker characterisation.

---

## 3. Top-Level Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Wet mass | ≤ 500 kg | REQ-NF-003 |
| C2 | Orbit-average power consumption | ≤ 1.5 kW | REQ-006 |
| C3 | Stowed envelope | 1.2 × 1.2 × 1.5 m | — |

Further constraints are in the constraints register (CON-SAT-022).

---

## 4. Open Points

- The launch vehicle is not selected; C3 must be checked against its payload
  envelope.
- The subscriber frequency band is subject to ITU filing and is not yet assigned.
