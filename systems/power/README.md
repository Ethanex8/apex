# System 3: `power` — Smart Power Distribution, Soft Startup & Electronic Breaker Spine

**In Plain English**: Twelve motors powering up at once draw a huge electrical surge that can spark connectors or brown out your CPU. This board gently pre-charges the motor bus on startup, acts as a microsecond electronic circuit breaker (`e-fuse`) wired to a big red E-stop button, provides clean `5V` logic power, and runs a smart statistical filter to track remaining battery percentage under spike loads.

## Locked Interface Contracts
- **Battery Input**: `6S LiFePO4` (`19.2V` nom, `21.9V` max, non-volatile chemistry, `< 22V` touch-safe SELV).
- **Outputs**: Protected `21.9V` bus (fused/monitored leg channels), regulated `5.0V / 4A` logic rail for `brain` and `sight`, isolated/referenced physical mushroom E-stop loop (`< 5 µs` gate turn-off), and CAN-FD Pack Voltage / Current / SoC / Temperature telemetry.

## Directory Layout
- `sim/` — Randles battery equivalent-circuit model, capacitive inrush SPICE sim & online EKF SoC estimator
- `pcb/` — 4-layer heavy-copper Power & Safety Spine schematic, layout & BOM
- `firmware/` — Supervisor protection state machine, online EKF & black-box fault logger

## Optional Reference Reading
- Gregory L. Plett, *Battery Management Systems, Vol. II: Equivalent-Circuit Methods*, Ch. 1–7
- Erickson & Maksimović, *Fundamentals of Power Electronics*, Ch. 1–6 (buck converters & switching transients)
