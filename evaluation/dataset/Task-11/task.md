Hi — I need you to build a SysML v2 allocation diagram for an industrial robot arm system.

The system has the following functions:
- **PickAndPlace**: The overall function of picking an object and placing it at a target location. Inputs: object position, target position. Output: placement confirmation.
- **DetectObject**: Detect and locate an object using the vision system. Inputs: raw camera feed. Outputs: detected object position, object classification.
- **CalculateTrajectory**: Compute the motion path from current position to the object and to the target. Inputs: current pose, target pose, object position. Output: joint trajectory waypoints.
- **GripObject**: Actuate the end effector to grip the object securely. Inputs: grip command. Output: grip force feedback.
- **MoveToPosition**: Move the arm segments to achieve the desired position and orientation. Inputs: joint trajectory. Output: achieved pose.

The physical components are:
- **RoboticArm**, composed of:
  - **Base**: The fixed base of the arm (mass: 50 kg, material: cast iron)
  - **ArmSegment** (3×): The articulated arm segments (length: 0.5 m each, mass: 4 kg each including the distal joint drive)
  - **JointMotor** (6×): Servo drives for each joint (motor: 3.75 N·m at 3000 rpm; 100:1 harmonic reduction; rated output: 300 N·m at 30 rpm)
  - **EndEffector**: The gripper at the end of the arm (grip force: 80–100 N, opening: 0–100 mm, mass: 1.5 kg)
- **VisionSystem**, composed of:
  - **Camera**: Captures visual data of the workspace (resolution: 1920×1080 px, frame rate: 60 fps)
  - **ProcessingUnit**: Processes camera data to detect objects (processor: quad-core ARM, memory: 4 GB)
- **MotionController**: Controls joint motors to execute trajectories (control rate: 1 kHz, communication: EtherCAT)

Please model this as a proper SysML v2 model with:
1. `part def` definitions for all physical components with typed attributes using SI units
2. `action def` definitions for all functions with typed inputs and outputs
3. `allocate` statements mapping each function to the component(s) that perform it
4. Proper imports from the SysML v2 SI and ScalarValues libraries
5. A system context part that composes the top-level subsystems
