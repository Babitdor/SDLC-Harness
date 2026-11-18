# Morphological Box — DC Fast-Charging Network

Document: MB-EVN-029
Status: Concept selected

## 1. Function / Option Matrix

| Function | Option A | Option B | Option C |
|---|---|---|---|
| Connector standard | CCS1 | CHAdeMO | SAE J3400 (NACS) |
| Power delivery | Unidirectional | Bidirectional (V2G) | — |
| Authorisation | RFID card | Mobile app | ISO 15118 Plug & Charge |
| Billing | Per kWh | Per minute | Subscription |
| Grid integration | Passive | Active demand response | — |

## 2. Option Characteristics

**Connectors — CCS1.** The established DC standard in North America. **SAE J3400.**
The connector most new North American vehicles are adopting. **CHAdeMO.** A
declining installed base in North America.

**Power — bidirectional.** Enables V2G revenue and grid services; requires ISO
15118-20 in the vehicle and charger, OCPP 2.1 at the CSMS, and UL 1741 SB
certification because the site then exports to the grid.

**Authorisation — mobile app.** Rich user experience; excludes users without the
app. **Plug & Charge.** No user action; needs ISO 15118 certificates in the
vehicle. **RFID.** Simple; cards must be issued.

**Billing — per kWh.** Transparent and consistent with metering. **Per minute.**
Simple, but the price per unit of energy varies with each vehicle's charging rate.

## 3. Known Incompatibilities

- Bidirectional power delivery requires ISO 15118-20 and OCPP 2.1; it cannot be
  controlled over OCPP 2.0.1 alone.
- CHAdeMO-only sites cannot serve the CCS1 and J3400 fleet in this market.
- Per-kWh billing of V2G sessions requires metering in both directions.

## 4. Selected Concept

| Function | Selected | Reason |
|---|---|---|
| Connectors | CCS1 + SAE J3400 | Covers the North American fleet |
| Power delivery | Bidirectional (V2G) | Grid services revenue |
| Authorisation | Mobile app + Plug & Charge | App for all vehicles; seamless for ISO 15118 vehicles |
| Billing | Per kWh (net of export) | Transparent; supports V2G settlement |
| Grid integration | Active demand response | OpenADR programme participation |
