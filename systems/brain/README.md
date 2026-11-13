# System 1: `brain` — Custom CPU on FPGA, 6-Layer Circuit Board, C Compiler & Real-Time OS

**In Plain English**: You design your own processor chip (RISC-V + a neural multiply-add instruction) in code, load it onto a reprogrammable FPGA chip, plug it into a custom 6-layer circuit board with 32 MB of RAM, and run your own from-scratch C compiler and strict-deadline Real-Time OS. It works standalone as a custom computer and becomes the spinal cord + walking brain of the final robot.

## Target Architecture & Memory Map

- **CPU Core**: 5-stage pipelined processor implementing the base 32-bit RISC-V integer instruction set + hardware multiply/divide (`RV32IM`), Control and Status Registers for traps, cycle counters, and privilege handling (`Zicsr`), and a custom packed dual-16-bit multiply-accumulate instruction (`Xapex mac` in RISC-V's open `custom-0` opcode `0x0B`), running at `50–100 MHz` on a Gowin `GW2A-LV18PG256C8/I7` programmable-logic (**FPGA**) chip.
- **Memory Map** *(everything—memory chips and hardware I/O ports alike—is accessed via ordinary 32-bit pointer reads and writes at fixed addresses, called **Memory-Mapped I/O / MMIO**)*:
  - `0x0000_0000` – `0x0000_3FFF`: **On-chip Boot ROM (`16 KB`)** — read-only startup code baked into the FPGA bitstream that initializes external Flash/RAM and jumps to your OS image.
  - `0x1000_0000` – `0x1000_FFFF`: **On-chip Block RAM (`BRAM`, `64 KB`)** — ultra-fast static SRAM inside the FPGA fabric with zero wait states, used for strict-deadline OS stacks and hot neural-network weights.
  - `0x2000_0000` – `0x20FF_FFFF`: **Quad-SPI Non-Volatile Flash (`QSPI NOR`, `16 MB`, `W25Q128JVSIQ`)** — persistent storage chip where compiled code lives when power is off, mapped into address space for direct reads (**Execute-In-Place / XIP**) or fast block copies (**DMA**).
  - `0x4000_0000` – `0x41FF_FFFF`: **External 16-bit Dynamic RAM (`SDR SDRAM`, `32 MB`, `W9825G6KH-6`)** — high-capacity off-chip memory storing each bit in a tiny leaking capacitor that our controller must periodically recharge (**refresh**) every `64 ms`.
  - `0x8000_0000`: **64-bit Hardware Cycle Timer & Alarm (`CLINT`)** — generates deterministic OS scheduler timer interrupts (`mtime` / `mtimecmp`).
  - `0x8001_0000`: **Serial Console Port (`UART0`)** — byte-level asynchronous serial port (`115200` or `2M` baud) with hardware transmit/receive buffers (**FIFOs**).
  - `0x8002_0000`: **Motion-Sensor Serial Master (`SPI0`)** — `10–24 MHz` synchronous serial controller talking to the `ICM-42688-P` 6-axis accelerometer + gyroscope (`IMU`).
  - `0x8003_0000`: **Motor Bus A Controller (`CAN-FD`)** — `5 Mbps` noise-immune differential bus driving Legs 1–2 (`6` joints).
  - `0x8004_0000`: **Motor Bus B Controller (`CAN-FD`)** — `5 Mbps` noise-immune differential bus driving Legs 3–4 (`6` joints).
  - `0x8005_0000`: **Sub-µs Camera Shutter Sync & Timestamp Latch** — sends crisp `3.3V` exposure triggers to `sight`'s stereo cameras while recording exact `mtime` clock ticks.
  - `0x8006_0000`: **General-Purpose I/O (`GPIO`)** — status LEDs and a hardware safety timeout (**watchdog**) reset.

## Graduation Demo

Boot directly from persistent `QSPI` Flash into `32 MB` `SDRAM` on your custom 6-layer Spine circuit board running three concurrent tasks compiled **entirely by your scratch `SysC` toolchain**:
1. **Task 0 (1,000 Hz Hard Real-Time)**: Reads the `ICM-42688-P` motion sensor, computes board tilt (**attitude filter**), and runs a proportional-integral-derivative (**PID**) balance loop with `< 2 µs` timing jitter verified on a USB logic analyzer.
2. **Task 1 (`ash` Interactive Serial Shell)**: Live debugging terminal supporting `ps` (tasks), `jitter` (latency histogram), `ipc` (instructions per cycle), `memtest` (32 MB RAM sweep), `imu`, `can`, and `peek`/`poke` (raw memory reads/writes).
3. **Task 2 (Background Neural Walking Network)**: Quantized `48 -> 128 -> 128 -> 12` quadruped walking network executing in `< 0.6 ms` via your custom `mac` instruction.

## Directory Layout

- `rtl/` — Synthesizable hardware-description code (**SystemVerilog RTL**: `core/`, `mem/`, `periph/`, `soc_top.sv`)
- `sim/` — Golden cycle-accurate Python CPU emulator (`RV32IM` + `Zicsr` + `Xapex`) & custom assembler/linker
- `tb/` — Automated testbenches (`Verilator` digital simulator + `Cocotb` + `pytest`) comparing hardware vs. emulator bit-for-bit
- `pcb/` — 6-layer (`JLC06161H-3313`) trace-impedance and power-network (**PDN**) solvers, KiCad schematics/layout, design-rule checklists & [BOM.md](./pcb/BOM.md)
- `toolchain/` — Scratch `SysC` C compiler (`lexer -> parser -> SSA-lite IR -> optimizer -> register allocator -> RV32IM+MAC machine code`)
- `rtos/` — Assembly boot entry (`crt0.S`), `QSPI` Flash bootloader, `trap.S` register context switcher, priority preemptive scheduler & device drivers
- `apps/` — `ash` shell, 1,000 Hz tilt/PID task, neural walking runner, and `memtest`

## Optional Reference Reading

- Harris & Harris, *Digital Design and Computer Architecture (RISC-V Edition)*, Ch. 1–8
- Clayton R. Paul, *Introduction to Electromagnetic Compatibility*, Ch. 1–11 (6-layer signal integrity & return paths)
- Cooper & Torczon, *Engineering a Compiler*, Ch. 1–13
- Cox, Kaashoek & Morris, *xv6: A Simple, Unix-Like Teaching Operating System (RISC-V)*
