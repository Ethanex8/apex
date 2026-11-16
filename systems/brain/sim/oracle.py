"""Golden instruction-by-instruction RISC-V reference emulator (RV32IM + Zicsr + Xapex MAC).

Purpose:
  Serve as the single source of truth for verifying every SystemVerilog CPU core
  (single-cycle and 5-stage pipelined) and the scratch SysC compiler toolchain.

Usage:
  cpu = RV32Oracle()
  cpu.load_words(BOOT_ROM_BASE, program_words)
  traces = cpu.run(max_steps=10_000)

Invariants:
  - Models architectural `pc`, `x0..x31` (`x0` hardwired to 0), 32-bit saturating `mac_acc`,
    17 Machine-mode Control & Status Registers (CSRs, Write-Any/Read-Legal WARL-masked),
    and `CLINT`/`UART0` peripherals across 4 KB sparse memory pages.
  - Pre-fetch interrupt priority follows RISC-V Privileged Spec (`MEIP > MSIP > MTIP`).

Memory Map (matching systems/brain/README.md):
  0x0000_0000 - 0x0000_3FFF : Boot ROM (16 KB, read-only to CPU)
  0x1000_0000 - 0x1000_FFFF : On-chip BRAM (64 KB, R/W)
  0x2000_0000 - 0x20FF_FFFF : QSPI NOR Flash XIP window (16 MB, read-only to CPU)
  0x4000_0000 - 0x41FF_FFFF : External SDR SDRAM (32 MB, R/W)
  0x8000_0000 - 0x8000_FFFF : CLINT 64-bit timer & alarm (mtime / mtimecmp)
  0x8001_0000 - 0x8001_FFFF : UART0 serial console (TX/RX FIFOs + status)
  0x8002_0000 - 0x8006_FFFF : Reserved spine MMIO stub pages (SPI0/CAN0/CAN1/SYNC/GPIO)

Custom Xapex MAC Instruction (RISC-V custom-0 opcode 0x0B, funct7 = 0x00):
  Uses an internal 32-bit saturating accumulator (`mac_acc`) so dual-int16 dot products
  run at 1 instruction/cycle with a standard 2-read-port register file:
    funct3 = 0b000 : mac rd, rs1, rs2     -> acc = sat32(acc + s16(rs1[15:0])*s16(rs2[15:0]) + s16(rs1[31:16])*s16(rs2[31:16])); rd = acc
    funct3 = 0b001 : mac.clr rd, rs1, rs2 -> acc = sat32(0   + s16(rs1[15:0])*s16(rs2[15:0]) + s16(rs1[31:16])*s16(rs2[31:16])); rd = acc
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
SYS_CLK_HZ = 50_000_000       # 50 MHz FPGA fabric clock
UART_DEFAULT_BAUD = 115_200   # Default serial bit rate (50e6 // 115200 = 434 ticks/bit)

# Boot ROM & QSPI Flash reject CPU writes (MemoryAccessFault); host loaders use bypass_ro=True
BOOT_ROM_BASE = 0x0000_0000   # Immutable on-chip startup bootloader
BOOT_ROM_SIZE = 0x0000_4000   # 16 KB

BRAM_BASE = 0x1000_0000       # Single-cycle on-chip FPGA Block RAM (stack, hot weights)
BRAM_SIZE = 0x0001_0000       # 64 KB

QSPI_BASE = 0x2000_0000       # External Execute-in-Place (XIP) NOR Flash window
QSPI_SIZE = 0x0100_0000       # 16 MB

SDRAM_BASE = 0x4000_0000      # External main Synchronous DRAM (firmware heap & buffers)
SDRAM_SIZE = 0x0200_0000      # 32 MB

# CLINT (Core-Local Interruptor): 64-bit monotonic clock & comparator split across 32-bit LE offsets
CLINT_BASE = 0x8000_0000
CLINT_SIZE = 0x0001_0000
CLINT_MTIME_LO = 0x00         # Bits 31..0 of 64-bit timer tick counter
CLINT_MTIME_HI = 0x04         # Bits 63..32 of 64-bit timer tick counter
CLINT_MTIMECMP_LO = 0x08      # Bits 31..0 of 64-bit alarm threshold (IRQ when mtime >= mtimecmp)
CLINT_MTIMECMP_HI = 0x0C      # Bits 63..32 of 64-bit alarm threshold

# UART0 (Universal Asynchronous Receiver-Transmitter): byte-stream debug console
UART0_BASE = 0x8001_0000
UART0_SIZE = 0x0001_0000
UART0_TXDATA = 0x00           # Write-only low byte transmits to TX buffer + callback
UART0_RXDATA = 0x04           # Read pops 1 byte from RX FIFO (returns 0 when empty)
UART0_STATUS = 0x08           # Bit 0: TX ready (1), Bit 1: TX empty (1), Bit 2: RX data valid
UART0_BAUDDIV = 0x0C          # Clock cycles per serial bit (clamped >= 1 on write)

# Five reserved 64 KB MMIO pages (SPI0, CAN0, CAN1, SYNC, GPIO) backed by stub scratch RAM
MMIO_STUB_BASE = 0x8002_0000
MMIO_STUB_END = 0x8007_0000

# ---------------------------------------------------------------------------
# Machine-Mode CSR Addresses & Trap Causes
# ---------------------------------------------------------------------------
# RISC-V CSR encoding: Bits 11..10 = privilege/access (`11` = read-only), Bits 9..8 = mode (`11` = M)
CSR_MSTATUS = 0x300           # Machine status: global interrupt gate MIE & saved MPIE/MPP
CSR_MISA = 0x301              # ISA capability ID (read-only here; writes trap as illegal)
CSR_MIE = 0x304               # Machine interrupt-enable mask (MSIE/MTIE/MEIE)
CSR_MTVEC = 0x305             # Trap handler base address + mode (0=Direct, 1=Vectored)
CSR_MSCRATCH = 0x340          # OS scratch register (atomic swap during trap entry)
CSR_MEPC = 0x341              # Saved return PC on exception/interrupt (4-byte aligned)
CSR_MCAUSE = 0x342            # Trap cause code (Bit 31 = 1 for interrupt, 0 for exception)
CSR_MTVAL = 0x343             # Trap-specific diagnostic value (faulting PC, addr, or insn word)
CSR_MIP = 0x344               # Pending interrupts: software/external latch OR live CLINT MTIP
CSR_MCYCLE = 0xB00            # Lower 32 bits of total cycle counter (ticks every step)
CSR_MINSTRET = 0xB02          # Lower 32 bits of retired (non-trapping) instruction counter
CSR_MCYCLEH = 0xB80           # Upper 32 bits of `mcycle`
CSR_MINSTRETH = 0xB82         # Upper 32 bits of `minstret`
CSR_MVENDORID = 0xF11         # Read-only vendor ID (0 = non-commercial/open)
CSR_MARCHID = 0xF12           # Read-only architecture ID (0)
CSR_MIMPID = 0xF13            # Read-only implementation ID (0)
CSR_MHARTID = 0xF14           # Read-only hardware thread ID (0 = single-core hart)

# Synchronous exception causes (Bit 31 = 0) and asynchronous interrupt causes (Bit 31 = 1)
CAUSE_INSN_MISALIGNED = 0     # PC or jump/taken-branch target not divisible by 4
CAUSE_INSN_ACCESS_FAULT = 1   # Instruction fetch hit unmapped bus address
CAUSE_ILLEGAL_INSN = 2        # Unknown opcode/funct, unsupported SYSTEM encoding, or RO CSR write
CAUSE_BREAKPOINT = 3          # EBREAK instruction executed
CAUSE_LOAD_MISALIGNED = 4     # Load address not divisible by access width (2 or 4)
CAUSE_LOAD_ACCESS_FAULT = 5   # Load hit unmapped bus address or invalid MMIO width
CAUSE_STORE_MISALIGNED = 6    # Store address not divisible by access width (2 or 4)
CAUSE_STORE_ACCESS_FAULT = 7  # Store hit ROM/QSPI or unmapped address
CAUSE_ECALL_M = 11            # Synchronous Machine-mode system call (ECALL)
CAUSE_INT_M_SW = 0x8000_0003     # Machine software interrupt (Bit 31 | 3)
CAUSE_INT_M_TIMER = 0x8000_0007  # Machine timer interrupt from CLINT (Bit 31 | 7)
CAUSE_INT_M_EXT = 0x8000_000B    # Machine external interrupt (Bit 31 | 11)

MSTATUS_MIE_BIT = 1 << 3      # Bit 3: Master machine interrupt enable
MSTATUS_MPIE_BIT = 1 << 7     # Bit 7: 1-deep stack holding prior MIE across trap/MRET
MSTATUS_MPP_M = 0b11 << 11    # Bits 12..11: Previous privilege hardwired to Machine mode (0b11)

MIE_MSIE_BIT = 1 << 3         # Bit 3 in both `mie` and `mip` (Software IRQ enable/pending)
MIE_MTIE_BIT = 1 << 7         # Bit 7 in both `mie` and `mip` (Timer IRQ enable/pending)
MIE_MEIE_BIT = 1 << 11        # Bit 11 in both `mie` and `mip` (External IRQ enable/pending)

# RISC-V custom-0 major opcode reserved for Xapex extensions
OPCODE_CUSTOM0 = 0x0B

# Explicit bitmasks constrain Python's infinite-precision ints to fixed 32/64-bit hardware wires
MASK32 = 0xFFFF_FFFF
MASK64_HI32 = 0xFFFF_FFFF_0000_0000
INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1


# ---------------------------------------------------------------------------
# Bitwise Arithmetic & Instruction Encoding Helpers
# ---------------------------------------------------------------------------
def u32(val: int) -> int:
    """Wrap an arbitrary Python integer into unsigned 32-bit range [0, 2^32 - 1] (mod 2^32)."""
    return val & MASK32


def s32(val: int) -> int:
    """Interpret lower 32 bits as signed two's complement: S_32(b) = U_32(b) - b_31 * 2^32."""
    u = u32(val)
    return u - (u >> 31) * (1 << 32)


def s16(val: int) -> int:
    """Interpret lower 16 bits as signed two's complement: S_16(b) = U_16(b) - b_15 * 2^16."""
    u = val & 0xFFFF
    return u - (u >> 15) * (1 << 16)


def sat32(val: int) -> int:
    """Clamp an integer to signed 32-bit bounds [INT32_MIN, INT32_MAX] without wrapping."""
    if val < INT32_MIN:
        return INT32_MIN
    if val > INT32_MAX:
        return INT32_MAX
    return val


def sign_extend(val: int, bits: int) -> int:
    """Sign-extend a `bits`-wide value branchlessly via `(u ^ 2^(k-1)) - 2^(k-1)`."""
    # Flipping the MSB turns [0..2^(k-1)-1] -> [2^(k-1)..2^k-1] and vice versa; subtracting 2^(k-1) recovers S_k
    sign_bit = 1 << (bits - 1)
    mask = (1 << bits) - 1
    val &= mask
    return (val ^ sign_bit) - sign_bit


def enc_r(funct7: int, rs2: int, rs1: int, funct3: int, rd: int, opcode: int) -> int:
    """Encode a 32-bit R-type (register-register) RISC-V instruction word."""
    return (
        ((funct7 & 0x7F) << 25)
        | ((rs2 & 0x1F) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | ((rd & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def enc_i(imm: int, rs1: int, funct3: int, rd: int, opcode: int) -> int:
    """Encode a 32-bit I-type (12-bit immediate / load / jalr / CSR) RISC-V instruction word."""
    return (
        ((imm & 0xFFF) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | ((rd & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def enc_s(imm: int, rs2: int, rs1: int, funct3: int, opcode: int) -> int:
    """Encode a 32-bit S-type (store) word, keeping `rs1`/`rs2` fixed and splitting `imm[11:0]`."""
    # Pins rs2 at Bits 24..20 and rs1 at 19..15 across formats, so imm[11:0] splits around them
    imm12 = imm & 0xFFF
    return (
        (((imm12 >> 5) & 0x7F) << 25)
        | ((rs2 & 0x1F) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | ((imm12 & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def enc_b(imm: int, rs2: int, rs1: int, funct3: int, opcode: int = 0x63) -> int:
    """Encode a 32-bit B-type conditional branch from a signed byte offset (omits Bit 0 = 0)."""
    # Scrambles imm[12:1] so sign bit stays at Bit 31 and bits 10..5 / 4..1 align with S-type wires
    imm13 = imm & 0x1FFF
    return (
        (((imm13 >> 12) & 0x1) << 31)
        | (((imm13 >> 5) & 0x3F) << 25)
        | ((rs2 & 0x1F) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | (((imm13 >> 1) & 0xF) << 8)
        | (((imm13 >> 11) & 0x1) << 7)
        | (opcode & 0x7F)
    )


def enc_u(imm20_shifted: int, rd: int, opcode: int) -> int:
    """Encode a 32-bit U-type (`LUI` / `AUIPC`) word taking pre-shifted bits `[31:12]`."""
    # Caller supplies bits already aligned to [31:12] (e.g., 0x1234_5000), unlike unshifted enc_i..enc_j
    return (imm20_shifted & 0xFFFF_F000) | ((rd & 0x1F) << 7) | (opcode & 0x7F)


def enc_j(imm: int, rd: int, opcode: int = 0x6F) -> int:
    """Encode a 32-bit J-type (`JAL`) word from a signed 21-bit byte offset (omits Bit 0 = 0)."""
    # Keeps imm[20] at Bit 31 (sign) and imm[19:12] in Bits 19..12 (matching U-type mux lanes)
    imm21 = imm & 0x1F_FFFF
    return (
        (((imm21 >> 20) & 0x1) << 31)
        | (((imm21 >> 1) & 0x3FF) << 21)
        | (((imm21 >> 11) & 0x1) << 20)
        | (((imm21 >> 12) & 0xFF) << 12)
        | ((rd & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def enc_mac(rd: int, rs1: int, rs2: int, funct3: int = 0) -> int:
    """Encode Xapex `custom-0` MAC (`0=mac`, `1=mac.clr`, `2=mac.set` ignores `rs2`, `3=mac.get` ignores both)."""
    return enc_r(0x00, rs2, rs1, funct3, rd, OPCODE_CUSTOM0)


# ---------------------------------------------------------------------------
# Memory Model & Commit Trace Types
# ---------------------------------------------------------------------------
class MemoryAccessFault(Exception):
    """Raised internally when a bus transaction targets an unmapped, misaligned, or RO region."""


class SparseMemory:
    """Page-backed little-endian memory supporting large address spaces without upfront allocation."""

    PAGE_SIZE = 4096

    def __init__(self, base: int, size: int, writable: bool = True) -> None:
        """Initialize a sparse memory region spanning `[base, base + size)`."""
        self.base = base
        self.size = size
        self.writable = writable
        self._pages: dict[int, bytearray] = {}

    def contains(self, addr: int, width: int) -> bool:
        """Return True if the entire `[addr, addr + width)` access falls within this region."""
        return self.base <= addr and (addr + width) <= (self.base + self.size)

    def _get_page(self, page_idx: int, create: bool) -> bytearray | None:
        """Fetch an allocated 4 KB page by index, optionally allocating zeroed bytes on write."""
        page = self._pages.get(page_idx)
        if page is None and create:
            page = bytearray(self.PAGE_SIZE)
            self._pages[page_idx] = page
        return page

    def read_bytes(self, addr: int, width: int) -> int:
        """Read `width` bytes (1, 2, or 4) from `addr` in little-endian byte order."""
        if width not in (1, 2, 4) or not self.contains(addr, width):
            raise MemoryAccessFault(f"Out-of-bounds read at 0x{addr:08x} (width={width})")
        val = 0
        # Byte-by-byte loop handles multi-byte accesses crossing 4 KB sparse page boundaries cleanly
        for i in range(width):
            offset = (addr + i) - self.base
            page = self._pages.get(offset // self.PAGE_SIZE)
            byte = page[offset % self.PAGE_SIZE] if page is not None else 0
            val |= byte << (8 * i)
        return val

    def write_bytes(self, addr: int, width: int, val: int, bypass_ro: bool = False) -> None:
        """Write `width` little-endian bytes of `val` to `addr`, honoring `writable` unless bypassed."""
        if width not in (1, 2, 4) or not self.contains(addr, width):
            raise MemoryAccessFault(f"Out-of-bounds write at 0x{addr:08x} (width={width})")
        if not self.writable and not bypass_ro:
            raise MemoryAccessFault(f"Write to read-only region at 0x{addr:08x}")
        for i in range(width):
            offset = (addr + i) - self.base
            page = self._get_page(offset // self.PAGE_SIZE, create=True)
            assert page is not None
            page[offset % self.PAGE_SIZE] = (val >> (8 * i)) & 0xFF


@dataclass
class StepTrace:
    """Architectural commit record emitted by `RV32Oracle.step()` for RTL lockstep checks.

    On normal instructions, `insn` is the fetched word and `next_pc` is the sequential/branch PC.
    On traps or interrupts, `trap_cause` holds `mcause`, `next_pc` holds the trap vector target,
    and `insn` is `0` when preemption or fetch failure occurred before decode. `rd`/`rd_val` default
    to `(0, 0)` when no register commits or `rd == x0`. `mem_val` holds the 32-bit extended load
    value on loads and the width-masked low byte/halfword/word (`0xFF`/`0xFFFF`/`0xFFFF_FFFF`) on stores.
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


# ---------------------------------------------------------------------------
# Golden RISC-V Reference CPU & SoC Emulator
# ---------------------------------------------------------------------------
class RV32Oracle:
    """Instruction-accurate RISC-V RV32IM + Zicsr + Xapex MAC reference CPU and SoC.

    Models the complete programmer-visible state of the `brain` System-on-Chip:
      - Architectural CPU state: program counter (`pc`), 32 general-purpose registers (`regs`),
        and the internal 32-bit saturating `mac_acc` accumulator.
      - Machine-mode Control & Status Registers (`mstatus`, `mie`, `mip`, `mtvec`, `mepc`,
        `mcause`, `mtval`, `mscratch`, `mcycle`, `minstret`, and read-only IDs).
      - Sparse memory map (`rom`, `bram`, `qspi`, `sdram`, plus `mmio_stub`).
      - Memory-mapped peripherals: `CLINT` 64-bit timer/alarm and `UART0` TX/RX FIFOs.

    Primary entry points are `load_words()` / `load_bytes()`, `step()`, and `run()`.
    """

    def __init__(
        self,
        reset_pc: int = BOOT_ROM_BASE,
        uart_tx_callback: Callable[[int], None] | None = None,
    ) -> None:
        """Create an oracle instance booted to `reset_pc` with optional UART TX byte callback."""
        self.reset_pc = u32(reset_pc)
        self.uart_tx_callback = uart_tx_callback

        self.rom = SparseMemory(BOOT_ROM_BASE, BOOT_ROM_SIZE, writable=False)
        self.bram = SparseMemory(BRAM_BASE, BRAM_SIZE, writable=True)
        self.qspi = SparseMemory(QSPI_BASE, QSPI_SIZE, writable=False)
        self.sdram = SparseMemory(SDRAM_BASE, SDRAM_SIZE, writable=True)
        self.mmio_stub = SparseMemory(MMIO_STUB_BASE, MMIO_STUB_END - MMIO_STUB_BASE, writable=True)
        # Keep mmio_stub separate from _mem_regions so loaders never write into MMIO space
        self._mem_regions = (self.rom, self.bram, self.qspi, self.sdram)

        self.reset()

    def reset(self, reset_pc: int | None = None) -> None:
        """Reset all CPU registers, CSRs, timers, and UART FIFOs to power-on state."""
        # Sparse ROM/Flash/RAM backing stores persist across warm resets so firmware stays loaded
        if reset_pc is not None:
            self.reset_pc = u32(reset_pc)
        self.pc: int = self.reset_pc                   # Byte address of next instruction to fetch
        self.regs: list[int] = [0] * 32                # x0..x31 (`regs[0]` stays 0 via _set_reg)
        self.mac_acc: int = 0                          # 32-bit signed saturating Xapex accumulator

        self.mstatus: int = MSTATUS_MPP_M              # Boots in Machine mode (MPP=0b11), IRQs off (MIE=0)
        # misa: Bits 31..30 = 0b01 (RV32), Bit 23 = 1 ('X' custom), Bit 12 = 1 ('M'), Bit 8 = 1 ('I')
        self.misa: int = 0x4080_1100
        self.mie: int = 0                              # Per-source IRQ enable bits (MSIE/MTIE/MEIE)
        self.mtvec: int = 0                            # Trap handler base + dispatch mode (Bits 1..0)
        self.mscratch: int = 0                         # OS scratch CSR swapped atomically on trap entry
        self.mepc: int = 0                             # Return PC saved when taking a trap
        self.mcause: int = 0                           # Encodes interrupt flag (Bit 31) + cause ID
        self.mtval: int = 0                            # Faulting PC, memory address, or insn word
        self.mip_sw_ext: int = 0                       # Latched SW/External IRQs (MTIP is wired live)
        self.mcycle: int = 0                           # Counts every step() (instructions + traps)
        self.minstret: int = 0                         # Counts retired non-trapping instructions

        self.mtime: int = 0                            # 64-bit CLINT clock counter (ticks pre-fetch)
        self.mtimecmp: int = (1 << 64) - 1             # Max 64-bit ceiling prevents spurious IRQ at boot

        self.uart_tx_buf: bytearray = bytearray()      # Host-readable log of all UART0 TX bytes
        self.uart_rx_fifo: deque[int] = deque()        # Queued incoming UART0 RX bytes (host -> CPU)
        self.uart_bauddiv: int = SYS_CLK_HZ // UART_DEFAULT_BAUD  # 434 ticks/bit at 50 MHz, 115200 bps

        self.halted: bool = False                      # Latched True by EBREAK; cleared on run()

    # -----------------------------------------------------------------------
    # Loader & Host Inspection Helpers
    # -----------------------------------------------------------------------
    def _find_mem_region(self, addr: int, width: int) -> SparseMemory | None:
        """Locate the backing memory region covering `[addr, addr + width)`, or None."""
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
            cur = u32(addr + idx * 4)
            region = self._find_mem_region(cur, 4)
            if region is None:
                raise MemoryAccessFault(f"Cannot load word to unmapped address 0x{cur:08x}")
            region.write_bytes(cur, 4, u32(word), bypass_ro=True)

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
    # Bus Read / Write (Memory + MMIO)
    # -----------------------------------------------------------------------
    def _clint_read(self, offset: int) -> int:
        """Read one 32-bit CLINT register (unused offsets read 0)."""
        if offset == CLINT_MTIME_LO:
            return u32(self.mtime)
        if offset == CLINT_MTIME_HI:
            return u32(self.mtime >> 32)
        if offset == CLINT_MTIMECMP_LO:
            return u32(self.mtimecmp)
        if offset == CLINT_MTIMECMP_HI:
            return u32(self.mtimecmp >> 32)
        return 0

    def _clint_write(self, offset: int, val: int) -> None:
        """Read-modify-write the low or high 32-bit half of `mtime` or `mtimecmp`."""
        val = u32(val)
        # 32-bit CPU bus writes only half a 64-bit counter at once, preserving the untouched 32 bits
        if offset == CLINT_MTIME_LO:
            self.mtime = (self.mtime & MASK64_HI32) | val
        elif offset == CLINT_MTIME_HI:
            self.mtime = (self.mtime & MASK32) | (val << 32)
        elif offset == CLINT_MTIMECMP_LO:
            self.mtimecmp = (self.mtimecmp & MASK64_HI32) | val
        elif offset == CLINT_MTIMECMP_HI:
            self.mtimecmp = (self.mtimecmp & MASK32) | (val << 32)

    def _uart_read(self, offset: int) -> int:
        """Read a UART0 register (`RXDATA`, `STATUS`, or `BAUDDIV`); unmapped offsets return 0."""
        if offset == UART0_RXDATA:
            return self.uart_rx_fifo.popleft() if self.uart_rx_fifo else 0  # Destructive pop
        if offset == UART0_STATUS:
            rx_valid = 1 if self.uart_rx_fifo else 0
            return 0x03 | (rx_valid << 2)  # Bit 0=TX ready (1), Bit 1=TX empty (1), Bit 2=RX valid
        if offset == UART0_BAUDDIV:
            return self.uart_bauddiv
        return 0

    def _uart_write(self, offset: int, val: int) -> None:
        """Write a UART0 register (`TXDATA` byte push or `BAUDDIV` clock divisor)."""
        if offset == UART0_TXDATA:
            byte = val & 0xFF
            self.uart_tx_buf.append(byte)
            if self.uart_tx_callback is not None:
                self.uart_tx_callback(byte)
        elif offset == UART0_BAUDDIV:
            self.uart_bauddiv = max(1, u32(val))  # Clamp >= 1 to prevent hardware divide-by-zero

    def bus_read(self, addr: int, width: int) -> int:
        """Perform a CPU bus read of `width` bytes across memory regions and MMIO devices."""
        if width not in (1, 2, 4):
            raise MemoryAccessFault(f"Unsupported read width {width} at 0x{addr:08x}")
        addr = u32(addr)
        region = self._find_mem_region(addr, width)
        if region is not None:
            return region.read_bytes(addr, width)
        if CLINT_BASE <= addr and (addr + width) <= CLINT_BASE + CLINT_SIZE:
            # Hardware CLINT timer registers expose only full 32-bit bus strobes; sub-word reads fault
            if width != 4 or (addr & 3) != 0:
                raise MemoryAccessFault(f"CLINT requires 32-bit aligned access at 0x{addr:08x}")
            return self._clint_read(addr - CLINT_BASE)
        if UART0_BASE <= addr and (addr + width) <= UART0_BASE + UART0_SIZE:
            off = addr - UART0_BASE
            # RXDATA allows 1-byte (lbu) or 4-byte FIFO pops at offset 0; STATUS/BAUDDIV are 32-bit only
            if (addr & 3) != 0 or width not in (1, 4) or (width == 1 and off in (UART0_STATUS, UART0_BAUDDIV)):
                raise MemoryAccessFault(f"UART misaligned/unsupported access at 0x{addr:08x}")
            return self._uart_read(off)
        if self.mmio_stub.contains(addr, width):
            return self.mmio_stub.read_bytes(addr, width)
        raise MemoryAccessFault(f"Load access fault at 0x{addr:08x}")

    def bus_write(self, addr: int, width: int, val: int) -> None:
        """Perform a CPU bus write of `width` bytes across memory regions and MMIO devices."""
        if width not in (1, 2, 4):
            raise MemoryAccessFault(f"Unsupported write width {width} at 0x{addr:08x}")
        addr = u32(addr)
        region = self._find_mem_region(addr, width)
        if region is not None:
            region.write_bytes(addr, width, val)
            return
        if CLINT_BASE <= addr and (addr + width) <= CLINT_BASE + CLINT_SIZE:
            # Hardware CLINT timer registers wire full 32-bit words; byte/halfword writes fault cleanly
            if width != 4 or (addr & 3) != 0:
                raise MemoryAccessFault(f"CLINT requires 32-bit aligned access at 0x{addr:08x}")
            self._clint_write(addr - CLINT_BASE, val)
            return
        if UART0_BASE <= addr and (addr + width) <= UART0_BASE + UART0_SIZE:
            off = addr - UART0_BASE
            # TXDATA accepts 1-byte (sb) or 4-byte (sw) pushes; STATUS (RO) and BAUDDIV require 32-bit access
            if (addr & 3) != 0 or width not in (1, 4) or (width == 1 and off in (UART0_STATUS, UART0_BAUDDIV)):
                raise MemoryAccessFault(f"UART misaligned/unsupported access at 0x{addr:08x}")
            self._uart_write(off, val)
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
        """Compute `mip`: latched MSIP/MEIP combined with live read-only CLINT `mtime >= mtimecmp`."""
        mtip = MIE_MTIE_BIT if (self.mtime >= self.mtimecmp) else 0
        return (self.mip_sw_ext & (MIE_MSIE_BIT | MIE_MEIE_BIT)) | mtip

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
        """Write `val` with WARL field masking; returns False (traps) on read-only CSRs like `misa`."""
        val = u32(val)
        if addr == CSR_MSTATUS:
            # WARL: only MIE and MPIE are writable; MPP stays hardwired to Machine mode (0b11)
            self.mstatus = (val & (MSTATUS_MIE_BIT | MSTATUS_MPIE_BIT)) | MSTATUS_MPP_M
            return True
        if addr == CSR_MIE:
            # WARL: only software (MSIE), timer (MTIE), and external (MEIE) enables are implemented
            self.mie = val & (MIE_MSIE_BIT | MIE_MTIE_BIT | MIE_MEIE_BIT)
            return True
        if addr == CSR_MTVEC:
            # WARL: modes > 1 are reserved here and snap cleanly to Direct mode (0)
            mode = val & 0x3
            if mode > 1:
                mode = 0
            self.mtvec = (val & 0xFFFF_FFFC) | mode
            return True
        if addr == CSR_MSCRATCH:
            self.mscratch = val
            return True
        if addr == CSR_MEPC:
            # IALIGN=32 (no 16-bit compressed instructions), so Bits 1..0 stay hardwired 0
            self.mepc = val & 0xFFFF_FFFC
            return True
        if addr == CSR_MCAUSE:
            self.mcause = val
            return True
        if addr == CSR_MTVAL:
            self.mtval = val
            return True
        if addr == CSR_MIP:
            # Software/external pending bits act as test latches; MTIP is strictly read-only wire
            self.mip_sw_ext = val & (MIE_MSIE_BIT | MIE_MEIE_BIT)
            return True
        if addr == CSR_MCYCLE:
            self.mcycle = (self.mcycle & MASK64_HI32) | val
            return True
        if addr == CSR_MCYCLEH:
            self.mcycle = (self.mcycle & MASK32) | (val << 32)
            return True
        if addr == CSR_MINSTRET:
            self.minstret = (self.minstret & MASK64_HI32) | val
            return True
        if addr == CSR_MINSTRETH:
            self.minstret = (self.minstret & MASK32) | (val << 32)
            return True
        # Note: writes to `misa` (0x301) and IDs (0xF11..0xF14) intentionally trap with illegal_insn
        return False

    def _take_trap(self, cause: int, tval: int, is_interrupt: bool) -> int:
        """Execute atomic hardware trap entry: save context, disable IRQs, jump to `mtvec`."""
        # 1. IALIGN=32 hardwires mepc[1:0]=0 even on misaligned fetch; mtval keeps exact faulting PC
        self.mepc = self.pc & 0xFFFF_FFFC
        self.mcause = u32(cause)
        self.mtval = u32(tval)

        # 2. Push MIE -> MPIE and clear MIE=0 using MASK32 ^ (avoids negative Python ~ ints)
        mie_was = bool(self.mstatus & MSTATUS_MIE_BIT)
        clear_mask = MASK32 ^ (MSTATUS_MIE_BIT | MSTATUS_MPIE_BIT)
        self.mstatus = (self.mstatus & clear_mask) | (MSTATUS_MPIE_BIT if mie_was else 0) | MSTATUS_MPP_M

        # 3. Dispatch to Direct base or Vectored (base + 4 * cause_code) handler address
        base = self.mtvec & 0xFFFF_FFFC
        mode = self.mtvec & 0x3
        if is_interrupt and mode == 1:
            target = u32(base + 4 * (cause & 0x7FFF_FFFF))
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
            trap_cause=cause,
            interrupt=is_interrupt,
        )

    def _set_reg(self, rd: int, val: int) -> tuple[int, int]:
        """Write `u32(val)` to register `rd` while keeping `x0` hardwired to `0`."""
        val = u32(val)
        if rd != 0:
            self.regs[rd] = val
        return rd, (0 if rd == 0 else val)

    # -----------------------------------------------------------------------
    # Modular Instruction-Family Execution Helpers
    # -----------------------------------------------------------------------
    def _check_pending_interrupt(self, cur_pc: int) -> StepTrace | None:
        """Return a trap `StepTrace` if any enabled machine interrupt is pending (`MEIP > MSIP > MTIP`)."""
        # Global interrupt enable (mstatus.MIE) gates all maskable interrupts atomically
        if not (self.mstatus & MSTATUS_MIE_BIT):
            return None
        # Pending line ANDed with per-source enable bit triggers preemption in fixed priority order
        pending = self._live_mip() & self.mie
        for bit, cause in (
            (MIE_MEIE_BIT, CAUSE_INT_M_EXT),
            (MIE_MSIE_BIT, CAUSE_INT_M_SW),
            (MIE_MTIE_BIT, CAUSE_INT_M_TIMER),
        ):
            if pending & bit:
                return self._trap_trace(cur_pc, 0, cause, 0, is_interrupt=True)
        return None

    def _fetch_instruction(self, cur_pc: int) -> int | StepTrace:
        """Fetch a 32-bit aligned instruction at `cur_pc`, or return a trap `StepTrace`."""
        # Check IALIGN=32 word alignment before touching memory; fetch faults record cur_pc in mtval
        if (cur_pc & 3) != 0:
            return self._trap_trace(cur_pc, 0, CAUSE_INSN_MISALIGNED, cur_pc)
        try:
            return self.bus_read(cur_pc, 4)
        except MemoryAccessFault:
            return self._trap_trace(cur_pc, 0, CAUSE_INSN_ACCESS_FAULT, cur_pc)

    def _exec_jal(self, insn: int, cur_pc: int, rd: int, next_pc: int) -> tuple[int, int, int] | StepTrace:
        """Execute `JAL`, returning `(wb_rd, wb_val, target_pc)` or a misaligned-target trap."""
        # J-type scrambles a 21-bit signed byte offset (Bit 0 is implicitly 0 for even offsets)
        imm = sign_extend(
            (((insn >> 31) & 1) << 20)
            | (((insn >> 12) & 0xFF) << 12)
            | (((insn >> 20) & 1) << 11)
            | (((insn >> 21) & 0x3FF) << 1),
            21,
        )
        target = u32(cur_pc + imm)
        # Validate 4-byte target alignment before committing the return link (cur_pc + 4) to rd
        if target & 3:
            return self._trap_trace(cur_pc, insn, CAUSE_INSN_MISALIGNED, target)
        wb_rd, wb_val = self._set_reg(rd, next_pc)
        return wb_rd, wb_val, target

    def _exec_jalr(
        self, insn: int, cur_pc: int, rd: int, rs1_u: int, funct3: int, next_pc: int
    ) -> tuple[int, int, int] | StepTrace:
        """Execute `JALR`, returning `(wb_rd, wb_val, target_pc)` or an illegal/misaligned trap."""
        if funct3 != 0:
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
        imm = sign_extend(insn >> 20, 12)
        # RV32I clears Bit 0 of (rs1 + imm); (target & 3) then traps if Bit 1 is set (IALIGN=32)
        target = u32((rs1_u + imm) & (MASK32 ^ 1))
        if target & 3:
            return self._trap_trace(cur_pc, insn, CAUSE_INSN_MISALIGNED, target)
        # rs1_u was latched prior to execution, so `jalr rd, 0(rd)` safely reads old rs1 before writing rd
        wb_rd, wb_val = self._set_reg(rd, next_pc)
        return wb_rd, wb_val, target

    def _exec_branch(
        self, insn: int, cur_pc: int, rs1_u: int, rs2_u: int, rs1_s: int, rs2_s: int, funct3: int, next_pc: int
    ) -> int | StepTrace:
        """Evaluate a B-type conditional branch and return `next_pc` or a trap `StepTrace`."""
        # B-type packs a 13-bit signed byte offset (Bit 0 implicitly 0); keeps Bit 31 as sign bit
        imm = sign_extend(
            (((insn >> 31) & 1) << 12)
            | (((insn >> 7) & 1) << 11)
            | (((insn >> 25) & 0x3F) << 5)
            | (((insn >> 8) & 0xF) << 1),
            13,
        )
        comparisons = {
            0: rs1_u == rs2_u,  # BEQ
            1: rs1_u != rs2_u,  # BNE
            4: rs1_s < rs2_s,   # BLT
            5: rs1_s >= rs2_s,  # BGE
            6: rs1_u < rs2_u,   # BLTU
            7: rs1_u >= rs2_u,  # BGEU
        }
        if funct3 not in comparisons:
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
        # An untaken branch ignores target alignment and advances cleanly to PC + 4
        if not comparisons[funct3]:
            return next_pc
        target = u32(cur_pc + imm)
        if target & 3:
            return self._trap_trace(cur_pc, insn, CAUSE_INSN_MISALIGNED, target)
        return target

    def _exec_load(
        self, insn: int, cur_pc: int, rd: int, rs1_u: int, funct3: int
    ) -> tuple[int, int, int, int] | StepTrace:
        """Execute `LB`/`LH`/`LW`/`LBU`/`LHU`, returning `(wb_rd, wb_val, addr, mem_val)` or a trap."""
        # funct3 bit 2 distinguishes signed (0,1,2) vs unsigned zero-extended (4,5) loads
        width_map = {0: 1, 1: 2, 2: 4, 4: 1, 5: 2}
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

        if funct3 == 0:
            val = sign_extend(raw, 8)
        elif funct3 == 1:
            val = sign_extend(raw, 16)
        elif funct3 == 2:
            val = raw
        elif funct3 == 4:
            val = raw & 0xFF
        else:
            val = raw & 0xFFFF

        wb_rd, wb_val = self._set_reg(rd, val)
        return wb_rd, wb_val, addr, u32(val)

    def _exec_store(
        self, insn: int, cur_pc: int, rs1_u: int, rs2_u: int, funct3: int
    ) -> tuple[int, int] | StepTrace:
        """Execute `SB`/`SH`/`SW`, returning `(addr, stored_val)` or a trap `StepTrace`."""
        width_map = {0: 1, 1: 2, 2: 4}
        width = width_map.get(funct3)
        if width is None:
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

        # S-type keeps rs1/rs2 at fixed register bits, splitting imm[11:0] across Bits 31..25 & 11..7
        imm = sign_extend(((insn >> 25) << 5) | ((insn >> 7) & 0x1F), 12)
        addr = u32(rs1_u + imm)
        if (addr & (width - 1)) != 0:
            return self._trap_trace(cur_pc, insn, CAUSE_STORE_MISALIGNED, addr)

        # Truncate rs2 down to 8, 16, or 32 low bits before writing little-endian bytes to bus
        store_val = rs2_u & ((1 << (8 * width)) - 1)
        try:
            self.bus_write(addr, width, store_val)
        except MemoryAccessFault:
            return self._trap_trace(cur_pc, insn, CAUSE_STORE_ACCESS_FAULT, addr)
        return addr, store_val

    def _exec_op_imm(
        self, insn: int, rd: int, rs1_u: int, rs1_s: int, funct3: int, funct7: int
    ) -> tuple[int, int] | None:
        """Execute RV32I immediate ALU instructions (`OP-IMM`), returning `(wb_rd, wb_val)` or None."""
        imm = sign_extend(insn >> 20, 12)
        # Shift-immediates use only the bottom 5 bits (shamt) and reserve Bits 31..25 (funct7) for mode
        shamt = (insn >> 20) & 0x1F
        if funct3 == 0:
            # Signed and unsigned addition share identical low 32 bits modulo 2^32 (_set_reg)
            res = rs1_u + imm
        elif funct3 == 2:
            res = 1 if rs1_s < imm else 0
        elif funct3 == 3:
            # SLTIU sign-extends imm[11:0] first, then compares unsigned (so -1 becomes 0xFFFF_FFFF)
            res = 1 if rs1_u < u32(imm) else 0
        elif funct3 == 4:
            # Logical ops wrap sign-extended 12-bit imm via u32 (so xori rd, rs1, -1 acts as NOT)
            res = rs1_u ^ u32(imm)
        elif funct3 == 6:
            res = rs1_u | u32(imm)
        elif funct3 == 7:
            res = rs1_u & u32(imm)
        elif funct3 == 1:
            if funct7 != 0x00:
                return None
            res = rs1_u << shamt
        else:  # funct3 == 5 (all 3-bit funct3 values 0..7 handled)
            if funct7 == 0x00:
                res = rs1_u >> shamt
            elif funct7 == 0x20:
                res = rs1_s >> shamt  # Signed right shift copies Bit 31; _set_reg truncates to 32b
            else:
                return None
        return self._set_reg(rd, res)

    def _exec_muldiv(self, rd: int, rs1_u: int, rs2_u: int, rs1_s: int, rs2_s: int, funct3: int) -> tuple[int, int]:
        """Execute all 8 RV32M multiply/divide instructions with RISC-V overflow/zero semantics."""
        if funct3 == 0:  # MUL: lower 32 bits match for signed and unsigned products
            res = rs1_s * rs2_s
        elif funct3 == 1:  # MULH: >> 32 on negative product shifts in 1s matching 64-bit [63:32]
            res = (rs1_s * rs2_s) >> 32
        elif funct3 == 2:  # MULHSU: upper 32 bits of signed rs1 * unsigned rs2
            res = (rs1_s * rs2_u) >> 32
        elif funct3 == 3:  # MULHU: upper 32 bits of unsigned * unsigned 64-bit product
            res = (rs1_u * rs2_u) >> 32
        elif funct3 == 4:  # DIV: truncates toward zero; divide-by-zero & INT32_MIN/-1 never trap
            if rs2_s == 0:
                res = -1
            elif rs1_s == INT32_MIN and rs2_s == -1:
                res = INT32_MIN
            else:
                # Truncate magnitude toward zero rather than Python's floor division (// toward -inf)
                q = abs(rs1_s) // abs(rs2_s)
                res = -q if (rs1_s < 0) ^ (rs2_s < 0) else q
        elif funct3 == 5:  # DIVU
            res = MASK32 if rs2_u == 0 else (rs1_u // rs2_u)
        elif funct3 == 6:  # REM: remainder sign follows dividend so q * divisor + rem == dividend
            if rs2_s == 0:
                res = rs1_s
            elif rs1_s == INT32_MIN and rs2_s == -1:
                res = 0
            else:
                q = abs(rs1_s) // abs(rs2_s)
                if (rs1_s < 0) ^ (rs2_s < 0):
                    q = -q
                res = rs1_s - q * rs2_s
        else:  # REMU
            res = rs1_u if rs2_u == 0 else (rs1_u % rs2_u)
        return self._set_reg(rd, res)

    def _exec_op_reg(
        self, rd: int, rs1_u: int, rs2_u: int, rs1_s: int, rs2_s: int, funct3: int, funct7: int
    ) -> tuple[int, int] | None:
        """Execute RV32I + RV32M register-register ALU instructions (`OP`), or None if illegal."""
        if funct7 == 0x01:
            return self._exec_muldiv(rd, rs1_u, rs2_u, rs1_s, rs2_s, funct3)
        if funct7 == 0x00:
            # 32-bit barrel shifters use only the low 5 bits (rs2 & 0x1F) for shift distances 0..31
            ops = {
                0: rs1_u + rs2_u,
                1: rs1_u << (rs2_u & 0x1F),
                2: 1 if rs1_s < rs2_s else 0,
                3: 1 if rs1_u < rs2_u else 0,
                4: rs1_u ^ rs2_u,
                5: rs1_u >> (rs2_u & 0x1F),
                6: rs1_u | rs2_u,
                7: rs1_u & rs2_u,
            }
            return self._set_reg(rd, ops[funct3])
        if funct7 == 0x20:
            if funct3 == 0:
                return self._set_reg(rd, rs1_u - rs2_u)
            if funct3 == 5:
                return self._set_reg(rd, rs1_s >> (rs2_u & 0x1F))
        # Returning None lets step() raise a unified CAUSE_ILLEGAL_INSN trap
        return None

    def _exec_system(
        self, insn: int, cur_pc: int, rd: int, rs1: int, rs1_u: int, funct3: int, next_pc: int
    ) -> tuple[int, int, int, bool] | StepTrace:
        """Execute `ECALL`/`EBREAK`/`MRET`/`WFI` and Zicsr instructions."""
        if funct3 == 0:
            # Full-word comparison ensures reserved rs1/rd bits must be 0 per RV32I privileged spec
            if insn == 0x0000_0073:  # ECALL
                return self._trap_trace(cur_pc, insn, CAUSE_ECALL_M, 0)
            if insn == 0x0010_0073:  # EBREAK
                self.halted = True
                return self._trap_trace(cur_pc, insn, CAUSE_BREAKPOINT, cur_pc)
            if insn == 0x3020_0073:  # MRET: pop 1-deep interrupt-enable stack (MIE <- MPIE; MPIE <- 1)
                mpie = bool(self.mstatus & MSTATUS_MPIE_BIT)
                # MASK32 ^ avoids Python negative infinite-precision ~ ints
                clear_mask = MASK32 ^ (MSTATUS_MIE_BIT | MSTATUS_MPIE_BIT)
                self.mstatus = (
                    (self.mstatus & clear_mask)
                    | (MSTATUS_MIE_BIT if mpie else 0)
                    | MSTATUS_MPIE_BIT
                    | MSTATUS_MPP_M
                )
                return 0, 0, self.mepc & 0xFFFF_FFFC, False
            if insn == 0x1050_0073:  # WFI (Wait For Interrupt): sequential nop advancing to PC + 4
                return 0, 0, next_pc, False
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

        if funct3 in (1, 2, 3, 5, 6, 7):
            csr_addr = (insn >> 20) & 0xFFF
            old_val = self._read_csr(csr_addr)
            if old_val is None:
                return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

            # Bit 2 of funct3 selects zero-extended 5-bit uimm encoded directly in the rs1 field
            src_val = rs1 if (funct3 & 0x4) else rs1_u
            op = funct3 & 0x3
            if op == 1:  # CSRRW / CSRRWI always attempt a CSR write
                new_val, do_write = src_val, True
            elif op == 2:  # CSRRS / CSRRSI suppress write when rs1/uimm == 0 (safe read of RO CSRs)
                new_val, do_write = old_val | src_val, (rs1 != 0)
            else:  # CSRRC / CSRRCI clear bits via 32-bit XOR complement (avoids Python ~) and skip if rs1 == 0
                new_val, do_write = u32(old_val & (MASK32 ^ src_val)), (rs1 != 0)

            wrote_minstret = False
            if do_write:
                if not self._write_csr(csr_addr, new_val):
                    return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
                wrote_minstret = csr_addr in (CSR_MINSTRET, CSR_MINSTRETH)

            wb_rd, wb_val = self._set_reg(rd, old_val)
            return wb_rd, wb_val, next_pc, wrote_minstret

        return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

    def _exec_mac(
        self, rd: int, rs1_u: int, rs2_u: int, rs1_s: int, funct3: int, funct7: int
    ) -> tuple[int, int] | None:
        """Execute Xapex `custom-0` dual-int16 saturating MAC instructions, or None if invalid."""
        if funct7 != 0x00:
            return None
        if funct3 in (0, 1):
            # Split rs1 and rs2 into lower [15:0] and upper [31:16] signed int16 lanes
            a0, a1 = s16(rs1_u), s16(rs1_u >> 16)
            b0, b1 = s16(rs2_u), s16(rs2_u >> 16)
            # funct3=0 accumulates into prior mac_acc; funct3=1 (mac.clr) zeroes accumulator first
            base_acc = 0 if funct3 == 1 else self.mac_acc
            self.mac_acc = sat32(base_acc + a0 * b0 + a1 * b1)
            # Note: even when rd == x0, mac_acc retains the updated dot product while x0 discards wb
            return self._set_reg(rd, self.mac_acc)
        if funct3 == 2:  # mac.set: preload bias directly into accumulator
            self.mac_acc = rs1_s
            return self._set_reg(rd, self.mac_acc)
        if funct3 == 3:  # mac.get: copy current accumulator into rd
            return self._set_reg(rd, self.mac_acc)
        return None

    # -----------------------------------------------------------------------
    # Single-Instruction Execution & Run Loop
    # -----------------------------------------------------------------------
    # code-gate: allow-long-dispatch (flat single-level RISC-V major-opcode dispatch table)
    def step(self) -> StepTrace:
        """Advance CPU and CLINT timers by one instruction/trap and return its `StepTrace`."""
        cur_pc = self.pc
        # Advance free-running hardware clocks before interrupt sampling so pending alarms fire cleanly
        self.mcycle += 1
        self.mtime += 1

        # 1. Sample enabled pending interrupts; interrupts preempt fetch so minstret does not tick
        irq_trace = self._check_pending_interrupt(cur_pc)
        if irq_trace is not None:
            return irq_trace

        # 2. Fetch aligned 32-bit instruction word at cur_pc
        fetched = self._fetch_instruction(cur_pc)
        if isinstance(fetched, StepTrace):
            return fetched
        insn = fetched

        # 3. Extract fixed RISC-V bit columns shared across instruction formats
        opcode = insn & 0x7F
        rd = (insn >> 7) & 0x1F
        funct3 = (insn >> 12) & 0x7
        rs1 = (insn >> 15) & 0x1F
        rs2 = (insn >> 20) & 0x1F
        funct7 = (insn >> 25) & 0x7F

        rs1_u, rs2_u = self.regs[rs1], self.regs[rs2]
        rs1_s, rs2_s = s32(rs1_u), s32(rs2_u)

        next_pc = u32(cur_pc + 4)
        wb_rd, wb_val = 0, 0
        mem_addr: int | None = None
        mem_val: int | None = None
        mem_write = False
        csr_wrote_minstret = False

        # 4. Dispatch by 7-bit major opcode
        if opcode == 0x37:  # LUI: upper 20 bits verbatim into rd, low 12 bits zeroed
            wb_rd, wb_val = self._set_reg(rd, insn & 0xFFFF_F000)
        elif opcode == 0x17:  # AUIPC: PC-relative upper 20-bit base address calculation
            wb_rd, wb_val = self._set_reg(rd, cur_pc + (insn & 0xFFFF_F000))
        elif opcode == 0x6F:  # JAL
            res = self._exec_jal(insn, cur_pc, rd, next_pc)
            if isinstance(res, StepTrace):
                return res
            wb_rd, wb_val, next_pc = res
        elif opcode == 0x67:  # JALR
            res = self._exec_jalr(insn, cur_pc, rd, rs1_u, funct3, next_pc)
            if isinstance(res, StepTrace):
                return res
            wb_rd, wb_val, next_pc = res
        elif opcode == 0x63:  # BRANCH
            res = self._exec_branch(insn, cur_pc, rs1_u, rs2_u, rs1_s, rs2_s, funct3, next_pc)
            if isinstance(res, StepTrace):
                return res
            next_pc = res
        elif opcode == 0x03:  # LOAD
            res = self._exec_load(insn, cur_pc, rd, rs1_u, funct3)
            if isinstance(res, StepTrace):
                return res
            wb_rd, wb_val, mem_addr, mem_val = res
        elif opcode == 0x23:  # STORE
            res = self._exec_store(insn, cur_pc, rs1_u, rs2_u, funct3)
            if isinstance(res, StepTrace):
                return res
            mem_addr, mem_val = res
            mem_write = True
        elif opcode == 0x13:  # OP-IMM
            res = self._exec_op_imm(insn, rd, rs1_u, rs1_s, funct3, funct7)
            if res is None:
                return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
            wb_rd, wb_val = res
        elif opcode == 0x33:  # OP (RV32I + RV32M)
            res = self._exec_op_reg(rd, rs1_u, rs2_u, rs1_s, rs2_s, funct3, funct7)
            if res is None:
                return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
            wb_rd, wb_val = res
        elif opcode == 0x0F:  # FENCE / FENCE.I: memory/instruction barriers are sequential no-ops
            if funct3 not in (0, 1):
                return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
        elif opcode == 0x73:  # SYSTEM (traps return early above; normal Zicsr/MRET/WFI retire)
            res = self._exec_system(insn, cur_pc, rd, rs1, rs1_u, funct3, next_pc)
            if isinstance(res, StepTrace):
                return res
            wb_rd, wb_val, next_pc, csr_wrote_minstret = res
        elif opcode == OPCODE_CUSTOM0:  # Xapex MAC
            res = self._exec_mac(rd, rs1_u, rs2_u, rs1_s, funct3, funct7)
            if res is None:
                return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
            wb_rd, wb_val = res
        else:
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

        # 5. Retire instruction: commit PC and advance minstret unless explicitly overwritten
        self.pc = next_pc
        if not csr_wrote_minstret:
            self.minstret += 1

        return StepTrace(
            pc=cur_pc,
            insn=insn,
            next_pc=next_pc,
            rd=wb_rd,
            rd_val=wb_val,
            mem_addr=mem_addr,
            mem_val=mem_val,
            mem_write=mem_write,
        )

    def run(
        self,
        max_steps: int = 10_000,
        stop_on_ebreak: bool = True,
        stop_on_pc: int | None = None,
    ) -> list[StepTrace]:
        """Execute up to `max_steps` instructions, optionally halting on `EBREAK` or `stop_on_pc`."""
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
