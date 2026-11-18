# Constraints Register — Metro CBTC Signalling System

Document: CON-CBTC-019
Revision: B

## Operational Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C1 | Minimum train headway | 90 s | Peak-hour headway at the busiest station |
| C2 | Emergency braking distance | ≤ 300 m | From maximum line speed (80 km/h) on dry rail |
| C3 | Radio handover time | ≤ 100 ms | Between adjacent base stations at line speed |
| C4 | End-to-end latency (position report → MA) | ≤ 2 s | Includes processing, transmission, and radio propagation |
| C5 | Maximum trains in service | 30 | Simultaneous operation on the same line |
| C6 | System availability | ≥ 99.9 % | Revenue-service hours excluding planned maintenance |
| C7 | Radio link success rate | ≥ 99.99 % | Per connection attempt |

## Physical & Infrastructure Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C8 | Line length | 25 km | Double-track metro line with 20 stations |
| C9 | Maximum gradient | 4 % | Affects braking distance and tractive effort |
| C10 | Tunnel sections | 12 km | Underground segments with limited radio propagation |
| C11 | Base station spacing | 500–800 m | Depends on tunnel vs. open-air alignment |
| C21 | Guaranteed emergency brake rate (level track) | ≥ 1.4 m/s² | Needed for C2 on the 4 % down-gradient (C9) |

## Budget & Timeline Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C12 | Total project budget | € 120 M | Includes design, installation, testing, and commissioning |
| C13 | System design phase | 12 months | From concept to detailed design review |
| C14 | Installation & integration | 18 months | On-site installation, cabling, and subsystem integration |
| C15 | Testing & commissioning | 8 months | Factory acceptance, site acceptance, and trial running |
| C16 | Revenue service start | Month 38 | From project kick-off |

## Safety & Regulatory Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C17 | Safety integrity level | SIL 4 | For ATP and interlocking functions per EN 50129 |
| C18 | Tolerable functional failure rate | Within the SIL 4 band: 10⁻⁹ ≤ TFFR < 10⁻⁸ per hour | EN 50129, for ATP and interlocking functions |
| C19 | Independent safety assessment | Required | By an accredited third-party assessor |
| C20 | RAMS demonstration period | 6 months | Continuous revenue-service operation with full data logging |

## Consistency Check — C2 on the Steepest Gradient

On a 4 % down-gradient, gravity reduces the effective deceleration by
9.81 × 0.04 = 0.39 m/s². With a 1.5 s reaction at 80 km/h (22.2 m/s):

| Guaranteed brake rate (level) | Effective on 4 % down | Stopping distance | C2 (≤ 300 m) |
|---|---|---|---|
| 1.2 m/s² | 0.81 m/s² | 339 m | Fails |
| 1.3 m/s² | 0.91 m/s² | 305 m | Fails |
| 1.4 m/s² | 1.01 m/s² | 278 m | Meets |

C21 therefore sets the guaranteed emergency brake rate at ≥ 1.4 m/s².

