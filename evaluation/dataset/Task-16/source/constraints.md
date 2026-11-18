# Constraints Register — Highway Driving Assistance System

Document: CON-ADAS-016
Revision: B

C1–C3 are stated in the requirements specification; this register continues from C4.

## Physical Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C4 | Host-vehicle speed range | 30 – 130 km/h | Lower bound avoids city driving; upper bound covers highway speed limits |
| C5 | Maximum automated deceleration in ACC and minimal-risk manoeuvre | 0.6 g (≈ 5.9 m/s²) | Comfort limit. Does not apply to collision-avoidance braking (REQ-004), which may use the full available tyre–road adhesion |
| C6 | Maximum lateral acceleration | 0.3 g | Comfort limit for lane-change and curve negotiation |
| C7 | Take-over transition time | ≤ 4 s | From TOR issuance to driver assuming control |
| C8 | Ambient temperature range | −40 °C to +85 °C | Automotive-grade electronics (AEC-Q100) |
| C9 | Vibration tolerance | 5 – 2000 Hz, 3 axes | ISO 16750-3 (random vibration, vehicle body) |
| C10 | Ingress protection | IP5K (dust) / IPX9K (high-pressure wash) | Sensor housings and ECU enclosures |
| C11 | Power supply | 12 V DC (9 – 16 V range), max 50 A peak | Vehicle electrical system per ISO 16750-2 |

## Budget Constraints

| ID | Item | Target | Notes |
|---|---|---|---|
| C12 | Sensor suite BOM cost | ≤ $2,500 (2026 volume pricing) | Cameras ($150), radars ($400), LiDAR ($800), IMU ($200), ECU ($950) |
| C13 | Compute platform TDP | ≤ 75 W | Fanless enclosure, passive cooling |
| C14 | Memory | ≥ 16 GB LPDDR5, ≥ 256 GB flash | For perception models and ring-buffer logging |
| C15 | Development timeline | 24 months to SOP | Prototype → integration → validation → production release |
| C16 | Fleet test mileage | ≥ 500,000 km | Across 3 climate zones, 5 vehicle platforms |

## Safety Constraints

| ID | Constraint |
|---|---|
| C17 | **ASIL-D** for braking and steering command paths (ISO 26262). |
| C18 | **SOTIF** release criteria: all known hazardous scenarios resolved; unknown-hazard rate < 1 per 10⁶ km. |
| C19 | **Cybersecurity** TARA must show all high-risk threats mitigated before SOP. |
| C20 | **False-positive rate** for forward-collision warning < 1 per 1,000 km. |
| C21 | **Perception update rate** ≥ 20 Hz (50 ms period). |
| C22 | **End-to-end latency** (sensor → actuation) ≤ 150 ms. |
