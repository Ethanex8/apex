# System 5: `walker` — 4-Legged Autonomous Quadruped (Dynamics, Balance & Learned Locomotion)

System 5 (`walker`) integrates `brain`, `power`, and four articulated legs (`12×` `drive` actuators) into an untethered, `about 2.5 kg` indoor-safe quadruped. We first develop a model-based predictive balance controller, then train a resilient locomotion policy inside a 3D physics simulator (`MuJoCo`) across randomized terrain and external disturbances, and finally deploy the quantized policy natively onto the custom `RISC-V + MAC` processor so the robot stands, recovers from perturbations, and trots untethered.

## Locked Interface Contracts
- **Compute**: `brain` executes the floating-base velocity and height estimator (**Error-State Kalman Filter / `ESKF`**, fusing `1,000 Hz` inertial measurements with stance-foot kinematics), dual `5 Mbps` `CAN-FD` leg buses (`1,000 Hz`), joint safety envelopes, and the 16-bit integer-quantized `48 -> 128 -> 128 -> 12` walking network (`50 Hz`, `< 0.6 ms` via the custom `mac` instruction).
- **Safety Rig**: Tabletop `20×20 mm` aluminum overhead bungee gantry, physical mushroom `E-stop`, and current-limited bench power-supply testing prior to untethered `6S LiFePO4` operation.

## Directory Layout
- `sim/` — Full 12-joint (`12-DOF`) robot description (`URDF`/`MuJoCo`) model, floating-base `ESKF` estimator, receding-horizon force optimizer (**Convex Centroidal `MPC`**), and GPU-parallel reinforcement learning (**`MJX PPO`**) training pipeline
- `cad/` — Lightweight carbon/aluminum torso bay housing `brain`, `power`, battery, and `4×` `limb` mounts plus wire harnesses
- `firmware/` — `SysC` `ESKF` estimator, quantized neural policy weights and runner, and closed-loop `Verilator` hardware-to-physics co-simulation harness

## Reference Reading
- Russ Tedrake, *Underactuated Robotics*, Ch. 1–10
- Sutton & Barto, *Reinforcement Learning: An Introduction*
