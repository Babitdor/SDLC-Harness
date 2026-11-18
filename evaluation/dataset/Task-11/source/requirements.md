# Requirements Specification — Industrial Pick-and-Place Robot Cell

Document: SPEC-ROB-011
Revision: C
Status: Released for functional allocation
Scope: A six-axis articulated arm with a two-finger gripper, a fixed vision
system and a motion controller, performing pick-and-place of parts up to 5 kg
within a guarded cell. Excludes the cell guarding and upstream conveyors.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| ISO 10218-1 | Robotics — Safety requirements — Industrial robots | Robot safety functions |
| ISO 10218-2 | Robotics — Safety requirements — Robot applications and cells | Cell integration |
| ISO 9283 | Manipulating industrial robots — Performance criteria and test methods | Accuracy and repeatability tests |
| IEC 61800-5-2 | Adjustable speed drives — Functional safety | Safe torque off |
| IEC 61158 (Type 12) | Industrial communication networks — EtherCAT | Controller-to-drive bus |

---

## 2. Functional Requirements

**REQ-001 — Object detection**
The vision system shall detect and locate objects within the workspace.
*Verification:* Test — detection of 20 reference parts at random poses.

**REQ-002 — Trajectory calculation**
The motion controller shall calculate a collision-free joint trajectory from the
current pose to the object and from the object to the target location.
*Verification:* Simulation — cell model with fixtures as obstacles.

**REQ-003 — Gripping**
The end effector shall grip an object with a force of at least 80 N.
*Verification:* Test — force gauge between the fingers.

**REQ-004 — Positioning**
The arm shall move the tool centre point to a commanded pose with a pose accuracy
of ±1.0 mm.
*Verification:* Test — ISO 9283 pose accuracy procedure.

**REQ-005 — Placement**
The system shall place each object at its designated target location and confirm
placement.
*Verification:* Demonstration — 100 consecutive placements.

**REQ-006 — Cycle rate**
The system shall complete at least 10 pick-and-place cycles per minute.
*Verification:* Test — timed 10-minute production run.

---

## 3. Performance Requirements

**REQ-NF-001 — Payload**
The arm shall handle a payload of 5 kg at full reach.
*Verification:* Test — rated payload at maximum horizontal extension.

**REQ-NF-002 — Repeatability**
The arm shall achieve a pose repeatability of ±0.5 mm.
*Verification:* Test — ISO 9283 pose repeatability procedure.

**REQ-NF-003 — Detection latency**
The vision system shall report a detected object's position within 200 ms of the
object entering the field of view.
*Verification:* Test — timestamped detections on a moving conveyor.

**REQ-NF-004 — Control rate**
The motion controller shall update joint setpoints at a rate of at least 1 kHz.
*Verification:* Inspection — EtherCAT cycle configuration; test — bus trace.

**REQ-NF-005 — Maximum grip force**
The end effector shall limit grip force to 100 N.
*Verification:* Test — force gauge at full command.

---

## 4. Interface Requirements

**REQ-007 — Vision to controller**
The vision system shall provide each detected object's position (x, y, z) and
classification to the motion controller.
*Verification:* Test — interface message inspection.

**REQ-008 — Controller to drives**
The motion controller shall send joint setpoints to each joint drive over
EtherCAT.
*Verification:* Test — bus trace.

**REQ-009 — Grip feedback**
The end effector shall report measured grip force to the motion controller.
*Verification:* Test — commanded versus reported force.

**REQ-010 — Safe torque off**
Every joint drive shall provide a safe-torque-off function triggered by the cell
safety controller.
*Verification:* Test — STO activation per IEC 61800-5-2.

---

## 5. Component Data

| Component | Quantity | Key data |
|---|---|---|
| Base | 1 | Mass 50 kg, cast iron |
| ArmSegment | 3 | Length 0.5 m, mass 4 kg including its distal joint drive, aluminium |
| JointMotor | 6 | Servo motor 3.75 N·m at 3000 rpm with 100 : 1 harmonic reduction (80 % efficiency); rated output 300 N·m at 30 rpm |
| EndEffector | 1 | Two-finger gripper, 80–100 N grip force, 0–100 mm opening, mass 1.5 kg |
| Camera | 1 | 1920 × 1080 px, 60 fps |
| ProcessingUnit | 1 | Quad-core ARM, 4 GB memory |
| MotionController | 1 | 1 kHz control rate, EtherCAT master |

---

## 6. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Reach radius | ≤ 1.5 m | REQ-NF-001 |
| C2 | Operating temperature | 0–50 °C | — |
| C3 | Workspace illumination | 300–500 lux | REQ-001 |
| C4 | Segment length | ≤ 0.5 m | C1 |
| C5 | Base mass | ≥ 50 kg | REQ-NF-001 |
| C6 | Static shoulder torque at full reach with payload | ≤ 70 % of rated joint torque | REQ-NF-001 |

### Load check for C6

With the arm horizontal at full reach, the static shoulder torque is the sum of
the segment weights at their centres (0.25, 0.75 and 1.25 m), the 5 kg payload at
1.5 m and the 1.5 kg gripper at 1.5 m: 88.3 + 73.6 + 22.1 = 183.9 N·m, which is 61 %
of the 300 N·m rating and satisfies C6 with margin for dynamic loads.

---

## 7. Traceability Map

| Requirement | Function | Component |
|---|---|---|
| REQ-001 | DetectObject | VisionSystem (Camera, ProcessingUnit) |
| REQ-002 | CalculateTrajectory | MotionController |
| REQ-003 | GripObject | RoboticArm.EndEffector |
| REQ-004 | MoveToPosition | RoboticArm (JointMotor, ArmSegment), MotionController |
| REQ-005 | PickAndPlace | RobotSystem |
| REQ-006 | PickAndPlace | RobotSystem |
| REQ-NF-003 | DetectObject | VisionSystem |
| REQ-NF-004 | MoveToPosition | MotionController |
| REQ-NF-005 | GripObject | RoboticArm.EndEffector |

---

## 8. Open Points

- Collaborative operation without guarding (ISO 10218-2:2025, which absorbed
  ISO/TS 15066) is out of scope for this revision; the cell is fully guarded.
