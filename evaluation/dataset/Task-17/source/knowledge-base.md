# Knowledge Base — Medical Infusion Pump

## Applicable Standards

| Standard | Title | Relevance |
|---|---|---|
| IEC 62304 | Medical Device Software — Software Life Cycle Processes | Class C (highest criticality); requires documented software development plan, hazard-driven design, unit/integration/system testing, and post-market surveillance |
| IEC 60601-1 | Medical Electrical Equipment — General Requirements for Basic Safety and Essential Performance | Mandatory for all mains-powered medical devices; covers leakage current, dielectric strength, risk management process, and essential performance |
| IEC 60601-2-24 | Particular Requirements for Infusion Pumps and Controllers | Infusion-pump-specific: accuracy, occlusion alarm thresholds, air-in-line detection, anti-free-flow protection, and EMC immunity |
| IEC 60601-1-8 | Medical Electrical Equipment — Alarm Systems | Alarm priorities, auditory and visual signals, escalation |
| ISO 14971 | Medical Devices — Application of Risk Management | Mandatory risk management process: hazard identification, risk estimation, risk control verification, and residual risk acceptance |
| FDA Guidance | Infusion Pumps — Premarket Notification [510(k)] Submissions | FDA-specific: human-factors validation, cybersecurity, interoperability, and real-world performance monitoring |

## Design Rules

- **Fail-safe**: On any unrecoverable fault (CPU watchdog, sensor self-test failure, critical software exception), the pump must stop fluid flow immediately and enter a safe state. Flow may only resume after a manual power-cycle and clinician re-verification.
- **Single-fault tolerance**: No single-point hardware or software failure shall result in a hazardous situation. All safety-critical functions must have redundant sensing or diverse software implementation.
- **Alarm escalation**: If a clinician does not acknowledge an alarm within 30 seconds, the alarm must escalate (increased volume, nurse-call activation). Alarms that do not already stop delivery (for example low battery) shall not stop the infusion automatically, because interrupting some therapies is itself hazardous.
- **Anti-free-flow**: The pumping mechanism must prevent uncontrolled gravity free-flow when the pump door is opened or the tubing set is improperly loaded.
- **Cybersecurity**: Networked infusion pumps must implement device authentication, encrypted communication (TLS 1.3), and role-based access control per FDA post-market cybersecurity guidance.
- **Human factors**: All alarms must be distinguishable by type (occlusion vs. air-in-line vs. low battery). Programming workflow must require ≤3 clinician actions to start a new infusion.
