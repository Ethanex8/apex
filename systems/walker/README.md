# System 5: `walker` — 4-Legged Walking Robot Dog (Physics Balance + Simulator-Trained AI)

**In Plain English**: We combine `brain` + `power` + 4 legs (`12x` `drive` muscles) into a `~2.5 kg` living-room-safe robot dog. We train a neural walking policy inside a 3D physics simulator (`MuJoCo`) across thousands of randomized floors and shoves, then compile that neural brain directly onto your custom RISC-V+MAC processor so it stands, recovers from pushes, and trots untethered.

## Locked Interface Contracts
- **Compute**: `brain` runs the floating-base `ESKF` state estimator (`1 kHz` IMU + 12-joint kinematics), dual 5 Mbps CAN-FD spine (`1 kHz`), safety joint envelopes, and the `INT16`-quantized `48 -> 128 -> 128 -> 12` walking MLP (`50 Hz`, `< 0.6 ms` via `mac` instruction).
- **Safety Rig**: Tabletop 2020 aluminum bungee gantry + physical mushroom E-stop + PSU-first bring-up before untethered `6S LiFePO4` battery walking.

## Directory Layout
- `sim/` — Full 12-DOF URDF/MuJoCo model, floating-base `ESKF`, Convex Centroidal `MPC` & `MJX` `PPO` RL training pipeline
- `cad/` — Lightweight carbon/aluminum torso bay housing `brain`, `power`, battery & 4x `limb` mounts + wire harnesses
- `firmware/` — `SysC` `ESKF`, quantized neural policy weights/runner & closed-loop `Verilator` co-simulation harness

## Optional Reference Reading
- Russ Tedrake, *Underactuated Robotics*, Ch. 1–10
- Sutton & Barto, *Reinforcement Learning: An Introduction*
