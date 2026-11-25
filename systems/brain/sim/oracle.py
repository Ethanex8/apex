"""Golden instruction-by-instruction RISC-V reference processor and System-on-Chip emulator.

Purpose:
  Serve as the unambiguous single source of truth for verifying every SystemVerilog CPU
  core (single-cycle and pipelined) and the scratch SysC (minimal C-subset) compiler.

Plain-English Glossary of Abbreviations Used Below:
  - RV32IM   : RISC-V 32-bit Base Integer instruction set (I) + integer multiply/divide (M).
  - ALU      : Arithmetic Logic Unit (combinational adder, bitwise logic, comparator, and shifter).
  - FPGA     : Field-Programmable Gate Array (reprogrammable logic chip hosting the `brain` CPU).
  - Zicsr    : RISC-V Control and Status Register Instructions extension for reading/updating CSRs.
  - IRQ      : Interrupt Request (asynchronous hardware signal pausing execution via trap entry).
  - Xapex MAC: Custom dual-16-bit saturating Multiply-Accumulate neural extension (`opcode = 0x0B`).
  - Memory   : Boot ROM (read-only startup memory), BRAM (on-chip static Block RAM),
               4-wire persistent Quad Serial Peripheral Interface (QSPI) flash supporting
               direct Execute-in-Place (XIP) reads, and off-chip Synchronous Dynamic RAM (SDRAM).
  - MMIO     : Memory-Mapped Input/Output (hardware device registers wired to bus addresses):
               CLINT (64-bit Core-Local Interruptor timer), UART0 (serial debug console with
               TX/RX First-In, First-Out (FIFO) byte queues), and reserved peripheral windows for
               the Serial Peripheral Interface (SPI0), dual Controller Area Network (CAN0/CAN1)
               motor buses, stereo camera shutter sync, and General-Purpose Input/Output (GPIO).
  - Instruction Fields (32-bit word Bits 31..0): `opcode` (Bits 6..0 operation family),
               `rd` (destination register index 0..31), `rs1`/`rs2` (source register indices),
               and `funct3`/`funct7` (3-bit and 7-bit sub-operation selectors).

Usage:
  cpu = Oracle()
  cpu.load_words(BOOT_ROM_BASE, program_words)
  traces = cpu.run(max_steps=10_000)

Invariants:
  - Models architectural program counter (`pc`), `x0` through `x31` (`x0` hardwired to 0),
    32-bit saturating accumulator (`mac_acc`), 17 Machine-mode CSRs constrained via
    Write-Any/Read-Legal (WARL) bitmasks, CLINT/UART0 64 KB MMIO peripherals, and
    on-demand 4 KB chunked sparse memory.
  - Note: writes to `misa` (`0x301`) intentionally trap as illegal (`misa` is fixed in silicon).
  - Pre-fetch interrupt priority follows the RISC-V Privileged Spec: Machine External >
    Machine Software > Machine Timer (MEIP > MSIP > MTIP).

Memory Map (matching systems/brain/README.md):
  0x0000_0000 - 0x0000_3FFF : Boot ROM (16 KB, read-only to CPU instructions)
  0x1000_0000 - 0x1000_FFFF : On-chip BRAM (64 KB, read/write)
  0x2000_0000 - 0x20FF_FFFF : QSPI flash XIP window (16 MB, read-only to CPU)
  0x4000_0000 - 0x41FF_FFFF : External SDRAM (32 MB, read/write)
  0x8000_0000 - 0x8000_FFFF : CLINT 64-bit timer & alarm (`mtime` / `mtimecmp`)
  0x8001_0000 - 0x8001_FFFF : UART0 serial console (TX/RX FIFOs + status + baud divider)
  0x8002_0000 - 0x8006_FFFF : Reserved spine MMIO stub pages (SPI0/CAN0/CAN1/SYNC/GPIO)

Custom Xapex MAC Instruction (RISC-V custom-0 opcode 0x0B, funct7 = 0x00):
  Uses an internal 32-bit saturating accumulator (`mac_acc`) so dual-int16 dot products
  run at 1 instruction/cycle with a standard 2-read-port register file:
    funct3 = 0b000 : mac rd, rs1, rs2     -> acc = sat32(acc + a0*b0 + a1*b1); rd = acc
    funct3 = 0b001 : mac.clr rd, rs1, rs2 -> acc = sat32(0   + a0*b0 + a1*b1); rd = acc
    funct3 = 0b010 : mac.set rd, rs1      -> acc = s32(rs1); rd = acc
    funct3 = 0b011 : mac.get rd           -> rd = acc
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Address Map & Peripheral Register Offsets
# ---------------------------------------------------------------------------
SYS_CLK_HZ = 50_000_000       # 50 MHz reprogrammable logic chip (FPGA) fabric clock
UART_DEFAULT_BAUD = 115_200   # Default serial bit rate (50e6 // 115200 = 434 ticks/bit)

# Boot ROM & QSPI Flash reject CPU writes (MemoryAccessFault); host loaders use bypass_ro=True
BOOT_ROM_BASE = 0x0000_0000   # Immutable on-chip startup memory
BOOT_ROM_SIZE = 0x0000_4000   # 16 KB

BRAM_BASE = 0x1000_0000       # Single-cycle on-chip FPGA Block RAM (stack, hot weights)
BRAM_SIZE = 0x0001_0000       # 64 KB

QSPI_BASE = 0x2000_0000       # External Execute-in-Place (XIP) flash window
QSPI_SIZE = 0x0100_0000       # 16 MB

SDRAM_BASE = 0x4000_0000      # External main Synchronous DRAM (firmware heap & buffers)
SDRAM_SIZE = 0x0200_0000      # 32 MB

# CLINT (Core-Local Interruptor): 64-bit monotonic clock & comparator at 32-bit offsets
CLINT_BASE = 0x8000_0000
CLINT_SIZE = 0x0001_0000
CLINT_MTIME_LO = 0x00         # Bits 31..0 of 64-bit timer tick counter
CLINT_MTIME_HI = 0x04         # Bits 63..32 of 64-bit timer tick counter
CLINT_MTIMECMP_LO = 0x08      # Bits 31..0 of 64-bit alarm threshold (IRQ when mtime >= mtimecmp)
CLINT_MTIMECMP_HI = 0x0C      # Bits 63..32 of 64-bit alarm threshold

# UART0 (Universal Asynchronous Receiver-Transmitter): byte-stream debug console
UART0_BASE = 0x8001_0000
UART0_SIZE = 0x0001_0000
UART0_TXDATA = 0x00           # Write low byte to TX buffer + callback; reads return 0
UART0_RXDATA = 0x04           # Read pops 1 byte from RX FIFO (returns 0 when empty)
UART0_STATUS = 0x08           # Read-only status flags (4-byte aligned writes silently ignored)
UART0_BAUDDIV = 0x0C          # Clock cycles per serial bit (clamped >= 1 on write)

UART0_STATUS_TX_READY = 1 << 0
UART0_STATUS_TX_EMPTY = 1 << 1
UART0_STATUS_RX_VALID = 1 << 2

# Five reserved 64 KB MMIO pages (SPI0, CAN0, CAN1, SYNC, GPIO) backed by stub scratch RAM
MMIO_STUB_BASE = 0x8002_0000
MMIO_STUB_END = 0x8007_0000

# ---------------------------------------------------------------------------
# Machine-Mode CSR Addresses, WARL Masks & Trap Causes
# ---------------------------------------------------------------------------
CSR_MSTATUS = 0x300           # Machine status: global MIE, prior MPIE, and privilege MPP
CSR_MISA = 0x301              # ISA capability ID (hardwired read-only here; writes trap as illegal)
CSR_MIE = 0x304               # Interrupt-enable mask (Software MSIE, Timer MTIE, External MEIE)
CSR_MTVEC = 0x305             # Trap handler base address + mode (0=Direct, 1=Vectored)
CSR_MSCRATCH = 0x340          # Operating-system scratch register swapped during trap entry
CSR_MEPC = 0x341              # Saved return PC on exception/interrupt (4-byte aligned)
CSR_MCAUSE = 0x342            # Trap cause code (Bit 31 = 1 for interrupt, 0 for exception)
CSR_MTVAL = 0x343             # Trap-specific diagnostic value (faulting PC, addr, or insn word)
CSR_MIP = 0x344               # Pending interrupts: software/external latches OR live timer MTIP
CSR_MCYCLE = 0xB00            # Lower 32 bits of total cycle counter (ticks every step)
CSR_MINSTRET = 0xB02          # Lower 32 bits of retired (non-trapping) instruction counter
CSR_MCYCLEH = 0xB80           # Upper 32 bits of `mcycle`
CSR_MINSTRETH = 0xB82         # Upper 32 bits of `minstret`
CSR_MVENDORID = 0xF11         # Read-only vendor ID (0 = non-commercial/open)
CSR_MARCHID = 0xF12           # Read-only architecture ID (0)
CSR_MIMPID = 0xF13            # Read-only implementation ID (0)
CSR_MHARTID = 0xF14           # Read-only hardware thread ID (0 = single-core hart)

# Bits 31..30 = 0b01 (RV32), Bit 23 = 'X' custom, Bit 12 = 'M', Bit 8 = 'I'
MISA_RV32IMX = 0x4080_1100

CAUSE_INSN_MISALIGNED = 0     # PC or jump/taken-branch target not divisible by 4
CAUSE_INSN_ACCESS_FAULT = 1   # Instruction fetch hit unmapped or non-executable address
CAUSE_ILLEGAL_INSN = 2        # Unknown opcode/funct, invalid SYSTEM word, or read-only CSR write
CAUSE_BREAKPOINT = 3          # Environment Breakpoint (`ebreak`) instruction executed
CAUSE_LOAD_MISALIGNED = 4     # Load address not divisible by access width (2 or 4)
CAUSE_LOAD_ACCESS_FAULT = 5   # Load hit unmapped bus address or invalid MMIO width
CAUSE_STORE_MISALIGNED = 6    # Store address not divisible by access width (2 or 4)
CAUSE_STORE_ACCESS_FAULT = 7  # Store hit ROM/QSPI or unmapped address
CAUSE_ECALL_M = 11            # Synchronous Machine-mode Environment Call (`ecall`)
CAUSE_INT_M_SW = 0x8000_0003     # Machine software interrupt (Bit 31 | 3)
CAUSE_INT_M_TIMER = 0x8000_0007  # Machine timer interrupt from CLINT (Bit 31 | 7)
CAUSE_INT_M_EXT = 0x8000_000B    # Machine external interrupt (Bit 31 | 11)

MSTATUS_MIE_BIT = 1 << 3      # Bit 3: Master Machine Interrupt Enable (MIE)
MSTATUS_MPIE_BIT = 1 << 7     # Bit 7: Machine Previous Interrupt Enable (MPIE, saved across `mret`)
MSTATUS_MPP_M = 0b11 << 11    # Bits 12..11: Machine Previous Privilege fixed to Machine (0b11)

MIE_MSIE_BIT = 1 << 3         # Bit 3 in `mie`/`mip` (Machine Software IRQ enable/pending)
MIE_MTIE_BIT = 1 << 7         # Bit 7 in `mie`/`mip` (Machine Timer IRQ enable/pending)
MIE_MEIE_BIT = 1 << 11        # Bit 11 in `mie`/`mip` (Machine External IRQ enable/pending)

MTVEC_MODE_MASK = 0x3
MTVEC_MODE_DIRECT = 0
MTVEC_MODE_VECTORED = 1
MCAUSE_CODE_MASK = 0x7FFF_FFFF

# ---------------------------------------------------------------------------
# RISC-V Major Opcodes, Funct3/Funct7 Selectors & Fixed Masks
# ---------------------------------------------------------------------------
OPCODE_LOAD = 0x03
OPCODE_CUSTOM0 = 0x0B         # Reserved RISC-V custom-0 space used by Xapex MAC
OPCODE_MISC_MEM = 0x0F        # Memory ordering barriers (`fence` / `fence.i`)
OPCODE_OP_IMM = 0x13          # Register-immediate Arithmetic Logic Unit (ALU) & shift operations
OPCODE_AUIPC = 0x17
OPCODE_STORE = 0x23
OPCODE_OP = 0x33              # Register-register RV32I + RV32M ALU operations
OPCODE_LUI = 0x37
OPCODE_BRANCH = 0x63
OPCODE_JALR = 0x67
OPCODE_JAL = 0x6F
OPCODE_SYSTEM = 0x73          # System (`ecall`/`ebreak`/`mret`/`wfi`) and Zicsr CSR instructions

F7_BASE = 0x00
F7_MULDIV = 0x01
F7_ALT = 0x20

F3_ADD_SUB = 0
F3_SLL = 1
F3_SLT = 2
F3_SLTU = 3
F3_XOR = 4
F3_SRL_SRA = 5
F3_OR = 6
F3_AND = 7

F3_MUL = 0
F3_MULH = 1
F3_MULHSU = 2
F3_MULHU = 3
F3_DIV = 4
F3_DIVU = 5
F3_REM = 6
F3_REMU = 7

F3_BEQ = 0
F3_BNE = 1
F3_BLT = 4
F3_BGE = 5
F3_BLTU = 6
F3_BGEU = 7

F3_LB = 0
F3_LH = 1
F3_LW = 2
F3_LBU = 4
F3_LHU = 5

F3_SB = 0
F3_SH = 1
F3_SW = 2

F3_FENCE = 0
F3_FENCE_I = 1
F3_JALR = 0

F3_PRIV = 0
F3_CSRRW = 1
F3_CSRRS = 2
F3_CSRRC = 3
F3_CSRRWI = 5
F3_CSRRSI = 6
F3_CSRRCI = 7

ZICSR_IMM_BIT = 0x4
ZICSR_OP_MASK = 0x3
ZICSR_OP_RW = 1
ZICSR_OP_RS = 2

MAC_F3_ACC = 0
MAC_F3_CLR = 1
MAC_F3_SET = 2
MAC_F3_GET = 3

INSN_ECALL = 0x0000_0073
INSN_EBREAK = 0x0010_0073
INSN_MRET = 0x3020_0073
INSN_WFI = 0x1050_0073
INSN_FENCE = 0x0000_000F
INSN_FENCE_I = 0x0000_100F

# Common 32-bit field masks, alignment constants, and hardware bounds
INSN_SIZE_BYTES = 4
VALID_BUS_WIDTHS = (1, 2, 4)
OPCODE_MASK = 0x7F
REG_MASK = 0x1F
FUNCT3_MASK = 0x7
FUNCT7_MASK = 0x7F
IMM12_MASK = 0xFFF
CSR_ADDR_MASK = IMM12_MASK

MASK32 = 0xFFFF_FFFF
MASK64 = (1 << 64) - 1
MASK64_HI32 = 0xFFFF_FFFF_0000_0000
UINT32_MAX = 0xFFFF_FFFF
UINT64_MAX = MASK64
WORD_ALIGN_MASK = 0xFFFF_FFFC
WORD_ALIGN_LOW_BITS = 0x3
JALR_TARGET_MASK = 0xFFFF_FFFE
UPPER20_MASK = 0xFFFF_F000
INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1


# ---------------------------------------------------------------------------
# Bitwise Arithmetic & Instruction Encoding Helpers
# ---------------------------------------------------------------------------
def u32(val: int) -> int:
    """Wrap an arbitrary Python integer into unsigned 32-bit range [0, 2^32 - 1] (mod 2^32)."""
    return val & MASK32


def sign_extend(val: int, bits: int) -> int:
    """Sign-extend `bits`-wide `val` via `(val ^ (1 << (bits - 1))) - (1 << (bits - 1))`."""
    # Flipping the top sign bit (Most Significant Bit / MSB) swaps [0..2^(bits-1)-1] and
    # [2^(bits-1)..2^bits-1]; subtracting 2^(bits-1) maps [0..2^bits-1] onto signed range.
    sign_bit = 1 << (bits - 1)
    mask = (1 << bits) - 1
    val &= mask
    return (val ^ sign_bit) - sign_bit


def s32(val: int) -> int:
    """Interpret lower 32 bits as signed two's complement: S_32(b) = U_32(b) - b_31 * 2^32."""
    return sign_extend(val, 32)


def s16(val: int) -> int:
    """Interpret lower 16 bits as signed two's complement: S_16(b) = U_16(b) - b_15 * 2^16."""
    return sign_extend(val, 16)


def sat32(val: int) -> int:
    """Clamp an integer to signed 32-bit bounds [INT32_MIN, INT32_MAX] without wrapping."""
    if val < INT32_MIN:
        return INT32_MIN
    if val > INT32_MAX:
        return INT32_MAX
    return val


def trunc_div_s32(dividend: int, divisor: int) -> int:
    """Divide signed 32-bit integers toward zero with non-trapping RISC-V corner semantics."""
    if divisor == 0:
        return -1
    if dividend == INT32_MIN and divisor == -1:
        return INT32_MIN
    # Truncate magnitude toward zero rather than Python's floor division (// toward -inf)
    q = abs(dividend) // abs(divisor)
    return -q if (dividend < 0) ^ (divisor < 0) else q


def _set_u64_lo(cur: int, val: int) -> int:
    """Replace Bits 31..0 of a 64-bit integer while preserving Bits 63..32."""
    return (cur & MASK64_HI32) | u32(val)


def _set_u64_hi(cur: int, val: int) -> int:
    """Replace Bits 63..32 of a 64-bit integer while preserving Bits 31..0."""
    return (cur & MASK32) | (u32(val) << 32)


def enc_r(funct7: int, rs2: int, rs1: int, funct3: int, rd: int, opcode: int) -> int:
    """Encode a 32-bit R-type (register-register) RISC-V instruction word."""
    return (
        ((funct7 & FUNCT7_MASK) << 25)
        | ((rs2 & REG_MASK) << 20)
        | ((rs1 & REG_MASK) << 15)
        | ((funct3 & FUNCT3_MASK) << 12)
        | ((rd & REG_MASK) << 7)
        | (opcode & OPCODE_MASK)
    )


def enc_i(imm: int, rs1: int, funct3: int, rd: int, opcode: int) -> int:
    """Encode a 32-bit I-type (12-bit immediate / load / `jalr` / CSR) RISC-V instruction word."""
    return (
        ((imm & IMM12_MASK) << 20)
        | ((rs1 & REG_MASK) << 15)
        | ((funct3 & FUNCT3_MASK) << 12)
        | ((rd & REG_MASK) << 7)
        | (opcode & OPCODE_MASK)
    )


def enc_s(imm: int, rs2: int, rs1: int, funct3: int, opcode: int = OPCODE_STORE) -> int:
    """Encode a 32-bit S-type (store) word, keeping `rs1`/`rs2` fixed and splitting Bits 11..0."""
    # Pins rs2 at Bits 24..20 and rs1 at Bits 19..15, splitting the 12-bit offset around them
    imm12 = imm & IMM12_MASK
    return (
        ((imm12 >> 5) << 25)
        | ((rs2 & REG_MASK) << 20)
        | ((rs1 & REG_MASK) << 15)
        | ((funct3 & FUNCT3_MASK) << 12)
        | ((imm12 & 0x1F) << 7)
        | (opcode & OPCODE_MASK)
    )


def enc_b(imm: int, rs2: int, rs1: int, funct3: int, opcode: int = OPCODE_BRANCH) -> int:
    """Encode a 32-bit B-type conditional branch from a signed byte offset (omits Bit 0 = 0)."""
    # Keeps sign bit at Bit 31 and aligns middle/low offset slices with S-type bit positions
    imm13 = imm & 0x1FFF
    return (
        ((imm13 >> 12) << 31)
        | (((imm13 >> 5) & 0x3F) << 25)
        | ((rs2 & REG_MASK) << 20)
        | ((rs1 & REG_MASK) << 15)
        | ((funct3 & FUNCT3_MASK) << 12)
        | (((imm13 >> 1) & 0xF) << 8)
        | (((imm13 >> 11) & 0x1) << 7)
        | (opcode & OPCODE_MASK)
    )


def enc_u(imm20_shifted: int, rd: int, opcode: int) -> int:
    """Encode a 32-bit U-type (`lui` / `auipc`) word from pre-shifted `imm20_shifted`."""
    # Caller supplies bits already aligned to Bits 31..12 (e.g., 0x1234_5000)
    return (imm20_shifted & UPPER20_MASK) | ((rd & REG_MASK) << 7) | (opcode & OPCODE_MASK)


def enc_j(imm: int, rd: int, opcode: int = OPCODE_JAL) -> int:
    """Encode a 32-bit J-type (`jal`) word from a signed 21-bit byte offset (omits Bit 0 = 0)."""
    # Keeps Offset Bit 20 at Bit 31 (sign) and Offset Bits 19..12 at Bits 19..12 (U-type match)
    imm21 = imm & 0x1F_FFFF
    return (
        ((imm21 >> 20) << 31)
        | (((imm21 >> 1) & 0x3FF) << 21)
        | (((imm21 >> 11) & 0x1) << 20)
        | (((imm21 >> 12) & 0xFF) << 12)
        | ((rd & REG_MASK) << 7)
        | (opcode & OPCODE_MASK)
    )


def enc_mac(rd: int, rs1: int = 0, rs2: int = 0, funct3: int = MAC_F3_ACC) -> int:
    """Encode Xapex custom-0 MAC (`mac`, `mac.clr`, `mac.set`, or `mac.get`) from `funct3`."""
    return enc_r(F7_BASE, rs2, rs1, funct3, rd, OPCODE_CUSTOM0)


def _dec_imm_s(insn: int) -> int:
    """Reassemble signed 12-bit store offset from instruction Bits 31..25 and Bits 11..7."""
    return sign_extend(((insn >> 25) << 5) | ((insn >> 7) & 0x1F), 12)


def _dec_imm_b(insn: int) -> int:
    """Reassemble signed 13-bit even branch offset from scrambled B-type bit slices."""
    return sign_extend(
        (((insn >> 31) & 1) << 12)
        | (((insn >> 7) & 1) << 11)
        | (((insn >> 25) & 0x3F) << 5)
        | (((insn >> 8) & 0xF) << 1),
        13,
    )


def _dec_imm_j(insn: int) -> int:
    """Reassemble signed 21-bit even jump offset from scrambled J-type bit slices."""
    return sign_extend(
        (((insn >> 31) & 1) << 20)
        | (((insn >> 12) & 0xFF) << 12)
        | (((insn >> 20) & 1) << 11)
        | (((insn >> 21) & 0x3FF) << 1),
        21,
    )


# ---------------------------------------------------------------------------
# Memory Model, Execution Outcomes & Commit Trace Types
# ---------------------------------------------------------------------------
class MemoryAccessFault(Exception):
    """Raised internally when a bus access targets an unmapped, misaligned, or read-only region."""


class SparseMemory:
    """On-demand 4 KB chunked little-endian memory backing large regions sparsely."""

    PAGE_SIZE = 4096

    def __init__(self, base: int, size: int, writable: bool = True) -> None:
        """Initialize a sparse memory region spanning `base` up to `base + size`."""
        self.base = base
        self.size = size
        self.writable = writable
        self._pages: dict[int, bytearray] = {}

    def contains(self, addr: int, width: int) -> bool:
        """Return True if the access from `addr` up to `addr + width` fits inside this region."""
        return self.base <= addr and (addr + width) <= (self.base + self.size)

    def _get_or_alloc_page(self, page_idx: int) -> bytearray:
        """Return existing 4 KB chunk for `page_idx`, allocating zeroed bytes on first write."""
        page = self._pages.get(page_idx)
        if page is None:
            page = bytearray(self.PAGE_SIZE)
            self._pages[page_idx] = page
        return page

    def read_bytes(self, addr: int, width: int) -> int:
        """Read `width` bytes (1, 2, or 4) from `addr` in little-endian byte order."""
        if width not in VALID_BUS_WIDTHS or not self.contains(addr, width):
            raise MemoryAccessFault(f"Out-of-bounds read at 0x{addr:08x} (width={width})")
        val = 0
        # Byte-by-byte loop handles multi-byte accesses crossing 4 KB chunk boundaries cleanly
        for i in range(width):
            offset = (addr + i) - self.base
            page = self._pages.get(offset // self.PAGE_SIZE)
            byte = page[offset % self.PAGE_SIZE] if page is not None else 0
            val |= byte << (8 * i)
        return val

    def write_bytes(self, addr: int, width: int, val: int, bypass_ro: bool = False) -> None:
        """Write `width` little-endian bytes of `val` to `addr` (`self.writable` or `bypass_ro`)."""
        if width not in VALID_BUS_WIDTHS or not self.contains(addr, width):
            raise MemoryAccessFault(f"Out-of-bounds write at 0x{addr:08x} (width={width})")
        if not self.writable and not bypass_ro:
            raise MemoryAccessFault(f"Write to read-only region at 0x{addr:08x}")
        for i in range(width):
            offset = (addr + i) - self.base
            page = self._get_or_alloc_page(offset // self.PAGE_SIZE)
            page[offset % self.PAGE_SIZE] = (val >> (8 * i)) & 0xFF


@dataclass
class StepTrace:
    """Record of one step executed by `Oracle.step()`.

    All integer address, word, and register fields (`pc`, `insn`, `next_pc`, `rd_val`,
    `mem_addr`, `mem_val`, and `trap_cause`) hold unsigned 32-bit values in [0, 2^32 - 1]
    (sub-word stores mask `mem_val` to 8/16 bits; signed loads sign-extend `mem_val` via
    `u32`). `rd` lies in 0..31, `mem_write` is False on loads and True on stores, and
    `interrupt` is True if and only if `trap_cause` (`mcause` Bit 31 = 1) came from an
    asynchronous interrupt rather than a synchronous exception.
    """

    pc: int
    insn: int
    next_pc: int
    rd: int = 0
    rd_val: int = 0
    mem_addr: int | None = None
    mem_val: int | None = None
    mem_write: bool = False
    trap_cause: int | None = None
    interrupt: bool = False


@dataclass(frozen=True)
class ExecOutcome:
    """Pending register writeback, next PC, and StepTrace metadata from a non-trapping instruction.

    All fault/permission checks succeed before any bus write, CSR write, or `mac_acc` update
    occurs; `rd_val` is normalized via `u32()` inside `Oracle._set_reg()` at retirement.
    """

    rd: int = 0
    rd_val: int = 0
    next_pc: int | None = None          # None advances sequentially to cur_pc + 4
    mem_addr: int | None = None
    mem_val: int | None = None
    mem_write: bool = False
    # True when a Zicsr write targets minstret/minstreth so step() does not overwrite it
    suppress_minstret: bool = False


# ---------------------------------------------------------------------------
# Golden RISC-V Reference CPU & System-on-Chip Emulator
# ---------------------------------------------------------------------------
class Oracle:
    """Instruction-accurate RISC-V RV32IM + Zicsr + Xapex MAC reference CPU and System-on-Chip.

    Models all programmer-visible state of the `brain` chip:
      - Core computation state: program counter (`pc`), 32 integer registers (`regs`), and
        the 32-bit signed saturating `mac_acc` accumulator.
      - Privileged Control and Status Registers (CSRs): `mstatus` (interrupt enable gate),
        `mie`/`mip` (interrupt mask/pending flags), `mtvec` (trap handler address),
        `mepc`/`mcause`/`mtval` (saved trap context), `mscratch`, 64-bit `mcycle`/`minstret`
        counters, and read-only identification CSRs (`misa`, vendor/arch/impl/hart IDs).
      - Sparse memory regions (`rom`, `bram`, `qspi`, `sdram`, plus `mmio_stub`).
      - Memory-mapped peripherals: CLINT 64-bit timer/alarm and UART0 TX/RX serial queues.

    Primary entry points are `load_words()` / `load_bytes()`, `step()`, and `run()`.
    """

    def __init__(
        self,
        reset_pc: int = BOOT_ROM_BASE,
        uart_tx_callback: Callable[[int], None] | None = None,
    ) -> None:
        """Create an oracle booted to `reset_pc` with optional `uart_tx_callback`."""
        self.reset_pc = u32(reset_pc)
        self.uart_tx_callback = uart_tx_callback

        self.rom = SparseMemory(BOOT_ROM_BASE, BOOT_ROM_SIZE, writable=False)
        self.bram = SparseMemory(BRAM_BASE, BRAM_SIZE, writable=True)
        self.qspi = SparseMemory(QSPI_BASE, QSPI_SIZE, writable=False)
        self.sdram = SparseMemory(SDRAM_BASE, SDRAM_SIZE, writable=True)
        self.mmio_stub = SparseMemory(MMIO_STUB_BASE, MMIO_STUB_END - MMIO_STUB_BASE, writable=True)
        # Keep mmio_stub outside _mem_regions so loaders and instruction fetches stay in memory
        self._mem_regions = (self.rom, self.bram, self.qspi, self.sdram)

        self.reset()

    def reset(self, reset_pc: int | None = None) -> None:
        """Reset all CPU registers, CSRs, timers, and UART FIFOs to power-on state."""
        # Sparse ROM/Flash/RAM backing stores persist across warm resets so firmware stays loaded
        if reset_pc is not None:
            self.reset_pc = u32(reset_pc)
        self.pc: int = self.reset_pc             # Byte address of next instruction to fetch
        self.regs: list[int] = [0] * 32          # `x0`..`x31` (`regs[0]` stays 0 via _set_reg)
        self.mac_acc: int = 0                    # 32-bit signed saturating Xapex accumulator

        # Machine Previous Privilege (MPP) stays at Machine mode (0b11); global IRQ gate MIE = 0
        self.mstatus: int = MSTATUS_MPP_M
        self.misa: int = MISA_RV32IMX
        self.mie: int = 0                        # Per-source IRQ enable bits (MSIE/MTIE/MEIE)
        self.mtvec: int = 0                      # Trap handler base + dispatch mode (Bits 1..0)
        self.mscratch: int = 0                   # Operating-system scratch CSR for trap entry
        self.mepc: int = 0                       # Return PC saved when taking a trap
        self.mcause: int = 0                     # Encodes interrupt flag (Bit 31) + cause ID
        self.mtval: int = 0                      # Faulting PC, memory address, or insn word
        # Software/External pending IRQ bits (MSIP/MEIP); timer pending (MTIP) is wired live
        self.mip_sw_ext: int = 0
        self.mcycle: int = 0                     # Counts every step() (instructions + traps)
        self.minstret: int = 0                   # Counts retired non-trapping instructions

        self.mtime: int = 0                      # 64-bit CLINT clock counter (ticks pre-fetch)
        self.mtimecmp: int = UINT64_MAX          # Max 64-bit ceiling avoids spurious boot IRQ

        self.uart_tx_buf: bytearray = bytearray()                # Host log of UART0 TX bytes
        self.uart_rx_fifo: deque[int] = deque()                  # Queued UART0 RX bytes
        self.uart_bauddiv: int = SYS_CLK_HZ // UART_DEFAULT_BAUD  # 434 ticks/bit at 50 MHz

        self.halted: bool = False                # Set True on `ebreak`; cleared on `run()`

    # -----------------------------------------------------------------------
    # Loader & Host Inspection Helpers
    # -----------------------------------------------------------------------
    def _find_mem_region(self, addr: int, width: int) -> SparseMemory | None:
        """Locate the backing memory region covering `addr` up to `addr + width`, or None."""
        for region in self._mem_regions:
            if region.contains(addr, width):
                return region
        return None

    def load_bytes(self, addr: int, data: bytes | bytearray) -> None:
        """Load raw bytes into any mapped memory region, bypassing read-only protection."""
        for i, b in enumerate(data):
            cur = u32(addr + i)
            region = self._find_mem_region(cur, 1)
            if region is None:
                raise MemoryAccessFault(f"Cannot load byte to unmapped address 0x{cur:08x}")
            region.write_bytes(cur, 1, b, bypass_ro=True)

    def load_words(self, addr: int, words: list[int] | tuple[int, ...]) -> None:
        """Load 32-bit little-endian instruction or data words into any mapped memory region."""
        for idx, word in enumerate(words):
            cur = u32(addr + idx * INSN_SIZE_BYTES)
            region = self._find_mem_region(cur, INSN_SIZE_BYTES)
            if region is None:
                raise MemoryAccessFault(f"Cannot load word to unmapped address 0x{cur:08x}")
            region.write_bytes(cur, INSN_SIZE_BYTES, u32(word), bypass_ro=True)

    def push_uart_rx(self, data: bytes | bytearray | str) -> None:
        """Append bytes or Latin-1 text into the simulated UART0 receive FIFO."""
        raw = data.encode("latin-1") if isinstance(data, str) else data
        for b in raw:
            self.uart_rx_fifo.append(b & 0xFF)

    def read_uart_tx(self, clear: bool = False) -> bytes:
        """Return all bytes transmitted to UART0 so far, optionally clearing the buffer."""
        out = bytes(self.uart_tx_buf)
        if clear:
            self.uart_tx_buf.clear()
        return out

    # -----------------------------------------------------------------------
    # Bus Read / Write (Memory + MMIO Peripherals)
    # -----------------------------------------------------------------------
    def _in_clint_window(self, addr: int, width: int) -> bool:
        """Return True if `addr` up to `addr + width` lies inside the CLINT peripheral window."""
        return CLINT_BASE <= addr and (addr + width) <= CLINT_BASE + CLINT_SIZE

    def _clint_offset(self, addr: int, width: int) -> int:
        """Validate 32-bit CLINT alignment/width and return its register byte offset."""
        # Hardware CLINT timer registers expose only full 32-bit aligned reads and writes
        if width != 4 or (addr & WORD_ALIGN_LOW_BITS) != 0:
            raise MemoryAccessFault(f"CLINT requires 32-bit aligned access at 0x{addr:08x}")
        return addr - CLINT_BASE

    def _clint_read(self, addr: int, width: int) -> int:
        """Read one 32-bit CLINT register (unused offsets inside the 64 KB window read 0)."""
        offset = self._clint_offset(addr, width)
        if offset == CLINT_MTIME_LO:
            return u32(self.mtime)
        if offset == CLINT_MTIME_HI:
            return u32(self.mtime >> 32)
        if offset == CLINT_MTIMECMP_LO:
            return u32(self.mtimecmp)
        if offset == CLINT_MTIMECMP_HI:
            return u32(self.mtimecmp >> 32)
        return 0

    def _clint_write(self, addr: int, width: int, val: int) -> None:
        """Read-modify-write the low or high 32-bit half of `mtime` or `mtimecmp`."""
        offset = self._clint_offset(addr, width)
        # 32-bit CPU bus writes only half a 64-bit counter at once, preserving the untouched 32 bits
        if offset == CLINT_MTIME_LO:
            self.mtime = _set_u64_lo(self.mtime, val)
        elif offset == CLINT_MTIME_HI:
            self.mtime = _set_u64_hi(self.mtime, val)
        elif offset == CLINT_MTIMECMP_LO:
            self.mtimecmp = _set_u64_lo(self.mtimecmp, val)
        elif offset == CLINT_MTIMECMP_HI:
            self.mtimecmp = _set_u64_hi(self.mtimecmp, val)

    def _in_uart_window(self, addr: int, width: int) -> bool:
        """Return True if `addr` up to `addr + width` lies inside the UART0 peripheral window."""
        return UART0_BASE <= addr and (addr + width) <= UART0_BASE + UART0_SIZE

    def _uart_offset(self, addr: int, width: int) -> int:
        """Validate UART0 alignment/width rules and return its register byte offset."""
        off = addr - UART0_BASE
        # Data registers allow 1- or 4-byte aligned accesses; control registers require 4 bytes
        if (addr & WORD_ALIGN_LOW_BITS) != 0 or width not in (1, 4):
            raise MemoryAccessFault(f"UART misaligned/unsupported access at 0x{addr:08x}")
        if width == 1 and off in (UART0_STATUS, UART0_BAUDDIV):
            raise MemoryAccessFault(f"UART control register requires 32-bit access at 0x{addr:08x}")
        return off

    def _uart_read(self, addr: int, width: int) -> int:
        """Read `UART0_RXDATA`, `UART0_STATUS`, or `UART0_BAUDDIV` (`UART0_TXDATA` reads 0)."""
        offset = self._uart_offset(addr, width)
        if offset == UART0_RXDATA:
            return self.uart_rx_fifo.popleft() if self.uart_rx_fifo else 0  # Destructive FIFO pop
        if offset == UART0_STATUS:
            rx_flag = UART0_STATUS_RX_VALID if self.uart_rx_fifo else 0
            return UART0_STATUS_TX_READY | UART0_STATUS_TX_EMPTY | rx_flag
        if offset == UART0_BAUDDIV:
            return self.uart_bauddiv
        return 0

    def _uart_write(self, addr: int, width: int, val: int) -> None:
        """Write `UART0_TXDATA` or `UART0_BAUDDIV` (read-only `UART0_STATUS` ignores writes)."""
        offset = self._uart_offset(addr, width)
        if offset == UART0_TXDATA:
            byte = val & 0xFF
            self.uart_tx_buf.append(byte)
            if self.uart_tx_callback is not None:
                self.uart_tx_callback(byte)
        elif offset == UART0_BAUDDIV:
            self.uart_bauddiv = max(1, u32(val))  # Clamp >= 1 to prevent hardware divide-by-zero

    def bus_read(self, addr: int, width: int) -> int:
        """Perform a CPU bus read of `width` bytes across memory regions and MMIO devices."""
        if width not in VALID_BUS_WIDTHS:
            raise MemoryAccessFault(f"Unsupported read width {width} at 0x{addr:08x}")
        addr = u32(addr)
        if (region := self._find_mem_region(addr, width)) is not None:
            return region.read_bytes(addr, width)
        if self._in_clint_window(addr, width):
            return self._clint_read(addr, width)
        if self._in_uart_window(addr, width):
            return self._uart_read(addr, width)
        if self.mmio_stub.contains(addr, width):
            return self.mmio_stub.read_bytes(addr, width)
        raise MemoryAccessFault(f"Load access fault at 0x{addr:08x}")

    def bus_write(self, addr: int, width: int, val: int) -> None:
        """Perform a CPU bus write of `width` bytes across memory regions and MMIO devices."""
        if width not in VALID_BUS_WIDTHS:
            raise MemoryAccessFault(f"Unsupported write width {width} at 0x{addr:08x}")
        addr = u32(addr)
        if (region := self._find_mem_region(addr, width)) is not None:
            region.write_bytes(addr, width, val)
            return
        if self._in_clint_window(addr, width):
            self._clint_write(addr, width, val)
            return
        if self._in_uart_window(addr, width):
            self._uart_write(addr, width, val)
            return
        if self.mmio_stub.contains(addr, width):
            self.mmio_stub.write_bytes(addr, width, val)
            return
        raise MemoryAccessFault(f"Store access fault at 0x{addr:08x}")

    def read_u32(self, addr: int) -> int:
        """Convenience helper to read an aligned 32-bit word from the system bus."""
        return self.bus_read(addr, 4)

    def write_u32(self, addr: int, val: int) -> None:
        """Convenience helper to write an aligned 32-bit word to the system bus."""
        self.bus_write(addr, 4, val)

    # -----------------------------------------------------------------------
    # CSRs & Traps
    # -----------------------------------------------------------------------
    def _live_mip(self) -> int:
        """Compute `mip`: software/external pending latches OR live CLINT `mtime >= mtimecmp`."""
        mtip = MIE_MTIE_BIT if (self.mtime >= self.mtimecmp) else 0
        # Defensive mask ensures direct test mutations to `mip_sw_ext` expose only MSIP/MEIP
        return (self.mip_sw_ext & (MIE_MSIE_BIT | MIE_MEIE_BIT)) | mtip

    def _set_mstatus_irq_bits(self, mie: bool, mpie: bool) -> None:
        """Update `self.mstatus` interrupt flags `mie` and `mpie`, keeping MPP fixed to Machine."""
        # MASK32 ^ avoids Python negative infinite-precision ~ ints
        clear_mask = MASK32 ^ (MSTATUS_MIE_BIT | MSTATUS_MPIE_BIT)
        self.mstatus = (
            (self.mstatus & clear_mask)
            | (MSTATUS_MIE_BIT if mie else 0)
            | (MSTATUS_MPIE_BIT if mpie else 0)
            | MSTATUS_MPP_M
        )

    def _read_csr(self, addr: int) -> int | None:
        """Return the current 32-bit value of CSR `addr`, or None if unimplemented."""
        if addr == CSR_MSTATUS:
            return self.mstatus
        if addr == CSR_MISA:
            return self.misa
        if addr == CSR_MIE:
            return self.mie
        if addr == CSR_MTVEC:
            return self.mtvec
        if addr == CSR_MSCRATCH:
            return self.mscratch
        if addr == CSR_MEPC:
            return self.mepc
        if addr == CSR_MCAUSE:
            return self.mcause
        if addr == CSR_MTVAL:
            return self.mtval
        if addr == CSR_MIP:
            return self._live_mip()
        if addr == CSR_MCYCLE:
            return u32(self.mcycle)
        if addr == CSR_MCYCLEH:
            return u32(self.mcycle >> 32)
        if addr == CSR_MINSTRET:
            return u32(self.minstret)
        if addr == CSR_MINSTRETH:
            return u32(self.minstret >> 32)
        if addr in (CSR_MVENDORID, CSR_MARCHID, CSR_MIMPID, CSR_MHARTID):
            return 0
        return None

    def _write_csr(self, addr: int, val: int) -> bool:
        """Write a known CSR using WARL masking; assumes `addr` was verified by `_read_csr()`.

        Returns False only on read-only CSRs (`misa` and ID CSRs) so `_exec_zicsr()` traps cleanly.
        """
        val = u32(val)
        if addr == CSR_MSTATUS:
            # WARL: only MIE and MPIE are writable; MPP stays hardwired to Machine mode (0b11)
            self._set_mstatus_irq_bits(bool(val & MSTATUS_MIE_BIT), bool(val & MSTATUS_MPIE_BIT))
            return True
        if addr == CSR_MIE:
            # WARL: only Software (MSIE), Timer (MTIE), and External (MEIE) enables exist
            self.mie = val & (MIE_MSIE_BIT | MIE_MTIE_BIT | MIE_MEIE_BIT)
            return True
        if addr == CSR_MTVEC:
            # WARL: modes > 1 are reserved here and snap cleanly to Direct mode (0)
            mode = val & MTVEC_MODE_MASK
            if mode > MTVEC_MODE_VECTORED:
                mode = MTVEC_MODE_DIRECT
            self.mtvec = (val & WORD_ALIGN_MASK) | mode
            return True
        if addr == CSR_MSCRATCH:
            self.mscratch = val
            return True
        if addr == CSR_MEPC:
            # No 16-bit compressed instructions (4-byte alignment / IALIGN=32), so Bits 1..0 stay 0
            self.mepc = val & WORD_ALIGN_MASK
            return True
        if addr == CSR_MCAUSE:
            self.mcause = val
            return True
        if addr == CSR_MTVAL:
            self.mtval = val
            return True
        if addr == CSR_MIP:
            # Software/external pending bits act as writable latches; MTIP is wired live from CLINT
            self.mip_sw_ext = val & (MIE_MSIE_BIT | MIE_MEIE_BIT)
            return True
        if addr == CSR_MCYCLE:
            self.mcycle = _set_u64_lo(self.mcycle, val)
            return True
        if addr == CSR_MCYCLEH:
            self.mcycle = _set_u64_hi(self.mcycle, val)
            return True
        if addr == CSR_MINSTRET:
            self.minstret = _set_u64_lo(self.minstret, val)
            return True
        if addr == CSR_MINSTRETH:
            self.minstret = _set_u64_hi(self.minstret, val)
            return True
        # Design choice: writes to `misa` (0x301) and ID CSRs (0xF11..0xF14) trap as illegal_insn
        return False

    def _take_trap(self, cause: int, tval: int, is_interrupt: bool) -> int:
        """Execute atomic hardware trap entry: save context, disable interrupts, jump to `mtvec`."""
        # 1. 4-byte instruction alignment forces mepc Bits 1..0 = 0; mtval keeps exact faulting PC
        self.mepc = self.pc & WORD_ALIGN_MASK
        self.mcause = u32(cause)
        self.mtval = u32(tval)

        # 2. Push current MIE -> MPIE and mask MIE = 0 atomically
        self._set_mstatus_irq_bits(mie=False, mpie=bool(self.mstatus & MSTATUS_MIE_BIT))

        # 3. Dispatch to Direct base or Vectored (base + 4 * cause_code) handler address
        base = self.mtvec & WORD_ALIGN_MASK
        mode = self.mtvec & MTVEC_MODE_MASK
        if is_interrupt and mode == MTVEC_MODE_VECTORED:
            target = u32(base + INSN_SIZE_BYTES * (cause & MCAUSE_CODE_MASK))
        else:
            target = base
        self.pc = target
        return target

    def _trap_trace(
        self, cur_pc: int, insn: int, cause: int, tval: int, is_interrupt: bool = False
    ) -> StepTrace:
        """Record a trap via `_take_trap()` and return the corresponding `StepTrace`."""
        target = self._take_trap(cause, tval, is_interrupt=is_interrupt)
        return StepTrace(
            pc=cur_pc,
            insn=insn,
            next_pc=target,
            trap_cause=u32(cause),
            interrupt=is_interrupt,
        )

    def _set_reg(self, rd: int, val: int) -> int:
        """Write `u32(val)` to `rd` (`x0` stays hardwired to `0`) and return the committed word."""
        if rd == 0:
            return 0
        u_val = u32(val)
        self.regs[rd] = u_val
        return u_val

    # -----------------------------------------------------------------------
    # Modular Instruction-Family Execution Helpers (Uniform ExecOutcome | StepTrace)
    # -----------------------------------------------------------------------
    def _check_pending_interrupt(self, cur_pc: int) -> StepTrace | None:
        """Return a trap `StepTrace` if an enabled IRQ is pending (MEIP > MSIP > MTIP)."""
        # Global interrupt enable (MSTATUS_MIE_BIT) gates all maskable interrupts atomically
        if not (self.mstatus & MSTATUS_MIE_BIT):
            return None
        pending = self._live_mip() & self.mie
        for bit, cause in (
            (MIE_MEIE_BIT, CAUSE_INT_M_EXT),
            (MIE_MSIE_BIT, CAUSE_INT_M_SW),
            (MIE_MTIE_BIT, CAUSE_INT_M_TIMER),
        ):
            if pending & bit:
                # Asynchronous interrupts arrive before instruction fetch, so insn=0 and mtval=0
                return self._trap_trace(cur_pc, 0, cause, 0, is_interrupt=True)
        return None

    def _fetch_instruction(self, cur_pc: int) -> int | StepTrace:
        """Fetch an aligned 32-bit word from executable memory, or return a trap `StepTrace`."""
        if (cur_pc & WORD_ALIGN_LOW_BITS) != 0:
            return self._trap_trace(cur_pc, 0, CAUSE_INSN_MISALIGNED, cur_pc)
        # Restrict instruction fetches to memory regions so MMIO registers never run as code
        if (region := self._find_mem_region(cur_pc, INSN_SIZE_BYTES)) is None:
            return self._trap_trace(cur_pc, 0, CAUSE_INSN_ACCESS_FAULT, cur_pc)
        return region.read_bytes(cur_pc, INSN_SIZE_BYTES)

    def _exec_jal(self, insn: int, cur_pc: int, rd: int, link_pc: int) -> ExecOutcome | StepTrace:
        """Execute `jal`, returning `ExecOutcome` or a misaligned-target trap."""
        target = u32(cur_pc + _dec_imm_j(insn))
        # Validate 4-byte target alignment before retiring return link (cur_pc + 4) into rd
        if target & WORD_ALIGN_LOW_BITS:
            return self._trap_trace(cur_pc, insn, CAUSE_INSN_MISALIGNED, target)
        return ExecOutcome(rd=rd, rd_val=link_pc, next_pc=target)

    def _exec_jalr(
        self, insn: int, cur_pc: int, rd: int, rs1_u: int, funct3: int, link_pc: int
    ) -> ExecOutcome | StepTrace:
        """Execute `jalr`, returning `ExecOutcome` or an illegal/misaligned trap."""
        if funct3 != F3_JALR:
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
        imm = sign_extend(insn >> 20, 12)
        # Clears Bit 0 of (rs1 + imm); traps if Bit 1 stays set (4-byte alignment / IALIGN=32)
        target = u32((rs1_u + imm) & JALR_TARGET_MASK)
        if target & WORD_ALIGN_LOW_BITS:
            return self._trap_trace(cur_pc, insn, CAUSE_INSN_MISALIGNED, target)
        return ExecOutcome(rd=rd, rd_val=link_pc, next_pc=target)

    def _exec_branch(
        self, insn: int, cur_pc: int, rs1_u: int, rs2_u: int, funct3: int
    ) -> ExecOutcome | StepTrace:
        """Evaluate a B-type conditional branch and return `ExecOutcome` or a trap."""
        rs1_s, rs2_s = s32(rs1_u), s32(rs2_u)
        comparisons = {
            F3_BEQ: rs1_u == rs2_u,
            F3_BNE: rs1_u != rs2_u,
            F3_BLT: rs1_s < rs2_s,
            F3_BGE: rs1_s >= rs2_s,
            F3_BLTU: rs1_u < rs2_u,
            F3_BGEU: rs1_u >= rs2_u,
        }
        if funct3 not in comparisons:
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
        # An untaken branch ignores target alignment and advances cleanly to default_next_pc
        if not comparisons[funct3]:
            return ExecOutcome()
        target = u32(cur_pc + _dec_imm_b(insn))
        if target & WORD_ALIGN_LOW_BITS:
            return self._trap_trace(cur_pc, insn, CAUSE_INSN_MISALIGNED, target)
        return ExecOutcome(next_pc=target)

    def _exec_load(
        self, insn: int, cur_pc: int, rd: int, rs1_u: int, funct3: int
    ) -> ExecOutcome | StepTrace:
        """Execute `lb`/`lh`/`lw`/`lbu`/`lhu`, returning `ExecOutcome` or an alignment/bus trap."""
        width_map = {F3_LB: 1, F3_LH: 2, F3_LW: 4, F3_LBU: 1, F3_LHU: 2}
        width = width_map.get(funct3)
        if width is None:
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

        addr = u32(rs1_u + sign_extend(insn >> 20, 12))
        # Natural alignment (addr & (width - 1)) is checked before bus lookup per privilege priority
        if (addr & (width - 1)) != 0:
            return self._trap_trace(cur_pc, insn, CAUSE_LOAD_MISALIGNED, addr)

        try:
            raw = self.bus_read(addr, width)
        except MemoryAccessFault:
            return self._trap_trace(cur_pc, insn, CAUSE_LOAD_ACCESS_FAULT, addr)

        if funct3 == F3_LB:
            val = sign_extend(raw, 8)
        elif funct3 == F3_LH:
            val = s16(raw)
        else:  # F3_LW, F3_LBU, and F3_LHU (`bus_read` already zero-extends 1/2/4-byte reads)
            val = raw

        u_val = u32(val)
        return ExecOutcome(rd=rd, rd_val=u_val, mem_addr=addr, mem_val=u_val)

    def _exec_store(
        self, insn: int, cur_pc: int, rs1_u: int, rs2_u: int, funct3: int
    ) -> ExecOutcome | StepTrace:
        """Execute `sb`/`sh`/`sw`, returning `ExecOutcome` or an alignment/bus trap."""
        width_map = {F3_SB: 1, F3_SH: 2, F3_SW: 4}
        width = width_map.get(funct3)
        if width is None:
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

        addr = u32(rs1_u + _dec_imm_s(insn))
        if (addr & (width - 1)) != 0:
            return self._trap_trace(cur_pc, insn, CAUSE_STORE_MISALIGNED, addr)

        # Truncate rs2 down to 8, 16, or 32 low bits before writing little-endian bytes to bus
        store_val = rs2_u & ((1 << (8 * width)) - 1)
        try:
            self.bus_write(addr, width, store_val)
        except MemoryAccessFault:
            return self._trap_trace(cur_pc, insn, CAUSE_STORE_ACCESS_FAULT, addr)
        return ExecOutcome(mem_addr=addr, mem_val=store_val, mem_write=True)

    def _exec_op_imm(
        self, insn: int, cur_pc: int, rd: int, rs1_u: int, funct3: int, funct7: int
    ) -> ExecOutcome | StepTrace:
        """Execute RV32I immediate ALU instructions (`OPCODE_OP_IMM`), or return a trap."""
        rs1_s = s32(rs1_u)
        imm = sign_extend(insn >> 20, 12)
        # Shift-immediates use the low 5 bits (shamt) and reserve Bits 31..25 (funct7) for mode
        shamt = (insn >> 20) & REG_MASK
        if funct3 == F3_ADD_SUB:
            res = rs1_u + imm
        elif funct3 == F3_SLT:
            res = 1 if rs1_s < imm else 0
        elif funct3 == F3_SLTU:
            # `sltiu` sign-extends the 12-bit constant first, then compares unsigned
            res = 1 if rs1_u < u32(imm) else 0
        elif funct3 == F3_XOR:
            res = rs1_u ^ u32(imm)
        elif funct3 == F3_OR:
            res = rs1_u | u32(imm)
        elif funct3 == F3_AND:
            res = rs1_u & u32(imm)
        elif funct3 == F3_SLL:
            if funct7 != F7_BASE:
                return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
            res = rs1_u << shamt
        else:  # F3_SRL_SRA (all 3-bit funct3 values 0..7 handled)
            if funct7 == F7_BASE:
                res = rs1_u >> shamt
            elif funct7 == F7_ALT:
                res = rs1_s >> shamt  # Copies Bit 31; retirement truncates result to 32 bits
            else:
                return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
        return ExecOutcome(rd=rd, rd_val=res)

    def _exec_muldiv(self, rd: int, rs1_u: int, rs2_u: int, funct3: int) -> ExecOutcome:
        """Execute all 8 RV32M multiply/divide instructions with RISC-V overflow/zero semantics."""
        rs1_s, rs2_s = s32(rs1_u), s32(rs2_u)
        if funct3 == F3_MUL:      # Lower 32 bits match across signed and unsigned products
            res = rs1_s * rs2_s
        elif funct3 == F3_MULH:   # >> 32 on negative product keeps Bits 63..32 in two's complement
            res = (rs1_s * rs2_s) >> 32
        elif funct3 == F3_MULHSU:
            res = (rs1_s * rs2_u) >> 32
        elif funct3 == F3_MULHU:
            res = (rs1_u * rs2_u) >> 32
        elif funct3 == F3_DIV:
            res = trunc_div_s32(rs1_s, rs2_s)
        elif funct3 == F3_DIVU:
            # RISC-V does not trap on division by zero; unsigned divu returns UINT32_MAX (all 1s)
            res = UINT32_MAX if rs2_u == 0 else (rs1_u // rs2_u)
        elif funct3 == F3_REM:
            # Exact zero when INT32_MIN / -1 overflows; otherwise q * divisor + rem == dividend
            if rs1_s == INT32_MIN and rs2_s == -1:
                res = 0
            else:
                res = rs1_s - trunc_div_s32(rs1_s, rs2_s) * rs2_s
        else:  # F3_REMU: RISC-V remainder by zero returns the original dividend unchanged
            res = rs1_u if rs2_u == 0 else (rs1_u % rs2_u)
        return ExecOutcome(rd=rd, rd_val=res)

    def _exec_op_reg(
        self,
        insn: int,
        cur_pc: int,
        rd: int,
        rs1_u: int,
        rs2_u: int,
        funct3: int,
        funct7: int,
    ) -> ExecOutcome | StepTrace:
        """Execute RV32I + RV32M register ALU instructions (`OPCODE_OP`), or return a trap."""
        if funct7 == F7_MULDIV:
            return self._exec_muldiv(rd, rs1_u, rs2_u, funct3)
        rs1_s, rs2_s = s32(rs1_u), s32(rs2_u)
        if funct7 == F7_BASE:
            # 32-bit barrel shifters use only the low 5 bits (rs2 & REG_MASK) for shifts 0..31
            ops = {
                F3_ADD_SUB: rs1_u + rs2_u,
                F3_SLL: rs1_u << (rs2_u & REG_MASK),
                F3_SLT: 1 if rs1_s < rs2_s else 0,
                F3_SLTU: 1 if rs1_u < rs2_u else 0,
                F3_XOR: rs1_u ^ rs2_u,
                F3_SRL_SRA: rs1_u >> (rs2_u & REG_MASK),
                F3_OR: rs1_u | rs2_u,
                F3_AND: rs1_u & rs2_u,
            }
            return ExecOutcome(rd=rd, rd_val=ops[funct3])
        if funct7 == F7_ALT:
            if funct3 == F3_ADD_SUB:
                return ExecOutcome(rd=rd, rd_val=rs1_u - rs2_u)
            if funct3 == F3_SRL_SRA:
                return ExecOutcome(rd=rd, rd_val=rs1_s >> (rs2_u & REG_MASK))
        return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

    def _exec_zicsr(
        self, insn: int, cur_pc: int, rd: int, rs1: int, rs1_u: int, funct3: int
    ) -> ExecOutcome | StepTrace:
        """Execute atomic Zicsr ops (`csrrw`, `csrrs`, `csrrc`, `csrrwi`, `csrrsi`, `csrrci`)."""
        csr_addr = (insn >> 20) & CSR_ADDR_MASK
        old_val = self._read_csr(csr_addr)
        if old_val is None:
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

        # Bit 2 of funct3 selects zero-extended 5-bit uimm encoded directly in the rs1 bitfield
        src_val = rs1 if (funct3 & ZICSR_IMM_BIT) else rs1_u
        op = funct3 & ZICSR_OP_MASK
        if op == ZICSR_OP_RW:     # csrrw / csrrwi always attempt a CSR write
            new_val, do_write = src_val, True
        elif op == ZICSR_OP_RS:   # csrrs / csrrsi skip write when rs1 == 0 (read-only query)
            new_val, do_write = old_val | src_val, (rs1 != 0)
        else:                     # csrrc / csrrci clear bits via MASK32 XOR; skip if rs1 == 0
            new_val, do_write = old_val & (MASK32 ^ src_val), (rs1 != 0)

        wrote_minstret = False
        if do_write:
            # Trap before writing rd so faulted read-only CSR writes leave rd untouched;
            # rs1_u was latched before writeback so rd == rs1 swaps remain atomic.
            if not self._write_csr(csr_addr, new_val):
                return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
            wrote_minstret = csr_addr in (CSR_MINSTRET, CSR_MINSTRETH)

        return ExecOutcome(rd=rd, rd_val=old_val, suppress_minstret=wrote_minstret)

    def _exec_system(
        self, insn: int, cur_pc: int, rd: int, rs1: int, rs1_u: int, funct3: int
    ) -> ExecOutcome | StepTrace:
        """Execute `ecall`/`ebreak`/`mret`/`wfi` and delegate Zicsr register accesses."""
        if funct3 == F3_PRIV:
            # Exact full-word matching enforces reserved rd=x0/rs1=x0 zeros per privileged spec
            if insn == INSN_ECALL:
                return self._trap_trace(cur_pc, insn, CAUSE_ECALL_M, 0)
            if insn == INSN_EBREAK:
                self.halted = True
                return self._trap_trace(cur_pc, insn, CAUSE_BREAKPOINT, cur_pc)
            if insn == INSN_MRET:
                # Pop 1-deep IRQ-enable stack (MIE <- MPIE; MPIE <- 1) under 4-byte IALIGN=32 mask
                mpie = bool(self.mstatus & MSTATUS_MPIE_BIT)
                self._set_mstatus_irq_bits(mie=mpie, mpie=True)
                return ExecOutcome(next_pc=self.mepc & WORD_ALIGN_MASK)
            if insn == INSN_WFI:
                # Single-step emulation has no idle clock-gating wait, so `wfi` retires as a no-op
                return ExecOutcome()
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

        if funct3 in (F3_CSRRW, F3_CSRRS, F3_CSRRC, F3_CSRRWI, F3_CSRRSI, F3_CSRRCI):
            return self._exec_zicsr(insn, cur_pc, rd, rs1, rs1_u, funct3)
        return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

    def _exec_mac(
        self, insn: int, cur_pc: int, rd: int, rs1_u: int, rs2_u: int, funct3: int, funct7: int
    ) -> ExecOutcome | StepTrace:
        """Execute Xapex custom-0 dual-int16 saturating MAC instructions, or return a trap."""
        if funct7 != F7_BASE:
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
        if funct3 in (MAC_F3_ACC, MAC_F3_CLR):
            # Split rs1 and rs2 into lower Bits 15..0 and upper Bits 31..16 signed int16 lanes
            a0, a1 = s16(rs1_u), s16(rs1_u >> 16)
            b0, b1 = s16(rs2_u), s16(rs2_u >> 16)
            base_acc = 0 if funct3 == MAC_F3_CLR else self.mac_acc
            self.mac_acc = sat32(base_acc + a0 * b0 + a1 * b1)
            return ExecOutcome(rd=rd, rd_val=self.mac_acc)
        if funct3 == MAC_F3_SET:
            self.mac_acc = s32(rs1_u)
            return ExecOutcome(rd=rd, rd_val=self.mac_acc)
        if funct3 == MAC_F3_GET:
            return ExecOutcome(rd=rd, rd_val=self.mac_acc)
        return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

    # -----------------------------------------------------------------------
    # Single-Instruction Execution & Run Loop
    # -----------------------------------------------------------------------
    def step(self) -> StepTrace:
        """Advance CPU and CLINT timers by one instruction/trap and return its `StepTrace`."""
        cur_pc = self.pc
        # 1. Advance free-running 64-bit clocks pre-fetch (wrapped to 64 bits) so alarms fire
        self.mcycle = (self.mcycle + 1) & MASK64
        self.mtime = (self.mtime + 1) & MASK64
        if (irq_trace := self._check_pending_interrupt(cur_pc)) is not None:
            return irq_trace

        # 2. Fetch aligned 32-bit instruction word at cur_pc
        fetched = self._fetch_instruction(cur_pc)
        if isinstance(fetched, StepTrace):
            return fetched
        insn = fetched

        # 3. Slice common RISC-V bitfields and latch unsigned 32-bit operands pre-writeback
        opcode = insn & OPCODE_MASK
        rd = (insn >> 7) & REG_MASK
        funct3 = (insn >> 12) & FUNCT3_MASK
        rs1 = (insn >> 15) & REG_MASK
        rs2 = (insn >> 20) & REG_MASK
        funct7 = (insn >> 25) & FUNCT7_MASK

        rs1_u, rs2_u = self.regs[rs1], self.regs[rs2]
        default_next_pc = u32(cur_pc + INSN_SIZE_BYTES)

        # 4. Dispatch by 7-bit major opcode under uniform ExecOutcome | StepTrace contract
        result: ExecOutcome | StepTrace
        if opcode == OPCODE_LUI:
            result = ExecOutcome(rd=rd, rd_val=insn & UPPER20_MASK)
        elif opcode == OPCODE_AUIPC:
            result = ExecOutcome(rd=rd, rd_val=cur_pc + (insn & UPPER20_MASK))
        elif opcode == OPCODE_JAL:
            result = self._exec_jal(insn, cur_pc, rd, default_next_pc)
        elif opcode == OPCODE_JALR:
            result = self._exec_jalr(insn, cur_pc, rd, rs1_u, funct3, default_next_pc)
        elif opcode == OPCODE_BRANCH:
            result = self._exec_branch(insn, cur_pc, rs1_u, rs2_u, funct3)
        elif opcode == OPCODE_LOAD:
            result = self._exec_load(insn, cur_pc, rd, rs1_u, funct3)
        elif opcode == OPCODE_STORE:
            result = self._exec_store(insn, cur_pc, rs1_u, rs2_u, funct3)
        elif opcode == OPCODE_OP_IMM:
            result = self._exec_op_imm(insn, cur_pc, rd, rs1_u, funct3, funct7)
        elif opcode == OPCODE_OP:
            result = self._exec_op_reg(insn, cur_pc, rd, rs1_u, rs2_u, funct3, funct7)
        elif opcode == OPCODE_MISC_MEM:
            # Single-core execution without caches commits in order, so `fence`/`fence.i` no-op
            result = (
                ExecOutcome()
                if funct3 in (F3_FENCE, F3_FENCE_I)
                else self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
            )
        elif opcode == OPCODE_SYSTEM:
            result = self._exec_system(insn, cur_pc, rd, rs1, rs1_u, funct3)
        elif opcode == OPCODE_CUSTOM0:
            result = self._exec_mac(insn, cur_pc, rd, rs1_u, rs2_u, funct3, funct7)
        else:
            result = self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

        if isinstance(result, StepTrace):
            return result

        # 5. Retire: enforce hardwired x0 via _set_reg(), commit next_pc, and tick 64-bit minstret
        wb_val = self._set_reg(result.rd, result.rd_val)
        next_pc = default_next_pc if result.next_pc is None else result.next_pc
        self.pc = next_pc
        if not result.suppress_minstret:
            self.minstret = (self.minstret + 1) & MASK64

        return StepTrace(
            pc=cur_pc,
            insn=insn,
            next_pc=next_pc,
            rd=result.rd,
            rd_val=wb_val,
            mem_addr=result.mem_addr,
            mem_val=result.mem_val,
            mem_write=result.mem_write,
        )

    def run(
        self,
        max_steps: int = 10_000,
        stop_on_ebreak: bool = True,
        stop_on_pc: int | None = None,
    ) -> list[StepTrace]:
        """Run up to `max_steps` steps, halting on `stop_on_ebreak` (`ebreak`) or `stop_on_pc`."""
        traces: list[StepTrace] = []
        self.halted = False
        for _ in range(max_steps):
            if stop_on_pc is not None and self.pc == u32(stop_on_pc):
                break
            tr = self.step()
            traces.append(tr)
            if stop_on_ebreak and tr.trap_cause == CAUSE_BREAKPOINT:
                break
        return traces
