# System 2: `drive` — Force-Controlled Brushless Motor Driver & 8:1 Gearbox (Electric Muscle)

**In Plain English**: Cheap hobby servos blindly jam to an angle and snap gears. Here we pair a strong drone-style brushless motor with our own 24V motor-driver board that regulates exact current (= exact physical force) 20,000 times a second, turning each joint into a finger-safe (`< 2.5 N·m`) programmable spring and shock absorber. One unit is built here; 12 identical units power the full robot.

## Locked Interface Contracts
- **Power Input**: `19.2V` nominal (`21.9V` max `6S LiFePO4` SELV) via XT30/Molex Micro-Fit daisy-chain bus.
- **Control Bus**: `5 Mbps` CAN-FD matching `brain` framing (`q_des`, `dq_des`, `kp`, `kd`, `tau_ff` $\leftrightarrow$ `q`, `dq`, `i_q`, `temp`, `fault` at `1 kHz` per leg bus).
- **Mechanics**: `3508`/`4006` pancake BLDC + `8:1` low-backlash planetary/cycloidal gearbox in industrial MJF Nylon (`PA12`) + CNC aluminum carrier + `AS5047P` 14-bit magnetic encoder.

## Directory Layout
- `sim/` — PMSM $dq0$ motor model, SVPWM modulator & 20 kHz FOC loop simulator
- `pcb/` — 4-layer 24V 30A 3-phase inverter schematic, layout & BOM (`STM32G4` + `TCAN1044V` + current sense)
- `firmware/` — Bare-metal 20 kHz ADC-injected FOC, encoder linearization, anticogging & CAN-FD handler
- `cad/` — Parametric 8:1 gearbox geometry, structural/contact FEA (`CalculiX`) & manufacturing STEP/STL exports

## Optional Reference Reading
- Sang-Hoon Kim, *Electric Motor Control: DC, AC, and BLDC Motors*, Ch. 1–10
- Budynas & Nisbett, *Shigley's Mechanical Engineering Design* (gear stress, bearings, fits)
