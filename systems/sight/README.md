# System 6: `sight` — Hardware-Synced Stereo-Inertial SLAM & Navigation Head

**Role**: The high-level visual cortex that bolts onto `walker`, synchronizes stereo global-shutter frames to `brain`'s FPGA sub-microsecond exposure trigger, builds real-time 3D obstacle maps, and streams `[vx, vy, wz]` velocity goals to `brain` for autonomous room navigation.

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
