# Design Constraints — HRS 700 bar

Document: CON-HRS-002
Revision: B

Every constraint below is binding on the concept and on the site layout. Values
marked *(parametric)* are not yet fixed because they depend on the site-specific
risk assessment, which is in progress; the layout must be produced so that these
values can be varied without redesign.

---

## 1. Process Constraints

| ID | Constraint | Limit | Source |
|---|---|---|---|
| C1 | Dispensing pressure, light duty | 70 MPa nominal working pressure | REQ-001 |
| C2 | Dispensing pressure, fleet | 35 MPa nominal working pressure | REQ-001 |
| C3 | High-pressure buffer bank pressure | 950 bar maximum | REQ-012 |
| C4 | Medium-pressure buffer bank pressure | 650 bar nominal | REQ-012 |
| C5 | Low-pressure buffer bank pressure | 450 bar nominal | REQ-012 |
| C6 | Fuel delivery temperature at nozzle, H70 | −40 °C to −33 °C (category T40) | REQ-003 |
| C7 | Vehicle tank gas temperature during fill | 85 °C maximum | REQ-005 |
| C8 | Nominal fill time, 5 kg from 10 % to 95 % SOC | 180 s maximum | REQ-004 |
| C9 | Consecutive fills without extended recovery | 6 minimum, ≤ 300 s between | REQ-006 |
| C10 | Daily dispensed mass | 420 kg per 24 h minimum | REQ-013 |
| C11 | Peak hourly dispensed mass | 60 kg/h minimum | REQ-013 |
| C12 | Buffer autonomy, compressor unavailable | 80 kg minimum | REQ-014 |
| C13 | Hydrogen purity at nozzle | ISO 14687 Grade D | REQ-010 |
| C14 | Custody transfer metering accuracy | ±1.5 % of dispensed mass | REQ-008 |

## 2. Safety Constraints

| ID | Constraint | Limit | Source |
|---|---|---|---|
| C15 | Gas detection shutdown threshold | 25 % LFL | REQ-017 |
| C16 | Emergency shutdown isolation time | 10 s maximum | REQ-018 |
| C17 | Separation, process equipment to site boundary | *(parametric)* — from risk assessment | REQ-020 |
| C18 | Separation, dispensing area to occupied building | *(parametric)* — from risk assessment | REQ-020 |
| C19 | Separation, storage bank to public highway | *(parametric)* — from risk assessment | REQ-020 |
| C20 | Vent stack discharge | Vertically upward, not toward occupied areas | REQ-021 |
| C21 | Hazardous area equipment certification | ATEX, zone-appropriate | REQ-019 |
| C22 | Crash protection in circulation area | Required on all exposed process equipment | REQ-024 |

## 3. Site and Layout Constraints

| ID | Constraint | Limit | Source |
|---|---|---|---|
| C23 | Site envelope | 48 m × 26 m hard standing | REQ-NF-001 |
| C24 | Vehicle circulation | Forward-in, forward-out; no reversing for a 12 m rigid | REQ-NF-005 |
| C25 | Dispensing island clearance | Minimum 3.5 m lane width each side | Forecourt design guide |
| C26 | Tube trailer bay (if F1-A selected) | 18 m × 4 m standing plus connection panel access | Delivery vehicle envelope |
| C27 | Maintenance access to compression skid | Skid removable without disturbing storage banks | REQ-NF-006 |
| C28 | Maintenance access to precooling skid | Skid removable without disturbing dispensing island | REQ-NF-006 |

## 4. Performance and Environmental Constraints

| ID | Constraint | Limit | Source |
|---|---|---|---|
| C29 | Specific energy, compression plus precooling | 4.0 kWh/kg maximum, weekly average | REQ-NF-004 |
| C30 | Boundary noise | 55 dB(A) maximum during normal operation | REQ-NF-003 |
| C31 | Station availability | 97 % minimum, monthly | REQ-NF-002 |
| C32 | Design life, static equipment | 20 years | REQ-NF-007 |
| C33 | Design life, rotating equipment | 10 years | REQ-NF-007 |
| C34 | Ambient operating range | −20 °C to +40 °C | Site meteorological data |

---

## 5. Notes on Constraint Interaction

C8 (fill time), C6 (delivery temperature) and C29 (specific energy) are in
tension. Meeting the fill time at the cold end of the T40 window requires
refrigeration capacity that raises specific energy consumption; meeting the
energy target by precooling at the warm end of the window reduces the permissible
pressure ramp rate and so extends the fill time. The concept must state where in
this trade space it sits and on what basis.

C12 (buffer autonomy) and C23 (site envelope) are in tension for the
higher-pressure storage options: satisfying autonomy with a single 950 bar bank
requires more vessel volume than the cascade options for the same dispensed mass,
and vessel count drives footprint.

C17 to C19 are parametric by intent. A layout that hard-codes separation
distances will require rework when the risk assessment completes. The layout
shall therefore express these distances as named parameters with the values used
for the current iteration stated explicitly.
