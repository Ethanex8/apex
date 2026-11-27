# Apex Textbook Chapter Index

Compact, auto-generated structural and dependency map (`scripts/build.py`) for isolated textbook reviewers and readers.

## Chapter 1 Instruction Set Architecture (`systems/brain/chapters/01_isa_and_binary_arithmetic.md`, 1139 lines)

| Section | Lines (% Ch.) | Newly Defined Terms & Symbols | First Later Consumers | Visuals |
| :--- | :--- | :--- | :--- | :--- |
| **Sec 1: 1. Software Golden Reference Models** | `L7..L47` (41, 3.6%) | — | — | — |
| ↳ `1.1` Instruction Set Architecture Boundaries | `L32..L47` (16, 1.4%) | Instruction Set Architecture, Architectural State, registers, `step` | 2.4, 2.7, 3.1, 3.2 | — |
| **Sec 2: 2. Fixed-Width Binary Arithmetic** | `L48..L261` (214, 18.8%) | — | — | — |
| ↳ `2.1` Bitwise Wire Gates and Bit Shifts | `L55..L74` (20, 1.8%) | bitwise gate, bit shifts | — | — |
| ↳ `2.2` Unsigned Binary Integers | `L75..L99` (25, 2.2%) | hexadecimal, unsigned integer interpretation, bijection | 2.3, 2.5, 2.6, 2.7 | — |
| ↳ `2.3` Binary Addition and Carry Propagation | `L100..L121` (22, 1.9%) | Binary addition, carry-out, No Carry ($t_i \in \{0, 1\}$) | 2.4, 2.5, 2.6, 4.2 | <BinaryAdditionCarryDiagram /> |
| ↳ `2.4` Modular Rings and Congruence | `L122..L162` (41, 3.6%) | Euclidean division, modular ring, residue class | 2.7, 4.1, 4.4, 5.3 | <UnsignedClockRing /> |
| ↳ `2.5` Two's Complement Signed Integers | `L163..L195` (33, 2.9%) | sign-magnitude, two's complement, Most Significant Bit, `MASK32`, `u32` | 2.6, 2.7, 4.1, 4.2 | <ModularRingAdder /> |
| ↳ `2.6` Unified Addition, Negation, and Subtraction | `L196..L235` (40, 3.5%) | Sign-Agnostic Addition and Subtraction, Negation via Invert Plus One, Subtraction via Invert Plus One, `INT32_MIN` | 4.1, 4.2, 4.7, 5.3 | — |
| ↳ `2.7` Sign-Agnostic Left-Shift Scaling | `L236..L261` (26, 2.3%) | left shift | 4.4 | — |
| **Sec 3: 3. Core Registers and Instruction Encoding** | `L262..L393` (132, 11.6%) | — | — | — |
| ↳ `3.1` Program Counter and Hardwired Zero Register | `L267..L286` (20, 1.8%) | Program Counter, General-Purpose Register File, `x31`, `Oracle._set_reg` | 6.2, 6.3, 7.1, 8.2 | — |
| ↳ `3.2` Six Functional Instruction Families | `L287..L302` (16, 1.4%) | 32-bit Base Integer, Integer Multiply and Divide, RV32IM, `brain` | 3.3, 3.4, 4.1, 4.2 | — |
| ↳ `3.3` Bitfield Layouts and Offset Reach | `L303..L347` (45, 4.0%) | assembly syntax, Add, immediate, `insn`, `rs1`, `rs2`, `imm` | 3.4, 4.1, 4.3, 4.5 | <RiscvFormatMatrix /> |
| ↳ `3.4` Widening Narrow Signed and Unsigned Integers | `L348..L393` (46, 4.0%) | sign extension, zero extension, `sign_extend`, `s32`, `mask`, `sign_bit` | 4.1, 4.2, 4.3, 4.4 | <SignExtensionWidener /> |
| **Sec 4: 4. Integer Arithmetic, Multiplication, and Division** | `L394..L643` (250, 21.9%) | — | — | — |
| ↳ `4.1` Base Integer Operations and Zero Idioms | `L400..L431` (32, 2.8%) | shift amount, pseudoinstructions, `funct3`, `funct7`, `_exec_op_imm`, `_exec_op_reg` | 4.2, 4.3, 4.4, 4.6 | — |
| ↳ `4.2` Right Shifts and Integer Floor Division | `L432..L475` (44, 3.9%) | logical right shift, arithmetic right shift, floor division, `srl`, `srli`, `sra`, `srai` | 4.4, 4.7, 5.3, 5.4 | <RightShiftComparator /> |
| ↳ `4.3` Equality and Ordered Comparisons | `L476..L491` (16, 1.4%) | ordered comparisons, `slt`, `slti`, `sltu`, `sltiu` | 4.4, 4.5, 4.7, 5.3 | — |
| ↳ `4.4` Base Integer Signedness Equivalence | `L492..L505` (14, 1.2%) | — | 4.6, 5.1, 5.3, 6.1 | — |
| ↳ `4.5` Full 32-Bit Constant Construction | `L506..L541` (36, 3.2%) | Load Upper Immediate, Add Upper Immediate to PC, compiler or assembler, `imm20`, `lui`, `auipc`, `cur_pc` | 5.1, 5.5, 6.1, 6.3 | <LuiBiasCarryDiagram /> |
| ↳ `4.6` Full 64-Bit Integer Multiplication | `L542..L588` (47, 4.1%) | RV32M, Multiply, Multiply High, `mul`, `mulh`, `mulhsu`, `mulhu` | 6.2, 7.1, 8.2 | <Product64SplitDiagram /> |
| ↳ `4.7` Truncating Integer Division Semantics | `L589..L643` (55, 4.8%) | Divide, Divide Unsigned, Remainder, `div`, `divu`, `rem`, `remu` | 5.3, 5.4, 5.5, 6.1 | <TruncatingDivisionComparator /> |
| **Sec 5: 5. Memory Map and Bus Peripherals** | `L644..L794` (151, 13.3%) | — | — | — |
| ↳ `5.1` Load and Store Memory Instructions | `L649..L664` (16, 1.4%) | `add`, `lbu`, `lhu` | 5.2, 5.4, 5.5, 6.1 | — |
| ↳ `5.2` System-on-Chip Memory Map | `L665..L688` (24, 2.1%) | Memory-Mapped Input/Output, System-on-Chip, Core-Local Interruptor, `BOOT_ROM_BASE`, `BRAM_BASE`, `QSPI_BASE`, `SDRAM_BASE` | — | — |
| ↳ `5.3` Power-of-Two Prefix Decoding | `L689..L708` (20, 1.8%) | `addr` | 5.4, 6.3, 8.1 | — |
| ↳ `5.4` Natural Alignment and Little-Endian Storage | `L709..L728` (20, 1.8%) | natural alignment, little-endian byte order, `Oracle._exec_load`, `Oracle._exec_store`, `bus_read`, `bus_write` | 6.1, 6.3, 8.2, 8.3 | — |
| ↳ `5.5` Monotonic Timer and Serial Console | `L729..L794` (66, 5.8%) | First-In, First-Out, baud rate, 64-Bit Counter Lifetime and Rollover Tearing, `push_uart_rx`, `read_uart_tx`, `reset`, `mtime` | 6.2, 6.3, 8.2, 8.3 | <TimerRolloverTearDiagram /> |
| **Sec 6: 6. Control Flow and Trap Handling** | `L795..L974` (180, 15.8%) | — | — | — |
| ↳ `6.1` Conditional Branches and Subroutine Jumps | `L800..L835` (36, 3.2%) | link address, `Oracle._exec_branch`, `_exec_jal`, `_exec_jalr`, `imm13` | 8.1 | — |
| ↳ `6.2` Control Registers and System Instructions | `L836..L899` (64, 5.6%) | hardware thread, hart, Control and Status Registers, `_write_csr`, `_read_csr`, `misa`, `mstatus` | 6.3, 7.1, 7.2, 8.2 | — |
| ↳ `6.3` Trap Entry and Return Choreography | `L900..L974` (75, 6.6%) | Atomic Interrupt Masking and Restore, Interrupt Service Routine, Exact Resume Offset, `mepc`, `mcause`, `mtval`, `mtvec` | 8.1, 8.3 | — |
| **Sec 7: 7. Custom Neural Multiply-Accumulate Extension** | `L975..L1059` (85, 7.5%) | — | — | — |
| ↳ `7.1` Saturating Clamping and Dual-Lane Datapath | `L986..L1022` (37, 3.2%) | saturating arithmetic, Register-File Port Limit, Hardwired 18-Bit Multiplier Blocks, `sat32`, `Oracle`, `s16`, `enc_mac` | 7.2, 8.2, 8.3 | <XapexMacDatapath /> |
| ↳ `7.2` First-Step Accumulator Overflow Bounds | `L1023..L1059` (37, 3.2%) | No First-Step Negative Saturation, Unique First-Step Positive Saturation, Positive Peak First, `INT32_MAX`, `mac` | 8.3 | — |
| **Sec 8: 8. Unified Decoding and Lockstep Verification** | `L1060..L1139` (80, 7.0%) | — | — | — |
| ↳ `8.1` Unified 32-Bit Instruction Decoder | `L1065..L1090` (26, 2.3%) | `CAUSE_ILLEGAL_INSN`, `fence`, `beq`, `bgeu` | 8.2, 8.3 | <RiscvBitfieldDecoder /> |
| ↳ `8.2` Deterministic Fetch and Retirement Priority | `L1091..L1108` (18, 1.6%) | Pre-Fetch Clock Advance, Pre-Fetch Interrupt Priority, Instruction-Fetch Alignment and Access Check, `StepTrace`, `MASK64`, `mcycle`, `_fetch_instruction` | 8.3 | — |
| ↳ `8.3` Precise Faults and Inductive Trace Equivalence | `L1109..L1139` (31, 2.7%) | Precise Exception Atomicity, `next_pc`, `mret`, `rd_val`, `mem_addr` | — | <OracleStepTracer /> |
