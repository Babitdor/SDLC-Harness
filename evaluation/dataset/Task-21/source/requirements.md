# Requirements Specification — Powertrain Assembly Cell

Document: SPEC-ROB-021
Revision: B
Status: Issued for concept design
Scope: An automated robotic cell assembling automotive powertrain sub-assemblies:
six-axis robots for handling, fastening and alignment, a vision inspection station,
a conveyor feed, tool changers, a cell controller and safety-rated area
protection. Target rate 60 assemblies per hour.

---

## 1. Functional Requirements

**REQ-001 — Cell coordination**
The cell controller shall coordinate robot motion, conveyor feed and tool changes
according to the assembly sequence.
*Verification:* Demonstration — full assembly sequence.

**REQ-002 — Part handling**
Each robot shall pick parts from the conveyor and place them in the assembly fixture.
*Verification:* Test — 500 consecutive pick-and-place cycles.

**REQ-003 — Fastening**
Each fastening robot shall drive threaded fasteners to the programmed torque and
angle.
*Verification:* Test — torque/angle traces against the joint specification.

**REQ-004 — Vision inspection**
The vision system shall check each assembly for part presence and alignment before
release.
*Verification:* Test — seeded defects (missing and misaligned parts).

**REQ-005 — Reject routing**
The cell controller shall route assemblies that fail inspection to a rework station.
*Verification:* Test — seeded defect runs.

**REQ-006 — Area protection**
The safety laser scanner shall stop all robot motion and conveyor feed when a person
enters the operating envelope.
*Verification:* Test — intrusion with the ISO 13855 test piece.

**REQ-007 — Restart**
The cell shall resume production only after the safety zone is clear and an operator
confirms restart outside the envelope.
*Verification:* Test — restart attempts with and without confirmation.

**REQ-008 — Tool changing**
The tool changer shall exchange end-effectors within the programmed cycle time.
*Verification:* Test — tool change timing over 100 cycles.

**REQ-009 — Traceability log**
The cell shall log every assembly result, robot fault and safety event.
*Verification:* Inspection — log after a production shift.

**REQ-010 — MES reporting**
The cell controller shall report production status and faults to the plant MES.
*Verification:* Test — MES interface message check.

---

## 2. Non-Functional Requirements

**REQ-NF-001 — Production rate**
The cell shall sustain at least 60 assemblies per hour over an 8-hour shift.
*Verification:* Test — full-shift production run.

**REQ-NF-002 — False rejects**
The vision inspection shall falsely reject fewer than 0.1 % of good assemblies.
*Verification:* Test — 1,000 known-good assemblies.

**REQ-NF-003 — Safety response**
The safety system shall stop motion within 100 ms of a zone intrusion being detected.
*Verification:* Test — stop-time measurement per ISO 13855.

**REQ-NF-004 — OEE**
The cell shall achieve an overall equipment effectiveness of at least 85 %.
*Verification:* Analysis — OEE over the first month of production.

**REQ-NF-005 — Repeatability**
Robot pose repeatability shall be within ±0.1 mm.
*Verification:* Test — ISO 9283 repeatability procedure.

---

## 3. Top-Level Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Cell footprint | ≤ 8 m × 6 m | — |
| C2 | Robot payload including end-effector | ≤ 20 kg | REQ-002 |
| C3 | Safety-rated stop distance from maximum speed | ≤ 500 mm | REQ-006 |

Further constraints are in the constraints register (CON-ROB-021).

---

## 4. Open Points

- Whether an operator loads parts inside the cell during operation, which would
  bring collaborative requirements of ISO 10218-2:2025 into scope, is not decided.
- The rework station's location relative to the cell is not fixed.
