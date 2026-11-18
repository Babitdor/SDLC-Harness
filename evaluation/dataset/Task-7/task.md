Hi — I've attached the requirements for our autonomous vehicle's driving mode controller.

Please build a SysML v2 state machine diagram for the driving mode controller. The system has the following states:

- **Idle**: Vehicle is powered on but stationary, awaiting driver input.
- **Active**: Vehicle is operational and ready to accept navigation commands.
- **Navigating**: Vehicle is following a planned route under autonomous control.
- **ObstacleAvoidance**: Vehicle has detected an obstacle and is executing an evasive or slowing manoeuvre.
- **Parked**: Vehicle has reached its destination and is secured.
- **EmergencyStop**: Vehicle has triggered an emergency braking sequence due to a critical fault or collision risk.

Transitions between states with guards:

| Transition | Source | Target | Guard |
|---|---|---|---|
| engineStart | Idle | Active | engineStarted == true |
| setDestination | Active | Navigating | routeValidated == true |
| obstacleDetected | Navigating | ObstacleAvoidance | obstacleDistance < 2.0 |
| obstacleCleared | ObstacleAvoidance | Navigating | obstacleDistance >= 5.0 |
| destinationReached | Navigating | Parked | atDestination == true |
| emergencyStop | *any state* | EmergencyStop | emergencyTriggered == true |
| manualReset | EmergencyStop | Idle | manualResetPerformed == true |
| wake | Parked | Idle | driverWake == true |

Use proper SysML v2 patterns following the Sensmetry Advent of SysML v2 Lesson 19 approach:
- Define each state with `state def`
- Define each transition with `transition def` including `from`, `to`, and `guard` clauses
- Create a `part def DrivingModeController` that owns the state machine
- Declare attributes on the part def for all guard condition variables
- Use the `state machine` body with `then ... -> ... by ...` syntax to wire transitions

Respect the constraints in the requirements doc (response time, fail-safe behaviour, sensor coverage, non-volatile logging).