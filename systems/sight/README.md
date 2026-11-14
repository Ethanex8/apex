# System 6: `sight` — Synchronized Stereo Camera Eyes, 3D Room Mapping & Navigation Head

**In Plain English**: Two synchronized cameras (like left and right human eyes) measure 3D distance to walls and furniture, track the robot's position through a room by fusing video with `brain`'s motion sensor, and send simple *"walk forward / turn left"* commands down to the spinal-cord CPU so the robot navigates around obstacles on its own.

## Locked Interface Contracts
- **Hardware Sync & Link**: Receives a `3.3V` sub-microsecond exposure trigger pulse from `brain` (keeping motion-sensor samples and both camera shutters strictly phase-locked); exchanges `1,000 Hz` `ICM-42688-P` inertial samples + `frame_seq` exposure timestamps (`brain -> sight`) and error-checked (`CRC-16`) `[vx, vy, wz]` velocity commands + heartbeat (`sight -> brain`) over `brain`'s dedicated `2 Mbps` `UART1` link (`150 ms` safety timeout falls back to zero velocity).
- **From-Scratch Spatial Math, Pragmatic Silicon Stack**: Because computer architecture, C compilation, and real-time OS design are built from scratch in `brain`, `sight` openly uses embedded Linux (zero-copy camera frame transfers via `V4L2 DMA` over high-speed `MIPI` ribbons, plus Wi-Fi telemetry) and a dedicated neural inference chip (**NPU**, e.g., `RPi 5 + Hailo` or `Jetson Orin Nano`) for hardware I/O and 8-bit integer (`INT8`) person/pet detection (`sight-16`), while prohibiting black-box robotics middleware (`no ROS`, `no ORB-SLAM`, `no Nav2`)—every lens calibration, stereo depth solver, 3D rotation/pose Kalman filter (**Visual-Inertial Odometry / VIO**), sparse map optimization (**bundle adjustment**), loop-closure, 3D obstacle grid, and path planner is derived and written from first principles.
- **Power**: Regulated `5.0V / 4A` logic rail supplied by `power`.

## Directory Layout
- `sim/` — Stereo lens calibration, 3D pose-manifold Kalman filter (`ESKF` `VIO`), rolling 2.5D floor-height obstacle grid & `A*`/`RRT*` path planner
- `perception/` — Quantized neural person/obstacle detector & real-time local navigation node
- `cad/` — Rigid stereo bar holding two monochrome simultaneous-exposure (**global-shutter**) `OV9281` cameras + companion vision computer head enclosure

## Optional Reference Reading
- Timothy D. Barfoot, *State Estimation for Robotics (2nd Ed.)*
- Peter Corke, *Robotics, Vision and Control (3rd Ed.)*, Ch. 10–14
