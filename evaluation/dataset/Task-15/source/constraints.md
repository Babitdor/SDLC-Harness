# Constraints Register — Autonomous UAV Delivery System

Document: CON-UDS-015
Revision: B

C1–C3 are stated in the requirements specification; this register continues from C4.

## 1. Physical Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C4 | Maximum payload mass | 5 kg | REQ-NF-001 |
| C5 | Minimum endurance before reserve | 30 min | REQ-NF-002; at nominal load and cruise speed |
| C6 | Return-to-home reserve | 25 % state of charge | Normal operation never below 20 % |
| C7 | Operating temperature | −10 °C to +50 °C | Commercial drone envelope |
| C8 | Maximum precipitation | Light rain, < 2.5 mm/h | No operation in heavy rain |

C1 (25 kg) matches the open-category upper bound; the operation itself is in the
specific category because it is flown beyond visual line of sight.

## 2. Performance Constraints

| ID | Constraint | Value | Notes |
|---|---|---|---|
| C9 | Cruise speed | 10–15 m/s | Endurance versus delivery time |
| C10 | C2 link latency | ≤ 200 ms | REQ-NF-003 |
| C11 | Obstacle detection | ≥ 99.99 % for objects > 0.3 m | REQ-NF-004 |
| C12 | Concurrent fleet | ≥ 50 drones | REQ-NF-005 |
| C13 | GNSS fallback threshold | 2 m horizontal (95 %) | REQ-003 |
| C14 | Geofence breach response | ≤ 1 s to return-to-home | REQ-010 |
| C15 | C2 link-loss timeout | 5 s | Then autonomous return to home |

## 3. Budget and Schedule Constraints

| ID | Constraint | Value |
|---|---|---|
| C16 | Unit cost per drone | ≤ USD 8,000 |
| C17 | Ground control station cost | ≤ USD 50,000 |
| C18 | Development duration | 18 months |
| C19 | Certification activities | 6 months, in parallel with development |
| C20 | Fleet size at launch | 20 drones |

## 4. Safety Constraints

| ID | Constraint |
|---|---|
| C21 | A failure mode and effects analysis (FMEA) shall be completed before first flight. |
| C22 | A safety pilot shall be present for every test flight outside the designated test range. |
| C23 | The ground control station shall have a physical emergency-stop button. |
| C24 | Every flight-critical software update shall be validated on a hardware-in-the-loop bench before deployment. |
| C25 | The UAV shall log position, attitude, battery and link status at ≥ 10 Hz. |
| C26 | Flight controller, IMU, GNSS receiver and battery monitor shall each be at least dual-redundant. |
