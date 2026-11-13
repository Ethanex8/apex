# System 1: `brain` — Custom CPU on FPGA, 6-Layer Circuit Board, C Compiler & Real-Time OS

**In Plain English**: You design your own processor chip (RISC-V + a neural multiply-add instruction) in code, load it onto a reprogrammable FPGA chip, plug it into a custom 6-layer circuit board with 32 MB of RAM, and run your own from-scratch C compiler and strict-deadline Real-Time OS. It works standalone as a custom computer and becomes the spinal cord + walking brain of the final robot.

## Target Architecture & Memory Map

- **CPU Core**: 5-stage pipelined `RV32IM` + `Zicsr` + custom `Xapex` fixed-point neural `mac` unit (`custom-0` opcode `0x0B`), running at `50–100 MHz` on Gowin `GW2A-LV18PG256C8/I7`.
- **Memory Map**:
  - `0x0000_0000` – `0x0000_3FFF`: On-chip Boot ROM (`16 KB`, initializes QSPI & SDRAM and jumps to user image)
  - `0x1000_0000` – `0x1000_FFFF`: On-chip SRAM / BRAM (`64 KB`, fast RTOS stacks & hot neural weights)
  - `0x2000_0000` – `0x20FF_FFFF`: QSPI NOR Flash XIP / DMA window (`16 MB`, `W25Q128JVSIQ`)
  - `0x4000_0000` – `0x41FF_FFFF`: External 16-bit SDR SDRAM (`32 MB`, `W9825G6KH-6`)
  - `0x8000_0000`: CLINT 64-bit Timer (`mtime`, `mtimecmp`)
  - `0x8001_0000`: UART0 (`115200` / `2M` baud TX/RX FIFO + status)
  - `0x8002_0000`: SPI0 Master (`ICM-42688-P` 6-axis IMU @ 10–24 MHz)
  - `0x8003_0000`: CAN-FD Bus A Controller (Legs 1–2 @ 5 Mbps)
  - `0x8004_0000`: CAN-FD Bus B Controller (Legs 3–4 @ 5 Mbps)
  - `0x8005_0000`: Sub-µs Camera Exposure Sync & Timestamp Generator
  - `0x8006_0000`: GPIO / User LEDs / Hardware Watchdog

## Graduation Demo

Boot from QSPI Flash into 32 MB SDRAM on your custom 6-layer Spine PCB running three concurrent tasks compiled **entirely by your scratch `SysC` toolchain**:
1. **Task 0 (1 kHz Hard Real-Time)**: `ICM-42688-P` IMU attitude filter + PID loop with `< 2 µs` interrupt jitter verified on logic analyzer.
2. **Task 1 (`ash` Interactive UART Shell)**: `ps`, `jitter`, `ipc`, `memtest`, `imu`, `can`, `peek`/`poke`.
3. **Task 2 (Background Neural Cerebellum)**: Quantized `48 -> 128 -> 128 -> 12` quadruped walking MLP executing in `< 0.6 ms` via your custom `mac` instruction.

## Directory Layout

- `rtl/` — Synthesizable SystemVerilog modules (`core/`, `mem/`, `periph/`, `soc_top.sv`)
- `sim/` — Golden `RV32IM` + `Zicsr` + `Xapex` Python architectural oracle & custom assembler/linker
- `tb/` — `Verilator` + `Cocotb` + `pytest` differential and adversarial testbenches
- `pcb/` — 6-layer `JLC06161H-3313` impedance/PDN solver, KiCad schematics/layout, DRC checklists & [BOM.md](./pcb/BOM.md)
- `toolchain/` — Scratch `SysC` compiler (`lexer -> parser -> SSA-lite IR -> optimizer -> regalloc -> RV32IM+MAC codegen`)
- `rtos/` — `crt0.S`, QSPI bootloader, `trap.S` context switcher, priority preemptive scheduler & drivers
- `apps/` — `ash` shell, 1 kHz IMU/PID task, neural walking MLP runner, and `memtest`

## Optional Reference Reading

- Harris & Harris, *Digital Design and Computer Architecture (RISC-V Edition)*, Ch. 1–8
- Clayton R. Paul, *Introduction to Electromagnetic Compatibility*, Ch. 1–11 (6-layer signal integrity & return paths)
- Cooper & Torczon, *Engineering a Compiler*, Ch. 1–13
- Cox, Kaashoek & Morris, *xv6: A Simple, Unix-Like Teaching Operating System (RISC-V)*
