# System 4: `limb` — 3-Joint Force-Controlled Leg & Tabletop Hopping Stand

**In Plain English**: Before building 12 joints, we bolt 3 `drive` electric muscles together into one complete robotic leg on a compact desk rail. Controlled by code compiled with your own `SysC` compiler on `brain`, the leg cancels its own weight, softens hard drops like a virtual spring-damper, and hops smoothly on its own—and that exact leg then moves straight onto the final robot as Front-Left Leg #1.

## Locked Interface Contracts
- **Actuation**: `3×` `drive` actuators per leg (**3 Degrees of Freedom / 3-DOF**: side-to-side hip roll, forward-back hip pitch, and knee pitch driven via a low-inertia belt or linkage) controlled over `brain`'s `CAN-FD` Bus A at `1,000 Hz`.
- **Control Software**: Written in your own `SysC` language and executed natively on `brain` (3D rigid-body screw geometry / `SE(3)` Product-of-Exponentials, foot force-to-joint-torque mapping $\tau = J^\top F$, virtual 3D spring-damper **Cartesian impedance**, sensorless momentum touchdown detection, and energy-regulated **Raibert hopping**).

## Directory Layout
- `sim/` — 3-joint forward/inverse kinematics, fast recursive gravity/inertia solver (**RNEA**), and `MuJoCo` vertical-rail hopping physics simulation
- `cad/` — Low-inertia leg links, lightweight carbon-fiber (`CF`) tube adapters, compliant flexible-polymer (`TPU`) spherical foot, landing impact stress checks (`FEA`), and tabletop `20×20 mm` slotted aluminum (`2020`) test rail
- `firmware/` — `SysC` 1,000 Hz leg kinematics, spring-damper impedance & hopping controller running on `brain`

## Optional Reference Reading
- Lynch & Park, *Modern Robotics: Mechanics, Planning, and Control*, Ch. 1–8
