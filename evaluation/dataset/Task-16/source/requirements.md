# Requirements Specification — Highway Driving Assistance System

Document: SPEC-ADAS-016
Revision: B
Status: Issued for concept design
Scope: A highway driving assistance function combining adaptive cruise control,
lane keeping, collision-avoidance braking and automated lane change, with take-over
requests and a minimal-risk manoeuvre at the boundary of its operational design
domain (ODD). The driver can override at any time.

---

## 1. Functional Requirements

**REQ-001 — Object fusion**
The system shall fuse camera, radar and lidar measurements into one object list of
surrounding vehicles and obstacles.
*Verification:* Test — recorded highway scenarios against labelled ground truth.

**REQ-002 — Lane keeping**
The system shall keep the host vehicle within its lane using the perceived lane
boundaries.
*Verification:* Test — ISO 11270 lane-keeping procedure on a test track.

**REQ-003 — Following distance**
The system shall regulate the distance to the lead vehicle to the driver-selected
time gap.
*Verification:* Test — ISO 15622 time-gap procedure.

**REQ-004 — Collision-avoidance braking**
The system shall command service braking when a forward collision is predicted.
*Verification:* Test — stationary and braking lead-vehicle targets.

**REQ-005 — Lane change**
The system shall execute a lane change only when the target lane is confirmed clear.
*Verification:* Test — target lane occupied and clear.

**REQ-006 — Driver override**
The system shall hand control to the driver when the driver brakes, steers or
accelerates beyond the override thresholds.
*Verification:* Test — each override input during active control.

**REQ-007 — Take-over request**
The system shall issue a take-over request at least 4 s before the vehicle reaches
the boundary of its ODD.
*Verification:* Test — approach to an ODD exit (end of lane markings).

**REQ-008 — Minimal-risk manoeuvre**
The system shall perform a minimal-risk manoeuvre, stopping in the current lane,
when the driver does not respond to a take-over request within 4 s.
*Verification:* Test — take-over request with no driver response.

**REQ-009 — Logging**
The system shall log every perception fault and actuation command.
*Verification:* Inspection — log after a fault-injection run.

**REQ-010 — Driver display**
The system shall display its automation state and the detected lead vehicle to the
driver.
*Verification:* Inspection — HMI in each state.

---

## 2. Non-Functional Requirements

**REQ-NF-001 — Perception rate**
The perception pipeline shall update the object list at least every 50 ms.
*Verification:* Test — timestamp analysis.

**REQ-NF-002 — End-to-end latency**
Latency from sensor capture to actuation command shall not exceed 150 ms.
*Verification:* Test — hardware-in-the-loop timing.

**REQ-NF-003 — Safety integrity**
The braking and steering command paths shall meet ISO 26262 ASIL D.
*Verification:* Analysis — safety case per ISO 26262.

**REQ-NF-004 — False warnings**
The forward-collision warning shall produce fewer than one false warning per
1,000 km.
*Verification:* Analysis — fleet test data over 500,000 km.

**REQ-NF-005 — Temperature**
The system shall remain available from −40 °C to +85 °C ambient.
*Verification:* Test — climatic chamber.

---

## 3. Top-Level Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Operating speed range | 30–130 km/h | REQ-002, REQ-003 |
| C2 | Automated deceleration in ACC and the minimal-risk manoeuvre | ≤ 0.6 g; collision-avoidance braking (REQ-004) is not limited by C2 | REQ-003, REQ-008 |
| C3 | Take-over transition time | ≤ 4 s | REQ-007, REQ-008 |

Further constraints are in the constraints register (CON-ADAS-016).

---

## 4. Open Points

- The ODD attribute thresholds (lane-marking quality, weather) are not yet
  quantified.
- Whether the lane-change function is driver-initiated or system-initiated is not
  decided.
