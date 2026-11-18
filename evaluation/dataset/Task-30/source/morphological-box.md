# Morphological Box — Active Medical Cold-Chain Container

Document: MB-CC-030
Status: Concept selected

## 1. Function / Option Matrix

| Function | Option A | Option B | Option C |
|---|---|---|---|
| Cooling | Compressor | Thermoelectric (Peltier) | Phase-change material |
| Insulation | Vacuum insulation panels | Polyurethane foam | Aerogel |
| Monitoring | BLE data logger | Cellular IoT | Satellite |
| Power | Li-ion battery with external supply | Solar + battery | Vehicle power only |
| Packaging | Foam insert | Custom tray | Vacuum-sealed pouch |

## 2. Option Characteristics

**Cooling — compressor.** COP around 1.5 at 43 °C ambient; holds 2–8 °C
indefinitely with power; needs defrost. **Thermoelectric.** Solid-state and
silent; COP well below 1, so battery life is short. **Phase-change material.** No
power needed; hold time fixed by the PCM mass, and it must be pre-conditioned.

**Insulation — vacuum panels.** Thermal conductivity around 0.005 W/m·K, so
thin walls leave more payload volume; a puncture destroys the panel's
performance. **Polyurethane.** Robust and cheap; walls about five times thicker
for the same heat leak.

**Monitoring — cellular IoT.** Real-time alerts wherever there is coverage.
**BLE logger.** Data only when a phone is nearby; no real-time alert.
**Satellite.** Global coverage at higher cost and power.

## 3. Known Incompatibilities

- A BLE logger cannot send a remote alert within 60 s while out of phone range
  (REQ-006).
- Phase-change cooling cannot hold 2–8 °C for 48 hours at 43 °C within 30 kg and
  60 × 40 × 40 cm.
- Polyurethane walls thick enough for the heat leak leave too little internal
  volume for 200 vials within C2.
- Vehicle power alone cannot meet the 4-hour backup requirement (REQ-NF-004).

## 4. Selected Concept

| Function | Selected | Reason |
|---|---|---|
| Cooling | Compressor | 48 h at 43 °C with external power (REQ-001) |
| Insulation | Vacuum insulation panels | Heat leak and volume within C2 |
| Monitoring | Cellular IoT | Remote alert within 60 s (REQ-006) |
| Power | Li-ion battery with external supply | 4 h backup (REQ-NF-004) |
| Packaging | Custom tray | 200 vials, removable (REQ-007) |
