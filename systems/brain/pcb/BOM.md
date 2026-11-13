# `brain` Phased Bill of Materials & Bench Procurement (`~$290` Total)

All components target safe `< 22V` desktop bench operation and zero-fume turnkey PCBA assembly at JLCPCB.

## Order 1 — Phase 1 (`brain-05`, Week 2) — `~$60`

| Item | Suggested Part / Spec | Purpose | Est. Cost |
| :--- | :--- | :--- | :---: |
| FPGA Dev Kit | **Sipeed Tang Primer 20K Dock + Core SOM** (`GW2A-LV18PG256C8/I7`) | Weeks 1–10 RTL bring-up on Dock; exact same `SODIMM-204` SOM plugs onto custom 6-layer Spine PCB later | \$45 |
| USB Logic Analyzer | 24 MHz 8-channel FX2LP analyzer (PulseView/Sigrok compatible) | Capturing UART, SPI IMU, CAN-FD, and 1 kHz RTOS jitter traces | \$15 |

## Order 2 — Phase 4 (`brain-23`, Week 6–7) — `~$230`

| Item | Suggested Part / Spec | Purpose | Est. Cost |
| :--- | :--- | :--- | :---: |
| 6-Layer Spine PCBA (2x assembled) | JLCPCB `JLC06161H-3313` controlled-impedance `50 Ohm` 6-layer PCB + SMT assembly (`TPS563201` 3.3V buck, `W9825G6KH-6` 32MB SDRAM, `W25Q128JVSIQ` 16MB QSPI, Dual `TCAN1044V` CAN-FD, `ICM-42688-P` SPI IMU, `CP2102N`/`CH340C` USB-UART, `SODIMM-204` socket, edge-launch SMA TDR coupons) | Custom robot cerebellum carrier board + TDR signal-integrity metrology coupon (runs in fab during Phases 5–7) | ~\$115 |
| Vector Network Analyzer | **LiteVNA 64** (`50 kHz – 6.3 GHz`) + SMA Open/Short/Load cal kit + 1x coax jumper | Real-world Time-Domain Reflectometry ($Z_0(x)$) sweeps on the 6-layer SMA test coupons | ~\$115 |

> [!TIP]
> **Reusable Core Bench Instruments (Order in Month 4 before `drive`/`power`, if not already owned — `~$310–$540`)**:
> 4-channel 70–100 MHz oscilloscope (`~$160–$390`), 30V/10A current-limited bench power supply (`~$55`), Pinecil USB-C soldering iron + multimeter + JST/Molex crimpers (`~$95`).
