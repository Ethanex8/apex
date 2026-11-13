# System 5: `walker` — 12-DOF Dynamic Quadruped with Convex MPC & Sim-to-Real Neural Locomotion

**Role**: Full-system integration of `brain` + `power` + `4x limb` (`12x drive`) into a `~2.5 kg` desktop torque-controlled quadruped capable of standing, trotting, push recovery, and rough-terrain walking—running its GPU-trained neural walking policy natively on your custom `brain` RISC-V+`MAC` SoC.

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
