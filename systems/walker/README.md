# System 5: `walker` — 4-Legged Walking Robot Dog (Physics Balance + Simulator-Trained AI)

**In Plain English**: We combine `brain` + `power` + 4 legs (`12×` `drive` muscles) into a `~2.5 kg` living-room-safe robot dog. We first build a model-based predictive balance controller, then train a resilient neural walking policy inside a 3D physics simulator (`MuJoCo`) across thousands of randomized floors and shoves, and finally compile that neural policy directly onto your custom `RISC-V + MAC` processor so the robot stands, recovers from pushes, and trots untethered.

## Locked Interface Contracts
- **Compute**: `brain` runs the body velocity/height estimator (**floating-base Error-State Kalman Filter / ESKF**, fusing `1,000 Hz` motion-sensor accelerations with planted-foot geometry), dual `5 Mbps` `CAN-FD` leg buses (`1,000 Hz`), joint safety envelopes, and the 16-bit integer-quantized `48 -> 128 -> 128 -> 12` walking network (`50 Hz`, `< 0.6 ms` via your custom `mac` instruction).
- **Safety Rig**: Tabletop `20×20 mm` aluminum overhead bungee gantry + physical mushroom `E-stop` + current-limited bench power-supply testing before untethered `6S LiFePO4` battery walking.

## Directory Layout
- `sim/` — Full 12-joint (`12-DOF`) standard robot description (`URDF`/`MuJoCo`) model, floating-base `ESKF` estimator, receding-horizon force optimizer (**Convex Centroidal MPC**), and GPU-parallel reinforcement learning (**MJX PPO**) training pipeline
- `cad/` — Lightweight carbon/aluminum torso bay housing `brain`, `power`, battery & `4×` `limb` mounts + wire harnesses
- `firmware/` — `SysC` `ESKF` estimator, quantized neural policy weights/runner & closed-loop `Verilator` hardware-to-physics co-simulation harness

## Optional Reference Reading
- Russ Tedrake, *Underactuated Robotics*, Ch. 1–10
- Sutton & Barto, *Reinforcement Learning: An Introduction*
