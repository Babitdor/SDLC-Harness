# Constraints Register — Large-Volume Infusion Pump

Document: CON-INF-017
Revision: B

## Physical Constraints

| ID | Constraint | Value | Rationale |
|---|---|---|---|
| PC-1 | Flow rate range | 0.1 – 1,200 mL/h | Covers neonatal (0.1 mL/h) to large-volume adult infusions |
| PC-2 | Occlusion alarm pressure threshold | ≤ 15 psi | Prevents vessel damage while allowing early occlusion detection |
| PC-3 | Air-in-line detection threshold | ≤ 0.1 mL accumulated air | Design value; IEC 60601-2-24 requires air-in-line protection with a declared threshold |
| PC-4 | Delivered-volume accuracy | ±5 % of programmed volume | Design value; measured with the IEC 60601-2-24 accuracy test method |
| PC-5 | Device weight | ≤ 5 kg (including battery) | Portable for pole-mount and transport use |
| PC-6 | Ingress protection | IPX2 (drip-proof) minimum; IPX5 preferred | Clinical cleaning and spill protection |

## Performance Constraints

| ID | Constraint | Value | Rationale |
|---|---|---|---|
| PC-7 | Alarm annunciation latency | ≤ 2 s from fault detection | Timely clinician response to fault conditions |
| PC-8 | Battery life (mains loss) | ≥ 4 h at nominal flow rate | Covers typical patient transport and shift handover |
| PC-9 | DERS error-rejection probability | ≥ 99.99 % | Project target for the drug-library DERS |
| PC-10 | Software boot time | ≤ 10 s from power-on to ready | Clinical urgency scenarios |

## Budget & Schedule Constraints

| ID | Constraint | Value | Rationale |
|---|---|---|---|
| BC-1 | Total development budget | ≤ $4.5 M (NRE) | Program office allocation for Class C medical device |
| BC-2 | Per-unit BOM cost target | ≤ $850 (volume of 5,000 units/yr) | Competitive pricing for large-volume infusion pumps |
| BC-3 | Development timeline | 24 months to 510(k) submission | Regulatory and market-window constraints |
| BC-4 | Verification & validation | ≥ 6 months of dedicated V&V | IEC 62304 Class C requires independent V&V effort |
| BC-5 | Clinical evaluation | ≥ 2 clinical sites, 50 patients | Project decision for usability and clinical evaluation |
