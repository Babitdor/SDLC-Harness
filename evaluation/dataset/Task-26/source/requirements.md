# Requirements Specification — UAV Surveillance System

Document: SPEC-UAS-026
Revision: B
Status: Released for architecture
Scope: A small unmanned aircraft system for perimeter and area surveillance of an
industrial site in the United States: the aircraft with EO/IR payload, the
command-and-control and video link, and the ground control station. Operated
under 14 CFR Part 107.

---

## 1. Applicable Regulations and Standards

| Reference | Title | Applies to |
|---|---|---|
| 14 CFR Part 107 | Small unmanned aircraft systems | Operating limits, altitude, mass |
| 14 CFR Part 89 | Remote identification of unmanned aircraft | Remote ID broadcast |
| ASTM F3322 | Small UAS parachutes | Emergency descent (if fitted) |
| IEC 60529 | Degrees of protection (IP code) | Airframe ingress protection |

---

## 2. Functional Requirements

**REQ-001 — Sortie endurance**
The UAV shall fly for at least 40 minutes per battery with the EO/IR payload fitted.
*Verification:* Test — hover and loiter endurance flight at MTOW.

**REQ-002 — Mission duration**
The system shall sustain a 2-hour surveillance mission using battery swaps, with
each surveillance interruption for a swap not exceeding 10 minutes.
*Verification:* Demonstration — 2-hour mission with timed swap turnarounds.

**REQ-003 — Live video**
The UAV shall stream live video to the ground control station with an end-to-end
latency below 500 ms.
*Verification:* Test — timestamped frame capture at the GCS.

**REQ-004 — Waypoint navigation**
The UAV shall navigate GPS waypoints with a horizontal position accuracy of ±2 m.
*Verification:* Test — surveyed waypoint course.

**REQ-005 — Geofence**
The UAV shall prevent flight outside the defined geofence.
*Verification:* Test — commanded waypoint outside the boundary.

**REQ-006 — Return to home**
The UAV shall return to the launch point when battery charge reaches the reserve
threshold or when the command-and-control link is lost for more than 5 s.
*Verification:* Test — reserve threshold trigger; link interruption.

**REQ-007 — Day/night imaging**
The UAV shall carry a stabilised gimbal with visible and thermal infrared cameras.
*Verification:* Inspection — payload configuration.

**REQ-008 — Object tracking**
The UAV shall detect and track a moving person or vehicle within the camera field of
view, keeping it centred by gimbal and aircraft control.
*Verification:* Test — tracking of a vehicle at 30 km/h.

**REQ-009 — Onboard recording**
The UAV shall record all telemetry and video to onboard storage for post-mission
analysis.
*Verification:* Inspection — recordings after a mission.

**REQ-010 — Remote identification**
The UAV shall broadcast remote identification messages throughout flight.
*Verification:* Test — receiver decode per 14 CFR Part 89.

---

## 3. Non-Functional Requirements

**REQ-NF-001 — Operating temperature**
The UAV shall operate from −10 °C to +50 °C.
*Verification:* Test — climatic chamber at both limits.

**REQ-NF-002 — Altitude ceiling**
The UAV shall not exceed 400 ft (122 m) above ground level.
*Verification:* Test — altitude limiter.

**REQ-NF-003 — Link range**
The command-and-control and video link shall operate to 10 km from the ground
control station.
*Verification:* Test — range flight with link quality logging.

**REQ-NF-004 — Ingress protection**
The airframe shall achieve IP43.
*Verification:* Test — IEC 60529 spray and dust.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Maximum take-off mass | < 24.9 kg (55 lb, the Part 107 limit) | REQ-001 |
| C2 | Noise at 10 m | ≤ 70 dB(A) | — |
| C3 | Battery swap time | < 2 min, tool-free | REQ-002 |
| C4 | Altitude ceiling | 400 ft (122 m) AGL | REQ-NF-002 |
| C5 | Link-loss timeout | 5 s | REQ-006 |

---

## 5. Open Points

- Surveillance at 10 km is beyond visual line of sight; it requires an FAA waiver
  under 14 CFR 107.205, which has not been applied for.
- Gapless coverage through battery swaps would require a second aircraft; this
  revision accepts interruptions of up to 10 minutes.
