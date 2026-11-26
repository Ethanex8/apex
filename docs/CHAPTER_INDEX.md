# Apex Textbook Chapter Index

Compact, auto-generated structural and dependency map (`scripts/build.py`) for isolated textbook reviewers and readers.

## Chapter 1 Instruction Set Architecture (`systems/brain/chapters/01_isa_and_binary_arithmetic.md`, 1389 lines)

| Section | Lines (% Ch.) | Newly Defined Terms & Symbols | First Later Consumers | Visuals & Examples |
| :--- | :--- | :--- | :--- | :--- |
| **Sec 1: 1. Software Golden Reference Models** | `L7..L47` (41, 3.0%) | — | — | — |
| ↳ `1.1` Instruction Set Architecture Boundaries | `L32..L47` (16, 1.2%) | Instruction Set Architecture, Architectural State, registers, `step` | 2.4, 3.1, 3.2, 3.3 | — |
| **Sec 2: 2. Fixed-Width Binary Arithmetic** | `L48..L398` (351, 25.3%) | — | — | — |
| ↳ `2.1` Bitwise Wire Gates and Bit Shifts | `L55..L75` (21, 1.5%) | hexadecimal, bitwise gate, bit shifts | 2.2 | — |
| ↳ `2.2` Unsigned Binary Integers | `L76..L116` (41, 3.0%) | unsigned integer interpretation, bijection | 2.3, 2.5, 2.6, 2.7 | — |
| ↳ `2.3` Binary Addition and Carry Propagation | `L117..L146` (30, 2.2%) | Binary addition, No Carry ($t_i \in \{0, 1\}$), Generate Carry ($t_i \in \{2, 3\}$) | 2.4, 2.5, 2.6, 4.2 | <BinaryAdditionCarryDiagram /> |
| ↳ `2.4` Modular Rings and Congruence | `L147..L203` (57, 4.1%) | Euclidean division, modular ring, residue class | 2.5, 2.6, 2.7, 4.1 | <UnsignedClockRing />, Example 2.1 (3 pts) |
| ↳ `2.5` Two's Complement Signed Integers | `L204..L257` (54, 3.9%) | two's complement, Most Significant Bit, signed overflow, `MASK32`, `u32` | 2.6, 2.7, 4.1, 4.2 | <ModularRingAdder /> |
| ↳ `2.6` Shared Adder and Negation Circuits | `L258..L349` (92, 6.6%) | Sign-Agnostic Addition and Subtraction, Negation via Invert Plus One, Subtraction via Invert Plus One, `INT32_MIN` | 4.1, 4.7, 7.2 | Example 2.2 (0 pts) |
| ↳ `2.7` Sign-Agnostic Left-Shift Scaling | `L350..L398` (49, 3.5%) | left shift | 4.4 | Example 2.3 (0 pts) |
| **Sec 3: 3. Core Registers and Instruction Encoding** | `L399..L562` (164, 11.8%) | — | — | — |
| ↳ `3.1` Program Counter and Hardwired Zero Register | `L404..L423` (20, 1.4%) | Program Counter, General-Purpose Register File, `x31`, `Oracle._set_reg` | 6.2, 6.3, 7.1, 7.2 | — |
| ↳ `3.2` Six Functional Instruction Families | `L424..L439` (16, 1.2%) | 32-bit Base Integer, Integer Multiply and Divide, RV32IM, `brain` | 3.3, 3.4, 4.1, 4.3 | — |
| ↳ `3.3` Bitfield Layouts and Offset Reach | `L440..L485` (46, 3.3%) | assembly syntax, Add, immediate, `insn`, `rs1`, `rs2`, `imm` | 3.4, 4.1, 4.3, 4.5 | <RiscvFormatMatrix /> |
| ↳ `3.4` Widening Narrow Signed and Unsigned Integers | `L486..L562` (77, 5.5%) | sign extension, zero extension, fan-out, `sign_extend`, `s32`, `mask`, `sign_bit` | 4.1, 4.2, 4.3, 4.4 | <SignExtensionWidener /> |
| **Sec 4: 4. Integer Arithmetic, Multiplication, and Division** | `L563..L875` (313, 22.5%) | — | — | — |
| ↳ `4.1` Base Integer Operations and Zero Idioms | `L569..L600` (32, 2.3%) | shift amount, pseudoinstructions, `funct3`, `funct7`, `_exec_op_imm`, `_exec_op_reg` | 4.2, 4.4, 4.6, 4.7 | — |
| ↳ `4.2` Right Shifts and Integer Floor Division | `L601..L660` (60, 4.3%) | logical right shift, arithmetic right shift, floor division, `srl`, `srli`, `sra`, `srai` | 4.4, 4.7, 5.3, 5.4 | <RightShiftComparator /> |
| ↳ `4.3` Equality and Ordered Comparisons | `L661..L683` (23, 1.7%) | ordered comparisons, `slt`, `slti`, `sltu`, `sltiu` | 4.4, 4.5, 4.7, 5.3 | Example 4.1 (0 pts) |
| ↳ `4.4` Base Integer Hardware Equivalence | `L684..L697` (14, 1.0%) | — | 4.5, 4.6, 5.3, 6.1 | — |
| ↳ `4.5` Full 32-Bit Constant Construction | `L698..L741` (44, 3.2%) | Load Upper Immediate, Add Upper Immediate to PC, modulus scaling, `imm20`, `lui`, `auipc`, `cur_pc` | 4.6, 5.1, 5.5, 6.1 | <LuiBiasCarryDiagram />, Example 4.2 (2 pts) |
| ↳ `4.6` Full 64-Bit Integer Multiplication | `L742..L814` (73, 5.3%) | RV32M, Multiply, Multiply High, `mul`, `mulh`, `mulhsu`, `mulhu` | 6.2, 7.1, 7.2, 8.2 | <Product64SplitDiagram />, Example 4.3 (0 pts) |
| ↳ `4.7` Truncating Integer Division Semantics | `L815..L875` (61, 4.4%) | Divide, Divide Unsigned, Remainder, `div`, `divu`, `rem`, `remu` | 5.3, 5.4, 5.5, 6.1 | <TruncatingDivisionComparator />, Example 4.4 (2 pts) |
| **Sec 5: 5. Memory Map and Bus Peripherals** | `L876..L1035` (160, 11.5%) | — | — | — |
| ↳ `5.1` Load and Store Memory Instructions | `L881..L895` (15, 1.1%) | `add`, `lbu`, `lhu` | 5.2, 5.4, 5.5, 6.1 | — |
| ↳ `5.2` System-on-Chip Memory Map | `L896..L916` (21, 1.5%) | bus, Memory-Mapped Input/Output, System-on-Chip, `BOOT_ROM_BASE`, `BRAM_BASE`, `QSPI_BASE`, `SDRAM_BASE` | — | — |
| ↳ `5.3` Power-of-Two Prefix Decoding | `L917..L938` (22, 1.6%) | `addr`, `Oracle`, `load_bytes`, `load_words` | 5.4, 5.5, 6.1, 6.2 | — |
| ↳ `5.4` Natural Alignment and Little-Endian Storage | `L939..L963` (25, 1.8%) | natural alignment, little-endian byte order, `Oracle._exec_load`, `Oracle._exec_store`, `bus_read`, `bus_write` | 6.1, 8.2, 8.3 | Example 5.1 (0 pts) |
| ↳ `5.5` Monotonic Timer and Serial Console | `L964..L1035` (72, 5.2%) | First-In, First-Out, baud rate, 64-Bit Counter Lifetime and Rollover Tearing, `push_uart_rx`, `read_uart_tx`, `mtime`, `mtimecmp` | 6.2, 6.3, 8.2, 8.3 | <TimerRolloverTearDiagram />, Example 5.2 (0 pts) |
| **Sec 6: 6. Control Flow and Trap Handling** | `L1036..L1213` (178, 12.8%) | — | — | — |
| ↳ `6.1` Conditional Branches and Subroutine Jumps | `L1041..L1082` (42, 3.0%) | link address, Bit 0 Snapped (`jalr x2, 1(x2)`), Bit 1 Misaligned Trap (`jalr x2, 2(x2)`), `Oracle._exec_branch`, `_exec_jal`, `_exec_jalr`, `imm13` | 8.1 | Example 6.1 (2 pts) |
| ↳ `6.2` Control Registers and System Instructions | `L1083..L1145` (63, 4.5%) | hardware thread, hart, Control and Status Registers, `_write_csr`, `_read_csr`, `misa`, `mstatus` | 6.3, 7.1, 8.2, 8.3 | — |
| ↳ `6.3` Trap Entry and Return Choreography | `L1146..L1213` (68, 4.9%) | Atomic Interrupt Masking and Restore, Interrupt Service Routine, Exact Resume Offset, `mepc`, `mcause`, `mtval`, `mtvec` | 8.1, 8.3 | Example 6.2 (2 pts) |
| **Sec 7: 7. Custom Neural Multiply-Accumulate Extension** | `L1214..L1310` (97, 7.0%) | — | — | — |
| ↳ `7.1` Saturating Clamping and Dual-Lane Datapath | `L1225..L1261` (37, 2.7%) | saturating arithmetic, Register-File Port Limit, Hardwired 18-Bit Multiplier Blocks, `sat32`, `s16`, `enc_mac`, `mac_acc` | 7.2, 8.2, 8.3 | <XapexMacDatapath /> |
| ↳ `7.2` First-Step Accumulator Overflow Proof | `L1262..L1310` (49, 3.5%) | No First-Step Negative Saturation, Unique First-Step Positive Saturation, Bias Preload and Multiply-Accumulate, `INT32_MAX`, `_exec_mac`, `test_xapex_custom_mac_dot_product_and_saturation`, `x10` | — | Example 7.1 (2 pts) |
| **Sec 8: 8. Unified Decoding and Lockstep Verification** | `L1311..L1389` (79, 5.7%) | — | — | — |
| ↳ `8.1` Unified 32-Bit Instruction Decoder | `L1316..L1340` (25, 1.8%) | `fence`, `beq`, `bgeu`, `jalr` | 8.2, 8.3 | <RiscvBitfieldDecoder /> |
| ↳ `8.2` Deterministic Fetch and Retirement Priority | `L1341..L1358` (18, 1.3%) | Pre-Fetch Clock Advance, Pre-Fetch Interrupt Priority, Fault-Checked Operand Latching and Dispatch, `StepTrace`, `MASK64`, `ExecOutcome`, `rd_val` | 8.3 | — |
| ↳ `8.3` Precise Faults and Inductive Trace Equivalence | `L1359..L1389` (31, 2.2%) | Precise Exception Atomicity, `mret`, `mem_addr`, `mem_val`, `mem_write` | — | <OracleStepTracer /> |
