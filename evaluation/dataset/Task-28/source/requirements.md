# Requirements Specification — Autonomous Mobile Robot (AMR)

Document: SPEC-AMR-028
Revision: B
Status: Released for architecture
Scope: A driverless mobile robot transporting loads of up to 200 kg between racks,
workstations and docks in a warehouse shared with people. Covers the vehicle,
its safety system, navigation, load handling, energy and WMS interface.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| ISO 3691-4 | Industrial trucks — Safety — Driverless industrial trucks and their systems | Safety functions, protective fields, zones |
| ANSI/A3 R15.08-1 | Industrial mobile robots — Safety requirements | North American equivalent |
| IEC 61496-3 | Safety of machinery — Electro-sensitive protective equipment — AOPDDR | Safety laser scanners |
| ISO 13849-1 | Safety of machinery — Safety-related parts of control systems | Performance level of safety functions |
| ISO 13850 | Safety of machinery — Emergency stop function | Emergency stop |
| IEC 62619 | Secondary lithium cells and batteries for industrial applications | Traction battery |

---

## 2. Functional Requirements

**REQ-001 — Payload transport**
The AMR shall transport payloads of up to 200 kg between warehouse zones.
*Verification:* Test — rated load over the reference route.

**REQ-002 — Obstacle handling**
The AMR shall navigate autonomously and re-plan around static and moving
obstacles on its route.
*Verification:* Test — blocked-route scenario with a pedestrian dummy.

**REQ-003 — Route following**
The AMR shall follow defined routes between pickup, storage and drop-off points.
*Verification:* Test — mission sequence over all route segments.

**REQ-004 — Autonomous charging**
The AMR shall dock at a charging station when its state of charge falls below 20 %.
*Verification:* Test — discharge to threshold.

**REQ-005 — WMS communication**
The AMR shall receive transport missions from the WMS and report their completion.
*Verification:* Test — mission lifecycle over the interface.

**REQ-006 — Load handling**
The AMR shall lift and lower its fork to engage loads at rack and workstation
heights from 0.1 m to 0.8 m.
*Verification:* Test — engagement at both limits.

**REQ-007 — Emergency stop**
The AMR shall provide emergency stop buttons on each side that stop all motion.
*Verification:* Test — each button, per ISO 13850.

**REQ-008 — Status reporting**
The AMR shall report location, state of charge, load state and faults to the WMS at
least once per second.
*Verification:* Test — message rate over 1 h.

---

## 3. Non-Functional Requirements

**REQ-NF-001 — Endurance**
The AMR shall operate for at least 8 hours on one full charge under the nominal
duty cycle.
*Verification:* Test — full shift on the reference duty cycle.

**REQ-NF-002 — Speed**
The AMR shall not exceed 1.5 m/s, and 0.3 m/s in zones shared with pedestrians.
*Verification:* Test — speed logging per zone.

**REQ-NF-003 — Positioning accuracy**
The AMR shall stop within ±5 cm of a target location.
*Verification:* Test — 50 approaches to a surveyed point.

**REQ-NF-004 — Safety reaction**
The safety system shall begin braking within 200 ms of a person or obstacle
entering the protective field.
*Verification:* Test — test body per ISO 3691-4.

**REQ-NF-005 — Braking with load**
With rated load, braking shall not exceed 1.0 m/s² so that the load does not shift.
*Verification:* Test — accelerometer on the fork with 200 kg load.

**REQ-NF-006 — Safety integrity**
Personnel detection and emergency stop shall meet performance level PL d.
*Verification:* Analysis — ISO 13849-1 calculation.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Footprint | ≤ 1.2 m × 0.8 m | — |
| C2 | Floor load, fully loaded | ≤ 500 kg/m² | REQ-001 |
| C3 | Operating temperature | 0–40 °C | — |
| C4 | Robot mass (unladen) | ≤ 250 kg | C2 |
| C5 | Minimum protective field length at 1.5 m/s | 1.43 m | REQ-NF-004, REQ-NF-005 |

### Derivation of C2 and C5

Loaded mass 250 + 200 = 450 kg over 0.96 m² gives 469 kg/m², within C2.
Stopping distance at 1.5 m/s: reaction 1.5 × 0.2 = 0.30 m, plus braking
1.5² / (2 × 1.0) = 1.13 m, gives 1.43 m, the minimum protective field before any
scanner tolerance is added.

---

## 5. Open Points

- Wheel point loads, as opposed to average floor load, are not yet checked against
  the slab specification.
- The pedestrian zones on the site plan are not yet defined.
