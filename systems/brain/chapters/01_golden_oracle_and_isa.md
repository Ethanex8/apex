# Chapter 1 (`brain-01`): The Golden ISA Contract, Binary Math & Instruction Decoding

> **Reading Time**: about 10–12 minutes  
> **Focus**: How [`oracle.py`](../sim/oracle.py) specifies our **RISC-V** processor's **Instruction Set Architecture (ISA)**—covering architectural state, 32-bit two's complement math, instruction bit-fields, little-endian memory, and traps.

---

## 1. Why This Exists: The Golden Reference Contract

Suppose you are designing a custom processor from scratch. Before you wire together hardware logic or boot a real-time operating system on it, you need an **unambiguous specification** of what every machine instruction is supposed to do. In processor engineering, that executable specification is called a **golden reference emulator** (or **oracle**).

[`oracle.py`](../sim/oracle.py) is that golden oracle for our processor. It defines the **Instruction Set Architecture (ISA)**—the programmer-visible contract consisting of:
- What state the processor holds between instructions (**registers**, **program counter**, **memory**, **control registers**).
- How 32-bit binary instruction words are decoded into operations.
- How every valid instruction—and every error condition—updates that state.

Think of [`RV32Oracle`](../sim/oracle.py#L291-L1025) as a **deterministic state machine** for an in-memory computer:

$$S_{t+1} = \text{step}(S_t)$$

Each call to [`RV32Oracle.step()`](../sim/oracle.py#L906-L1007) runs one complete **Fetch → Decode → Execute → Commit** cycle:
1. **Fetch**: Read the 32-bit instruction word stored in memory at the current address (`self.pc`).
2. **Decode**: Slice out the operation code and register numbers from that 32-bit integer.
3. **Execute**: Perform the arithmetic, memory access, branch check, or system call.
4. **Commit**: Update `self.pc`, registers, and memory once, and return a [`StepTrace`](../sim/oracle.py#L273-L286) receipt describing everything that changed.

Later, when we write real hardware modules in SystemVerilog and run them in the `Verilator` simulator, our testbenches will run the exact same program on both the hardware and [`RV32Oracle`](../sim/oracle.py#L291-L1025), asserting after every retired instruction that the hardware's commit trace matches `oracle.step()` bit for bit.

### Key Terms Used in `oracle.py`

- **RISC-V & RV32IM**: **RISC-V** is an open-standard processor ISA. **`RV32I`** is its 32-bit base integer instruction set (`add`, `lw`, `beq`, etc.), and **`M`** adds integer multiply and divide instructions (`mul`, `div`, `rem`).
- **Zicsr**: The RISC-V extension adding instructions (`CSRRW`, `CSRRS`, `CSRRC`) to atomically read and update **Control and Status Registers (`CSRs`)**, which manage interrupts, traps, and hardware counters.
- **Xapex `mac`**: Our custom 32-bit RISC-V instruction (`custom-0` opcode `0x0B`) that multiplies two pairs of packed 16-bit signed integers and accumulates them into an internal 32-bit register (`mac_acc`) for fast neural walking inference.
- **CLINT (Core-Local Interruptor)**: A memory-mapped 64-bit timer (`mtime`) and alarm comparator (`mtimecmp`) that triggers periodic timer interrupts.
- **UART0 (Universal Asynchronous Receiver-Transmitter)**: A byte-at-a-time serial port used as our debug text console (`115200` baud).

---

## 2. Core Concepts (Anchored to `oracle.py`)

### Concept 1: Architectural State, Hardwired `x0`, and Commit Receipts

Inside [`RV32Oracle.reset()`](../sim/oracle.py#L323-L350), you can see the entire programmer-visible state of our System-on-Chip:

- **Program Counter (`self.pc`)**: The 32-bit byte address of the *next* instruction to fetch (initialized to `BOOT_ROM_BASE = 0x0000_0000`).
- **32 General-Purpose Registers (`self.regs[0..31]`)**: Fast 32-bit integer slots (`x0` through `x31`).
- **Neural Accumulator (`self.mac_acc`)**: A dedicated 32-bit signed accumulator updated by our custom `Xapex mac` instructions.
- **Machine-Mode CSRs (`mstatus`, `mie`, `mtvec`, `mepc`, `mcause`, `mtval`, `mscratch`, `mcycle`, `minstret`)**: Special registers that control trap handling, interrupts, and cycle/instruction counters.
- **Memory & Peripherals**: Four backing memory regions (`rom`, `bram`, `qspi`, `sdram`) plus the `CLINT` timer and `UART0` serial console buffers.

Notice the clean separation inside [`step()`](../sim/oracle.py#L906-L1007): persistent fields on `self` survive from one instruction to the next, while local variables (`opcode`, `rd`, `rs1_u + imm`, `next_pc`) are computed fresh during each call and discarded when `step()` returns.

**Why Register `x0` (`regs[0]`) Is Hardwired to Zero**:
Look at [`_set_reg(rd, val)`](../sim/oracle.py#L608-L613):

```python
def _set_reg(self, rd: int, val: int) -> tuple[int, int]:
    val = u32(val)
    if rd != 0:
        self.regs[rd] = val
    return rd, (0 if rd == 0 else val)
```

Whenever `rd == 0`, the write is silently ignored and `regs[0]` stays `0`. This single rule simplifies the entire instruction set:
- To load the constant `5` into `x1`, you just execute `addi x1, x0, 5` (`0 + 5`)—no separate `MOV_IMM` opcode needed.
- To jump to an address without saving a return address (such as returning from a function), you write `jalr x0, 0(x5)`—sending the return address into `x0` discards it cleanly.

---

### Concept 2: Fixed-Width Binary Math (`u32`, `s32`, Two's Complement & `sign_extend`)

Python integers grow to arbitrary bit widths (`-5` is just `-5`), whereas processor registers hold **exactly 32 bits**. [`oracle.py`](../sim/oracle.py#L112-L143) models fixed-width 32-bit hardware arithmetic explicitly.

#### 1. Modular Wrap-Around (`u32`) and Two's Complement (`s32`)

[`u32(val)`](../sim/oracle.py#L112-L114) masks any Python integer down to its lowest 32 bits (`val & 0xFFFF_FFFF`), wrapping `0xFFFF_FFFF + 1` back around to `0x0000_0000`.

To represent negative numbers inside those same 32 bits without a separate minus sign, processors use **two's complement**. To see why two's complement is so clever, look at a tiny **4-bit** number wheel (16 total bit patterns, `0..15`):

| 4-Bit Pattern | Unsigned Value (`u4`) | Signed Two's Complement (`s4`) |
| :---: | :---: | :---: |
| `0000` .. `0111` | `0` .. `7` | `0` .. `+7` |
| `1000` | `8` | `-8` (`8 - 16`) |
| `1011` | `11` | `-5` (`11 - 16`) |
| `1110` | `14` | `-2` (`14 - 16`) |
| `1111` | `15` | `-1` (`15 - 16`) |

Try adding `-5 + 3` in binary:
- `-5` is `1011` (unsigned `11`).
- `+3` is `0011` (unsigned `3`).
- `1011 + 0011 = 1110` (unsigned `14`), which in two's complement is **`-2`**!

Because unsigned addition modulo $2^N$ and signed two's complement addition produce the **exact same bit pattern**, the processor doesn't need separate `ADD_SIGNED` and `ADD_UNSIGNED` instructions! The same holds for subtraction (`sub`) and left shifts (`sll`).

The *only* operations that care whether bit `31` represents a huge unsigned number (`>= 2^31`) or a negative signed number (`< 0`) are:
- **Ordered comparisons**: `SLT` / `BLT` (signed: `-5 < 3` is true) vs. `SLTU` / `BLTU` (unsigned: `0xFFFF_FFFB < 3` is false).
- **Right shifts**: `SRA` / `SRAI` (**arithmetic** right shift, which copies bit `31` into the left so `-5 >> 1` stays negative: `-3`) vs. `SRL` / `SRLI` (**logical** right shift, which shifts in `0` from the left so `0xFFFF_FFFB >> 1` becomes `0x7FFF_FFFD`).
- **Multiply/divide upper bits & signs**: `MULH` vs. `MULHU`, `DIV` vs. `DIVU`.

That is why [`step()`](../sim/oracle.py#L928-L929) reads the raw 32-bit unsigned values (`rs1_u`, `rs2_u`) and immediately computes their signed interpretations (`rs1_s = s32(rs1_u)`, `rs2_s = s32(rs2_u)`) once up front.

#### 2. Sign Extension (`sign_extend`)

An instruction word is only 32 bits wide, so an embedded constant (**immediate**) inside `addi` or `lw` only gets **12 bits** (`[-2048 .. +2047]`). Before the processor can add that 12-bit constant to a 32-bit register, it must widen the 12-bit number to 32 bits while preserving its negative or positive value.

- Positive 12-bit `+5` (`0x005`, top bit `0`) widens by filling bits `31..12` with `0`s → `0x0000_0005`.
- Negative 12-bit `-5` (`0xFFB`, top bit `1`) widens by copying bit `11` (`1`) across bits `31..12` → `0xFFFF_FFFB` (`-5` in 32-bit two's complement).

Look at how [`sign_extend(val, bits)`](../sim/oracle.py#L138-L143) implements this for any width `bits`:

```python
sign_bit = 1 << (bits - 1)   # For 12 bits: 2048 (0x800)
mask = (1 << bits) - 1       # For 12 bits: 4095 (0xFFF)
val &= mask
return (val ^ sign_bit) - sign_bit
```

Walk through both cases with `bits = 12`:
- If `val = 5`: `(5 ^ 2048) - 2048 = 2053 - 2048 = 5`.
- If `val = 0xFFB` (`4091`, which has bit `11` set): `(4091 ^ 2048) - 2048 = 2043 - 2048 = -5`.

#### 3. Saturation (`sat32`)

Regular integer overflow wraps around from `INT32_MAX` (`+2,147,483,647`) to `INT32_MIN` (`-2,147,483,648`). When accumulating neural-network dot products for robot joint control, a wrap-around flip from maximum positive to maximum negative would slam a motor backward. [`sat32(val)`](../sim/oracle.py#L129-L135) prevents that by clamping the custom `Xapex mac` accumulator (`mac_acc`) to `[INT32_MIN, INT32_MAX]`.

---

### Concept 3: Packing Operations into 32 Bits (The 6 Instruction Formats)

Every RISC-V instruction is packed into a single 32-bit integer (`insn`). In [`step()`](../sim/oracle.py#L921-L926), the decoder slices fixed bit positions using right-shifts and masks:

```python
opcode = insn & 0x7F          # Bits 6..0   (7 bits): instruction family
rd     = (insn >> 7)  & 0x1F  # Bits 11..7  (5 bits): destination register x0..x31
funct3 = (insn >> 12) & 0x7   # Bits 14..12 (3 bits): sub-operation within family
rs1    = (insn >> 15) & 0x1F  # Bits 19..15 (5 bits): source register 1
rs2    = (insn >> 20) & 0x1F  # Bits 24..20 (5 bits): source register 2
funct7 = (insn >> 25) & 0x7F  # Bits 31..25 (7 bits): extra sub-operation
```

Because `opcode`, `rd`, `rs1`, and `rs2` stay in **fixed columns** across every instruction format, different instruction types share the exact same bit extraction:

```text
Bit:  31        25 24   20 19   15 14   12 11    7 6      0
      +-----------+-------+-------+-------+-------+--------+
R:    |  funct7   |  rs2  |  rs1  |funct3 |  rd   | opcode |  add, sub, mul, mac
      +-----------+-------+-------+-------+-------+--------+
I:    |     imm[11:0]     |  rs1  |funct3 |  rd   | opcode |  addi, lw, jalr, csrrw
      +-----------+-------+-------+-------+-------+--------+
S:    | imm[11:5] |  rs2  |  rs1  |funct3 |imm[4:0]| opcode|  sw, sh, sb
      +-----------+-------+-------+-------+-------+--------+
B:    |12|imm[10:5]| rs2  |  rs1  |funct3 |4:1|11 | opcode |  beq, blt, bgeu
      +-----------+-------+-------+-------+-------+--------+
U:    |         imm[31:12]                |  rd   | opcode |  lui, auipc
      +-----------------------------------+-------+--------+
J:    |20| imm[10:1] |11|   imm[19:12]    |  rd   | opcode |  jal
      +-----------------------------------+-------+--------+
```

Notice how the 32-bit budget trades off registers vs. constants across formats:
- **`R`-type ([`enc_r`](../sim/oracle.py#L146-L155))**: Uses 3 registers (`rd`, `rs1`, `rs2`), leaving `funct3` + `funct7` (`10` bits) to distinguish operations like `add` (`funct7=0x00`), `sub` (`funct7=0x20`), `mul` (`funct7=0x01`), and our custom `Xapex mac` (`opcode=0x0B`, `funct7=0x00`).
- **`I`-type ([`enc_i`](../sim/oracle.py#L158-L166))**: Replaces `rs2` and `funct7` (`5 + 7 = 12` bits) with a single 12-bit constant `imm[11:0]` for `addi`, loads (`lw`), `jalr`, and `CSR` access. For immediate shifts (`slli`, `srli`, `srai`), only 5 bits (`0..31`) are needed for the shift amount (`shamt`), so bits `31..25` still act like `funct7` (`0x00` vs. `0x20`).
- **`S`-type ([`enc_s`](../sim/oracle.py#L169-L179))**: A store (`sw x2, 12(x1)`) needs two source registers (`x1` base address, `x2` value to write) and a 12-bit offset, with no destination `rd`. So `rs1` and `rs2` stay at bits `19..15` and `24..20`, and the 12-bit immediate splits into `imm[11:5]` (top 7 bits) and `imm[4:0]` (lower 5 bits in the unused `rd` column).
- **`B`-type ([`enc_b`](../sim/oracle.py#L182-L194)) & `J`-type ([`enc_j`](../sim/oracle.py#L202-L212))**: Branch and jump offsets are always multiples of 2 bytes, so bit `0` of the offset is always `0` and is omitted from the instruction word. Restoring an implicit `0` at bit `0` during decoding gives `B`-type a 13-bit signed reach (`±4 KB`) and `J`-type a 21-bit signed reach (`±1 MB`). Keeping the sign bit at bit `31` and keeping `rs1`/`rs2`/`rd` in their fixed columns arranges the remaining bits around them.
- **`U`-type ([`enc_u`](../sim/oracle.py#L197-L199))**: Drops both `rs1` and `rs2` to load an upper 20-bit constant into bits `31..12` (`LUI` = Load Upper Immediate, `AUIPC` = Add Upper Immediate to `pc`). Pairing `LUI` (upper 20 bits) with `ADDI` (lower 12 bits) builds any full 32-bit pointer or constant in two instructions.

---

### Concept 4: Little-Endian Memory, Alignment & Memory-Mapped I/O (MMIO)

Look at [`SparseMemory`](../sim/oracle.py#L227-L270), [`bus_read()`](../sim/oracle.py#L441-L457), and [`bus_write()`](../sim/oracle.py#L459-L479).

#### 1. Little-Endian Byte Ordering

Memory is addressed by **individual bytes**, even when instructions read or write 2-byte halfwords (`lh`/`sh`) or 4-byte words (`lw`/`sw`). In **little-endian** order ([`read_bytes`](../sim/oracle.py#L251-L259) and [`write_bytes`](../sim/oracle.py#L261-L269)), the *least-significant* byte sits at the lowest address.

For example, executing `sw x2, 0(x1)` with `x2 = 0x1122_80FF` and `x1 = 0x1000_0000` writes four bytes:

| Byte Address | `0x1000_0000` | `0x1000_0001` | `0x1000_0002` | `0x1000_0003` |
| :--- | :---: | :---: | :---: | :---: |
| **Stored Byte** | `0xFF` | `0x80` | `0x22` | `0x11` |

Now trace what different load widths return from `0x1000_0000`:
- `lb` (signed byte): reads `0xFF`, sign-extends bit `7` (`1`) → `0xFFFF_FFFF` (`-1`).
- `lbu` (unsigned byte): reads `0xFF`, zero-extends → `0x0000_00FF` (`255`).
- `lh` (signed 16-bit halfword): reads `0x80FF`, sign-extends bit `15` (`1`) → `0xFFFF_80FF` (`-32,513`).
- `lhu` (unsigned 16-bit halfword): reads `0x80FF`, zero-extends → `0x0000_80FF` (`32,991`).
- `lw` (32-bit word): reads all 4 bytes → `0x1122_80FF`.

#### 2. Natural Alignment & Sparse Paging

[`_exec_load`](../sim/oracle.py#L689-L719) and [`_exec_store`](../sim/oracle.py#L721-L740) enforce natural alignment with `(addr & (width - 1)) == 0`: 4-byte word accesses must be divisible by `4`, and 2-byte halfword accesses must be divisible by `2`. Misaligned accesses raise a hardware trap (`CAUSE_LOAD_MISALIGNED` or `CAUSE_STORE_MISALIGNED`).

Because our target address space includes 16 MB of Flash (`0x2000_0000`) and 32 MB of SDRAM (`0x4000_0000`), [`SparseMemory`](../sim/oracle.py#L227-L270) stores memory lazily in 4 KB pages (`dict[int, bytearray]`), so unit tests execute in milliseconds without allocating 48 MB upfront.

#### 3. Memory-Mapped I/O (MMIO)

RISC-V has no separate I/O instructions. Instead, [`bus_read`](../sim/oracle.py#L441-L457) and [`bus_write`](../sim/oracle.py#L459-L479) inspect the 32-bit address and route the access to either memory or a peripheral device:
- `0x0000_0000`–`0x0000_3FFF`: **Boot ROM** (`writable=False`; CPU writes raise `CAUSE_STORE_ACCESS_FAULT`).
- `0x1000_0000`–`0x1000_FFFF`: **BRAM** (64 KB read/write on-chip RAM).
- `0x8000_0000`–`0x8000_FFFF`: **CLINT** (`mtime` at `+0x00/+0x04`, `mtimecmp` at `+0x08/+0x0C`).
- `0x8001_0000`–`0x8001_FFFF`: **UART0** (storing a byte to `+0x00` transmits over serial; reading `+0x04` pops a received byte).

---

### Concept 5: Control Flow, CSRs & Trap Entry/Exit

Normal instructions advance `self.pc` by `4` bytes ([line 931](../sim/oracle.py#L931)). Control-flow instructions override `next_pc`:
- **Conditional Branches (`BEQ`, `BNE`, `BLT`, `BGE`, `BLTU`, `BGEU`)**: Jump to `cur_pc + imm` if the comparison is true; otherwise continue to `cur_pc + 4`.
- **Unconditional Jumps (`JAL`, `JALR`)**: Jump to `cur_pc + imm` (`JAL`) or `(rs1 + imm) & ~1` (`JALR`) while saving `cur_pc + 4` in `rd` for function calls.

#### Atomic CSR Instructions (`Zicsr`)

In [`_exec_system`](../sim/oracle.py#L856-L879), `CSRRW` (read/write), `CSRRS` (read/set bits), and `CSRRC` (read/clear bits) atomically return the *old* CSR value into `rd` while updating the CSR in a single step. Setting `rs1 = x0` (`0`) on `CSRRS` reads a CSR without modifying it (commonly written `csrr rd, csr`), and setting `rd = x0` on `CSRRW` writes a CSR while discarding the old value (`csrw csr, rs1`).

#### Synchronous Exceptions vs. Asynchronous Interrupts

When an error or external event interrupts normal execution, [`_take_trap()`](../sim/oracle.py#L573-L593) acts like a hardware `try/catch` redirect:

1. **Save Return Address**: `mepc = self.pc` (where execution should resume after handling the trap).
2. **Record Cause & Context**: `mcause = cause` and `mtval = tval` (the offending address or instruction). Bit `31` of `mcause` is `0` for **synchronous exceptions** caused by the current instruction (`ECALL`, illegal opcode, misaligned address) and `1` for **asynchronous interrupts** like the `CLINT` timer (`CAUSE_INT_M_TIMER = 0x8000_0007`), which [`step()`](../sim/oracle.py#L912-L914) checks *before* fetching the next instruction.
3. **Disable Nested Interrupts**: Copy `mstatus.MIE` (Machine Interrupt Enable) into `mstatus.MPIE` (Previous Interrupt Enable), then clear `MIE = 0` so a second interrupt cannot overwrite `mepc` before the handler saves it.
4. **Jump to Handler**: Set `self.pc` to the base address in `mtvec` (or `base + 4 * cause_code` in vectored interrupt mode when `mtvec[1:0] == 1`).

When the handler finishes, executing **`MRET`** ([lines 843–851](../sim/oracle.py#L843-L851)) restores `mstatus.MIE` from `MPIE` and sets `pc` back to `mepc`. Notice the key difference between the two trap types:
- After a timer **interrupt**, `mepc` holds the instruction that was *about* to run when the timer fired, so the handler returns directly to `mepc`.
- After a synchronous **`ECALL`**, `mepc` holds the `ECALL` instruction itself, so the handler increments `mepc` by `4` before calling `MRET` so it doesn't re-execute `ECALL` in an infinite loop.

---

## 3. Concrete Trace Walkthrough (2 Instructions Through `oracle.py`)

Watch [`step()`](../sim/oracle.py#L906-L1007) execute two instructions from [`test_oracle.py`](../tb/test_oracle.py):

### Trace A: `addi x1, x0, -5` (`enc_i(-5, 0, 0, 1, 0x13)`)

1. **Encode ([`enc_i`](../sim/oracle.py#L158-L166))**:
   - `-5 & 0xFFF` = `0xFFB` (`1111_1111_1011`) placed in `Bits 31..20`.
   - `rs1 = 0` (`Bits 19..15`), `funct3 = 0` (`Bits 14..12`), `rd = 1` (`Bits 11..7`), `opcode = 0x13` (`Bits 6..0`).
   - 32-bit machine word: `0xFFB0_0093`.
2. **Decode in `step()` ([lines 921–929](../sim/oracle.py#L921-L929))**:
   - `opcode = 0x13` (`OP-IMM`), `rd = 1`, `funct3 = 0`, `rs1 = 0` → `rs1_u = regs[0] = 0`.
3. **Execute in `_exec_op_imm()` ([lines 746–748](../sim/oracle.py#L746-L748))**:
   - `insn >> 20` extracts `0xFFB` (`4091`).
   - `sign_extend(0xFFB, 12)` computes `(4091 ^ 2048) - 2048 = -5`.
   - `res = 0 + (-5) = -5`.
4. **Commit ([`_set_reg`](../sim/oracle.py#L608-L613))**:
   - `u32(-5)` = `0xFFFF_FFFB` is written to `regs[1]`, and `pc` advances by `4`.

### Trace B: `blt x2, x3, -8` (`enc_b(-8, 3, 2, 4)` at `pc = 0x14`)

1. **Encode ([`enc_b`](../sim/oracle.py#L182-L194))**:
   - `-8 & 0x1FFF` = `0x1FF8` (`1_1111_1111_1000`), dropping bit `0` (`0`).
   - Bit `12` (`1`) goes to bit `31`; bits `10:5` (`111111`) go to `30:25`; bits `4:1` (`1100`) go to `11:8`; bit `11` (`1`) goes to bit `7`.
   - 32-bit machine word: `0xFE31_4CE3`.
2. **Evaluate in `_exec_branch()` ([lines 665–687](../sim/oracle.py#L665-L687))**:
   - Reassembles those bits into `0x1FF8`, calls `sign_extend(..., 13)` → `-8`.
   - With `funct3 = 4` (`BLT`), compares **signed** `rs1_s < rs2_s`.
   - When `x2 < x3`, `next_pc = u32(0x14 + (-8)) = 0x0C`.

---

## 4. Code-Reading Self-Checks

Open [`test_oracle.py`](../tb/test_oracle.py) and trace what each snippet verifies:

1. **Arithmetic vs. Logical Right Shift**: In `test_rv32i_arithmetic_shifts_and_x0` ([lines 87–95](../tb/test_oracle.py#L87-L95)), trace how `srai x7, x1, 1` (`x1 = -5`) preserves the sign bit to yield `u32(-3)`, whereas `srli x8, x1, 1` shifts in a `0` at bit `31` to yield `0x7FFF_FFFD`.
2. **Little-Endian Partial Overwrites**: In `test_memory_loads_stores_mmio_stub_and_faults` ([lines 223–236](../tb/test_oracle.py#L223-L236)), trace how storing `0x1122_80FF`, then overwriting halfword at `+2` and byte at `+1`, produces `0x80FF_FF00`.
3. **Trap Return `mepc` Offset**: Compare the `ECALL` handler ([lines 289–292](../tb/test_oracle.py#L289-L292)) with the timer interrupt handler ([lines 293–296](../tb/test_oracle.py#L293-L296)) and verify why `ECALL` advances `mepc` by `4` before `MRET` while the timer interrupt returns directly to `mepc`.
