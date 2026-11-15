# System 4: `limb` — 3-Joint Force-Controlled Leg & Tabletop Hopping Stand

Before scaling to twelve joints, three `drive` actuators are integrated into a single 3-DOF robotic leg mounted on a linear test rail. Running control firmware compiled by `SysC` on `brain`, the leg cancels its own gravitational torque, cushions impacts as a virtual spring-damper, and executes cyclic vertical hopping—before transferring directly onto the quadruped chassis as Front-Left Leg #1.

## Locked Interface Contracts
- **Actuation**: `3×` `drive` actuators per leg (**3 Degrees of Freedom / `3-DOF`**: hip abduction/adduction roll, hip flexion/extension pitch, and knee pitch driven via a low-inertia belt or linkage) controlled over `brain`'s `CAN-FD` Bus A at `1,000 Hz`.
- **Control Software**: Written in `SysC` and executed natively on `brain` (3D rigid-body screw geometry / `SE(3)` Product-of-Exponentials, foot force-to-joint-torque mapping $\tau = J^\top F$, 3D **Cartesian impedance** control, sensorless momentum touchdown detection, and energy-regulated **Raibert hopping**).

## Directory Layout
- `sim/` — 3-joint forward/inverse kinematics, fast recursive gravity and inertia solver (**`RNEA`**), and `MuJoCo` vertical-rail hopping physics simulation
- `cad/` — Low-inertia leg links, lightweight carbon-fiber (`CF`) tube adapters, compliant flexible-polymer (`TPU`) spherical foot, landing impact stress checks (`FEA`), and tabletop `20×20 mm` slotted-aluminum (`2020`) linear test rail
- `firmware/` — `SysC` 1,000 Hz leg kinematics, Cartesian impedance, and hopping controller executing on `brain`

## Reference Reading
- Lynch & Park, *Modern Robotics: Mechanics, Planning, and Control*, Ch. 1–8
