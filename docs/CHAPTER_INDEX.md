# Apex Textbook Chapter Index

Compact, auto-generated structural and dependency map (`scripts/build.py`) for isolated textbook reviewers and readers.

## Chapter 1 Instruction Set Architecture (`systems/brain/chapters/01_isa_and_binary_arithmetic.md`, 1636 lines)

| Section | Lines (% Ch.) | Newly Defined Terms & Symbols | First Later Consumers | Visuals & Drills |
| :--- | :--- | :--- | :--- | :--- |
| **Sec 1: 1. Software Golden Reference Models** | `L7..L48` (42, 2.6%) | — | — | — |
| ↳ `1.1` Instruction Set Architecture Boundaries | `L32..L48` (17, 1.0%) | Instruction Set Architecture, Architectural State, registers, `step`, `brain` | 2.1, 2.2, 3.1, 3.2 | — |
| **Sec 2: 2. Fixed-Width Binary Arithmetic** | `L49..L368` (320, 19.6%) | — | — | — |
| ↳ `2.1` Unsigned Integers and Modular Congruence | `L56..L164` (109, 6.7%) | unsigned integer interpretation, one-to-one, bijection | 2.2, 2.3, 3.3, 3.4 | Exercise 2.1 (8 pts) |
| ↳ `2.2` Two's Complement Signed Integers | `L165..L228` (64, 3.9%) | two's complement, carry-out, Most Significant Bit, `u32` | 2.3, 3.4, 4.1, 4.2 | <ModularRingAdder />, Exercise 2.2 (8 pts) |
| ↳ `2.3` Shared Adder, Negation, and Shift Circuits | `L229..L368` (140, 8.6%) | exact same slot, Sign-Agnostic Addition, Sign-Agnostic Subtraction Congruence, `INT32_MIN` | 4.1, 4.7, 6.1, 7.2 | Exercise 2.3 (8 pts) |
| **Sec 3: 3. Core Registers and Instruction Encoding** | `L369..L572` (204, 12.5%) | — | — | — |
| ↳ `3.1` Program Counter and Hardwired Zero Register | `L374..L393` (20, 1.2%) | Program Counter, General-Purpose Register File, `x31`, `RV32Oracle._set_reg` | 5.1, 6.2, 6.3, 7.1 | — |
| ↳ `3.2` Six Functional Instruction Families | `L394..L409` (16, 1.0%) | 32-bit Base Integer, Integer Multiply and Divide, RV32IM | 3.3, 3.4, 4.1, 4.5 | — |
| ↳ `3.3` Bitfield Layouts and Offset Reach | `L410..L476` (67, 4.1%) | assembly syntax, Add, immediate, `insn`, `rs1`, `rs2`, `imm` | 3.4, 4.1, 4.5, 4.6 | <RiscvFormatMatrix />, Exercise 3.1 (7 pts) |
| ↳ `3.4` Widening Narrow Signed and Unsigned Integers | `L477..L572` (96, 5.9%) | sign extension, zero extension, fan-out, `sign_extend`, `s32`, `sign_bit` | 4.1, 4.2, 4.3, 4.4 | <SignExtensionWidener />, Exercise 3.2 (7 pts) |
| **Sec 4: 4. Integer Arithmetic and Multiplication** | `L573..L1016` (444, 27.1%) | — | — | — |
| ↳ `4.1` Base Integer Operations and Zero Idioms | `L579..L611` (33, 2.0%) | shift amount, barrel shifter, `funct3`, `funct7`, `_exec_op_imm`, `_exec_op_reg` | 4.4, 4.6, 4.7, 5.1 | — |
| ↳ `4.2` Right Shifts and Integer Floor Division | `L612..L708` (97, 5.9%) | logical right shift, arithmetic right shift, floor division, `sll`, `slli`, `srl`, `srli` | 4.5, 4.7, 5.1, 5.2 | <RightShiftComparator />, Exercise 4.1 (8 pts) |
| ↳ `4.3` Equality and Ordered Comparisons | `L709..L749` (41, 2.5%) | ordered comparisons, `slt`, `slti`, `sltu`, `sltiu` | 4.4, 5.1, 6.1, 8.3 | Exercise 4.2 (6 pts) |
| ↳ `4.4` Hardware Equivalence Summary | `L750..L763` (14, 0.9%) | — | 5.1, 6.1, 8.3 | — |
| ↳ `4.5` Full 32-Bit Constant Construction | `L764..L855` (92, 5.6%) | Load Upper Immediate, Add Upper Immediate to PC, `lui`, `auipc`, `cur_pc`, `addi` | 5.1, 5.3, 6.1, 6.3 | Exercise 4.3 (7 pts) |
| ↳ `4.6` Full 64-Bit Integer Multiplication | `L856..L938` (83, 5.1%) | RV32M, Multiply, Multiply High, `mul`, `mulh`, `mulhsu`, `mulhu` | 6.2, 7.1, 7.2, 8.2 | <Product64Inspector />, Exercise 4.4 (7 pts) |
| ↳ `4.7` Truncating Integer Division Semantics | `L939..L1016` (78, 4.8%) | Divide, Divide Unsigned, Remainder, `div`, `divu`, `rem`, `remu` | 5.1, 5.2, 5.3, 6.1 | <TruncatingDivisionComparator />, Exercise 4.5 (7 pts) |
| **Sec 5: 5. Memory Map and Bus Peripherals** | `L1017..L1161` (145, 8.9%) | — | — | — |
| ↳ `5.1` Address Decoding and Memory Regions | `L1022..L1074` (53, 3.2%) | bus, Memory-Mapped Input/Output, System-on-Chip, `add`, `lbu`, `lhu`, `BOOT_ROM_BASE` | 5.2, 5.3, 8.1, 9.3 | — |
| ↳ `5.2` Natural Alignment and Little-Endian Storage | `L1075..L1092` (18, 1.1%) | natural alignment, little-endian byte order, `RV32Oracle._exec_load`, `RV32Oracle._exec_store`, `bus_read`, `bus_write` | 5.3, 6.1, 8.2, 8.3 | — |
| ↳ `5.3` Monotonic Timer and Serial Console | `L1093..L1161` (69, 4.2%) | First-In, First-Out, baud, 64-Bit Counter Lifetime and Rollover Tearing, `mtime`, `mtimecmp`, `uart_tx_buf`, `uart_rx_fifo` | 6.2, 6.3, 8.2, 8.3 | Exercise 5.1 (7 pts) |
| **Sec 6: 6. Control Flow and Trap Handling** | `L1162..L1313` (152, 9.3%) | — | — | — |
| ↳ `6.1` Conditional Branches and Subroutine Jumps | `L1167..L1197` (31, 1.9%) | link address, `RV32Oracle._exec_branch`, `_exec_jal`, `_exec_jalr`, `beq` | 8.1, 8.3, 9.4 | — |
| ↳ `6.2` Control and Status Registers | `L1198..L1256` (59, 3.6%) | Zicsr, Control and Status Registers, hardware thread, `_write_csr`, `_read_csr`, `misa`, `CAUSE_ILLEGAL_INSN` | 6.3, 8.1, 8.2, 9.4 | — |
| ↳ `6.3` Trap Entry and Return Choreography | `L1257..L1313` (57, 3.5%) | Exact Resume Offset and Stackable Interrupts, Interrupt Service Routine, Zero-Clobber `mscratch` Bootstrap, `RV32Oracle._check_pending_interrupt`, `RV32Oracle._take_trap`, `WORD_ALIGN_MASK`, `mcause` | 8.1, 8.3, 9.3, 9.4 | — |
| **Sec 7: 7. Custom Neural Multiply-Accumulate Extension** | `L1314..L1419` (106, 6.5%) | — | — | — |
| ↳ `7.1` Saturating Clamping and Dual-Lane Datapath | `L1325..L1358` (34, 2.1%) | saturating arithmetic, Register-File Port Limit, Hardwired 18-Bit Multiplier Blocks, `s16`, `sat32`, `RV32Oracle`, `enc_mac` | 7.2, 8.1, 8.2, 8.3 | <XapexMacDatapath /> |
| ↳ `7.2` First-Step Accumulator Overflow Proof | `L1359..L1419` (61, 3.7%) | No First-Step Negative Saturation, Unique First-Step Positive Saturation, `INT32_MAX`, `base_acc`, `mac` | 8.3, 9.2, 9.6 | Exercise 7.1 (7 pts) |
| **Sec 8: 8. Unified Decoding and Lockstep Verification** | `L1420..L1500` (81, 5.0%) | — | — | — |
| ↳ `8.1` Unified 32-Bit Instruction Decoder | `L1425..L1450` (26, 1.6%) | `fence`, `ebreak`, `wfi`, `bgeu` | 8.2, 8.3, 9.1, 9.4 | <RiscvBitfieldDecoder /> |
| ↳ `8.2` Deterministic Fetch and Retirement Priority | `L1451..L1467` (17, 1.0%) | Pre-Fetch Clock Advance, Pre-Fetch Interrupt Priority, Fault-Checked Operand Latching and Dispatch, `StepTrace`, `MASK64`, `ExecOutcome`, `rd_val` | 8.3, 9.4, 9.5, 9.6 | — |
| ↳ `8.3` Precise Faults and Inductive Trace Equivalence | `L1468..L1500` (33, 2.0%) | Precise Exception Atomicity, `mret`, `mtvec`, `mem_addr`, `mem_val` | 9.4, 9.5 | <OracleStepTracer /> |
| **Sec 9: 9. Problems** | `L1501..L1636` (136, 8.3%) | — | — | — |
| ↳ `9.1` Problem 1: Two's Complement and Constant Bias | `L1506..L1525` (20, 1.2%) | `hi20`, `lo12` | — | — |
| ↳ `9.2` Problem 2: Shifts, Comparisons, 64-Bit Products, and Division | `L1526..L1549` (24, 1.5%) | `_exec_muldiv`, `srai`, `imm12`, `rs1_u` | — | — |
| ↳ `9.3` Problem 3: Address Decoding, Alignment, and 64-Bit Timers | `L1550..L1574` (25, 1.5%) | `_clint_read`, `_exec_load`, `CLINT_BASE`, `CAUSE_LOAD_MISALIGNED` | 9.4 | — |
| ↳ `9.4` Problem 4: Indirect Jumps, Decoding, and Fault Atomicity | `L1575..L1597` (23, 1.4%) | `test_jalr_bit0_snap_and_untaken_misaligned_branch`, `target`, `mepc`, `mtval` | 9.5 | — |
| ↳ `9.5` Problem 5: Control Registers, Preemption, and Step Traces | `L1598..L1617` (20, 1.2%) | `test_clint_timer_interrupt_and_ecall_handler`, `test_vectored_mtvec_dispatch_and_sync_ecall_fallback`, `mie`, `mcycle` | — | — |
| ↳ `9.6` Problem 6: Neural Accumulator Preloading and Saturation | `L1618..L1636` (19, 1.2%) | `_exec_mac`, `test_xapex_custom_mac_dot_product_and_saturation`, `x10`, `x11` | — | — |
