# System 3: `power` — Smart Power Distribution, Soft Startup & Electronic Breaker Spine

Twelve motor-driver boards contain substantial bulk decoupling capacitance that momentarily acts like a short circuit when power is first applied, causing connector arcing and logic brownouts. System 3 (`power`) regulates a controlled pre-charge ramp on startup, implements a microsecond solid-state circuit breaker (**e-fuse**) interlocked with a physical emergency-stop (**E-stop**) switch, steps down a clean `5V` logic rail for `brain` and `sight`, and runs an **Extended Kalman Filter (`EKF`)** to track battery **State of Charge (`SoC`)** under dynamic motor loads.

## Locked Interface Contracts
- **Battery Input**: 6-cell series lithium-iron-phosphate pack (`6S LiFePO4`: `19.2V` nominal, `21.9V` max—non-volatile chemistry well below the `60V` touch-safe **SELV** limit).
- **Outputs**: Protected `21.9V` motor bus (individually current-monitored leg channels), regulated `5.0V / 4A` logic rail for `brain` and `sight`, hardware-wired physical mushroom E-stop loop (`< 5 µs` transistor gate cutoff independent of software), and `CAN-FD` Bus B (Node ID `13`, `100 Hz`) Pack Voltage / Current / State-of-Charge / Temperature telemetry with jumper-selectable `120 Ω` termination.

## Directory Layout
- `sim/` — Equivalent resistor-capacitor battery voltage-sag model (**Randles model**), startup capacitor-inrush circuit simulation (**SPICE**), and online `EKF` battery fuel-gauge estimator
- `pcb/` — 4-layer thick-copper (**2 oz**) Power & Safety Spine schematic, high-current layout, and parts list
- `firmware/` — Supervisor safety state machine, real-time `EKF` fuel gauge, and pre-trip **black-box** fault logger

## Reference Reading
- Gregory L. Plett, *Battery Management Systems, Vol. II: Equivalent-Circuit Methods*, Ch. 1–7
- Erickson & Maksimović, *Fundamentals of Power Electronics*, Ch. 1–6 (step-down buck converters & switching transients)
