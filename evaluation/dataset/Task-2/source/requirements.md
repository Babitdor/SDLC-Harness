# Drone Delivery System — Requirements Specification

> **Document ID:** DDS-REQ-001
> **Revision:** 1.1
> **Date:** 2026-01-15
> **Status:** Released for systems modelling
> **Scope:** Urban last-mile parcel delivery by multirotor UAS, flown beyond visual
> line of sight (BVLOS) from a fixed depot to customer drop points.
> **Sources:** Stakeholder Requirements Document v1.2 · Service Level Agreement ·
> Environmental Specification · Concept of Operations (ConOps) draft

---

## 1. Regulatory Basis

Urban BVLOS delivery exceeds the limits of the EASA *open* category, which requires
visual line of sight. The operation is therefore conducted in the **specific**
category under an operational authorisation issued on the basis of a risk
assessment.

| Reference | Title | Applies to |
|---|---|---|
| Regulation (EU) 2019/947 | Rules and procedures for the operation of unmanned aircraft | Operational category, authorisation |
| Regulation (EU) 2019/945 | Unmanned aircraft systems and third-country operators | Product requirements, remote identification |
| JARUS SORA | Specific Operations Risk Assessment | Ground and air risk classification, mitigations |
| Regulation (EU) 2021/664 | Regulatory framework for the U-space | Operations inside designated U-space airspace |
| ISO 21384-3 | Unmanned aircraft systems — Operational procedures | Operator procedures |

---

## 2. Functional Requirements

### REQ-001 — Delivery Time
- **Statement:** The system shall deliver a package to its drop point within 30 minutes of order dispatch for destinations within the urban service radius.
- **Rationale:** The 30-minute window is the service commitment in the SLA.
- **Priority:** Must
- **Source:** Stakeholder Requirements Document v1.2, §3.1
- **Verification:** Flight test — time from dispatch to confirmed drop across 50 urban routes; 95th percentile ≤ 30 min.

### REQ-002 — Payload Capacity
- **Statement:** The system shall carry a payload of up to 5 kg.
- **Rationale:** Covers approximately 85 % of last-mile parcel masses in the operator's order history.
- **Priority:** Must
- **Source:** Stakeholder Requirements Document v1.2, §3.2
- **Verification:** Load test — hover and full mission profile at 5.0 kg payload.

### REQ-003 — Wind Tolerance
- **Statement:** The system shall complete a delivery mission in sustained wind speeds up to 30 km/h.
- **Rationale:** 30 km/h corresponds to Beaufort 5 and covers the site's 90th-percentile wind climate.
- **Priority:** Must
- **Source:** Stakeholder Requirements Document v1.2, §3.3
- **Verification:** Flight test at measured sustained wind of 30 km/h, headwind and crosswind legs.

### REQ-004 — Position Accuracy
- **Statement:** The system shall determine its horizontal position to within 2 m (95 %) using GNSS.
- **Rationale:** Required for geofence conformance and precise drop-point arrival.
- **Priority:** Must
- **Source:** Stakeholder Requirements Document v1.2, §3.4
- **Verification:** Field test — compare reported position with surveyed ground truth at 10 waypoints.

### REQ-005 — Emergency Landing Reserve
- **Statement:** The system shall retain sufficient energy for 5 minutes of controlled flight at the moment an emergency landing is commanded.
- **Rationale:** The reserve allows a controlled descent to a designated emergency landing zone after a motor or navigation failure.
- **Priority:** Must
- **Source:** Stakeholder Requirements Document v1.2, §4.1
- **Verification:** Discharge test — command emergency landing at the configured reserve threshold and measure remaining controlled-flight endurance (≥ 5 min).

### REQ-006 — Geofence Conformance
- **Statement:** The system shall prevent the aircraft from leaving the geofence defined for the mission.
- **Rationale:** Containment is a SORA mitigation for ground and air risk.
- **Priority:** Must
- **Source:** ConOps draft, §5.2
- **Verification:** Flight test — command a waypoint outside the geofence; aircraft holds at the boundary.

### REQ-007 — Command-and-Control Link Loss
- **Statement:** The system shall initiate return-to-depot when the command-and-control link is lost for more than 5 s.
- **Rationale:** Defined contingency behaviour is a condition of the operational authorisation.
- **Priority:** Must
- **Source:** ConOps draft, §6.1
- **Verification:** Flight test — interrupt the C2 link and time the transition to return-to-depot.

### REQ-008 — Remote Identification
- **Statement:** The system shall broadcast remote identification data throughout flight.
- **Rationale:** Remote identification is required for operation in the specific category and in U-space airspace.
- **Priority:** Must
- **Source:** Regulation (EU) 2019/945
- **Verification:** Inspection and receiver test — decode the broadcast during a test flight.

---

## 3. Non-Functional Requirements

### REQ-NF-001 — Operating Temperature
- **Statement:** The system shall operate within an ambient temperature range of −10 °C to +40 °C.
- **Rationale:** Covers all-season operation in the service area.
- **Priority:** Must
- **Source:** Environmental Specification, §2.1
- **Verification:** Environmental chamber test across the range with a hover profile.

### REQ-NF-002 — Communication Range
- **Statement:** The system shall maintain the command-and-control link at a range of at least 2 km in the urban environment.
- **Rationale:** The urban service radius requires a reliable non-line-of-sight link over 2 km.
- **Priority:** Must
- **Source:** System Specification, §5.1
- **Verification:** Range test — RSSI and packet loss at 500 m increments to 3 km.

### REQ-NF-003 — Delivery Success Rate
- **Statement:** The system shall achieve a delivery success rate of at least 99.5 %.
- **Rationale:** SLA target; 99.5 % allows approximately one failed delivery per 200.
- **Priority:** Must
- **Source:** Service Level Agreement, §7.2
- **Verification:** Analysis over 10,000 simulated and 1,000 live missions.

### REQ-NF-004 — Noise
- **Statement:** The system shall not exceed 65 dB(A) at 30 m slant range during cruise.
- **Rationale:** Community acceptance condition from the municipality consultation.
- **Priority:** Should
- **Source:** Stakeholder Requirements Document v1.2, §3.7
- **Verification:** Acoustic flyover measurement.

---

## 4. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Maximum take-off mass including payload | ≤ 25 kg | REQ-002 |
| C2 | Maximum flight altitude | 120 m above ground level | Regulation (EU) 2019/947 |
| C3 | Urban service radius from depot | ≤ 8 km | REQ-001 |
| C4 | Sustained wind limit for dispatch | 30 km/h | REQ-003 |
| C5 | C2 link-loss timeout | 5 s | REQ-007 |
| C6 | Energy reserve at emergency landing | ≥ 5 min controlled flight | REQ-005 |

---

## 5. Open Points

- The SORA ground-risk and air-risk classes are not yet assigned; the
  operational authorisation, and therefore any additional mitigations, depends
  on them.
- The drop method (winch, landing, parachute) is not selected.
- Whether the service area lies inside designated U-space airspace is not
  confirmed.

---

## 6. Revision History

| Revision | Date | Description |
|---|---|---|
| 1.0 | 2026-01-15 | Initial release |
| 1.1 | 2026-09-21 | Regulatory basis added; REQ-005 verification aligned to the 5-minute reserve; REQ-006–REQ-008, REQ-NF-004, constraints and open points added |
