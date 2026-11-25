# Apex Textbook Chapter Index

Compact, auto-generated structural and dependency map (`scripts/build.py`) for isolated textbook reviewers and readers.

## Chapter 1 Instruction Set Architecture (`systems/brain/chapters/01_isa_and_binary_arithmetic.md`, 1343 lines)

| Section | Lines (% Ch.) | Newly Defined Terms & Symbols | First Later Consumers | Visuals & Examples |
| :--- | :--- | :--- | :--- | :--- |
| **Sec 1: 1. Software Golden Reference Models** | `L7..L47` (41, 3.1%) | — | — | — |
| ↳ `1.1` Instruction Set Architecture Boundaries | `L32..L47` (16, 1.2%) | Instruction Set Architecture, Architectural State, registers, `step` | 2.2, 3.1, 3.2, 3.3 | — |
| **Sec 2: 2. Fixed-Width Binary Arithmetic** | `L48..L368` (321, 23.9%) | — | — | — |
| ↳ `2.1` Bitwise Wire Gates and Bit Shifts | `L55..L71` (17, 1.3%) | hexadecimal, bitwise gate, bit shifts | — | — |
| ↳ `2.2` Unsigned Integers, Binary Addition, and Modular Congruence | `L72..L177` (106, 7.9%) | unsigned integer interpretation, bijection, binary addition | 2.3, 2.4, 3.3, 3.4 | <BinaryAdditionCarryDiagram />, <UnsignedClockRing />, Example 2.1 (3 pts) |
| ↳ `2.3` Two's Complement Signed Integers | `L178..L231` (54, 4.0%) | two's complement, Most Significant Bit, signed overflow, `MASK32`, `u32` | 2.4, 4.1, 4.2, 4.3 | <ModularRingAdder /> |
| ↳ `2.4` Shared Adder, Negation, and Left-Shift Circuits | `L232..L368` (137, 10.2%) | Sign-Agnostic Addition and Subtraction, Negation via Invert Plus One, Subtraction via Invert Plus One, `INT32_MIN` | 4.1, 4.7, 7.2 | Example 2.2 (2 pts) |
| **Sec 3: 3. Core Registers and Instruction Encoding** | `L369..L530` (162, 12.1%) | — | — | — |
| ↳ `3.1` Program Counter and Hardwired Zero Register | `L374..L393` (20, 1.5%) | Program Counter, General-Purpose Register File, `x31`, `RV32Oracle._set_reg` | 6.2, 6.3, 7.1, 7.2 | — |
| ↳ `3.2` Six Functional Instruction Families | `L394..L409` (16, 1.2%) | 32-bit Base Integer, Integer Multiply and Divide, RV32IM, `brain` | 3.3, 3.4, 4.1, 4.3 | — |
| ↳ `3.3` Bitfield Layouts and Offset Reach | `L410..L453` (44, 3.3%) | assembly syntax, Add, immediate, `insn`, `rs1`, `rs2`, `imm` | 3.4, 4.1, 4.3, 4.5 | <RiscvFormatMatrix /> |
| ↳ `3.4` Widening Narrow Signed and Unsigned Integers | `L454..L530` (77, 5.7%) | sign extension, zero extension, fan-out, `sign_extend`, `s32`, `mask`, `sign_bit` | 4.1, 4.2, 4.3, 4.4 | <SignExtensionWidener /> |
| **Sec 4: 4. Integer Arithmetic, Multiplication, and Division** | `L531..L834` (304, 22.6%) | — | — | — |
| ↳ `4.1` Base Integer Operations and Zero Idioms | `L537..L568` (32, 2.4%) | shift amount, pseudoinstructions, `funct3`, `funct7`, `_exec_op_imm`, `_exec_op_reg` | 4.2, 4.4, 4.6, 4.7 | — |
| ↳ `4.2` Right Shifts and Integer Floor Division | `L569..L628` (60, 4.5%) | logical right shift, arithmetic right shift, floor division, `sll`, `slli`, `srl`, `srli` | 4.4, 4.7, 5.1, 5.2 | <RightShiftComparator /> |
| ↳ `4.3` Equality and Ordered Comparisons | `L629..L651` (23, 1.7%) | ordered comparisons, `slt`, `slti`, `sltu`, `sltiu` | 4.4, 4.5, 4.7, 5.1 | Example 4.1 (0 pts) |
| ↳ `4.4` Base Integer Hardware Equivalence | `L652..L665` (14, 1.0%) | — | 4.5, 4.6, 5.1, 6.1 | — |
| ↳ `4.5` Full 32-Bit Constant Construction | `L666..L709` (44, 3.3%) | Load Upper Immediate, Add Upper Immediate to PC, modulus scaling, `imm20`, `lui`, `auipc`, `cur_pc` | 4.6, 5.1, 5.3, 6.1 | <LuiBiasCarryDiagram />, Example 4.2 (2 pts) |
| ↳ `4.6` Full 64-Bit Integer Multiplication | `L710..L773` (64, 4.8%) | RV32M, Multiply, Multiply High, `mul`, `mulh`, `mulhsu`, `mulhu` | 6.2, 7.1, 7.2, 8.2 | <Product64SplitDiagram />, Example 4.3 (0 pts) |
| ↳ `4.7` Truncating Integer Division Semantics | `L774..L834` (61, 4.5%) | Divide, Divide Unsigned, Remainder, `div`, `divu`, `rem`, `remu` | 5.1, 5.2, 5.3, 6.1 | <TruncatingDivisionComparator />, Example 4.4 (2 pts) |
| **Sec 5: 5. Memory Map and Bus Peripherals** | `L835..L989` (155, 11.5%) | — | — | — |
| ↳ `5.1` Memory Instructions, Regions, and Prefix Decoding | `L840..L893` (54, 4.0%) | bus, Memory-Mapped Input/Output, System-on-Chip, `add`, `lbu`, `lhu`, `BOOT_ROM_BASE` | 5.2, 5.3, 6.1, 6.2 | — |
| ↳ `5.2` Natural Alignment and Little-Endian Storage | `L894..L917` (24, 1.8%) | natural alignment, little-endian byte order, `RV32Oracle._exec_load`, `RV32Oracle._exec_store`, `bus_read`, `bus_write` | 6.1, 8.2, 8.3 | Example 5.1 (0 pts) |
| ↳ `5.3` Monotonic Timer and Serial Console | `L918..L989` (72, 5.4%) | First-In, First-Out, baud rate, 64-Bit Counter Lifetime and Rollover Tearing, `push_uart_rx`, `read_uart_tx`, `reset`, `mtime` | 6.2, 6.3, 8.2, 8.3 | <TimerRolloverTearDiagram />, Example 5.2 (0 pts) |
| **Sec 6: 6. Control Flow and Trap Handling** | `L990..L1167` (178, 13.3%) | — | — | — |
| ↳ `6.1` Conditional Branches and Subroutine Jumps | `L995..L1036` (42, 3.1%) | link address, Bit 0 Snapped (`jalr x2, 1(x2)`), Bit 1 Misaligned Trap (`jalr x2, 2(x2)`), `RV32Oracle._exec_branch`, `_exec_jal`, `_exec_jalr`, `imm13` | 8.1 | Example 6.1 (2 pts) |
| ↳ `6.2` Control Registers and System Instructions | `L1037..L1099` (63, 4.7%) | hardware thread, hart, Control and Status Registers, `_write_csr`, `_read_csr`, `misa`, `mstatus` | 6.3, 7.1, 8.2, 8.3 | — |
| ↳ `6.3` Trap Entry and Return Choreography | `L1100..L1167` (68, 5.1%) | Atomic Interrupt Masking and Restore, Interrupt Service Routine, Exact Resume Offset, `mepc`, `mcause`, `mtval`, `mtvec` | 8.1, 8.3 | Example 6.2 (2 pts) |
| **Sec 7: 7. Custom Neural Multiply-Accumulate Extension** | `L1168..L1264` (97, 7.2%) | — | — | — |
| ↳ `7.1` Saturating Clamping and Dual-Lane Datapath | `L1179..L1215` (37, 2.8%) | saturating arithmetic, Register-File Port Limit, Hardwired 18-Bit Multiplier Blocks, `sat32`, `RV32Oracle`, `s16`, `enc_mac` | 7.2, 8.2, 8.3 | <XapexMacDatapath /> |
| ↳ `7.2` First-Step Accumulator Overflow Proof | `L1216..L1264` (49, 3.6%) | No First-Step Negative Saturation, Unique First-Step Positive Saturation, Bias Preload and Multiply-Accumulate, `INT32_MAX`, `_exec_mac`, `test_xapex_custom_mac_dot_product_and_saturation`, `x10` | 8.3 | Example 7.1 (2 pts) |
| **Sec 8: 8. Unified Decoding and Lockstep Verification** | `L1265..L1343` (79, 5.9%) | — | — | — |
| ↳ `8.1` Unified 32-Bit Instruction Decoder | `L1270..L1294` (25, 1.9%) | `fence`, `beq`, `bgeu`, `jalr` | 8.2, 8.3 | <RiscvBitfieldDecoder /> |
| ↳ `8.2` Deterministic Fetch and Retirement Priority | `L1295..L1312` (18, 1.3%) | Pre-Fetch Clock Advance, Pre-Fetch Interrupt Priority, Fault-Checked Operand Latching and Dispatch, `StepTrace`, `MASK64`, `ExecOutcome`, `rd_val` | 8.3 | — |
| ↳ `8.3` Precise Faults and Inductive Trace Equivalence | `L1313..L1343` (31, 2.3%) | Precise Exception Atomicity, `mret`, `mem_addr`, `mem_val`, `mem_write` | — | <OracleStepTracer /> |
