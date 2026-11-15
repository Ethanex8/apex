# System 6: `sight` — Synchronized Stereo Vision, 3D Mapping & Autonomous Navigation

System 6 (`sight`) equips the quadruped with two synchronized monochrome cameras for stereo depth perception, fuses visual landmarks with inertial measurements from `brain` to track 3D pose, builds a local obstacle map, and streams bounded velocity commands to the real-time spinal controller for autonomous navigation.

## Locked Interface Contracts
- **Hardware Sync & Link**: Receives a `3.3V` sub-microsecond exposure trigger pulse from `brain` (keeping inertial samples and both camera shutters phase-locked); exchanges `1,000 Hz` `ICM-42688-P` inertial samples and `frame_seq` exposure timestamps (`brain -> sight`) alongside `CRC-16` framed `[vx, vy, wz]` velocity commands and heartbeat packets (`sight -> brain`) over `brain`'s dedicated `2 Mbps` `UART1` link (`150 ms` watchdog timeout falls back to zero velocity).
- **Compute Stack & First-Principles Autonomy**: `sight` runs on embedded Linux (zero-copy camera transfers via `V4L2 DMA` over high-speed `MIPI` ribbons, plus Wi-Fi telemetry) and a dedicated neural accelerator (**NPU**, e.g., `RPi 5 + Hailo` or `Jetson Orin Nano`) for hardware I/O and 8-bit integer (`INT8`) person/obstacle detection (`sight-16`). All spatial perception and planning algorithms—camera calibration, stereo depth matching, 3D manifold **Visual-Inertial Odometry (`VIO`)**, sparse **bundle adjustment**, loop closure, 3D occupancy mapping, and path planning—are derived and implemented directly from first principles.
- **Power**: Regulated `5.0V / 4A` logic rail supplied by `power`.

## Directory Layout
- `sim/` — Stereo lens calibration, 3D pose-manifold Kalman filter (`ESKF` `VIO`), rolling 2.5D elevation and 3D obstacle occupancy grid, and `A*`/`RRT*` path planner
- `perception/` — Quantized neural person/obstacle detector and real-time local navigation node
- `cad/` — Rigid stereo baseline bar holding two monochrome **global-shutter** `OV9281` cameras and companion vision-computer enclosure

## Reference Reading
- Timothy D. Barfoot, *State Estimation for Robotics (2nd Ed.)*
- Peter Corke, *Robotics, Vision and Control (3rd Ed.)*, Ch. 10–14
