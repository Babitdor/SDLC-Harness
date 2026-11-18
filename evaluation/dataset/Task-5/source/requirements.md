# Requirements Specification — Hospital Patient Monitoring System

Document: SPEC-PMS-005
Revision: B
Status: Released for use case analysis
Scope: Networked bedside patient monitoring for a 32-bed general ward, with a
central nursing station, clinician alarm handling, a historical data archive and
administrative reporting.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| IEC 60601-1-8 | Medical electrical equipment — Alarm systems | Alarm priorities, signals, acknowledgement |
| IEC 80601-2-49 | Particular requirements for multifunction patient monitoring equipment | Bedside monitors |
| ISO 14971 | Medical devices — Application of risk management | Hazard analysis |
| IEC 80001-1 | Safety, effectiveness and security of health software on IT networks | Networked deployment |
| HL7 FHIR R4 | Fast Healthcare Interoperability Resources | Data exchange with the EHR |

---

## 2. Actors

| Actor | Role |
|---|---|
| Doctor | Reviews live and historical vital signs; sets patient-specific alarm limits |
| Nurse | Observes live vital signs; responds to and acknowledges alarms |
| Patient | Monitored person; source of the vital-sign signals |
| HospitalAdministration | Requests ward-level compliance and utilisation reports |

---

## 3. Functional Requirements

**REQ-001 — Continuous vital-sign monitoring**
The system shall continuously monitor heart rate, non-invasive blood pressure,
oxygen saturation (SpO₂) and body temperature for each connected patient.
*Verification:* Test — patient simulator on all four parameters.

**REQ-002 — Real-time display**
The system shall display each patient's current vital signs on the bedside
monitor and at the central nursing station with a display latency not exceeding
2 s.
*Verification:* Test — simulator step change, timed at both displays.

**REQ-003 — Configurable alarm limits**
The system shall allow a clinician to set upper and lower alarm limits for each
monitored parameter for an individual patient.
*Verification:* Demonstration — set and trigger limits for each parameter.

**REQ-004 — Historical archive**
The system shall retain each patient's vital-sign history for at least 90 days
and allow it to be searched by patient, parameter and time range.
*Verification:* Test — query retrieval after 90 days of simulated data.

**REQ-005 — Alarm acknowledgement**
The system shall allow a nurse or doctor to acknowledge an active alarm, recording
the clinician identity and acknowledgement time.
*Verification:* Test — acknowledge alarms of each priority; inspect audit record.

**REQ-006 — Report generation**
The system shall generate reports from the historical archive for a selected
patient or ward and time period.
*Verification:* Demonstration — generate a ward report for a 30-day period.

---

## 4. Non-Functional Requirements

**REQ-NF-001 — Alarm priority**
The system shall classify every alarm as high, medium or low priority and signal
each with the distinct audible and visual pattern defined in IEC 60601-1-8.
*Verification:* Inspection and test against IEC 60601-1-8.

**REQ-NF-002 — Alarm latency**
The system shall present a physiological alarm at the central station within 5 s
of the alarm condition arising.
*Verification:* Test — simulator limit violation, timed at the station.

**REQ-NF-003 — Availability**
Central station monitoring shall be available at least 99.9 % of the time.
*Verification:* Analysis — architecture redundancy and field data.

**REQ-NF-004 — Access control**
Access to patient data shall require individual clinician authentication, and
every access shall be logged.
*Verification:* Inspection — access-control configuration and audit log.

---

## 5. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Monitored beds per central station | 32 | REQ-002 |
| C2 | Display latency | ≤ 2 s | REQ-002 |
| C3 | Alarm latency to central station | ≤ 5 s | REQ-NF-002 |
| C4 | Archive retention | ≥ 90 days | REQ-004 |
| C5 | EHR interface | HL7 FHIR R4 | REQ-006 |

---

## 6. Open Points

- Whether alarm limits set by a nurse require doctor confirmation is not decided.
- The report catalogue requested by administration is not yet defined.
