# Morphological Box — HRS Concept Options

Document: MB-HRS-002
Prepared by: Concept engineering
Status: For evaluation — no option selected

The box enumerates the candidate solution principle for each station function.
Concept selection combines exactly one option per function into a consistent
principle solution. Not all combinations are admissible; known incompatibilities
are listed in section 3.

---

## 1. Function / Option Matrix

| # | Function | Option A | Option B | Option C | Option D |
|---|---|---|---|---|---|
| F1 | Provide hydrogen supply | Tube trailer delivery, 300 bar | Liquid hydrogen tanker + vaporiser | On-site PEM electrolysis | Pipeline connection |
| F2 | Compress hydrogen | Diaphragm compressor | Ionic liquid compressor | Reciprocating piston compressor | Electrochemical compressor |
| F3 | Store hydrogen | Three-bank cascade, 450 / 650 / 950 bar | Single high-pressure bank, 950 bar | Two-bank cascade, 500 / 950 bar | Liquid storage with pump vaporisation |
| F4 | Precool hydrogen | Central chiller, silicone heat transfer fluid | Per-dispenser chiller | Liquid nitrogen heat exchanger | Phase-change thermal store |
| F5 | Dispense hydrogen | Twin dispenser, H70 + H35 per unit | Separate H70 and H35 islands | Single dispenser, switchable | — |
| F6 | Control the station | Central PLC with SCADA | Distributed skid controllers | PLC with cloud supervisory | — |
| F7 | Detect leakage | Point catalytic sensors | Open-path infrared | Ultrasonic acoustic | Combined point + acoustic |
| F8 | Manage vent and relief | Common vent header, single stack | Segregated vent per system | Vent with flare | — |

---

## 2. Option Characteristics

### F1 — Hydrogen supply

**A. Tube trailer, 300 bar.** Lowest capital cost and shortest lead time. Requires
a trailer parking bay with connection panel and imposes a delivery vehicle
movement roughly every two days at the specified throughput. Supply continuity
depends on logistics.

**B. Liquid hydrogen tanker with vaporiser.** Highest energy density per delivery
and fewest deliveries. Requires cryogenic storage, incurs boil-off losses when
throughput is low, and adds a cryogenic hazard class to the site.

**C. On-site PEM electrolysis.** Removes delivery logistics entirely and enables
green hydrogen where renewable supply is available. Highest capital cost, highest
electrical connection requirement, and requires water treatment. Footprint is
significant.

**D. Pipeline connection.** Lowest operating cost where a network exists. Not
available at this site in the project timeframe; retained for completeness only.

### F2 — Compression

**A. Diaphragm.** Hydraulically actuated triple-diaphragm head. No dynamic seal
in the gas path, therefore essentially leak-free and gas purity is preserved.
Widely used in refuelling service and well proven at 900+ bar. Diaphragm
replacement is a scheduled maintenance item.

**B. Ionic liquid.** Piston action with an ionic liquid replacing the solid
piston, eliminating gas leakage past the seal. Compact, few moving parts, good
isothermal efficiency. Smaller installed base and specialist maintenance.

**C. Reciprocating piston.** Mechanically simple, straightforward maintenance,
established supply chain. Dynamic seals introduce a small leakage path and a
lubricant contamination risk requiring downstream purification.

**D. Electrochemical.** No moving parts, silent, high isothermal efficiency.
Immature at the required flow rate and pressure; not considered viable for this
throughput in the project timeframe.

### F3 — Storage

**A. Three-bank cascade, 450 / 650 / 950 bar.** Fills draw sequentially from the
low bank upward, so the high bank supplies only the final pressure rise. Lowest
compressor duty per fill and best back-to-back performance. Most vessels and the
most complex bank-selection control.

**B. Single bank at 950 bar.** Simplest control and fewest vessels. Every fill
draws from the high bank, so compressor duty and specific energy are the highest
of the options.

**C. Two-bank cascade, 500 / 950 bar.** Intermediate on all counts.

**D. Liquid storage with cryogenic pump.** Very high stored mass in a small
footprint, and the pump replaces the gas compressor. Boil-off management is
required and the option is only consistent with a liquid supply mode.

### F4 — Precooling

**A. Central chiller with silicone heat transfer fluid.** One refrigeration plant
serves all dispensers through an insulated secondary loop, with the heat transfer
fluid held near −60 °C so the hydrogen reaches the T40 window at the nozzle.
Efficient at high utilisation; the secondary loop imposes a thermal lag that must
be managed for the first fill after an idle period.

**B. Per-dispenser chiller.** Short thermal path, fast recovery, no shared
failure mode between dispensers. Higher total installed refrigeration capacity
and more maintenance points.

**C. Liquid nitrogen heat exchanger.** No refrigeration machinery, very fast
cooldown. Requires a consumable nitrogen supply and a further delivery logistics
chain.

**D. Phase-change thermal store.** Charged during off-peak periods and drawn down
during fills, decoupling refrigeration capacity from peak demand. Limited
back-to-back capability once the store is depleted.

### F5 — Dispensing

**A. Twin dispenser, both nozzles per unit.** Either vehicle type can use either
dispenser, giving the best queue behaviour. More nozzle assemblies.

**B. Separate H70 and H35 islands.** Simpler dispensers. Poor utilisation when
demand is unbalanced between vehicle types.

**C. Single switchable dispenser.** Lowest cost. Only one vehicle can fuel at a
time, which conflicts with the back-to-back requirement at peak.

### F6 — Control

**A. Central PLC with SCADA.** Single point of sequencing and logging, well
understood, straightforward safety interlock design.

**B. Distributed skid controllers.** Each skid is independently testable and
supplied as a certified unit; station-level sequencing must then be coordinated
across controllers.

**C. PLC with cloud supervisory.** Local control with remote analytics.
Introduces an external dependency in the monitoring path.

### F7 — Leak detection

**A. Point catalytic sensors.** Established and inexpensive. Detects only at the
sensor location, so placement must follow dispersion analysis.

**B. Open-path infrared.** Covers a line rather than a point, good for perimeter
and compartment openings. Higher cost per unit.

**C. Ultrasonic acoustic.** Detects the sound of a pressurised release rather
than accumulated gas, so it responds before gas reaches a sensor, but is
susceptible to background noise.

**D. Combined point plus acoustic.** Complementary coverage: acoustic for rapid
release detection, point sensors for accumulation in enclosed compartments.

### F8 — Vent and relief

**A. Common vent header with a single stack.** Fewest penetrations and one
dispersion analysis. Cross-connection between systems must be assessed.

**B. Segregated vent per system.** No cross-connection risk. More stacks and more
dispersion cases.

**C. Vent with flare.** Eliminates an unignited release at the stack. Adds a
continuous pilot and a further hazard source; unusual at this station scale.

---

## 3. Known Incompatibilities

- F3-D (liquid storage with cryogenic pump) is admissible only with F1-B (liquid
  supply). It is inconsistent with F1-A, F1-C and F1-D.
- F1-B (liquid supply) with F3-A/B/C requires a vaporiser and a gas compressor in
  addition to the cryogenic storage, and the combination should only be selected
  if the boil-off penalty is justified by delivery frequency.
- F5-C (single switchable dispenser) cannot satisfy REQ-007, which requires two
  independently operable dispensers.
- F2-D (electrochemical compression) is not available at the required throughput
  and is excluded from selection.
- F1-D (pipeline) is not available at this site and is excluded from selection.
- F4-D (phase-change store) alone cannot satisfy REQ-006 (six consecutive fills)
  without oversizing the store beyond the available footprint; it is admissible
  only in combination with a chiller.
