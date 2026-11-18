# Requirements Specification — Advanced Emergency Braking System (AEBS)

Document: SPEC-AEB-013
Revision: B
Status: Released for verification planning
Scope: Forward-collision AEBS for an M1 passenger car: obstacle detection by radar
and camera fusion, collision warning, and automatic emergency braking. Covers
the requirements under verification and the reference test scenario.

---

## 1. Applicable Regulations and Standards

| Reference | Title | Applies to |
|---|---|---|
| UN Regulation No. 152 | Advanced Emergency Braking System for M1 and N1 vehicles | Warning timing, braking demand, speed range |
| Euro NCAP AEB Car-to-Car Test Protocol | Assessment protocol for AEB | Test scenario definition |
| ISO 22839 | Forward vehicle collision mitigation systems | Performance requirements and test procedures |
| ISO 26262 | Road vehicles — Functional safety | Safety integrity of the braking function |

Regulatory context from UN R152: the system shall be active at least between 10
and 60 km/h; the collision warning shall be given at the latest 0.8 s before the
start of emergency braking; the emergency braking demand shall be at least 5 m/s².

---

## 2. Requirements Under Verification

**REQ-001 — Braking actuation latency**
The AEB system shall initiate emergency braking within 500 ms of its decision that
a collision is imminent.
- Subject: AEBSystem
- Constraint: brakingActuationTime ≤ 500 ms
- Rationale: Product requirement bounding actuator latency. It is measured from the
  collision-imminent decision, not from first detection, so that it is compatible
  with the R152 warning interval in REQ-004.

**REQ-002 — Detection range**
The AEB system shall detect a stationary vehicle-sized obstacle at a range of at
least 50 m.
- Subject: AEBSystem
- Constraint: detectionRange ≥ 50 m
- Rationale: At 60 km/h (16.67 m/s), 50 m gives a time-to-collision of 3.0 s, enough
  for a compliant warning followed by emergency braking.

**REQ-003 — Collision avoidance**
The AEB system shall bring the vehicle to a stop before contact with the detected
obstacle, with at least 1 m clearance.
- Subject: AEBSystem
- Constraint: finalRelativeVelocity = 0 m/s and clearanceDistance ≥ 1 m

---

## 3. Supporting Requirements

**REQ-004 — Collision warning**
The AEB system shall issue an acoustic and optical collision warning at least 0.8 s
before the start of emergency braking.
*Verification:* Test — timestamp of warning versus braking onset.

**REQ-005 — Braking demand**
During emergency braking the AEB system shall demand a deceleration of at least
5 m/s² and shall achieve at least 8 m/s² on a dry surface.
*Verification:* Test — longitudinal acceleration trace.

**REQ-NF-001 — False activation**
The AEB system shall produce fewer than one false emergency-braking activation per
10,000 km driven.
*Verification:* Analysis — field operational test data.

**REQ-NF-002 — Environmental operation**
The AEB system shall meet REQ-002 in rain and at night, reporting reduced
capability to the driver when a sensor is degraded.
*Verification:* Test — wet-track and night-time runs.

**REQ-NF-003 — Driver override**
The AEB system shall not reduce the braking the driver commands.
*Verification:* Test — driver full braking during an AEB event.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Regulatory basis | UN R152 | REQ-004, REQ-005 |
| C2 | Operating speed range | 10–80 km/h (exceeds the R152 minimum of 10–60 km/h) | REQ-002 |
| C3 | Sensor set | Radar and camera fusion | REQ-002 |
| C4 | Warning-to-braking interval | ≥ 0.8 s | REQ-004 |
| C5 | Emergency braking demand | ≥ 5 m/s² | REQ-005 |

---

## 5. Reference Verification Scenario — AEB_Verification_001

Vehicle travelling at 60 km/h towards a stationary vehicle target placed 50 m ahead
on a dry, straight, level track. Verifies REQ-001, REQ-002 and REQ-003.

| Requirement | Method | Pass criterion |
|---|---|---|
| REQ-001 | Test — instrumented vehicle | Braking onset ≤ 500 ms after the collision-imminent flag |
| REQ-002 | Test — detection log | Target detected at ≥ 50 m |
| REQ-003 | Test — instrumented vehicle | Stop with clearance ≥ 1 m |

Feasibility at 60 km/h: the braking distance at 5 m/s² is 27.8 m, so braking must be
active 1.33 s after detection at the latest; a warning by 0.53 s satisfies the
0.8 s interval. At the 8 m/s² achieved deceleration the braking distance is 17.4 m.

---

## 6. Open Points

- The collision-imminent decision threshold (time-to-collision) is not specified;
  it determines when within the feasible window warning and braking occur.
