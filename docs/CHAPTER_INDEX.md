# Apex Textbook Chapter Index

Compact, auto-generated structural and dependency map (`scripts/build.py`) for isolated textbook reviewers and readers.

## Chapter 1 Instruction Set Architecture (`systems/brain/chapters/01_isa_and_binary_arithmetic.md`, 1691 lines)

| Section | Lines (% Ch.) | Newly Defined Terms & Symbols | First Later Consumers | Visuals & Drills |
| :--- | :--- | :--- | :--- | :--- |
| **Sec 1: 1. Software Golden Reference Models** | `L7..L49` (43, 2.5%) | — | — | — |
| ↳ `1.1` Instruction Set Architecture Boundaries | `L32..L49` (18, 1.1%) | Instruction Set Architecture, Architectural State, registers, `step` | 2.1, 2.2, 2.4, 3.1 | — |
| **Sec 2: 2. Fixed-Width Binary Arithmetic** | `L50..L471` (422, 25.0%) | — | — | — |
| ↳ `2.1` Unsigned Integers and Modular Congruence | `L57..L200` (144, 8.5%) | unsigned integer interpretation, bijection, hexadecimal | 2.2, 2.3, 2.4, 3.3 | <UnsignedClockRing />, Exercise 2.1 (4 pts) |
| ↳ `2.2` Bitwise Wire Gates and Bit Shifts | `L201..L213` (13, 0.8%) | bitwise gate, bit shifts | 4.1 | — |
| ↳ `2.3` Two's Complement Signed Integers | `L214..L267` (54, 3.2%) | two's complement, carry-out, Most Significant Bit, `MASK32`, `u32` | 2.4, 4.1, 4.2, 4.3 | <ModularRingAdder /> |
| ↳ `2.4` Shared Adder, Negation, and Left-Shift Circuits | `L268..L471` (204, 12.1%) | Sign-Agnostic Addition, Sign-Agnostic Subtraction Congruence, Negation via Invert Plus One, `INT32_MIN` | 4.1, 4.7, 7.2, 9.2 | Exercise 2.2 (4 pts) |
| **Sec 3: 3. Core Registers and Instruction Encoding** | `L472..L635` (164, 9.7%) | — | — | — |
| ↳ `3.1` Program Counter and Hardwired Zero Register | `L477..L496` (20, 1.2%) | Program Counter, General-Purpose Register File, `x31`, `RV32Oracle._set_reg` | 6.2, 6.3, 7.1, 8.2 | — |
| ↳ `3.2` Six Functional Instruction Families | `L497..L512` (16, 0.9%) | 32-bit Base Integer, Integer Multiply and Divide, RV32IM, `brain` | 3.3, 3.4, 4.1, 4.5 | — |
| ↳ `3.3` Bitfield Layouts and Offset Reach | `L513..L556` (44, 2.6%) | assembly syntax, Add, immediate, `insn`, `rs1`, `rs2`, `imm` | 3.4, 4.1, 4.5, 4.6 | <RiscvFormatMatrix /> |
| ↳ `3.4` Widening Narrow Signed and Unsigned Integers | `L557..L635` (79, 4.7%) | sign extension, zero extension, fan-out, `sign_extend`, `s32`, `mask`, `sign_bit` | 4.1, 4.2, 4.3, 4.4 | <SignExtensionWidener /> |
| **Sec 4: 4. Integer Arithmetic, Multiplication, and Division** | `L636..L1008` (373, 22.1%) | — | — | — |
| ↳ `4.1` Base Integer Operations and Zero Idioms | `L642..L679` (38, 2.2%) | Modular Addition and Subtraction, Single-Word Bit Shifts, shift amount, `funct3`, `funct7`, `_exec_op_imm`, `_exec_op_reg` | 4.2, 4.4, 4.6, 4.7 | — |
| ↳ `4.2` Right Shifts and Integer Floor Division | `L680..L739` (60, 3.5%) | logical right shift, arithmetic right shift, floor division, `sll`, `slli`, `srl`, `srli` | 4.4, 4.7, 5.1, 5.2 | <RightShiftComparator /> |
| ↳ `4.3` Equality and Ordered Comparisons | `L740..L757` (18, 1.1%) | ordered comparisons, `slt`, `slti`, `sltu`, `sltiu` | 4.4, 5.1, 6.1, 8.3 | — |
| ↳ `4.4` Base Integer Hardware Equivalence | `L758..L771` (14, 0.8%) | — | 4.6, 5.1, 6.1, 8.3 | — |
| ↳ `4.5` Full 32-Bit Constant Construction | `L772..L837` (66, 3.9%) | Load Upper Immediate, Add Upper Immediate to PC, `lui`, `auipc`, `cur_pc`, `addi` | 5.1, 5.3, 6.1, 6.3 | <LuiBiasCarryDiagram />, Exercise 4.1 (2 pts) |
| ↳ `4.6` Full 64-Bit Integer Multiplication | `L838..L924` (87, 5.1%) | RV32M, Multiply, Multiply High, `mul`, `mulh`, `mulhsu`, `mulhu` | 6.2, 7.1, 8.2, 9.2 | <Product64SplitDiagram />, Exercise 4.2 (2 pts) |
| ↳ `4.7` Truncating Integer Division Semantics | `L925..L1008` (84, 5.0%) | Divide, Divide Unsigned, Remainder, `div`, `divu`, `rem`, `remu` | 5.1, 5.2, 5.3, 6.1 | <TruncatingDivisionComparator />, Exercise 4.3 (2 pts) |
| **Sec 5: 5. Memory Map and Bus Peripherals** | `L1009..L1149` (141, 8.3%) | — | — | — |
| ↳ `5.1` Memory Instructions, Regions, and Prefix Decoding | `L1014..L1067` (54, 3.2%) | bus, Memory-Mapped Input/Output, System-on-Chip, `add`, `lbu`, `lhu`, `BOOT_ROM_BASE` | 5.2, 5.3, 6.1, 6.2 | — |
| ↳ `5.2` Natural Alignment and Little-Endian Storage | `L1068..L1086` (19, 1.1%) | natural alignment, little-endian byte order, `RV32Oracle._exec_load`, `RV32Oracle._exec_store`, `bus_read`, `bus_write` | 6.1, 8.2, 8.3, 9.3 | — |
| ↳ `5.3` Monotonic Timer and Serial Console | `L1087..L1149` (63, 3.7%) | First-In, First-Out, baud rate, 64-Bit Counter Lifetime and Rollover Tearing, `push_uart_rx`, `read_uart_tx`, `reset`, `mtime` | 6.2, 6.3, 8.2, 8.3 | <TimerRolloverTearDiagram /> |
| **Sec 6: 6. Control Flow and Trap Handling** | `L1150..L1314` (165, 9.8%) | — | — | — |
| ↳ `6.1` Conditional Branches and Subroutine Jumps | `L1155..L1189` (35, 2.1%) | link address, `RV32Oracle._exec_branch`, `_exec_jal`, `_exec_jalr`, `beq` | 8.1, 9.3, 9.4 | — |
| ↳ `6.2` Control Registers and System Instructions | `L1190..L1252` (63, 3.7%) | hardware thread, hart, Control and Status Registers, `_write_csr`, `_read_csr`, `misa`, `mstatus` | 6.3, 7.1, 8.2, 8.3 | — |
| ↳ `6.3` Trap Entry and Return Choreography | `L1253..L1314` (62, 3.7%) | Atomic Interrupt Masking and Restore, Interrupt Service Routine, Exact Resume Offset, `mepc`, `mcause`, `mtval`, `mtvec` | 8.1, 8.3, 9.3, 9.4 | — |
| **Sec 7: 7. Custom Neural Multiply-Accumulate Extension** | `L1315..L1399` (85, 5.0%) | — | — | — |
| ↳ `7.1` Saturating Clamping and Dual-Lane Datapath | `L1326..L1362` (37, 2.2%) | saturating arithmetic, Register-File Port Limit, Hardwired 18-Bit Multiplier Blocks, `sat32`, `RV32Oracle`, `s16`, `enc_mac` | 7.2, 8.2, 8.3, 9.6 | <XapexMacDatapath /> |
| ↳ `7.2` First-Step Accumulator Overflow Proof | `L1363..L1399` (37, 2.2%) | No First-Step Negative Saturation, Unique First-Step Positive Saturation, `INT32_MAX` | 9.2, 9.6 | — |
| **Sec 8: 8. Unified Decoding and Lockstep Verification** | `L1400..L1480` (81, 4.8%) | — | — | — |
| ↳ `8.1` Unified 32-Bit Instruction Decoder | `L1405..L1429` (25, 1.5%) | `fence`, `bgeu`, `jalr`, `jal` | 8.2, 8.3, 9.3, 9.4 | <RiscvBitfieldDecoder /> |
| ↳ `8.2` Deterministic Fetch and Retirement Priority | `L1430..L1447` (18, 1.1%) | Pre-Fetch Clock Advance, Pre-Fetch Interrupt Priority, Fault-Checked Operand Latching and Dispatch, `StepTrace`, `MASK64`, `ExecOutcome`, `rd_val` | 8.3, 9.4, 9.5, 9.6 | — |
| ↳ `8.3` Precise Faults and Inductive Trace Equivalence | `L1448..L1480` (33, 2.0%) | Precise Exception Atomicity, `mret`, `mem_addr`, `mem_val`, `mem_write` | 9.4, 9.5 | <OracleStepTracer /> |
| **Sec 9: 9. Problems** | `L1481..L1691` (211, 12.5%) | — | — | — |
| ↳ `9.1` Problem 1: Two's Complement and Constant Bias | `L1486..L1517` (32, 1.9%) | `hi20`, `lo12` | — | — |
| ↳ `9.2` Problem 2: Shifts, Comparisons, 64-Bit Products, and Division | `L1518..L1565` (48, 2.8%) | `_exec_muldiv`, `srai`, `UINT32_MAX`, `rs1_u` | — | — |
| ↳ `9.3` Problem 3: Address Decoding, Alignment, and 64-Bit Timers | `L1566..L1604` (39, 2.3%) | `_clint_read`, `_exec_load`, `CLINT_BASE`, `CAUSE_LOAD_MISALIGNED` | 9.4 | — |
| ↳ `9.4` Problem 4: Indirect Jumps, Decoding, and Fault Atomicity | `L1605..L1637` (33, 2.0%) | `test_jalr_bit0_snap_and_untaken_misaligned_branch`, `CAUSE_INSN_MISALIGNED`, `CAUSE_ILLEGAL_INSN` | — | — |
| ↳ `9.5` Problem 5: Control Registers, Preemption, and Step Traces | `L1638..L1665` (28, 1.7%) | Pre-fetch clock and interrupt, Trap CSRs and PC, Emitted `StepTrace`, `test_clint_timer_interrupt_and_ecall_handler`, `test_vectored_mtvec_dispatch_and_sync_ecall_fallback`, `mcycle`, `minstret` | — | — |
| ↳ `9.6` Problem 6: Neural Accumulator Preloading and Saturation | `L1666..L1691` (26, 1.5%) | `_exec_mac`, `test_xapex_custom_mac_dot_product_and_saturation`, `x10`, `x11` | — | — |
