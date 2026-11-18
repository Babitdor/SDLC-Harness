# Domain Knowledge Base — Standards & Design Rules

## Applicable Standards

| Standard | Title | Scope |
|---|---|---|
| ISO 10218-1:2025 | Robotics — Safety requirements — Part 1: Industrial robots | Robot manufacturer safety requirements |
| ISO 10218-2:2025 | Robotics — Safety requirements — Part 2: Industrial robot applications and robot cells | System integrator safety requirements; now includes the collaborative-operation content of ISO/TS 15066 |
| ISO/TS 15066:2016 | Collaborative robots — Safety requirements | Power- and force-limiting; content consolidated into ISO 10218-2:2025 |
| ANSI/A3 R15.06-2025 | American National Standard for Industrial Robots and Robot Systems — Safety Requirements | US adoption of ISO 10218:2025; replaces RIA R15.06-2012 |
| ISO 13849-1:2023 | Safety of machinery — Safety-related parts of control systems — Part 1: General principles for design | Performance Level (PL) determination for safety functions |
| ISO 13855:2024 | Safety of machinery — Positioning of safeguards with respect to the approach of the human body | Minimum distance calculation for safety devices |
| IEC 62061:2021 | Safety of machinery — Functional safety of safety-related control systems | SIL assignment for electrical/electronic safety systems |

## Design Rules

- **Safety-rated stop distance**: The stopping distance of the robot from maximum axis speed must not exceed 500 mm. Validate by dynamic simulation (e.g., ABB RobotStudio, KUKA Sim) before physical commissioning.
- **Minimum separation distance**: Per ISO 13855, calculate S = (K × T) + C where K = approach speed (2 000 mm/s where the resulting S ≤ 500 mm; 1 600 mm/s for whole-body approach where S > 500 mm), T = total stopping time (safety system + robot brake), C = intrusion distance. Use 1 600 mm/s for body approach.
- **Performance Level (PL)**: Safety functions (zone monitoring, emergency stop) shall achieve PL d, or the required level PLr determined by the risk assessment per ISO 13849-1. Use redundant architecture (dual-channel, cross-monitored).
- **Cycle time optimisation**: Minimise non-value-added motion by (a) overlapping robot and conveyor motion, (b) using shortest-path joint interpolation, (c) reducing tool-change time via parallel staging, (d) balancing workload across multiple robots.
- **Repeatability vs. accuracy**: Design for ±0.1 mm positioning repeatability at the tool centre point (TCP). Calibrate TCP after each tool change using a reference sphere and touch-off routine.
- **Vision inspection reliability**: Use diffuse on-axis lighting to minimise glare on metallic surfaces. Calibrate camera-to-robot transform with a grid target at least once per shift.
- **Conveyor synchronisation**: Use encoder-based tracking so the robot can pick parts on-the-fly (moving conveyor) rather than stop-and-pick, reducing cycle time by 15–25 %.
- **Tool changer maintenance**: Schedule pneumatic seal replacement every 100 000 cycles. Monitor tool-present sensors for early detection of mis-seat events.
