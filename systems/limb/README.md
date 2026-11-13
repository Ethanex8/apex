# System 4: `limb` — 3-Joint Force-Controlled Leg & Tabletop Hopping Stand

**In Plain English**: Before building 12 joints, we bolt 3 electric muscles together into one complete robotic leg on a compact desk rail. Controlled by code compiled with your own C compiler on `brain`, it learns to feel gravity, cushion drops softly, and hop on its own—and that exact leg then moves straight onto the final robot as Front-Left Leg #1.

## Locked Interface Contracts
- **Actuation**: `3x` `drive` units (hip abduction/adduction, hip pitch, knee pitch via low-inertia belt/linkage transmission) controlled over `brain`'s CAN-FD Bus A at `1 kHz`.
- **Control Software**: Written in `SysC` and executed natively on `brain` (`SE(3)` PoE kinematics, foot Jacobian $\tau = J^\top F$, Cartesian impedance, momentum contact observer, and Raibert hopping loop).

## Directory Layout
- `sim/` — 3-DOF kinematics/RNEA Python library & MuJoCo vertical rail hopping simulation
- `cad/` — Low-inertia leg links, CF tube adapters, TPU foot, impact FEA & tabletop 2020 test rail
- `firmware/` — `SysC` 1 kHz leg kinematics, impedance & hopping controller running on `brain`

## Optional Reference Reading
- Lynch & Park, *Modern Robotics: Mechanics, Planning, and Control*, Ch. 1–8
