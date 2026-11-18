# Requirements Specification — Large-Volume Infusion Pump

Document: SPEC-INF-017
Revision: B
Status: Issued for concept design
Scope: A single-channel large-volume infusion pump for hospital wards: the pumping
mechanism, the drug-library dose-error-reduction system (DERS), alarm handling,
therapy logging and power management. Software is developed to IEC 62304 Class C.

---

## 1. Functional Requirements

**REQ-001 — Rate delivery**
The pump shall deliver fluid at the clinician-programmed flow rate.
*Verification:* Test — gravimetric flow measurement per IEC 60601-2-24.

**REQ-002 — Dose validation**
The pump shall check every programmed dose against the active drug-library limits
before starting delivery.
*Verification:* Test — doses inside and outside library limits.

**REQ-003 — Soft limit**
The pump shall require clinician confirmation when a programmed dose exceeds a soft
limit.
*Verification:* Test — dose above the soft limit.

**REQ-004 — Hard limit**
The pump shall refuse to start delivery when a programmed dose exceeds a hard limit.
*Verification:* Test — dose above the hard limit.

**REQ-005 — Occlusion detection**
The pump shall detect a downstream occlusion and stop delivery.
*Verification:* Test — clamped line at minimum and maximum flow rate.

**REQ-006 — Air-in-line detection**
The pump shall detect accumulated air in the line above the threshold volume and
stop delivery.
*Verification:* Test — injected air at 0.08 mL and 0.12 mL.

**REQ-007 — Alarm annunciation**
The pump shall raise an audible and visual alarm for every fault condition, with a
distinct signal for each alarm type.
*Verification:* Test — each fault condition per IEC 60601-1-8.

**REQ-008 — Fail-safe state**
The pump shall stop fluid flow on any unrecoverable fault.
*Verification:* Test — watchdog and sensor self-test fault injection.

**REQ-009 — Therapy log**
The pump shall record every therapy event, alarm and setting change in a
tamper-evident log.
*Verification:* Inspection — log integrity check after edits are attempted.

**REQ-010 — Resumption**
The pump shall resume the programmed therapy after a recoverable alarm is cleared
by the clinician.
*Verification:* Test — clear an occlusion and resume.

**REQ-011 — Anti-free-flow**
The pump shall prevent gravity free-flow when the door is opened or the tubing set
is incorrectly loaded.
*Verification:* Test — door opened with a full bag above the pump.

---

## 2. Non-Functional Requirements

**REQ-NF-001 — Volume accuracy**
Delivered volume shall be within ±5 % of the programmed volume.
*Verification:* Test — IEC 60601-2-24 trumpet-curve method.

**REQ-NF-002 — Alarm latency**
The pump shall annunciate any alarm condition within 2 s of detection.
*Verification:* Test — timed fault injection.

**REQ-NF-003 — Battery operation**
The pump shall operate for at least 4 hours on battery at the nominal flow rate
after mains power is lost.
*Verification:* Test — mains removed at 125 mL/h.

**REQ-NF-004 — Software class**
The software shall be developed to IEC 62304 Class C.
*Verification:* Inspection — software development file.

**REQ-NF-005 — DERS effectiveness**
The DERS shall reject out-of-limit programming with a probability of at least 99.99 %.
*Verification:* Analysis — test campaign with statistical confidence bound.

---

## 3. Top-Level Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Programmable flow rate | 0.1–1,200 mL/h | REQ-001 |
| C2 | Occlusion alarm pressure | ≤ 15 psi | REQ-005 |
| C3 | Air-in-line threshold | ≤ 0.1 mL accumulated | REQ-006 |

Further constraints are in the constraints register (CON-INF-017).

---

## 4. Open Points

- The drug library content and its update process are not defined.
- Whether the pump integrates with the hospital EMR for auto-programming is not
  decided.
