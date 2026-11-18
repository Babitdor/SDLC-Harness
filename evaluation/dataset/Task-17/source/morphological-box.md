# Morphological Box — Medical Infusion Pump

Document: MB-INF-017
Status: For evaluation — no option selected

| Function | Option 1 | Option 2 | Option 3 |
|---|---|---|---|
| Fluid Delivery | Peristaltic finger mechanism (multi-finger camshaft, ±2 % accuracy) | Syringe-driven piston (high precision, low continuous-flow ripple) | Rotary peristaltic pump (low cost, simple tubing path) |
| Dose Calculation | Drug-library DERS with soft/hard limits (IEC 62304 Class C) | Weight-based dosing calculator (mg/kg/min) | TPN compounding calculator (multi-channel rate blending) |
| Alarm Management | Audible + visual annunciation with priority escalation | Nurse-call relay output (remote alert to central station) | Smart alarm suppression (nuisance-reduction algorithm) |
| User Interface | High-res colour TFT with touchscreen (capacitive, glove-compatible) | Membrane keypad + monochrome OLED (rugged, low power) | Rotary encoder + segment LCD (extreme reliability, minimal UI) |
| Data Logging | Tamper-evident internal flash (SHA-256 hashed audit trail) | Wireless HL7 / FHIR export to hospital EMR | Removable SD card with encrypted event log |
| Power Management | Hot-swappable Li-ion battery pack (≥4 h runtime) | Mains AC/DC with automatic internal battery backup | Wireless inductive charging (no exposed contacts, IPX5 sealed) |

## Option Characteristics

**Delivery — linear peristaltic (multi-finger).** The usual large-volume mechanism;
good accuracy across the full rate range with standard tubing sets.
**Syringe driver.** Very accurate and smooth at low rates; capacity limited to the
syringe, typically 60 mL or less. **Rotary peristaltic.** Cheapest; accuracy
degrades with tubing wear.

**Alarm management — nurse-call relay.** Extends alarms to the station; needs
hospital wiring. **Smart suppression.** Cuts nuisance alarms; must not suppress
alarm conditions required by IEC 60601-1-8.

**User interface — colour touchscreen.** Shows drug names, units and limits clearly;
highest power. **Segment LCD + encoder.** Robust and low power; cannot show drug
library entries legibly.

**Power — mains with internal battery backup.** Continuous ward use with transport
autonomy. **Hot-swappable pack.** Unlimited transport time; the swap must not
interrupt delivery. **Inductive charging.** Sealed enclosure; slow charging.

## Known Incompatibilities

- A syringe driver cannot deliver large-volume infusions: at 1,200 mL/h a 60 mL
  syringe empties in 3 minutes (C1).
- A segment LCD cannot present drug-library names and limits well enough to
  support DERS confirmation (REQ-003) without use errors.
- Smart alarm suppression cannot be applied to occlusion or air-in-line alarms,
  which must always annunciate (REQ-007, REQ-NF-002).
- Inductive charging alone, without a mains-powered mode, conflicts with continuous
  ward operation on long infusions.
