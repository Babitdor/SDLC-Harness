# Domain Knowledge Base — Railway Signaling & CBTC

## Applicable Standards

| Standard | Title | Scope |
|---|---|---|
| **CENELEC EN 50126** | Railway Applications — RAMS Specification | Lifecycle, reliability, availability, maintainability, safety |
| **CENELEC EN 50716** | Railway Applications — Requirements for software development (2023) | Software development process from basic integrity to SIL 4; replaced EN 50128 and EN 50657 |
| **CENELEC EN 50129** | Railway Applications — Safety-Related Electronic Systems | System-level safety case, SIL allocation, hazard log |
| **IEEE 1474.1** | Standard for CBTC Performance and Functional Requirements | CBTC system functions, performance, and interface requirements |
| **IEEE 1474.2** | User Interface Requirements in CBTC Systems | MMI design for train operators and controllers |
| **IEEE 1474.3** | Recommended Practice for CBTC System Design | System architecture, redundancy, and fail-safe principles |

## Design Rules

1. **Fail-Safe Principle** — All safety-critical functions must default to the safe state (brake application, signal at danger) on any single-point failure.
2. **Brake-to-Stop Guarantee** — The movement authority must be computed such that the train can stop before the limit of authority at the guaranteed emergency brake rate under worst-case adhesion, gradient, and reaction time.
3. **SIL 4 Integrity** — The ATP function (speed enforcement, brake intervention) must be developed to SIL 4 per EN 50129, requiring diverse hardware, formal methods, and independent safety assessment.
4. **Radio Black-Spot Coverage** — No loss of vital data for longer than the timeout period; overlapping base-station coverage with seamless handover.
5. **Two-out-of-Three (2oo3) Voting** — Vital processing channels shall use 2oo3 voting to tolerate one channel failure without spurious brake application.
6. **Separation of Vital and Non-Vital Functions** — Vital (safety) and non-vital (management) functions must run on physically or logically segregated platforms.
7. **Hazard Log Maintenance** — A living hazard log shall track all identified hazards, their SIL allocation, and the verification evidence for each safety requirement.
