# Requirements Specification — Perception Sensor Fusion Subsystem

Document: SPEC-ADS-FUS-004
Revision: B
Status: Released for interface design
Scope: Perception chain of an SAE Level 4 automated driving system — LiDAR,
camera and radar sensors, the fusion computer, the trajectory planner and the
vehicle actuation interface. Excludes the actuators themselves.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| ISO 23150 | Data communication between sensors and data fusion unit for automated driving functions — Logical interface | Sensor-to-fusion data contracts |
| ISO 26262 | Road vehicles — Functional safety | Safety integrity of the chain |
| ISO 21448 | Road vehicles — Safety of the intended functionality (SOTIF) | Performance limitations, weather |
| SAE J3016 | Taxonomy of driving automation levels | Automation level |
| ISO 11898-1 | CAN data link layer (incl. CAN FD) | Actuation interface |

---

## 2. Functional Requirements

**REQ-001 — LiDAR detection**
The LiDAR shall detect objects over a 360° horizontal field of view to a range of
150 m at a scan rate of 10 Hz.
*Verification:* Test — range and coverage test against calibrated targets.

**REQ-002 — Camera imaging**
The camera shall capture images at 1920 × 1080 resolution and 60 frames per
second for object classification and lane detection.
*Verification:* Inspection — sensor configuration; test of frame timing.

**REQ-003 — Radar detection**
The radar shall detect objects to a range of 250 m in the 76–81 GHz band and
report radial velocity and azimuth for each detection.
*Verification:* Test — corner-reflector targets at 50 m increments to 250 m.

**REQ-004 — Sensor fusion**
The fusion processor shall combine LiDAR point clouds, camera images and radar
detections into a single fused object list.
*Verification:* Test — replay of a recorded multi-sensor scenario.

**REQ-005 — Fusion latency**
The fusion processor shall publish the fused object list within 50 ms of the
latest contributing sensor frame.
*Verification:* Test — timestamp analysis over 10,000 cycles.

**REQ-006 — Trajectory generation**
The path planner shall generate a collision-free trajectory from the fused object
list, comprising waypoints, a velocity profile and an estimated duration.
*Verification:* Simulation — scenario catalogue with static and moving obstacles.

**REQ-007 — Actuation command rate**
The vehicle controller interface shall transmit trajectory commands over CAN FD
at a rate of at least 100 Hz.
*Verification:* Test — bus trace measurement.

**REQ-008 — End-to-end latency**
The subsystem shall produce an actuation command within 100 ms of the sensor
frame that triggered it.
*Verification:* Test — hardware-in-the-loop latency measurement.

---

## 3. Non-Functional Requirements

**REQ-NF-001 — Detection accuracy**
The subsystem shall detect at least 95 % of objects within 50 m under nominal
weather conditions.
*Verification:* Test — labelled validation dataset.

**REQ-NF-002 — Degraded weather operation**
The subsystem shall continue operating in rain, fog and low light, reporting the
reduced capability of each affected sensor to the planner.
*Verification:* Test — weather chamber and night-time track runs.

**REQ-NF-003 — Decision logging**
The subsystem shall record every fusion and planning decision with a timestamp
for post-drive analysis.
*Verification:* Inspection — log completeness over a 1 h drive.

**REQ-NF-004 — Sensor failure detection**
The subsystem shall detect degradation or failure of any single sensor within
200 ms and continue with the remaining sensors.
*Verification:* Test — sensor fault injection.

**REQ-NF-005 — Typed interfaces**
All data exchanged between components shall use explicitly defined, versioned
data types.
*Verification:* Inspection — interface control document review.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Fusion computer | NVIDIA Orin SoC, 16 GB memory | REQ-004 |
| C2 | Fusion computer power budget | ≤ 40 W | REQ-004 |
| C3 | Fusion latency | ≤ 50 ms | REQ-005 |
| C4 | End-to-end latency | ≤ 100 ms | REQ-008 |
| C5 | Actuation bus | CAN FD, ≥ 100 Hz command rate | REQ-007 |
| C6 | Safety integrity of the fusion function | ASIL B(D) decomposition | ISO 26262 |

---

## 5. Open Points

- The object-list schema is to follow ISO 23150; the exact interface version is
  not yet fixed.
- The allocation of ASIL levels between fusion and planning is not finalised.
