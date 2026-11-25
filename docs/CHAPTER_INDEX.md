# Apex Textbook Chapter Index

Compact, auto-generated structural and dependency map (`scripts/build.py`) for isolated textbook reviewers and readers.

## Chapter 1 Instruction Set Architecture (`systems/brain/chapters/01_isa_and_binary_arithmetic.md`, 1532 lines)

| Section | Lines (% Ch.) | Newly Defined Terms & Symbols | First Later Consumers | Visuals & Examples |
| :--- | :--- | :--- | :--- | :--- |
| **Sec 1: 1. Software Golden Reference Models** | `L7..L49` (43, 2.8%) | — | — | — |
| ↳ `1.1` Instruction Set Architecture Boundaries | `L32..L49` (18, 1.2%) | Instruction Set Architecture, Architectural State, registers, `step` | 2.2, 3.1, 3.2, 3.3 | — |
| **Sec 2: 2. Fixed-Width Binary Arithmetic** | `L50..L372` (323, 21.1%) | — | — | — |
| ↳ `2.1` Bitwise Wire Gates and Bit Shifts | `L57..L73` (17, 1.1%) | hexadecimal, bitwise gate, bit shifts | — | — |
| ↳ `2.2` Unsigned Integers, Binary Addition, and Modular Congruence | `L74..L179` (106, 6.9%) | unsigned integer interpretation, bijection, binary addition | 2.3, 2.4, 3.3, 3.4 | <BinaryAdditionCarryDiagram />, <UnsignedClockRing />, Example 2.1 (3 pts) |
| ↳ `2.3` Two's Complement Signed Integers | `L180..L233` (54, 3.5%) | two's complement, Most Significant Bit, signed overflow, `MASK32`, `u32` | 2.4, 4.1, 4.2, 4.3 | <ModularRingAdder /> |
| ↳ `2.4` Shared Adder, Negation, and Left-Shift Circuits | `L234..L372` (139, 9.1%) | Sign-Agnostic Addition and Subtraction, Negation via Invert Plus One, Subtraction via Invert Plus One, `INT32_MIN` | 4.1, 4.7, 7.2, 9.2 | Example 2.2 (2 pts) |
| **Sec 3: 3. Core Registers and Instruction Encoding** | `L373..L536` (164, 10.7%) | — | — | — |
| ↳ `3.1` Program Counter and Hardwired Zero Register | `L378..L397` (20, 1.3%) | Program Counter, General-Purpose Register File, `x31`, `RV32Oracle._set_reg` | 6.2, 6.3, 7.1, 8.2 | — |
| ↳ `3.2` Six Functional Instruction Families | `L398..L413` (16, 1.0%) | 32-bit Base Integer, Integer Multiply and Divide, RV32IM, `brain` | 3.3, 3.4, 4.1, 4.5 | — |
| ↳ `3.3` Bitfield Layouts and Offset Reach | `L414..L457` (44, 2.9%) | assembly syntax, Add, immediate, `insn`, `rs1`, `rs2`, `imm` | 3.4, 4.1, 4.5, 4.6 | <RiscvFormatMatrix /> |
| ↳ `3.4` Widening Narrow Signed and Unsigned Integers | `L458..L536` (79, 5.2%) | sign extension, zero extension, fan-out, `sign_extend`, `s32`, `mask`, `sign_bit` | 4.1, 4.2, 4.3, 4.4 | <SignExtensionWidener /> |
| **Sec 4: 4. Integer Arithmetic, Multiplication, and Division** | `L537..L837` (301, 19.6%) | — | — | — |
| ↳ `4.1` Base Integer Operations and Zero Idioms | `L543..L574` (32, 2.1%) | shift amount, pseudoinstructions, `funct3`, `funct7`, `_exec_op_imm`, `_exec_op_reg` | 4.2, 4.4, 4.6, 4.7 | — |
| ↳ `4.2` Right Shifts and Integer Floor Division | `L575..L634` (60, 3.9%) | logical right shift, arithmetic right shift, floor division, `sll`, `slli`, `srl`, `srli` | 4.4, 4.7, 5.1, 5.2 | <RightShiftComparator /> |
| ↳ `4.3` Equality and Ordered Comparisons | `L635..L652` (18, 1.2%) | ordered comparisons, `slt`, `slti`, `sltu`, `sltiu` | 4.4, 5.1, 6.1, 8.3 | — |
| ↳ `4.4` Base Integer Hardware Equivalence | `L653..L666` (14, 0.9%) | — | 4.5, 4.6, 5.1, 6.1 | — |
| ↳ `4.5` Full 32-Bit Constant Construction | `L667..L710` (44, 2.9%) | Load Upper Immediate, Add Upper Immediate to PC, modulus scaling, `imm20`, `lui`, `auipc`, `cur_pc` | 4.6, 5.1, 5.3, 6.1 | <LuiBiasCarryDiagram />, Example 4.1 (2 pts) |
| ↳ `4.6` Full 64-Bit Integer Multiplication | `L711..L774` (64, 4.2%) | RV32M, Multiply, Multiply High, `mul`, `mulh`, `mulhsu`, `mulhu` | 6.2, 7.1, 8.2, 9.2 | <Product64SplitDiagram />, Example 4.2 (0 pts) |
| ↳ `4.7` Truncating Integer Division Semantics | `L775..L837` (63, 4.1%) | Divide, Divide Unsigned, Remainder, `div`, `divu`, `rem`, `remu` | 5.1, 5.2, 5.3, 6.1 | <TruncatingDivisionComparator />, Example 4.3 (2 pts) |
| **Sec 5: 5. Memory Map and Bus Peripherals** | `L838..L978` (141, 9.2%) | — | — | — |
| ↳ `5.1` Memory Instructions, Regions, and Prefix Decoding | `L843..L896` (54, 3.5%) | bus, Memory-Mapped Input/Output, System-on-Chip, `add`, `lbu`, `lhu`, `BOOT_ROM_BASE` | 5.2, 5.3, 6.1, 6.2 | — |
| ↳ `5.2` Natural Alignment and Little-Endian Storage | `L897..L915` (19, 1.2%) | natural alignment, little-endian byte order, `RV32Oracle._exec_load`, `RV32Oracle._exec_store`, `bus_read`, `bus_write` | 6.1, 8.2, 8.3, 9.3 | — |
| ↳ `5.3` Monotonic Timer and Serial Console | `L916..L978` (63, 4.1%) | First-In, First-Out, baud rate, 64-Bit Counter Lifetime and Rollover Tearing, `push_uart_rx`, `read_uart_tx`, `reset`, `mtime` | 6.2, 6.3, 8.2, 8.3 | <TimerRolloverTearDiagram /> |
| **Sec 6: 6. Control Flow and Trap Handling** | `L979..L1143` (165, 10.8%) | — | — | — |
| ↳ `6.1` Conditional Branches and Subroutine Jumps | `L984..L1018` (35, 2.3%) | link address, `RV32Oracle._exec_branch`, `_exec_jal`, `_exec_jalr`, `beq` | 8.1, 9.3, 9.4 | — |
| ↳ `6.2` Control Registers and System Instructions | `L1019..L1081` (63, 4.1%) | hardware thread, hart, Control and Status Registers, `_write_csr`, `_read_csr`, `misa`, `mstatus` | 6.3, 7.1, 8.2, 8.3 | — |
| ↳ `6.3` Trap Entry and Return Choreography | `L1082..L1143` (62, 4.0%) | Atomic Interrupt Masking and Restore, Interrupt Service Routine, Exact Resume Offset, `mepc`, `mcause`, `mtval`, `mtvec` | 8.1, 8.3, 9.3, 9.4 | — |
| **Sec 7: 7. Custom Neural Multiply-Accumulate Extension** | `L1144..L1228` (85, 5.5%) | — | — | — |
| ↳ `7.1` Saturating Clamping and Dual-Lane Datapath | `L1155..L1191` (37, 2.4%) | saturating arithmetic, Register-File Port Limit, Hardwired 18-Bit Multiplier Blocks, `sat32`, `RV32Oracle`, `s16`, `enc_mac` | 7.2, 8.2, 8.3, 9.6 | <XapexMacDatapath /> |
| ↳ `7.2` First-Step Accumulator Overflow Proof | `L1192..L1228` (37, 2.4%) | No First-Step Negative Saturation, Unique First-Step Positive Saturation, `INT32_MAX` | 9.2, 9.6 | — |
| **Sec 8: 8. Unified Decoding and Lockstep Verification** | `L1229..L1309` (81, 5.3%) | — | — | — |
| ↳ `8.1` Unified 32-Bit Instruction Decoder | `L1234..L1258` (25, 1.6%) | `fence`, `bgeu`, `jalr`, `jal` | 8.2, 8.3, 9.3, 9.4 | <RiscvBitfieldDecoder /> |
| ↳ `8.2` Deterministic Fetch and Retirement Priority | `L1259..L1276` (18, 1.2%) | Pre-Fetch Clock Advance, Pre-Fetch Interrupt Priority, Fault-Checked Operand Latching and Dispatch, `StepTrace`, `MASK64`, `ExecOutcome`, `rd_val` | 8.3, 9.4, 9.5, 9.6 | — |
| ↳ `8.3` Precise Faults and Inductive Trace Equivalence | `L1277..L1309` (33, 2.2%) | Precise Exception Atomicity, `mret`, `mem_addr`, `mem_val`, `mem_write` | 9.4, 9.5 | <OracleStepTracer /> |
| **Sec 9: 9. Problems** | `L1310..L1532` (223, 14.6%) | — | — | — |
| ↳ `9.1` Problem 1: Two's Complement and Constant Bias | `L1315..L1358` (44, 2.9%) | `hi20`, `lo12` | — | — |
| ↳ `9.2` Problem 2: Shifts, Comparisons, 64-Bit Products, and Division | `L1359..L1406` (48, 3.1%) | `_exec_muldiv`, `srai`, `UINT32_MAX`, `rs1_u` | — | — |
| ↳ `9.3` Problem 3: Address Decoding, Alignment, and 64-Bit Timers | `L1407..L1445` (39, 2.5%) | `_clint_read`, `_exec_load`, `CLINT_BASE`, `CAUSE_LOAD_MISALIGNED` | 9.4 | — |
| ↳ `9.4` Problem 4: Indirect Jumps, Decoding, and Fault Atomicity | `L1446..L1478` (33, 2.2%) | `test_jalr_bit0_snap_and_untaken_misaligned_branch`, `CAUSE_INSN_MISALIGNED`, `CAUSE_ILLEGAL_INSN` | — | — |
| ↳ `9.5` Problem 5: Control Registers, Preemption, and Step Traces | `L1479..L1506` (28, 1.8%) | Pre-fetch clock and interrupt, Trap CSRs and PC, Emitted `StepTrace`, `test_clint_timer_interrupt_and_ecall_handler`, `test_vectored_mtvec_dispatch_and_sync_ecall_fallback`, `mcycle`, `minstret` | — | — |
| ↳ `9.6` Problem 6: Neural Accumulator Preloading and Saturation | `L1507..L1532` (26, 1.7%) | `_exec_mac`, `test_xapex_custom_mac_dot_product_and_saturation`, `x10`, `x11` | — | — |
