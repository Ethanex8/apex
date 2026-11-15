# System 2: `drive` — Force-Controlled Brushless Motor Driver & 8:1 Gearbox

System 2 (`drive`) pairs a flat pancake brushless motor with a custom `24V` inverter board and an `8:1` low-backlash planetary gearbox. Regulating coil current—and therefore mechanical torque—at `20 kHz` via **Field-Oriented Control (`FOC`)**, it turns each joint into a backdrivable, finger-safe (`< 2.5 N·m`) programmable spring and damper. A single actuator unit is built and verified here; twelve identical units actuate the full quadruped.

## Locked Interface Contracts
- **Power Input**: `19.2V` nominal (`21.9V` max, 6-cell `LiFePO4` touch-safe **SELV** battery bus) via daisy-chained XT30/Micro-Fit power connectors.
- **Control Bus**: `5 Mbps` differential motor bus (**CAN-FD**) with jumper-selectable `120 Ω` end-of-line termination (`JP_TERM`, closed only on the final distal actuator of each bus trunk) matching `brain`'s packet layout (`q_des`, `dq_des`, spring gain `kp`, damper gain `kd`, feedforward torque `tau_ff` ↔ measured angle `q`, speed `dq`, torque current `i_q`, temperature `temp`, and `fault` flags at `1,000 Hz` per leg bus).
- **Mechanics**: `3508`/`4006` flat pancake brushless motor (**BLDC**) paired with an `8:1` low-friction, low-backlash planetary or cycloidal gearbox fabricated in industrial powder-fused nylon (`MJF PA12`), a milled (`CNC`) aluminum motor carrier, and a `14-bit` contactless magnetic angle encoder (`AS5047P`). Keeping the reduction ratio modest (`8:1`) allows ground forces to transmit back through the gear train so the actuator senses contact directly without fragile foot force sensors (**quasi-direct-drive / `QDD`**).

## Directory Layout
- `sim/` — Brushless motor differential equations in rotating magnetic coordinates (`dq0`), hexagonal switching modulator (**Space-Vector PWM / `SVPWM`**), and `20 kHz` current-loop simulator
- `pcb/` — 4-layer `24V / 30A` 3-phase transistor bridge (**inverter**) schematic, copper layout, and bill of materials (`STM32G4` microcontroller, `10V`/`5V`/`3.3V` rails, `TCAN1044V` bus transceiver, and precision current-sense amplifiers)
- `firmware/` — Bare-metal `20 kHz` interrupt firmware synchronized to switching valleys (**ADC-injected FOC**), magnetic encoder linearization table, cogging-torque compensation (**anticogging**), and `CAN-FD` packet handler
- `cad/` — Parametric `8:1` gearbox 3D geometry, structural Finite Element Analysis (**`FEA`** via `CalculiX`), and factory-ready `STEP`/`STL` exports

## Reference Reading
- Sang-Hoon Kim, *Electric Motor Control: DC, AC, and BLDC Motors*, Ch. 1–10
- Budynas & Nisbett, *Shigley's Mechanical Engineering Design* (gear tooth stress, bearings, mechanical fits)
