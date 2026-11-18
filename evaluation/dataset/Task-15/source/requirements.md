# Requirements Specification — Autonomous UAV Delivery System

Document: SPEC-UDS-015
Revision: B
Status: Issued for concept design
Scope: A fleet of multirotor delivery drones and the ground control station that
plans missions, supervises the fleet and commands emergency landings, for urban
last-mile parcel delivery flown beyond visual line of sight in the EASA specific
category.

---

## 1. Functional Requirements

**REQ-001 — Mission acceptance**
The UAV shall accept a delivery mission of pickup and drop-off waypoints from the
ground control station.
*Verification:* Test — mission upload and acknowledgement.

**REQ-002 — GNSS navigation**
The UAV shall navigate to each waypoint using multi-constellation GNSS.
*Verification:* Test — waypoint course against surveyed points.

**REQ-003 — Visual fallback**
The UAV shall switch to visual-inertial navigation when GNSS horizontal accuracy is
worse than 2 m (95 %).
*Verification:* Test — GNSS degradation injected in flight.

**REQ-004 — Obstacle avoidance**
The UAV shall detect obstacles in its flight corridor and execute an avoidance
manoeuvre.
*Verification:* Test — static and moving obstacle course.

**REQ-005 — Payload release**
The UAV shall release the payload at the drop-off point only after confirming that
the drop zone is clear.
*Verification:* Test — drop zone occupied and clear.

**REQ-006 — Telemetry**
The UAV shall transmit position, battery state and payload status to the ground
control station once per second.
*Verification:* Inspection — telemetry log rate.

**REQ-007 — Fleet display**
The ground control station shall display the live status of every drone in the
fleet.
*Verification:* Demonstration — 50 simulated drones.

**REQ-008 — Return to home**
The UAV shall return to its home point when battery state of charge reaches the
25 % reserve threshold.
*Verification:* Test — discharge to threshold.

**REQ-009 — Commanded emergency landing**
The UAV shall perform a controlled emergency landing on command from the ground
control station.
*Verification:* Test — command during cruise.

**REQ-010 — Geofence**
The UAV shall remain within the mission geofence and initiate return to home within
1 s of a predicted breach.
*Verification:* Test — commanded waypoint beyond the boundary.

---

## 2. Non-Functional Requirements

**REQ-NF-001 — Payload**
The UAV shall carry a payload of up to 5 kg.
*Verification:* Test — full mission at 5 kg.

**REQ-NF-002 — Endurance**
The UAV shall fly for at least 30 minutes at nominal load before reaching the 25 %
reserve threshold.
*Verification:* Test — endurance flight at 5 kg payload.

**REQ-NF-003 — Link latency**
Command-and-control link latency shall not exceed 200 ms.
*Verification:* Test — round-trip timing over 1 h.

**REQ-NF-004 — Detection reliability**
Obstacle detection shall detect at least 99.99 % of objects larger than 0.3 m in the
flight corridor.
*Verification:* Analysis — simulation campaign supported by flight test.

**REQ-NF-005 — Fleet supervision**
The ground control station shall supervise at least 50 concurrent drones.
*Verification:* Test — 50-drone simulation.

---

## 3. Top-Level Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Maximum take-off mass | ≤ 25 kg | REQ-NF-001, REQ-NF-002 |
| C2 | Cruise altitude | 30–120 m above ground level | REQ-002 |
| C3 | Operating wind speed | ≤ 12 m/s | REQ-004 |

Further constraints are in the constraints register (CON-UDS-015).

---

## 4. Open Points

- Multirotor energy sizing (see the knowledge base) puts the take-off mass near
  23 kg, leaving about 2 kg of margin to C1. Any mass growth threatens either the
  payload or the endurance requirement.
- The SORA ground and air risk classes are not yet assigned.
