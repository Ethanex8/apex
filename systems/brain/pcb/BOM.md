# `brain` Phased Bill of Materials (`BOM`) & Bench Instruments (About \$290 Total)

All electronics operate at touch-safe `< 22V` desktop voltages and use external factory surface-mount assembly (**turnkey PCBA** at JLCPCB) so no solder-paste reflow takes place indoors.

## Order 1 — Phase 1 (`brain-05`, Week 2) — About \$60

| Item | Suggested Part / Spec | Purpose | Est. Cost |
| :--- | :--- | :--- | :---: |
| Programmable Logic Dev Kit | **Sipeed Tang Primer 20K Dock + Core Plug-In Module (`SOM`)** (`GW2A-LV18PG256C8/I7`) | Weeks 1–10 CPU bring-up on the starter Dock; the same FPGA compute module (`SODIMM-204` edge connector) later transfers directly onto the custom 6-layer Spine board | \$45 |
| USB Logic Analyzer | 24 MHz 8-channel `FX2LP` digital capture pod (compatible with `PulseView`/`Sigrok`) | Captures live `0/3.3V` bus waveforms to verify `UART`, `SPI`, `CAN-FD`, and `< 2 µs` real-time task jitter | \$15 |

## Order 2 — Phase 4 (`brain-23`, Week 6–7) — About \$230

| Item | Suggested Part / Spec | Purpose | Est. Cost |
| :--- | :--- | :--- | :---: |
| Custom 6-Layer Spine Board (2× factory-assembled) | JLCPCB `JLC06161H-3313` 6-layer `50 Ω` **controlled-impedance** PCB + factory assembly (`TPS563201` 3.3V buck regulator, `W9825G6KH-6` 32 MB SDRAM, `W25Q128JVSIQ` 16 MB QSPI Flash, dual `TCAN1044V` CAN-FD transceivers, `ICM-42688-P` 6-axis IMU, `CP2102N`/`CH340C` USB-UART bridge, `SODIMM-204` FPGA socket, and edge `SMA` test-trace coupons) | Custom robot carrier motherboard with two dedicated coax test traces for characterizing physical copper impedance on the bench (fabricated in parallel while Phases 5–7 run in simulation) | About \$115 |
| Vector Network Analyzer | **LiteVNA 64** (`50 kHz – 6.3 GHz`) + `SMA` Open/Short/Load calibration kit + 1× coax jumper | Sweeps RF frequency responses across the board's `SMA` test coupons and converts reflections into an impedance-vs-distance profile (**Time-Domain Reflectometry / `TDR`**) | About \$115 |

> [!TIP]
> **Reusable Bench Instruments (Order in Month 4 prior to `drive`/`power`, if not already on hand — about \$310–\$540)**:
> A 4-channel `70–100 MHz` oscilloscope for viewing fast analog switching edges (about \$160–\$390), a `30V/10A` current-limited bench power supply so wiring faults hit a safe current ceiling instead of damaging hardware (about \$55), and a `Pinecil` USB-C soldering iron, digital multimeter, and wire crimpers for harness assembly (about \$95).
