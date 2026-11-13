# System 2: `drive` — 24V Brushless FOC Servo PCB & Quasi-Direct-Drive Actuator

**Role**: Single torque-controlled robotic joint (`< 2.5 N·m` finger-safe backdrivable torque at `~2.5 kg` quadruped scale). `1x` built and tested here; `2x` more built in `limb` (Leg #1); `9x` batch-built in `walker` (`12x` total, zero throwaway hardware).

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
