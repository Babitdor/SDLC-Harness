# Morphological Box — Smart Greenhouse Control System

Document: MB-GH-027
Status: Concept selected

## 1. Function / Option Matrix

| Function | Option A | Option B | Option C |
|---|---|---|---|
| Climate control | HVAC with heat pump | Evaporative (pad-and-fan) cooling | Shade curtains |
| Irrigation | Drip irrigation in substrate | Hydroponic NFT | Aeroponics |
| Lighting | LED grow lights | High-pressure sodium lamps | Natural light with LED supplement |
| Sensing | Fixed sensor array | Mobile robot | Indoor drone |
| Control logic | PID control | Fuzzy logic | ML predictive control |

## 2. Option Characteristics

**Climate — heat pump HVAC.** Heats, cools and dehumidifies; highest electrical
demand. **Evaporative cooling.** Very efficient cooling, but it adds moisture and
cannot heat. **Shade curtains.** Reduce solar gain and night heat loss; no active
heating or cooling.

**Irrigation — drip in substrate.** Moisture-sensed per bed, low water use.
**NFT / aeroponics.** Very water-efficient; no substrate, so no substrate moisture
to sense; pump failure dries roots within hours.

**Lighting — LED.** About 3.0 µmol/J, so 150 µmol·m⁻²·s⁻¹ costs about 50 W/m².
**HPS.** About 1.8 µmol/J, so the same light costs about 85 W/m² and adds a
large heat load.

**Control — PID.** Well understood, tunable per loop. **ML predictive.** Can
anticipate weather, but needs at least one season of training data.

## 3. Known Incompatibilities

- Evaporative cooling cannot hold relative humidity at or below 80 % in humid
  weather, and cannot heat to 15 °C in winter; it cannot be the sole climate
  option.
- NFT and aeroponics have no substrate, so they are incompatible with
  substrate-moisture-based irrigation (REQ-003).
- HPS lighting at the required light level exceeds the 50 W/m² lighting power
  density (C4).
- ML predictive control has no training data in the first season.

## 4. Selected Concept

| Function | Selected | Reason |
|---|---|---|
| Climate | HVAC with heat pump | Heats in winter and dehumidifies (REQ-001, REQ-002) |
| Irrigation | Drip in substrate | Moisture-sensed irrigation (REQ-003) |
| Lighting | LED | Within 50 W/m² (C4) |
| Sensing | Fixed sensor array | Continuous coverage, no aisle traffic |
| Control | PID | No training data needed |
