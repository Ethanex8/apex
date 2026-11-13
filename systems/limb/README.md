# System 4: `limb` — 3-DOF Torque-Controlled Leg & Vertical Jumping Hopper

**Role**: Bridges single-motor bench control (`drive`) to full-body locomotion (`walker`) by building and hopping a 3-DOF robotic leg on a compact tabletop 2020 linear-rail stand—**which then becomes Leg #1 of 4 with zero throwaway hardware.**

## Locked Interface Contracts
- **Actuation**: `3x` `drive` units (hip abduction/adduction, hip pitch, knee pitch via low-inertia belt/linkage transmission) controlled over `brain`'s CAN-FD Bus A at `1 kHz`.
- **Control Software**: Written in `SysC` and executed natively on `brain` (`SE(3)` PoE kinematics, foot Jacobian $\tau = J^\top F$, Cartesian impedance, momentum contact observer, and Raibert hopping loop).

## Directory Layout
- `sim/` — 3-DOF kinematics/RNEA Python library & MuJoCo vertical rail hopping simulation
- `cad/` — Low-inertia leg links, CF tube adapters, TPU foot, impact FEA & tabletop 2020 test rail
- `firmware/` — `SysC` 1 kHz leg kinematics, impedance & hopping controller running on `brain`

## Optional Reference Reading
- Lynch & Park, *Modern Robotics: Mechanics, Planning, and Control*, Ch. 1–8
