# System 1: `brain` — Custom CPU on FPGA, 6-Layer Circuit Board, C Compiler & Real-Time OS

System 1 (`brain`) implements a custom 32-bit RISC-V processor extended with a neural multiply-accumulate instruction in SystemVerilog, synthesizes it onto a reprogrammable FPGA, integrates it onto a custom 6-layer circuit board with 32 MB of SDRAM, and runs a custom C compiler and preemptive Real-Time Operating System (`RTOS`). It operates as a standalone embedded computer and serves as the spinal cord and real-time locomotion controller of the final quadruped.

## Target Architecture & Memory Map

- **CPU Core**: 5-stage pipelined processor implementing the base 32-bit RISC-V integer instruction set and hardware multiply/divide (`RV32IM`), Control and Status Registers for traps, cycle counters, and privilege handling (`Zicsr`), and a custom packed dual-16-bit multiply-accumulate instruction (`Xapex mac` in RISC-V's `custom-0` opcode `0x0B` using an internal EX-stage saturating accumulator register so back-to-back dual-`int16` dot products execute at 1 cycle/instruction with a 2-read-port register file), running at `50–100 MHz` on a Gowin `GW2A-LV18PG256C8/I7` **Field-Programmable Gate Array (`FPGA`)**.
- **Memory Map** *(all memory arrays and hardware peripherals share a unified 32-bit address space accessed via standard load and store instructions — **Memory-Mapped I/O / `MMIO`**)*:
  - `0x0000_0000` – `0x0000_3FFF`: **On-chip Boot ROM (`16 KB`)** — read-only startup code baked into the FPGA bitstream that initializes external Flash and RAM before jumping to the operating system image.
  - `0x1000_0000` – `0x1000_FFFF`: **On-chip Block RAM (`BRAM`, `64 KB` via dual `32 KB` banks)** — single-cycle static SRAM inside the FPGA fabric, holding strict-deadline RTOS stacks and the `48.1 KB` (`24,064 × int16`) neural walking weight matrices for zero-wait-state `mac` execution.
  - `0x2000_0000` – `0x20FF_FFFF`: **Quad-SPI Non-Volatile Flash (`QSPI NOR`, `16 MB`, `W25Q128JVSIQ`)** — persistent storage chip retaining compiled firmware across power cycles, mapped for direct reads (**Execute-In-Place / `XIP`**) or block transfers (**`DMA`**).
  - `0x4000_0000` – `0x41FF_FFFF`: **External 16-bit Dynamic RAM (`SDR SDRAM`, `32 MB`, `W9825G6KH-6`)** — high-capacity off-chip memory storing each bit in a capacitive cell periodically recharged (**refreshed**) every `64 ms`.
  - `0x8000_0000`: **64-bit Hardware Cycle Timer & Alarm (`CLINT`)** — generates deterministic OS scheduler timer interrupts (`mtime` / `mtimecmp`).
  - `0x8001_0000`: **Serial Debug Console Port (`UART0`)** — asynchronous serial port (`115200` baud via onboard USB-UART bridge) with hardware transmit/receive buffers (**FIFOs**) dedicated to the interactive `ash` shell.
  - `0x8002_0000`: **Motion-Sensor Serial Master (`SPI0`)** — `10–24 MHz` synchronous serial controller polling the `ICM-42688-P` 6-axis accelerometer and gyroscope (`IMU`) at `1,000 Hz`.
  - `0x8003_0000`: **Motor Bus A Controller (`CAN-FD`)** — `5 Mbps` differential bus driving Front Legs 1–2 (`6` joints, Node IDs `1–6`).
  - `0x8004_0000`: **Motor Bus B Controller (`CAN-FD`)** — `5 Mbps` differential bus driving Rear Legs 3–4 (`6` joints, Node IDs `7–12`) plus `power` spine telemetry (Node ID `13`).
  - `0x8005_0000`: **Sub-µs Camera Shutter Sync, Timestamp Latch & High-Speed `sight` Link (`UART1`)** — triggers `3.3V` stereo camera exposures while latching exact `mtime` ticks, streaming `1,000 Hz` IMU and `frame_seq` telemetry (`brain -> sight`), and receiving `CRC-16` `[vx, vy, wz]` velocity commands (`sight -> brain`) at `2 Mbps`.
  - `0x8006_0000`: **General-Purpose I/O (`GPIO`)** — status LEDs and a hardware safety **watchdog** reset.

## Graduation Demo

Boot directly from persistent `QSPI` Flash into `32 MB` `SDRAM` on the custom 6-layer Spine circuit board running three concurrent tasks compiled by the custom `SysC` toolchain:
1. **Task 0 (1,000 Hz Hard Real-Time)**: Samples the `ICM-42688-P` inertial sensor, estimates board orientation (**attitude filter**), and executes a proportional-integral-derivative (**`PID`**) balance loop with `< 2 µs` timing jitter verified on a logic analyzer.
2. **Task 1 (`ash` Interactive Serial Shell)**: Live diagnostic shell supporting `ps` (tasks), `jitter` (latency histogram), `ipc` (instructions per cycle), `memtest` (32 MB RAM sweep), `imu`, `can`, and `peek`/`poke` (raw memory inspection).
3. **Task 2 (Background Neural Walking Network)**: Quantized `48 -> 128 -> 128 -> 12` quadruped locomotion network executing in `< 0.6 ms` via the custom `mac` instruction.

## Directory Layout

- `chapters/` — Parts I–III textbook chapters ([Chapter 1: Instruction Set Architecture & Fixed-Width Binary Arithmetic](./chapters/01_isa_and_binary_arithmetic.md))
- `rtl/` — Synthesizable hardware description (**SystemVerilog RTL**: `core/`, `mem/`, `periph/`, `soc_top.sv`)
- `sim/` — Golden cycle-accurate Python CPU emulator (`RV32IM` + `Zicsr` + `Xapex`) and assembler/linker
- `tb/` — Automated testbenches (`Verilator` + `Cocotb` + `pytest`) verifying hardware against the software oracle bit-for-bit
- `pcb/` — 6-layer (`JLC06161H-3313`) transmission-line and power-distribution (**`PDN`**) solvers, KiCad schematics and layout, design-rule checklists, and [BOM.md](./pcb/BOM.md)
- `toolchain/` — Custom `SysC` C compiler (`lexer -> parser -> SSA-lite IR -> optimizer -> register allocator -> RV32IM+MAC machine code`)
- `rtos/` — Assembly startup (`crt0.S`), `QSPI` Flash bootloader, `trap.S` context switcher, priority preemptive scheduler, and device drivers
- `apps/` — `ash` shell, 1,000 Hz tilt/PID task, neural walking runner, and `memtest`

## Reference Reading

- Harris & Harris, *Digital Design and Computer Architecture (RISC-V Edition)*, Ch. 1–8
- Clayton R. Paul, *Introduction to Electromagnetic Compatibility*, Ch. 1–11 (6-layer signal integrity & return paths)
- Cooper & Torczon, *Engineering a Compiler*, Ch. 1–13
- Cox, Kaashoek & Morris, *xv6: A Simple, Unix-Like Teaching Operating System (RISC-V)*
