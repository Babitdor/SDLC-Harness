# Knowledge Base — UAV Delivery: Regulation, Standards and Design Rules

Document: KB-UDS-015
Purpose: Background for concept selection. Descriptive only — the requirements and
constraints documents are binding.

## 1. Regulatory Framework

| Reference | Title / scope |
|---|---|
| Regulation (EU) 2019/947 | Operation of unmanned aircraft: open, specific and certified categories |
| Regulation (EU) 2019/945 | UAS product requirements, class marks, remote identification |
| JARUS SORA | Specific Operations Risk Assessment methodology |
| Regulation (EU) 2021/664 | U-space airspace framework |
| ASTM F3322 | Small UAS parachutes |
| ASTM F3005 | Batteries for small UAS |
| RTCA DO-362 | C2 data link minimum operational performance standards |
| ISO 21384-3 | UAS operational procedures |

**Why the specific category.** The open category requires visual line of sight
(VLOS). Urban delivery flights leave the pilot's sight, so they need an
operational authorisation in the specific category, obtained through a SORA or a
standard scenario. The 120 m altitude limit of the open category is normally
retained in the authorisation.

## 2. Design Rules

- **Geofencing.** Each mission defines a 3-D geofence, loaded before take-off and
  checked continuously; a predicted breach triggers return to home.
- **Link loss.** If the C2 link is lost for more than 5 s, the UAV climbs to a safe
  altitude and returns to its home point.
- **Redundancy.** Flight controller, IMU, GNSS receiver and battery monitor are at
  least dual-redundant.
- **Battery reserve.** Normal operation never discharges below 20 %; return to home
  starts at 25 %.
- **Airport separation.** Routes keep at least 100 m horizontal separation from
  aerodromes, heliports and restricted airspace unless the authorisation allows
  otherwise.
- **Emergency landing zones.** The mission planner designates at least one emergency
  landing zone per route segment, clear of people.

## 3. Energy Sizing Rule of Thumb

Multirotor hover power is roughly 150 W per kilogram of take-off mass for this
size class, and cruise power is similar. Because the 25 % reserve cannot be used
for the mission, flight time comes from 75 % of battery capacity.

Iterating mass and battery for a 5 kg payload, 6.5 kg of airframe and avionics,
and cells at about 200 Wh/kg gives a battery of about 2.3 kWh (11.5 kg), a take-off
mass of about 23 kg and a hover power of about 3.5 kW. A 6S 16 Ah pack (355 Wh)
would give under 5 minutes at that mass.
