# System 2: `drive` — Force-Controlled Brushless Motor Driver & 8:1 Gearbox (Electric Muscle)

**In Plain English**: Cheap hobby servos blindly jam toward a target angle and snap plastic gears on uneven ground. Here we pair a strong drone-style brushless motor with our own 24V motor-driver board that regulates exact coil current (= exact physical torque) 20,000 times a second (**Field-Oriented Control / FOC**), turning each joint into a finger-safe (`< 2.5 N·m`) programmable spring and shock absorber. You build one unit here; 12 identical units power the full robot.

## Locked Interface Contracts
- **Power Input**: `19.2V` nominal (`21.9V` max, 6-cell `LiFePO4` touch-safe **SELV** battery bus) via daisy-chained XT30/Micro-Fit power connectors.
- **Control Bus**: `5 Mbps` noise-immune differential motor bus (**CAN-FD**) matching `brain`'s packet layout (`q_des`, `dq_des`, spring gain `kp`, damper gain `kd`, feedforward torque `tau_ff` ↔ measured angle `q`, speed `dq`, torque current `i_q`, temperature `temp`, and `fault` flags at `1,000 Hz` per leg bus).
- **Mechanics**: `3508`/`4006` flat pancake brushless motor (**BLDC**) + `8:1` low-friction, low-play (**low-backlash**) planetary or cycloidal gearbox printed in industrial powder-fused nylon (`MJF PA12`) + milled (`CNC`) aluminum motor carrier + `14-bit` contactless magnetic angle chip (`AS5047P`). Keeping the gear ratio modest (`8:1`) means a foot hitting the floor pushes straight back through the gears so the motor can *feel* contact forces without fragile foot force sensors (**quasi-direct-drive / QDD**).

## Directory Layout
- `sim/` — Brushless motor differential equations in rotating magnetic coordinates (`dq0`), hexagonal switching modulator (**Space-Vector PWM / SVPWM**), and `20 kHz` current-loop simulator
- `pcb/` — 4-layer `24V / 30A` 3-phase transistor bridge (**inverter**) schematic, copper layout & parts list (`STM32G4` microcontroller + `TCAN1044V` bus driver + precision current-sense amplifiers)
- `firmware/` — Bare-metal `20 kHz` interrupt firmware synchronized to switching valleys (**ADC-injected FOC**), magnetic encoder error lookup table, magnetic-notch smoothing (**anticogging**), and `CAN-FD` packet handler
- `cad/` — Parametric `8:1` gearbox 3D geometry, structural Finite Element Analysis (**FEA** via `CalculiX`), and factory-ready `STEP`/`STL` CAD exports

## Optional Reference Reading
- Sang-Hoon Kim, *Electric Motor Control: DC, AC, and BLDC Motors*, Ch. 1–10
- Budynas & Nisbett, *Shigley's Mechanical Engineering Design* (gear tooth stress, bearings, mechanical fits)
