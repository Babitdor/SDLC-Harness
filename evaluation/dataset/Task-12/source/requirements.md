# Design Basis — Steel Plate-Girder Road Bridge, Structural Analysis

Document: DBR-BRG-012
Revision: B
Status: Released for analysis modelling
Scope: Static and dynamic (wind, seismic) analysis of one main girder of a 50 m
simply supported steel plate-girder road bridge in seismic zone IV. Covers the
analysis cases, their parameters and the acceptance criteria. Excludes
substructure, bearings and fatigue.

---

## 1. Applicable Codes

| Reference | Title | Applies to |
|---|---|---|
| IRC:6 | Standard specifications and code of practice for road bridges — Loads and load combinations | Wind load, combinations |
| IRC:24 | Steel road bridges (limit state method) | Deflection limits, steel design |
| IRC:SP:114 | Guidelines for seismic design of road bridges | Seismic coefficient |
| IS 2062 | Hot rolled structural steel | Grade E250 material |

---

## 2. Structure and Material Data

| Parameter | Symbol | Value |
|---|---|---|
| Span (simply supported) | L | 50 m |
| Girder depth | d | 2.6 m |
| Second moment of area, major axis | I | 0.28 m⁴ |
| Elastic section modulus, major axis | Z = I / (d/2) | 0.2154 m³ |
| Lateral section modulus of deck bracing system | Z_lat | 1.8 m³ |
| Modulus of elasticity | E | 200 GPa |
| Yield strength (IS 2062 E250) | f_y | 250 MPa |
| Exposed height for wind (girder + deck + barrier) | h_exp | 4.0 m |
| Dead load per girder, including self-weight | g | 30 kN/m |

---

## 3. Static Load Analysis Requirements

**REQ-001 — Static analysis case**
The girder shall be analysed under a uniformly distributed design load of
50 kN/m (dead load plus equivalent live load, including impact) over the full span.
*Verification:* Analysis — static linear-elastic model.

**REQ-002 — Allowable stress**
The maximum bending stress under the static design load shall not exceed
f_y / 1.5 = 166.7 MPa.
*Verification:* Analysis — σ = M / Z with M = wL² / 8.

**REQ-003 — Total deflection**
The mid-span deflection under the static design load shall not exceed L / 600
(83.3 mm), the IRC:24 limit for total deflection of plate girders.
*Verification:* Analysis — δ = 5wL⁴ / (384 E I).

---

## 4. Dynamic Load Analysis Requirements

**REQ-004 — Wind analysis case**
The girder shall be analysed for a design wind speed of 45 m/s, giving a wind
pressure of q = ½ ρ V² = 1.24 kPa (ρ = 1.225 kg/m³) on the exposed area
h_exp × L = 200 m².
*Verification:* Analysis — wind force F_w = q × A_exposed.

**REQ-005 — Seismic analysis case**
The girder shall be analysed for seismic load using the horizontal seismic
coefficient A_h = (Z/2) × (I/R) × (S_a/g) of IRC:SP:114, with:
zone factor Z = 0.24 (zone IV), importance factor I = 1.2 (important bridge),
response reduction factor R = 3.0 (ductile steel bracing) and spectral
acceleration coefficient S_a/g = 2.5.
*Verification:* Analysis — base shear V_b = A_h × W with W = g × L.

**REQ-006 — Combined stress**
The sum of the static bending stress and the lateral stress from the governing
dynamic case shall not exceed f_y / 1.5.
*Verification:* Analysis — σ_static + σ_lateral ≤ 166.7 MPa.

---

## 5. Analysis Constraints

| ID | Constraint | Traces to |
|---|---|---|
| C1 | Linear-elastic material behaviour | REQ-001–REQ-006 |
| C2 | Simply supported boundary conditions at both ends | REQ-001–REQ-006 |
| C3 | Self-weight included in the dead load g | REQ-001, REQ-005 |
| C4 | Wind and seismic are independent load cases, not applied together | REQ-004–REQ-006 |
| C5 | A_h = (Z/2)(I/R)(S_a/g); R divides the elastic demand | REQ-005 |
| C6 | Deflection limit L/600 (total); live load with impact alone limited to L/800 | REQ-003 |

---

## 6. Reference Results (for checking the model)

| Quantity | Value | Criterion | Status |
|---|---|---|---|
| Static bending moment M | 15.63 MN·m | — | — |
| Static bending stress | 72.5 MPa | ≤ 166.7 MPa | 44 % utilised |
| Mid-span deflection | 72.7 mm | ≤ 83.3 mm | Governs |
| Wind force | 248 kN | — | — |
| Lateral stress from wind | 0.86 MPa | — | — |
| Seismic coefficient A_h | 0.120 | — | — |
| Seismic base shear (W = 1500 kN) | 180 kN | — | — |
| Combined stress (static + wind) | 73.4 MPa | ≤ 166.7 MPa | Pass |

Deflection, not stress, governs this girder — typical for a long simply
supported span.

---

## 7. Open Points

- The live-load-only deflection check (L/800) needs the live-load component of the
  50 kN/m design load, which this revision does not separate.
- Wind drag and gust factors from IRC:6 are not applied; the wind case uses the
  basic dynamic pressure only.
