# Custom Processor and Spine

System 1 (`brain`) builds a custom 32-bit processor implementing the open-standard **Reduced Instruction Set Computer, Fifth Generation** (RISC-V) architecture in the SystemVerilog hardware-description language, compiles it onto a reprogrammable logic chip (**Field-Programmable Gate Array**, or FPGA), and mounts it onto a custom 6-layer circuit board.
On top of that hardware, `brain` runs our custom minimal C-subset compiler (SysC) and a deterministic preemptive task scheduler (**Real-Time Operating System**, or RTOS), operating first as a standalone embedded computer and ultimately as the real-time spinal cord of the quadruped.

## Processor Architecture and Memory Map

Every memory array and hardware peripheral controller shares one unified 32-bit byte-addressed map accessed through ordinary load and store instructions (**Memory-Mapped Input/Output**, or MMIO).
The processor core and its mapped regions follow locked address and electrical contracts across simulation and silicon:

- **Processor Core**: A 5-stage pipelined processor (overlapping five instruction stages like an assembly line) implementing the 32-bit RISC-V base integer and hardware multiply/divide extensions (RV32IM).
  Dedicated **Control and Status Registers** (CSRs), accessed via the **Control and Status Register Instructions** (Zicsr) extension, hold cycle counters, interrupt masks, and fault or interrupt handler entry addresses (**trap vectors**).
  A custom packed two-lane 16-bit **Multiply-Accumulate** (MAC) instruction (`mac` in RISC-V's reserved custom-0 binary operation code `0x0B`), backed by a 32-bit **saturating** accumulator that clamps sums at signed min/max bounds instead of wrapping, runs neural dot products at one instruction per clock cycle on a Gowin GW2A-LV18PG256C8/I7 FPGA at 50 to 100 MHz.
- `0x0000_0000` to `0x0000_3FFF` — **Startup Memory** (16 KB): Non-writable startup storage (**Boot Read-Only Memory**, or Boot ROM) baked into the FPGA configuration image that initializes external memory before jumping to the operating system.
- `0x1000_0000` to `0x1000_FFFF` — **On-Chip Static Memory** (64 KB): Single-cycle internal **Static Random-Access Memory** (SRAM) organized as FPGA **Block RAM** (BRAM) across two 32 KB banks (allocated alongside the 16 KB Boot ROM from the FPGA's 103.5 KB total block-SRAM pool), holding real-time stacks and the 47.0 KB (24,064 signed 16-bit weights) walking network for single-cycle, zero-wait `mac` execution.
- `0x2000_0000` to `0x20FF_FFFF` — **Persistent Flash Storage** (16 MB): A 4-wire persistent flash chip (**Quad Serial Peripheral Interface**, or QSPI, Winbond W25Q128JVSIQ) retains firmware across power cycles and serves direct processor instruction fetches (**Execute-in-Place**, or XIP).
  A background hardware block-copy engine (**Direct Memory Access**, or DMA) also streams bulk weights and code from QSPI flash into main memory without tying up processor cycles.
- `0x4000_0000` to `0x41FF_FFFF` — **External Main Memory** (32 MB): High-capacity off-chip working memory (**Synchronous Dynamic Random-Access Memory**, or SDRAM, Winbond W9825G6KH-6) storing bits in microscopic capacitors periodically recharged every 64 ms.
- `0x8000_0000` — **Hardware Cycle Timer** (**Core-Local Interruptor**, or CLINT): Provides a 64-bit free-running tick counter (`mtime`) and alarm comparator (`mtimecmp`) that trigger deterministic scheduler interrupts.
- `0x8001_0000` — **Serial Debug Console** (**Universal Asynchronous Receiver-Transmitter**, or UART0): Runs at 115,200 bits per second over USB with hardware **First-In, First-Out** (FIFO) transmit and receive byte queues for the interactive `ash` shell.
- `0x8002_0000` — **Motion-Sensor Link** (**Serial Peripheral Interface**, or SPI0): A 10 to 24 MHz synchronous serial controller polling the ICM-42688-P 6-axis accelerometer and gyroscope (**Inertial Measurement Unit**, or IMU) at 1,000 Hz.
- `0x8003_0000` — **Front Motor Bus** (**Controller Area Network with Flexible Data-Rate**, or CAN-FD, Bus A): A 5 Mbps noise-immune differential bus driving Front Legs 1 and 2 (6 joints, Node IDs 1 to 6).
- `0x8004_0000` — **Rear Motor Bus** (CAN-FD Bus B): A 5 Mbps differential bus driving Rear Legs 3 and 4 (6 joints, Node IDs 7 to 12) plus `power` spine telemetry (Node ID 13).
- `0x8005_0000` — **Camera Sync and Vision Bridge** (UART1): Emits sub-microsecond 3.3 V stereo camera shutter pulses while latching exact `mtime` timestamps, streaming 1,000 Hz IMU frames to the stereo-vision head (`sight`), and receiving `[vx, vy, wz]` velocity commands protected by an error-detecting 16-bit checksum (**Cyclic Redundancy Check**, or CRC-16) at 2 Mbps.
- `0x8006_0000` — **Digital Status Pins** (**General-Purpose Input/Output**, or GPIO): Drives board status **Light-Emitting Diodes** (LEDs) and a hardware safety watchdog reset.

## Graduation Milestone

Before connecting any motor drives, `brain` is brought up and verified as a complete standalone desktop computer on its custom 6-layer Spine circuit board.
Booting directly from persistent QSPI flash into 32 MB SDRAM, the graduation build runs three concurrent tasks compiled by SysC:

1. **Hard Real-Time Control Loop** (1,000 Hz): Samples the ICM-42688-P IMU, estimates board tilt, and runs a **Proportional-Integral-Derivative** (PID) feedback controller with under 2 µs timing jitter verified on a logic analyzer.
2. **Interactive Diagnostic Shell** (`ash`): Provides live serial commands (`ps`, `jitter`, `ipc`, `memtest`, `imu`, `can`, `peek`, and `poke`) over UART0 without disturbing the 1,000 Hz control task.
3. **Quantized Locomotion Network**: Evaluates a compact scaled-integer (**quantized**) two-lane 16-bit neural policy with layer neuron widths $48 \to 128 \to 128 \to 12$ at 50 Hz in under 0.6 ms per tick using the custom `mac` instruction.

## Directory Layout

Source files under `systems/brain/` mirror the hardware-to-software dependency order of Parts I through III so simulation models, gate-level hardware, board layout, compiler passes, and kernel code stay cleanly separated.
Each subdirectory owns one layer of the stack:

- `chapters/` — Parts I to III textbook chapters, starting with [Chapter 1 — Instruction Set Architecture](./chapters/01_isa_and_binary_arithmetic.md).
- `rtl/` — Clocked digital hardware descriptions written at the **Register-Transfer Level** (RTL) in SystemVerilog (`core/`, `mem/`, `periph/`, and `soc_top.sv`).
- `sim/` — Instruction-accurate Python reference processor (`oracle.py`) and machine-code assembler and linker.
- `tb/` — Automated verification testbenches combining the open-source SystemVerilog simulator Verilator, the Cocotb Python hardware test runner, and `pytest` against `oracle.py`.
- `pcb/` — Six-layer (JLC06161H-3313 stackup) transmission-line and **Power Distribution Network** (PDN) solvers, circuit-board schematics and layout in KiCad, design-rule checks, and the component **Bill of Materials** (BOM) in [BOM.md](./pcb/BOM.md).
- `toolchain/` — Scratch SysC compiler lowering C source through lexical scanning, parsing, an internal representation where each temporary variable is assigned once (**Static Single-Assignment Intermediate Representation**, or SSA IR), register allocation, and RV32IM plus `mac` code generation.
- `rtos/` — Assembly startup (`crt0.S`), QSPI flash bootloader, `trap.S` context switcher, preemptive priority scheduler, and peripheral drivers.
- `apps/` — Interactive `ash` shell, 1,000 Hz tilt feedback task, neural walking runner, and `memtest`.

## Reference Reading

Every derivation in Parts I through III is self-contained inside its textbook chapter, requiring no external books to follow the build.
For readers who want additional breadth across processor architecture, electromagnetics, compilers, or operating systems, four classic references complement `brain`:

- Harris and Harris, *Digital Design and Computer Architecture (RISC-V Edition)*, Ch. 1–8.
- Clayton Paul, *Introduction to Electromagnetic Compatibility*, Ch. 1–11.
- Cooper and Torczon, *Engineering a Compiler*, Ch. 1–13.
- Cox, Kaashoek, and Morris, *xv6: A Simple, Unix-Like Teaching Operating System (RISC-V)*.
