# System 6: `sight` — Synchronized Stereo Camera Eyes, 3D Room Mapping & Navigation Head

**In Plain English**: Two synchronized cameras (like left/right human eyes) measure 3D distance to walls and furniture, track the robot's position in a room by combining video with `brain`'s motion sensor, and send simple *"walk forward / turn left"* commands down to the spinal-cord CPU so the robot walks around obstacles on its own.

## Locked Interface Contracts
- **Hardware Sync & Link**: Receives `3.3V` sub-µs exposure trigger from `brain` (keeping IMU and stereo shutter phase-locked); streams CRC-16 framed `[vx, vy, wz]` velocity commands + heartbeat over `2 Mbps` UART / `10 MHz` SPI (`150 ms` watchdog fallback to zero velocity).
- **Power**: Regulated `5.0V / 4A` rail supplied by `power`.

## Directory Layout
- `sim/` — Stereo calibration, manifold `ESKF` Visual-Inertial Odometry (`VIO`), 2.5D obstacle grid & `A*`/`RRT*` planner
- `perception/` — Quantized lightweight obstacle/person detector & real-time local navigation node
- `cad/` — Dual `OV9281` stereo baseline mount + companion SBC/NPU head enclosure

## Optional Reference Reading
- Timothy D. Barfoot, *State Estimation for Robotics (2nd Ed.)*
- Peter Corke, *Robotics, Vision and Control (3rd Ed.)*, Ch. 10–14
