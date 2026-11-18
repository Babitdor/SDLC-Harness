# Requirements Specification — Hydraulic Service Brake Performance

Document: SPEC-HBS-008
Revision: C
Status: Released for performance analysis
Scope: Service-brake performance of a 1500 kg passenger car: hydraulic actuation,
caliper clamping, pad friction and the resulting deceleration and braking
distance. Excludes ABS and electronic stability control.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| FMVSS 135 | Light vehicle brake systems | Regulatory stopping performance |
| UN ECE R13-H | Uniform provisions for the approval of passenger cars with regard to braking | Regulatory stopping performance |
| FMVSS 116 | Motor vehicle brake fluids | DOT 4 fluid |
| SAE J2522 | Dynamometer global brake effectiveness | Pad friction characterisation |

The regulatory minimum (FMVSS 135: stop from 100 km/h within 70 m) is less
demanding than the performance targets below, which are set by the product
specification.

---

## 2. Modelling Basis

The performance analysis uses three relations:

| Relation | Expression |
|---|---|
| Braking force | F = P × A × μ |
| Deceleration | a = F / m |
| Braking distance | d = v² / (2 a) |

**Simplification.** `A` is the *effective* piston area: it folds the number of pad
faces and the ratio of effective disc radius to rolling tyre radius into a single
area, so that F is the braking force at the tyre contact patch. Braking distance
is measured from the moment of full brake application; it excludes the brake
response time in REQ-NF-001.

---

## 3. Functional Requirements

**REQ-001 — Braking force**
The brake system shall generate a braking force of at least 12,000 N at full
actuation.
*Verification:* Analysis — F = P × A × μ at maximum pressure; test on a brake
dynamometer.

**REQ-002 — Deceleration**
The brake system shall decelerate the vehicle at not less than 8.0 m/s² at a
vehicle mass of 1500 kg.
*Verification:* Test — instrumented braking on dry asphalt.

**REQ-003 — Braking distance**
The brake system shall bring the vehicle to rest from 25 m/s within a braking
distance of 40 m.
*Verification:* Test — ten stops from 25 m/s, measured from full application.

**REQ-004 — Operating pressure**
The hydraulic circuit shall not exceed an operating pressure of 12.0 MPa.
*Verification:* Test — pressure transducer at full pedal force.

**REQ-005 — Pad friction**
The brake pads shall provide a friction coefficient of at least 0.35 in the dry
condition.
*Verification:* Test — SAE J2522 dynamometer procedure.

**REQ-006 — Axle distribution**
The brake system shall distribute braking force between the front and rear axles
in a 60 : 40 ratio.
*Verification:* Test — axle-load measurement on a roller brake tester.

---

## 4. Non-Functional Requirements

**REQ-NF-001 — Brake response time**
The brake system shall reach full actuation within 200 ms of pedal application.
*Verification:* Test — pedal-to-pressure timing.

**REQ-NF-002 — Operating temperature**
The brake system shall meet REQ-001 to REQ-003 at ambient temperatures from
−10 °C to +60 °C.
*Verification:* Test — climatic chamber and hot-weather track testing.

**REQ-NF-003 — Service life**
The brake system shall withstand 50,000 braking cycles before major overhaul.
*Verification:* Test — dynamometer endurance schedule.

**REQ-NF-004 — Mass**
The brake system, including calipers, lines and master cylinder, shall not exceed
30 kg.
*Verification:* Inspection — weighed assembly.

---

## 5. Design Constraints and Nominal Values

| ID | Parameter | Value | Traces to |
|---|---|---|---|
| C1 | Vehicle mass | 1500 kg | REQ-002 |
| C2 | Initial velocity for the braking-distance case | 25 m/s | REQ-003 |
| C3 | Maximum hydraulic pressure | 12.0 MPa | REQ-004 |
| C4 | Effective piston area (nominal design) | 3.0 × 10⁻³ m² | REQ-001 |
| C5 | Pad friction coefficient (minimum) | 0.35 | REQ-005 |
| C6 | Master cylinder bore | ≤ 35 mm | REQ-004 |
| C7 | Brake fluid | DOT 4 minimum | FMVSS 116 |
| C8 | Pedal ratio | 4 : 1 to 6 : 1 | REQ-NF-001 |
| C9 | Tyre–road adhesion assumed for the braking-distance case | ≥ 0.90 (dry asphalt) | REQ-002 |

---

## 6. Consistency Check

At the nominal design values, F = 12.0 MPa × 3.0 × 10⁻³ m² × 0.35 = 12,600 N,
giving a = 8.4 m/s² and d = 37.2 m from 25 m/s. At the minimum required force,
12,000 N gives a = 8.0 m/s² and d = 39.1 m. Both satisfy REQ-003. The required
deceleration of 8.0 m/s² corresponds to 0.82 g and the nominal 8.4 m/s² to 0.86 g;
both are within the dry-road adhesion of 0.90 assumed in C9, so neither case is
traction-limited.

---

## 7. Open Points

- The wet-condition friction coefficient is not specified, so wet braking
  distance is not covered by this revision.
