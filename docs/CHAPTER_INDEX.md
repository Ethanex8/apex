# Apex Textbook Chapter Index

Compact, auto-generated structural and dependency map (`scripts/build.py`) for isolated textbook reviewers and readers.

## Chapter 1 Instruction Set Architecture (`systems/brain/chapters/01_isa_and_binary_arithmetic.md`, 1131 lines)

| Section | Lines (% Ch.) | Newly Defined Terms & Symbols | First Later Consumers | Visuals |
| :--- | :--- | :--- | :--- | :--- |
| **Sec 1: 1. Software Golden Reference Models** | `L7..L47` (41, 3.6%) | — | — | — |
| ↳ `1.1` Instruction Set Architecture Boundaries | `L32..L47` (16, 1.4%) | Instruction Set Architecture, Architectural State, registers, `step` | 2.4, 3.1, 3.2, 3.3 | — |
| **Sec 2: 2. Fixed-Width Binary Arithmetic** | `L48..L259` (212, 18.7%) | — | — | — |
| ↳ `2.1` Bitwise Wire Gates and Bit Shifts | `L55..L74` (20, 1.8%) | bitwise gate, bit shifts | — | — |
| ↳ `2.2` Unsigned Binary Integers | `L75..L99` (25, 2.2%) | hexadecimal, unsigned integer interpretation, bijection | 2.3, 2.5, 2.6, 2.7 | — |
| ↳ `2.3` Binary Addition and Carry Propagation | `L100..L121` (22, 1.9%) | Binary addition, No Carry ($t_i \in \{0, 1\}$), Generate Carry ($t_i \in \{2, 3\}$) | 2.4, 2.5, 2.6, 4.2 | <BinaryAdditionCarryDiagram /> |
| ↳ `2.4` Modular Rings and Congruence | `L122..L162` (41, 3.6%) | Euclidean division, modular ring, residue class | 2.7, 4.1, 4.4, 5.3 | <UnsignedClockRing /> |
| ↳ `2.5` Two's Complement Signed Integers | `L163..L201` (39, 3.4%) | two's complement, Most Significant Bit, signed overflow, `MASK32`, `u32` | 2.6, 2.7, 4.1, 4.2 | <ModularRingAdder /> |
| ↳ `2.6` Shared Adder and Negation Circuits | `L202..L241` (40, 3.5%) | Sign-Agnostic Addition and Subtraction, Negation via Invert Plus One, Subtraction via Invert Plus One, `INT32_MIN` | 4.1, 4.7, 7.2 | — |
| ↳ `2.7` Sign-Agnostic Left-Shift Scaling | `L242..L259` (18, 1.6%) | left shift | 4.4 | — |
| **Sec 3: 3. Core Registers and Instruction Encoding** | `L260..L392` (133, 11.8%) | — | — | — |
| ↳ `3.1` Program Counter and Hardwired Zero Register | `L265..L284` (20, 1.8%) | Program Counter, General-Purpose Register File, `x31`, `Oracle._set_reg` | 6.2, 6.3, 7.1, 8.2 | — |
| ↳ `3.2` Six Functional Instruction Families | `L285..L300` (16, 1.4%) | 32-bit Base Integer, Integer Multiply and Divide, RV32IM, `brain` | 3.3, 3.4, 4.1, 4.3 | — |
| ↳ `3.3` Bitfield Layouts and Offset Reach | `L301..L346` (46, 4.1%) | assembly syntax, Add, immediate, `insn`, `rs1`, `rs2`, `imm` | 3.4, 4.1, 4.3, 4.5 | <RiscvFormatMatrix /> |
| ↳ `3.4` Widening Narrow Signed and Unsigned Integers | `L347..L392` (46, 4.1%) | sign extension, zero extension, fan-out, `sign_extend`, `s32`, `mask`, `sign_bit` | 4.1, 4.2, 4.3, 4.4 | <SignExtensionWidener /> |
| **Sec 4: 4. Integer Arithmetic, Multiplication, and Division** | `L393..L642` (250, 22.1%) | — | — | — |
| ↳ `4.1` Base Integer Operations and Zero Idioms | `L399..L430` (32, 2.8%) | shift amount, pseudoinstructions, `funct3`, `funct7`, `_exec_op_imm`, `_exec_op_reg` | 4.2, 4.4, 4.6, 4.7 | — |
| ↳ `4.2` Right Shifts and Integer Floor Division | `L431..L474` (44, 3.9%) | logical right shift, arithmetic right shift, floor division, `srl`, `srli`, `sra`, `srai` | 4.4, 4.7, 5.3, 5.4 | <RightShiftComparator /> |
| ↳ `4.3` Equality and Ordered Comparisons | `L475..L490` (16, 1.4%) | ordered comparisons, `slt`, `slti`, `sltu`, `sltiu` | 4.4, 4.5, 4.7, 5.3 | — |
| ↳ `4.4` Base Integer Hardware Equivalence | `L491..L504` (14, 1.2%) | — | 5.3, 6.1, 8.3 | — |
| ↳ `4.5` Full 32-Bit Constant Construction | `L505..L540` (36, 3.2%) | Load Upper Immediate, Add Upper Immediate to PC, compiler or assembler, `imm20`, `lui`, `auipc`, `cur_pc` | 5.1, 5.5, 6.1, 6.3 | <LuiBiasCarryDiagram /> |
| ↳ `4.6` Full 64-Bit Integer Multiplication | `L541..L587` (47, 4.2%) | RV32M, Multiply, Multiply High, `mul`, `mulh`, `mulhsu`, `mulhu` | 6.2, 7.1, 8.2 | <Product64SplitDiagram /> |
| ↳ `4.7` Truncating Integer Division Semantics | `L588..L642` (55, 4.9%) | Divide, Divide Unsigned, Remainder, `div`, `divu`, `rem`, `remu` | 5.3, 5.4, 5.5, 6.1 | <TruncatingDivisionComparator /> |
| **Sec 5: 5. Memory Map and Bus Peripherals** | `L643..L793` (151, 13.4%) | — | — | — |
| ↳ `5.1` Load and Store Memory Instructions | `L648..L663` (16, 1.4%) | `add`, `lbu`, `lhu` | 5.2, 5.4, 5.5, 6.1 | — |
| ↳ `5.2` System-on-Chip Memory Map | `L664..L687` (24, 2.1%) | Memory-Mapped Input/Output, System-on-Chip, Core-Local Interruptor, `BOOT_ROM_BASE`, `BRAM_BASE`, `QSPI_BASE`, `SDRAM_BASE` | — | — |
| ↳ `5.3` Power-of-Two Prefix Decoding | `L688..L707` (20, 1.8%) | `addr` | 5.4, 6.3, 8.1 | — |
| ↳ `5.4` Natural Alignment and Little-Endian Storage | `L708..L727` (20, 1.8%) | natural alignment, little-endian byte order, `Oracle._exec_load`, `Oracle._exec_store`, `bus_read`, `bus_write` | 6.1, 6.3, 8.2, 8.3 | — |
| ↳ `5.5` Monotonic Timer and Serial Console | `L728..L793` (66, 5.8%) | First-In, First-Out, baud rate, 64-Bit Counter Lifetime and Rollover Tearing, `push_uart_rx`, `read_uart_tx`, `reset`, `mtime` | 6.2, 6.3, 8.2, 8.3 | <TimerRolloverTearDiagram /> |
| **Sec 6: 6. Control Flow and Trap Handling** | `L794..L967` (174, 15.4%) | — | — | — |
| ↳ `6.1` Conditional Branches and Subroutine Jumps | `L799..L835` (37, 3.3%) | link address, `Oracle._exec_branch`, `_exec_jal`, `_exec_jalr`, `imm13` | 8.1 | — |
| ↳ `6.2` Control Registers and System Instructions | `L836..L899` (64, 5.7%) | hardware thread, hart, Control and Status Registers, `_write_csr`, `_read_csr`, `misa`, `mstatus` | 6.3, 7.1, 7.2, 8.2 | — |
| ↳ `6.3` Trap Entry and Return Choreography | `L900..L967` (68, 6.0%) | Atomic Interrupt Masking and Restore, Interrupt Service Routine, Exact Resume Offset, `mepc`, `mcause`, `mtval`, `mtvec` | 8.1, 8.3 | — |
| **Sec 7: 7. Custom Neural Multiply-Accumulate Extension** | `L968..L1051` (84, 7.4%) | — | — | — |
| ↳ `7.1` Saturating Clamping and Dual-Lane Datapath | `L979..L1015` (37, 3.3%) | saturating arithmetic, Register-File Port Limit, Hardwired 18-Bit Multiplier Blocks, `sat32`, `Oracle`, `s16`, `enc_mac` | 7.2, 8.2, 8.3 | <XapexMacDatapath /> |
| ↳ `7.2` First-Step Accumulator Overflow Bounds | `L1016..L1051` (36, 3.2%) | No First-Step Negative Saturation, Unique First-Step Positive Saturation, Positive Peak First, `INT32_MAX`, `mac` | 8.3 | — |
| **Sec 8: 8. Unified Decoding and Lockstep Verification** | `L1052..L1131` (80, 7.1%) | — | — | — |
| ↳ `8.1` Unified 32-Bit Instruction Decoder | `L1057..L1082` (26, 2.3%) | `CAUSE_ILLEGAL_INSN`, `fence`, `beq`, `bgeu` | 8.2, 8.3 | <RiscvBitfieldDecoder /> |
| ↳ `8.2` Deterministic Fetch and Retirement Priority | `L1083..L1100` (18, 1.6%) | Pre-Fetch Clock Advance, Pre-Fetch Interrupt Priority, Instruction-Fetch Alignment and Access Check, `StepTrace`, `MASK64`, `mcycle`, `_fetch_instruction` | 8.3 | — |
| ↳ `8.3` Precise Faults and Inductive Trace Equivalence | `L1101..L1131` (31, 2.7%) | Precise Exception Atomicity, `next_pc`, `mret`, `rd_val`, `mem_addr` | — | <OracleStepTracer /> |
