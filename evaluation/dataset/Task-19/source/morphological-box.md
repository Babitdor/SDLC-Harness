# Morphological Box — CBTC Train Control System

Document: MB-CBTC-019
Status: For evaluation — no option selected

| Function | Option 1 | Option 2 | Option 3 |
|---|---|---|---|
| **Train Detection** | Axle counters on each track segment | Track circuits (audio-frequency jointless) | Odometry + radio position reports (CBTC native) |
| **Speed Enforcement** | Onboard ATP with continuous speed supervision | Coded track circuits with cab signalling | Balise-based intermittent speed check (PZB-style) |
| **Door Control** | Platform screen doors (PSD) interlocked with train doors | Train-hosted door supervision with zero-speed interlock | Centralised door release from zone controller |
| **Interlocking** | Centralised electronic interlocking (CEI) | Distributed object controllers at each switch | Relay-based interlocking (legacy fallback) |
| **Radio Communication** | LTE / 4G private network for CBTC data | Wi-Fi 6 mesh along the guideway | Leaky-feeder cable in tunnels |
| **Degraded Mode** | Line-of-sight operation at restricted speed (25 km/h) | Fallback to fixed-block signalling with axle counters | Manual block working with paper train orders |

## Option Characteristics

**Train detection — axle counters.** Robust, independent of train radio; the usual
secondary detection under CBTC. **Track circuits.** Also detect some broken rails;
more trackside equipment and maintenance. **Radio position only.** Cheapest; no
detection of non-communicating trains.

**Speed enforcement — continuous onboard ATP.** Native to CBTC, supports moving-block
headways. **Coded track circuits.** Fixed-block; headway limited by block length.
**Intermittent balises.** Supervision only at balise locations.

**Door control — platform screen doors.** Highest platform safety, needs precise
stopping and PSD interlocking. **Train-hosted supervision.** No platform equipment.

**Radio — private LTE.** Carrier-grade, QoS for CBTC; licensed spectrum needed.
**Wi-Fi mesh.** Unlicensed and cheap; interference risk. **Leaky feeder.** Reliable
tunnel coverage; used with another radio outside tunnels.

**Interlocking — CEI.** Single site to maintain. **Distributed object controllers.**
Less cabling. **Relay interlocking.** Legacy; hard to integrate with CBTC.

## Known Incompatibilities

- Radio position reports alone cannot detect a failed, non-communicating train, so
  they cannot support the degraded mode (REQ-010) without secondary detection.
- Coded track circuits and intermittent balises are fixed-block methods and cannot
  deliver a 90 s headway (C1) on this line as reliably as continuous CBTC.
- Relay interlocking cannot meet the logging requirement (REQ-009) without
  additional monitoring equipment.
- Wi-Fi mesh alone gives no assurance of the 99.99 % link success rate
  (REQ-NF-003) in the 12 km of tunnel (C10).
