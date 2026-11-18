Hi — I need you to build an internal block diagram (IBD) for an autonomous vehicle's sensor fusion system. The requirements are attached in source/requirements.md.

The system has these components with their real-world specifications:

- **LiDAR**: 360-degree field of view, 150m range, 10Hz scan rate
- **Camera**: 1920×1080 resolution, 60fps frame rate
- **Radar**: 77GHz operating frequency, 250m maximum range
- **SensorFusionProcessor**: NVIDIA Orin SoC, 16GB memory
- **PathPlanner**: Trajectory planning module
- **VehicleController**: CAN bus actuation interface

The sensors feed data to the fusion processor, which outputs a fused object list to the path planner, which sends trajectory commands to the vehicle controller.

Please produce a proper SysML v2 IBD with:

- `item def` for data types: PointCloudData, ImageData, RadarData, FusedObjectList, TrajectoryCommand
- `port def` with direction modifiers (e.g., `out item pointCloud : PointCloudData;`)
- `part def` for each component with realistic attributes
- `connect` statements wiring ports together
- `flow` statements for item flows on connections
- Conjugate ports with `~` where needed
- Proper imports from ScalarValues and ISQ for SI units
