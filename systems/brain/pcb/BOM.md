# `brain` Phased Parts List (`BOM`) & Bench Tools (`~$290` Total)

All electronics run at touch-safe `< 22V` desktop voltages and use external factory surface-mount soldering (**turnkey PCBA** at JLCPCB) so no solder-paste reflow happens indoors.

## Order 1 — Phase 1 (`brain-05`, Week 2) — `~$60`

| Item | Suggested Part / Spec | What It Does | Est. Cost |
| :--- | :--- | :--- | :---: |
| Programmable Logic Dev Kit | **Sipeed Tang Primer 20K Dock + Core Plug-In Module (`SOM`)** (`GW2A-LV18PG256C8/I7`) | Weeks 1–10 CPU bring-up on the starter Dock; later you unplug the exact same FPGA compute card (`SODIMM-204` edge connector) and snap it onto your custom 6-layer Spine board | \$45 |
| USB Logic Analyzer | 24 MHz 8-channel `FX2LP` digital capture pod (works with open-source `PulseView`/`Sigrok`) | Records real 0/3.3V wire waveforms to verify serial console (`UART`), motion sensor (`SPI`), motor bus (`CAN-FD`), and `< 2 µs` real-time task jitter | \$15 |

## Order 2 — Phase 4 (`brain-23`, Week 6–7) — `~$230`

| Item | Suggested Part / Spec | What It Does | Est. Cost |
| :--- | :--- | :--- | :---: |
| Custom 6-Layer Spine Board (2× factory-assembled) | JLCPCB `JLC06161H-3313` 6-layer `50 Ω` signal-matched (**controlled-impedance**) board + factory soldering (`TPS563201` 3.3V step-down buck regulator, `W9825G6KH-6` 32 MB external dynamic RAM, `W25Q128JVSIQ` 16 MB persistent Flash, dual `TCAN1044V` differential motor-bus drivers, `ICM-42688-P` 6-axis motion sensor, `CP2102N`/`CH340C` USB-serial bridge, `SODIMM-204` FPGA socket, and edge coax `SMA` test-trace coupons) | Your custom robot motherboard, plus two built-in coax test tracks so you can measure real high-speed copper trace impedance on your desk (manufactured in parallel while Phases 5–7 run in simulation) | ~\$115 |
| Vector Network Analyzer | **LiteVNA 64** (`50 kHz – 6.3 GHz`) + `SMA` Open/Short/Load calibration plugs + 1× coax jumper | Sends radio-frequency sweeps into the board's `SMA` test coupons and transforms echoes into an impedance-vs-distance plot (**Time-Domain Reflectometry / TDR**) | ~\$115 |

> [!TIP]
> **Reusable Core Bench Instruments (Order in Month 4 before `drive`/`power`, if not already owned — `~$310–$540`)**:
> 4-channel `70–100 MHz` oscilloscope for viewing fast analog voltages (`~$160–$390`), `30V/10A` current-limited bench power supply so wiring mistakes safely hit a current cap instead of smoking parts (`~$55`), and a `Pinecil` USB-C soldering iron + multimeter + wire crimpers for harness plugs (`~$95`).
