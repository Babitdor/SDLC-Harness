Hi — I need you to build a use case diagram for a hospital patient monitoring system. The requirements are attached in source/requirements.md.

**Actors:** Doctor, Nurse, Patient, HospitalAdministration.
**Use cases:** Monitor Patient Vitals, Display Real-Time Data, Set Alert Thresholds, Access Historical Data, Acknowledge Alerts, Generate Reports.

**Relationships:**
- *Include* — Display Real-Time Data includes Monitor Patient Vitals (live display depends on continuous data acquisition). Acknowledge Alerts includes Display Real-Time Data (clinicians need vitals context when acknowledging).
- *Extend* — Generate Reports extends Access Historical Data (reporting is an optional extension of data retrieval). Set Alert Thresholds extends Display Real-Time Data (threshold adjustment is an optional extension of the live view).
- *Satisfy* — Each use case shall satisfy the relevant requirement(s) via satisfy relationships.

**SysML v2 pattern to follow:**
- Use `part def` for actor types (Doctor, Nurse, Patient, HospitalAdministration) — actors are modeled as parts with the actor stereotype, following the Sensmetry / OMG SysML v2 reference pattern.
- Use `part def` for the system subject (PatientMonitoringSystem).
- Use `use case def` with explicit `subject` and actor parameters (e.g., `subject : PatientMonitoringSystem; actor doctor : Doctor;`).
- Use `requirement def` for the traced requirements (REQ-001–REQ-006), so that every use case satisfies at least one requirement.
- Use `include`, `extend`, and `satisfy` relationships at the package level.

Please produce a proper SysML v2 use case diagram file named `hospital-uc.sysml`.
