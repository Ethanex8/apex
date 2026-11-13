# System 3: `power` — Smart Power Distribution, Soft Startup & Electronic Breaker Spine

**In Plain English**: Twelve motor-driver boards contain large charge-smoothing capacitors that act like empty dead shorts for a split second when first plugged in—causing connector sparks or crashing your CPU. This board gently charges the motor bus through a pre-charge limiter on boot, acts as a microsecond solid-state circuit breaker (**e-fuse**) wired to a big red emergency-stop (**E-stop**) button, regulates a clean `5V` rail for `brain` and `sight`, and runs a statistical filter (**Extended Kalman Filter / EKF**) to track remaining battery percentage (**State of Charge / SoC**) accurately even under heavy motor spikes.

## Locked Interface Contracts
- **Battery Input**: 6-cell series lithium-iron-phosphate pack (`6S LiFePO4`: `19.2V` nominal, `21.9V` max—non-volatile chemistry well under the `60V` touch-safe **SELV** limit).
- **Outputs**: Protected `21.9V` motor bus (individually current-monitored leg channels), clean step-down `5.0V / 4A` logic rail for `brain` and `sight`, hardware-wired physical mushroom E-stop loop (`< 5 µs` transistor gate cutoff independent of software), and `CAN-FD` Pack Voltage / Current / State-of-Charge / Temperature telemetry.

## Directory Layout
- `sim/` — Equivalent resistor-capacitor battery voltage-sag model (**Randles model**), startup capacitor-inrush circuit simulation (**SPICE**), and online `EKF` battery fuel-gauge estimator
- `pcb/` — 4-layer thick-copper (**2 oz**) Power & Safety Spine schematic, high-current layout & parts list
- `firmware/` — Supervisor safety state machine, real-time `EKF` fuel gauge, and pre-trip flight-recorder (**black-box**) fault logger

## Optional Reference Reading
- Gregory L. Plett, *Battery Management Systems, Vol. II: Equivalent-Circuit Methods*, Ch. 1–7
- Erickson & Maksimović, *Fundamentals of Power Electronics*, Ch. 1–6 (step-down buck converters & switching transients)
