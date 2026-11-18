# Requirements Specification — Driving Mode Controller

Document: SPEC-DMC-007
Revision: B
Status: Released for behaviour modelling
Scope: The mode-management function of a low-speed automated shuttle operating on
a predefined route. Covers mode states, transitions and their guards. Excludes the
perception and motion-control functions that supply the guard conditions.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| ISO 22737 | Low-speed automated driving systems for predefined routes | Operational concept, minimal risk manoeuvre |
| ISO 26262 | Road vehicles — Functional safety | Emergency stop path |
| ISO 21448 | Safety of the intended functionality (SOTIF) | Obstacle-detection limitations |
| SAE J3016 | Taxonomy of driving automation levels | Automation level |

---

## 2. Functional Requirements

**REQ-001 — Idle state**
The controller shall provide an Idle state in which the vehicle is powered on,
stationary and awaiting input.
*Verification:* Test — power-on sequence.

**REQ-002 — Activation**
The controller shall transition from Idle to Active when the engine has started
and the power-on self-check has passed.
*Verification:* Test — power-on with passing and failing self-check.

**REQ-003 — Route start**
The controller shall transition from Active to Navigating when a destination is
set and the route has been validated.
*Verification:* Test — valid and invalid route submission.

**REQ-004 — Obstacle entry**
The controller shall transition from Navigating to ObstacleAvoidance when an
obstacle is detected closer than 2.0 m on the planned path.
*Verification:* Test — obstacle placed at 1.9 m and 2.1 m.

**REQ-005 — Obstacle exit**
The controller shall return from ObstacleAvoidance to Navigating when the nearest
obstacle on the planned path is at least 5.0 m away.
*Verification:* Test — obstacle withdrawn to 4.9 m and 5.1 m.

**REQ-006 — Arrival**
The controller shall transition from Navigating to Parked when the vehicle has
reached its destination.
*Verification:* Test — route completion.

**REQ-007 — Emergency stop entry**
The controller shall transition from any state to EmergencyStop when a critical
fault or collision risk is reported.
*Verification:* Test — fault injection in each state.

**REQ-008 — Emergency stop exit**
The controller shall leave EmergencyStop only for Idle, and only after a manual
reset has been performed.
*Verification:* Test — reset attempts with and without the manual reset.

**REQ-009 — Resumption from Parked**
The controller shall transition from Parked to Idle when the operator wakes the
vehicle for a new trip.
*Verification:* Test — wake command in Parked.

**REQ-010 — Transition logging**
The controller shall log every state transition with a timestamp, the source and
target states and the triggering event.
*Verification:* Inspection — log after a full scenario run.

---

## 3. Non-Functional Requirements

**REQ-NF-001 — Obstacle reporting latency**
Obstacle detections shall reach the controller within 200 ms of the sensor frame.
*Verification:* Test — timestamp analysis.

**REQ-NF-002 — Emergency stop latency**
The transition to EmergencyStop shall complete within 50 ms of fault detection.
*Verification:* Test — fault injection timing over 1,000 trials.

**REQ-NF-003 — Communication loss**
On loss of communication with any obstacle-detection sensor, the controller shall
enter EmergencyStop if moving and remain in Idle if stationary.
*Verification:* Test — sensor bus disconnection in each state.

**REQ-NF-004 — Endurance**
The controller shall process at least 10,000 consecutive state transitions without
performance degradation.
*Verification:* Test — soak test.

**REQ-NF-005 — Detection performance**
Obstacle detection shall achieve at least 99.5 % detection for objects larger than
0.1 m³ at ranges up to 50 m.
*Verification:* Test — labelled track runs.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Controller persistent memory | ≤ 50 MB | REQ-010 |
| C2 | Independent obstacle-detection modalities | ≥ 3 (LiDAR, radar, camera) | REQ-NF-005 |
| C3 | Manual reset | Physical button press; a software command alone is insufficient | REQ-008 |
| C4 | Transition log storage | Non-volatile memory | REQ-010 |
| C5 | Guard variables observable via the diagnostic interface | engineStarted, routeValidated, obstacleDistance, atDestination, emergencyTriggered, manualResetPerformed, driverWake | REQ-001–REQ-009 |
| C6 | Obstacle hysteresis | Enter < 2.0 m, exit ≥ 5.0 m | REQ-004, REQ-005 |

---

## 5. Open Points

- The minimal-risk manoeuvre performed on entry to EmergencyStop (in-lane stop or
  pull-over) is not specified.
