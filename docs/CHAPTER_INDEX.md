# Apex Textbook Chapter Index

Compact, auto-generated structural and dependency map (`scripts/build.py`) for isolated textbook reviewers and readers.

## Chapter 1 Instruction Set Architecture (`systems/brain/chapters/01_isa_and_binary_arithmetic.md`, 1585 lines)

| Section | Lines (% Ch.) | Newly Defined Terms & Symbols | First Later Consumers | Visuals & Drills |
| :--- | :--- | :--- | :--- | :--- |
| **Sec 1: 1. Software Golden Reference Models** | `L7..L48` (42, 2.6%) | — | — | — |
| ↳ `1.1` Instruction Set Architecture Boundaries | `L32..L48` (17, 1.1%) | Instruction Set Architecture, Architectural State, registers, `step`, `brain` | 2.1, 2.2, 2.3, 2.4 | — |
| **Sec 2: 2. Fixed-Width Binary Arithmetic** | `L49..L429` (381, 24.0%) | — | — | — |
| ↳ `2.1` Unsigned Integers and Modular Congruence | `L56..L188` (133, 8.4%) | unsigned integer interpretation, one-to-one, bijection | 2.2, 2.3, 2.4, 3.3 | <UnsignedClockRing />, Exercise 2.1 (4 pts) |
| ↳ `2.2` Bitwise Wire Gates and Bit Shifts | `L189..L201` (13, 0.8%) | bitwise gate, bit shifts | 4.1 | — |
| ↳ `2.3` Two's Complement Signed Integers | `L202..L240` (39, 2.5%) | two's complement, carry-out, Most Significant Bit, `u32` | 2.4, 4.1, 4.2, 4.3 | <ModularRingAdder /> |
| ↳ `2.4` Shared Adder, Negation, and Left-Shift Circuits | `L241..L429` (189, 11.9%) | Sign-Agnostic Addition, Sign-Agnostic Subtraction Congruence, Negation via Invert Plus One, `INT32_MIN` | 4.1, 4.7, 6.1, 7.2 | Exercise 2.2 (4 pts) |
| **Sec 3: 3. Core Registers and Instruction Encoding** | `L430..L588` (159, 10.0%) | — | — | — |
| ↳ `3.1` Program Counter and Hardwired Zero Register | `L435..L454` (20, 1.3%) | Program Counter, General-Purpose Register File, `x31`, `RV32Oracle._set_reg` | 5.1, 6.2, 6.3, 7.1 | — |
| ↳ `3.2` Six Functional Instruction Families | `L455..L470` (16, 1.0%) | 32-bit Base Integer, Integer Multiply and Divide, RV32IM | 3.3, 3.4, 4.1, 4.5 | — |
| ↳ `3.3` Bitfield Layouts and Offset Reach | `L471..L512` (42, 2.6%) | assembly syntax, Add, immediate, `insn`, `rs1`, `rs2`, `imm` | 3.4, 4.1, 4.5, 4.6 | <RiscvFormatMatrix /> |
| ↳ `3.4` Widening Narrow Signed and Unsigned Integers | `L513..L588` (76, 4.8%) | sign extension, zero extension, fan-out, `sign_extend`, `s32`, `mask`, `sign_bit` | 4.1, 4.2, 4.3, 4.4 | <SignExtensionWidener /> |
| **Sec 4: 4. Integer Arithmetic, Multiplication, and Division** | `L589..L1006` (418, 26.4%) | — | — | — |
| ↳ `4.1` Base Integer Operations and Zero Idioms | `L595..L631` (37, 2.3%) | Modular Addition and Subtraction, Single-Word Bit Shifts, shift amount, `funct3`, `funct7`, `_exec_op_imm`, `_exec_op_reg` | 4.4, 4.6, 4.7, 5.1 | — |
| ↳ `4.2` Right Shifts and Integer Floor Division | `L632..L701` (70, 4.4%) | logical right shift, arithmetic right shift, floor division, `sll`, `slli`, `srl`, `srli` | 4.5, 4.7, 5.1, 5.2 | <RightShiftComparator /> |
| ↳ `4.3` Equality and Ordered Comparisons | `L702..L719` (18, 1.1%) | ordered comparisons, `slt`, `slti`, `sltu`, `sltiu` | 4.4, 5.1, 6.1, 8.3 | — |
| ↳ `4.4` Hardware Equivalence Summary | `L720..L733` (14, 0.9%) | — | 5.1, 6.1, 8.3 | — |
| ↳ `4.5` Full 32-Bit Constant Construction | `L734..L832` (99, 6.2%) | Load Upper Immediate, Add Upper Immediate to PC, `lui`, `auipc`, `cur_pc`, `addi` | 5.1, 5.3, 6.1, 6.3 | Exercise 4.1 (2 pts) |
| ↳ `4.6` Full 64-Bit Integer Multiplication | `L833..L924` (92, 5.8%) | RV32M, Multiply, Multiply High, `mul`, `mulh`, `mulhsu`, `mulhu` | 6.2, 7.1, 8.2, 9.2 | <Product64Inspector />, Exercise 4.2 (2 pts) |
| ↳ `4.7` Truncating Integer Division Semantics | `L925..L1006` (82, 5.2%) | Divide, Divide Unsigned, Remainder, `div`, `divu`, `rem`, `remu` | 5.1, 5.2, 5.3, 6.1 | <TruncatingDivisionComparator />, Exercise 4.3 (2 pts) |
| **Sec 5: 5. Memory Map and Bus Peripherals** | `L1007..L1128` (122, 7.7%) | — | — | — |
| ↳ `5.1` Address Decoding and Memory Regions | `L1012..L1066` (55, 3.5%) | bus, Memory-Mapped Input/Output, System-on-Chip, `add`, `lbu`, `lhu`, `BOOT_ROM_BASE` | 5.2, 8.1, 9.3, 9.4 | — |
| ↳ `5.2` Natural Alignment and Little-Endian Storage | `L1067..L1084` (18, 1.1%) | natural alignment, little-endian byte order, `RV32Oracle._exec_load`, `RV32Oracle._exec_store`, `bus_read`, `bus_write` | 6.1, 8.2, 8.3, 9.3 | — |
| ↳ `5.3` Monotonic Timer and Serial Console | `L1085..L1128` (44, 2.8%) | First-In, First-Out, baud rate, 64-Bit Counter Lifetime and Rollover Tearing, `mtime`, `mtimecmp`, `uart_tx_buf`, `uart_rx_fifo` | 6.2, 6.3, 8.2, 8.3 | — |
| **Sec 6: 6. Control Flow and Trap Handling** | `L1129..L1285` (157, 9.9%) | — | — | — |
| ↳ `6.1` Conditional Branches and Subroutine Jumps | `L1134..L1167` (34, 2.1%) | link address, `RV32Oracle._exec_branch`, `_exec_jal`, `_exec_jalr`, `beq` | 8.1, 8.3, 9.4 | — |
| ↳ `6.2` Control Registers and System Instructions | `L1168..L1227` (60, 3.8%) | hardware thread, hart, Control and Status Registers, `_write_csr`, `_read_csr`, `misa`, `CAUSE_ILLEGAL_INSN` | 6.3, 7.1, 8.1, 8.2 | — |
| ↳ `6.3` Trap Entry and Return Choreography | `L1228..L1285` (58, 3.7%) | Exact Resume Offset and Stackable Interrupts, Interrupt Service Routine, Zero-Clobber `mscratch` Bootstrap, `RV32Oracle._check_pending_interrupt`, `RV32Oracle._take_trap`, `WORD_ALIGN_MASK`, `mcause` | 8.1, 8.3, 9.3, 9.4 | — |
| **Sec 7: 7. Custom Neural Multiply-Accumulate Extension** | `L1286..L1369` (84, 5.3%) | — | — | — |
| ↳ `7.1` Saturating Clamping and Dual-Lane Datapath | `L1297..L1333` (37, 2.3%) | saturating arithmetic, Register-File Port Limit, Hardwired 18-Bit Multiplier Blocks, `sat32`, `RV32Oracle`, `s16`, `enc_mac` | 7.2, 8.2, 8.3, 9.6 | <XapexMacDatapath /> |
| ↳ `7.2` First-Step Accumulator Overflow Proof | `L1334..L1369` (36, 2.3%) | No First-Step Negative Saturation, Unique First-Step Positive Saturation, `INT32_MAX`, `base_acc` | 9.2, 9.6 | — |
| **Sec 8: 8. Unified Decoding and Lockstep Verification** | `L1370..L1449` (80, 5.0%) | — | — | — |
| ↳ `8.1` Unified 32-Bit Instruction Decoder | `L1375..L1399` (25, 1.6%) | `fence`, `bgeu`, `jalr`, `jal` | 8.2, 8.3, 9.1, 9.4 | <RiscvBitfieldDecoder /> |
| ↳ `8.2` Deterministic Fetch and Retirement Priority | `L1400..L1416` (17, 1.1%) | Pre-Fetch Clock Advance, Pre-Fetch Interrupt Priority, Fault-Checked Operand Latching and Dispatch, `StepTrace`, `MASK64`, `ExecOutcome`, `rd_val` | 8.3, 9.4, 9.5, 9.6 | — |
| ↳ `8.3` Precise Faults and Inductive Trace Equivalence | `L1417..L1449` (33, 2.1%) | Precise Exception Atomicity, `mret`, `mtvec`, `mem_addr`, `mem_val` | 9.4, 9.5 | <OracleStepTracer /> |
| **Sec 9: 9. Problems** | `L1450..L1585` (136, 8.6%) | — | — | — |
| ↳ `9.1` Problem 1: Two's Complement and Constant Bias | `L1455..L1474` (20, 1.3%) | `hi20`, `lo12` | — | — |
| ↳ `9.2` Problem 2: Shifts, Comparisons, 64-Bit Products, and Division | `L1475..L1498` (24, 1.5%) | `_exec_muldiv`, `srai`, `rs1_u`, `rs2_u` | — | — |
| ↳ `9.3` Problem 3: Address Decoding, Alignment, and 64-Bit Timers | `L1499..L1523` (25, 1.6%) | `_clint_read`, `_exec_load`, `CLINT_BASE`, `CAUSE_LOAD_MISALIGNED` | 9.4 | — |
| ↳ `9.4` Problem 4: Indirect Jumps, Decoding, and Fault Atomicity | `L1524..L1546` (23, 1.5%) | `test_jalr_bit0_snap_and_untaken_misaligned_branch`, `target`, `mepc`, `mtval` | 9.5 | — |
| ↳ `9.5` Problem 5: Control Registers, Preemption, and Step Traces | `L1547..L1566` (20, 1.3%) | `test_clint_timer_interrupt_and_ecall_handler`, `test_vectored_mtvec_dispatch_and_sync_ecall_fallback`, `mie`, `mcycle` | — | — |
| ↳ `9.6` Problem 6: Neural Accumulator Preloading and Saturation | `L1567..L1585` (19, 1.2%) | `_exec_mac`, `test_xapex_custom_mac_dot_product_and_saturation`, `x10`, `x11` | — | — |
