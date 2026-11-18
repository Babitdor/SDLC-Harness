Hi — I need you to build a SysML v2 verification case diagram for an autonomous emergency braking (AEB) system.

The system has the following requirements:
- REQ-001: The AEB system shall initiate emergency braking within 500 ms of its decision that a collision is imminent.
- REQ-002: The AEB system shall detect obstacles at a minimum range of 50 m.
- REQ-003: The AEB system shall bring the vehicle to a stop before contact with the detected obstacle, with at least 1 m clearance.

Verification case: AEB_Verification_001
This verification case verifies all three requirements (REQ-001, REQ-002, REQ-003).

For each requirement, specify:
- Test method (e.g., simulation, physical test, inspection)
- Test scenario description
- Pass/fail criteria

The test scenario is: obstacle placed 50 m ahead of the vehicle, traveling at 60 km/h.

Please model this as a proper SysML v2 model with:
1. `requirement def` for each requirement, each with a `subject` parameter, `doc` for the shall statement, and a `require constraint` with a formal constraint expression
2. A `verification case def` with a `subject` parameter, `verify` relationships linking to each requirement, and attributes for `testMethod`, `testScenario`, and `passCriteria`
3. Proper imports from the SysML v2 libraries (SI units, ScalarValues, VerificationCases)
4. A part usage that instantiates the verification case
