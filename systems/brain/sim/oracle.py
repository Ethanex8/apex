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
    17 Machine-mode CSRs (`WARL`-masked), and `CLINT`/`UART0` peripherals across 4 KB sparse pages.
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
  Uses an internal 32-bit saturating accumulator (mac_acc) so dual-int16 dot products
  run at 1 instruction/cycle with a 2-read-port register file:
    funct3 = 0b000 : mac rd, rs1, rs2       -> acc = sat32(acc + s16_lo*s16_lo + s16_hi*s16_hi); rd = acc
    funct3 = 0b001 : mac.clr rd, rs1, rs2   -> acc = sat32(0   + s16_lo*s16_lo + s16_hi*s16_hi); rd = acc
    funct3 = 0b010 : mac.set rd, rs1        -> acc = s32(rs1); rd = acc
    funct3 = 0b011 : mac.get rd             -> rd = acc
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Address Map & Peripheral Register Offsets
# ---------------------------------------------------------------------------
SYS_CLK_HZ = 50_000_000
UART_DEFAULT_BAUD = 115_200

BOOT_ROM_BASE = 0x0000_0000
BOOT_ROM_SIZE = 0x0000_4000  # 16 KB

BRAM_BASE = 0x1000_0000
BRAM_SIZE = 0x0001_0000  # 64 KB

QSPI_BASE = 0x2000_0000
QSPI_SIZE = 0x0100_0000  # 16 MB

SDRAM_BASE = 0x4000_0000
SDRAM_SIZE = 0x0200_0000  # 32 MB

CLINT_BASE = 0x8000_0000
CLINT_SIZE = 0x0001_0000
CLINT_MTIME_LO = 0x00
CLINT_MTIME_HI = 0x04
CLINT_MTIMECMP_LO = 0x08
CLINT_MTIMECMP_HI = 0x0C

UART0_BASE = 0x8001_0000
UART0_SIZE = 0x0001_0000
UART0_TXDATA = 0x00
UART0_RXDATA = 0x04
UART0_STATUS = 0x08
UART0_BAUDDIV = 0x0C

MMIO_STUB_BASE = 0x8002_0000
MMIO_STUB_END = 0x8007_0000

# ---------------------------------------------------------------------------
# Machine-Mode CSR Addresses & Trap Causes
# ---------------------------------------------------------------------------
CSR_MSTATUS = 0x300
CSR_MISA = 0x301
CSR_MIE = 0x304
CSR_MTVEC = 0x305
CSR_MSCRATCH = 0x340
CSR_MEPC = 0x341
CSR_MCAUSE = 0x342
CSR_MTVAL = 0x343
CSR_MIP = 0x344
CSR_MCYCLE = 0xB00
CSR_MINSTRET = 0xB02
CSR_MCYCLEH = 0xB80
CSR_MINSTRETH = 0xB82
CSR_MVENDORID = 0xF11
CSR_MARCHID = 0xF12
CSR_MIMPID = 0xF13
CSR_MHARTID = 0xF14

CAUSE_INSN_MISALIGNED = 0
CAUSE_INSN_ACCESS_FAULT = 1
CAUSE_ILLEGAL_INSN = 2
CAUSE_BREAKPOINT = 3
CAUSE_LOAD_MISALIGNED = 4
CAUSE_LOAD_ACCESS_FAULT = 5
CAUSE_STORE_MISALIGNED = 6
CAUSE_STORE_ACCESS_FAULT = 7
CAUSE_ECALL_M = 11
CAUSE_INT_M_SW = 0x8000_0003
CAUSE_INT_M_TIMER = 0x8000_0007
CAUSE_INT_M_EXT = 0x8000_000B

MSTATUS_MIE_BIT = 1 << 3
MSTATUS_MPIE_BIT = 1 << 7
MSTATUS_MPP_M = 0b11 << 11

MIE_MSIE_BIT = 1 << 3
MIE_MTIE_BIT = 1 << 7
MIE_MEIE_BIT = 1 << 11

# RISC-V custom-0 major opcode reserved for Xapex extensions
OPCODE_CUSTOM0 = 0x0B

MASK32 = 0xFFFF_FFFF
INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1


# ---------------------------------------------------------------------------
# Bitwise Arithmetic & Instruction Encoding Helpers
# ---------------------------------------------------------------------------
def u32(val: int) -> int:
    """Wrap an arbitrary Python integer into an unsigned 32-bit range [0, 2^32 - 1]."""
    return val & MASK32


def s32(val: int) -> int:
    """Interpret the lower 32 bits of an integer as a signed two's complement int32."""
    u = u32(val)
    return u - (u >> 31) * (1 << 32)


def s16(val: int) -> int:
    """Interpret the lower 16 bits of an integer as a signed two's complement int16."""
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
    """Sign-extend a `bits`-wide two's complement bit pattern into a signed Python int."""
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
    """Encode a 32-bit S-type (store) RISC-V instruction word, splitting imm[11:0]."""
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
    """Encode a 32-bit B-type (conditional branch) RISC-V instruction word from a byte offset."""
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
    """Encode a 32-bit U-type (LUI / AUIPC) instruction using pre-shifted bits [31:12]."""
    return (imm20_shifted & 0xFFFF_F000) | ((rd & 0x1F) << 7) | (opcode & 0x7F)


def enc_j(imm: int, rd: int, opcode: int = 0x6F) -> int:
    """Encode a 32-bit J-type (JAL) instruction word from a signed byte offset."""
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
    """Encode an Xapex custom-0 dual-int16 MAC instruction (`mac`, `mac.clr`, `mac.set`, `mac.get`)."""
    return enc_r(0x00, rs2, rs1, funct3, rd, OPCODE_CUSTOM0)


# ---------------------------------------------------------------------------
# Memory Model & Commit Trace Types
# ---------------------------------------------------------------------------
class MemoryAccessFault(Exception):
    """Raised internally when a bus transaction targets an unmapped or read-only region."""


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
        val = 0
        for i in range(width):
            offset = (addr + i) - self.base
            page = self._pages.get(offset // self.PAGE_SIZE)
            byte = page[offset % self.PAGE_SIZE] if page is not None else 0
            val |= byte << (8 * i)
        return val

    def write_bytes(self, addr: int, width: int, val: int, bypass_ro: bool = False) -> None:
        """Write `width` little-endian bytes of `val` to `addr`, honoring `writable` unless bypassed."""
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

    `rd`/`rd_val` default to `(0, 0)` when no register commits or `rd == x0`.
    `mem_val` holds the 32-bit sign/zero-extended loaded value on loads and the
    width-masked low byte/halfword/word (`0xFF`/`0xFFFF`/`0xFFFF_FFFF`) on stores.
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
        self._mem_regions = (self.rom, self.bram, self.qspi, self.sdram)

        self.reset()

    def reset(self, reset_pc: int | None = None) -> None:
        """Reset all CPU registers, CSRs, timers, and UART FIFOs to power-on state."""
        if reset_pc is not None:
            self.reset_pc = u32(reset_pc)
        self.pc: int = self.reset_pc
        self.regs: list[int] = [0] * 32
        self.mac_acc: int = 0

        self.mstatus: int = MSTATUS_MPP_M
        self.misa: int = 0x4080_1100  # RV32I + M + X (custom extension)
        self.mie: int = 0
        self.mtvec: int = 0
        self.mscratch: int = 0
        self.mepc: int = 0
        self.mcause: int = 0
        self.mtval: int = 0
        self.mip_sw_ext: int = 0
        self.mcycle: int = 0
        self.minstret: int = 0

        self.mtime: int = 0
        self.mtimecmp: int = (1 << 64) - 1  # Max 64-bit ceiling prevents spurious timer IRQ at boot

        self.uart_tx_buf: bytearray = bytearray()
        self.uart_rx_fifo: deque[int] = deque()
        self.uart_bauddiv: int = SYS_CLK_HZ // UART_DEFAULT_BAUD

        self.halted: bool = False

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
        """Read one 32-bit CLINT timer register by byte offset from `CLINT_BASE`."""
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
        """Write one 32-bit CLINT timer register by byte offset from `CLINT_BASE`."""
        val = u32(val)
        if offset == CLINT_MTIME_LO:
            self.mtime = (self.mtime & 0xFFFF_FFFF_0000_0000) | val
        elif offset == CLINT_MTIME_HI:
            self.mtime = (self.mtime & MASK32) | (val << 32)
        elif offset == CLINT_MTIMECMP_LO:
            self.mtimecmp = (self.mtimecmp & 0xFFFF_FFFF_0000_0000) | val
        elif offset == CLINT_MTIMECMP_HI:
            self.mtimecmp = (self.mtimecmp & MASK32) | (val << 32)

    def _uart_read(self, offset: int) -> int:
        """Read a UART0 register (`RXDATA`, `STATUS`, or `BAUDDIV`) by word-aligned offset."""
        if offset == UART0_RXDATA:
            return self.uart_rx_fifo.popleft() if self.uart_rx_fifo else 0
        if offset == UART0_STATUS:
            rx_valid = 1 if self.uart_rx_fifo else 0
            return 0x03 | (rx_valid << 2)
        if offset == UART0_BAUDDIV:
            return self.uart_bauddiv
        return 0

    def _uart_write(self, offset: int, val: int) -> None:
        """Write a UART0 register (`TXDATA` or `BAUDDIV`) by word-aligned offset."""
        if offset == UART0_TXDATA:
            byte = val & 0xFF
            self.uart_tx_buf.append(byte)
            if self.uart_tx_callback is not None:
                self.uart_tx_callback(byte)
        elif offset == UART0_BAUDDIV:
            self.uart_bauddiv = max(1, u32(val))

    def bus_read(self, addr: int, width: int) -> int:
        """Perform a CPU bus read of `width` bytes across memory regions and MMIO devices."""
        addr = u32(addr)
        region = self._find_mem_region(addr, width)
        if region is not None:
            return region.read_bytes(addr, width)
        if CLINT_BASE <= addr and (addr + width) <= CLINT_BASE + CLINT_SIZE:
            if width != 4 or (addr & 3) != 0:
                raise MemoryAccessFault(f"CLINT requires 32-bit aligned access at 0x{addr:08x}")
            return self._clint_read(addr - CLINT_BASE)
        if UART0_BASE <= addr and (addr + width) <= UART0_BASE + UART0_SIZE:
            if (addr & 3) != 0 or width not in (1, 4):
                raise MemoryAccessFault(f"UART misaligned/unsupported access at 0x{addr:08x}")
            return self._uart_read(addr - UART0_BASE)
        if self.mmio_stub.contains(addr, width):
            return self.mmio_stub.read_bytes(addr, width)
        raise MemoryAccessFault(f"Load access fault at 0x{addr:08x}")

    def bus_write(self, addr: int, width: int, val: int) -> None:
        """Perform a CPU bus write of `width` bytes across memory regions and MMIO devices."""
        addr = u32(addr)
        region = self._find_mem_region(addr, width)
        if region is not None:
            region.write_bytes(addr, width, val)
            return
        if CLINT_BASE <= addr and (addr + width) <= CLINT_BASE + CLINT_SIZE:
            if width != 4 or (addr & 3) != 0:
                raise MemoryAccessFault(f"CLINT requires 32-bit aligned access at 0x{addr:08x}")
            self._clint_write(addr - CLINT_BASE, val)
            return
        if UART0_BASE <= addr and (addr + width) <= UART0_BASE + UART0_SIZE:
            if (addr & 3) != 0 or width not in (1, 4):
                raise MemoryAccessFault(f"UART misaligned/unsupported access at 0x{addr:08x}")
            self._uart_write(addr - UART0_BASE, val)
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
        """Compute `mip`, combining software/external bits with live CLINT `mtime >= mtimecmp`."""
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
        """Write `val` to CSR `addr`, returning False if the CSR is read-only or invalid."""
        val = u32(val)
        if addr == CSR_MSTATUS:
            self.mstatus = (val & (MSTATUS_MIE_BIT | MSTATUS_MPIE_BIT)) | MSTATUS_MPP_M
            return True
        if addr == CSR_MIE:
            self.mie = val & (MIE_MSIE_BIT | MIE_MTIE_BIT | MIE_MEIE_BIT)
            return True
        if addr == CSR_MTVEC:
            mode = val & 0x3
            if mode > 1:
                mode = 0
            self.mtvec = (val & ~0x3) | mode
            return True
        if addr == CSR_MSCRATCH:
            self.mscratch = val
            return True
        if addr == CSR_MEPC:
            self.mepc = val & ~0x3
            return True
        if addr == CSR_MCAUSE:
            self.mcause = val
            return True
        if addr == CSR_MTVAL:
            self.mtval = val
            return True
        if addr == CSR_MIP:
            self.mip_sw_ext = val & (MIE_MSIE_BIT | MIE_MEIE_BIT)
            return True
        if addr == CSR_MCYCLE:
            self.mcycle = (self.mcycle & 0xFFFF_FFFF_0000_0000) | val
            return True
        if addr == CSR_MCYCLEH:
            self.mcycle = (self.mcycle & MASK32) | (val << 32)
            return True
        if addr == CSR_MINSTRET:
            self.minstret = (self.minstret & 0xFFFF_FFFF_0000_0000) | val
            return True
        if addr == CSR_MINSTRETH:
            self.minstret = (self.minstret & MASK32) | (val << 32)
            return True
        return False

    def _take_trap(self, cause: int, tval: int, is_interrupt: bool) -> int:
        """Enter machine-mode trap handler, saving `mepc`/`mcause`/`mtval` and updating `pc`."""
        self.mepc = self.pc
        self.mcause = u32(cause)
        self.mtval = u32(tval)

        mie_was = bool(self.mstatus & MSTATUS_MIE_BIT)
        self.mstatus = (
            (self.mstatus & ~(MSTATUS_MIE_BIT | MSTATUS_MPIE_BIT))
            | (MSTATUS_MPIE_BIT if mie_was else 0)
            | MSTATUS_MPP_M
        )

        base = self.mtvec & ~0x3
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
        """Write `u32(val)` to general-purpose register `rd` (keeping `x0 == 0`)."""
        val = u32(val)
        if rd != 0:
            self.regs[rd] = val
        return rd, (0 if rd == 0 else val)

    # -----------------------------------------------------------------------
    # Modular Instruction-Family Execution Helpers
    # -----------------------------------------------------------------------
    def _check_pending_interrupt(self, cur_pc: int) -> StepTrace | None:
        """Return a trap `StepTrace` if any enabled machine interrupt is pending (`MEIP > MSIP > MTIP`)."""
        if not (self.mstatus & MSTATUS_MIE_BIT):
            return None
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
        if (cur_pc & 3) != 0:
            return self._trap_trace(cur_pc, 0, CAUSE_INSN_MISALIGNED, cur_pc)
        try:
            return self.bus_read(cur_pc, 4)
        except MemoryAccessFault:
            return self._trap_trace(cur_pc, 0, CAUSE_INSN_ACCESS_FAULT, cur_pc)

    def _exec_jal(self, insn: int, cur_pc: int, rd: int, next_pc: int) -> tuple[int, int, int] | StepTrace:
        """Execute `JAL`, returning `(wb_rd, wb_val, target_pc)` or a misaligned-target trap."""
        imm = sign_extend(
            (((insn >> 31) & 1) << 20)
            | (((insn >> 12) & 0xFF) << 12)
            | (((insn >> 20) & 1) << 11)
            | (((insn >> 21) & 0x3FF) << 1),
            21,
        )
        target = u32(cur_pc + imm)
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
        target = u32((rs1_u + imm) & ~1)  # Spec clears Bit 0; target & 3 enforces 4-byte alignment
        if target & 3:
            return self._trap_trace(cur_pc, insn, CAUSE_INSN_MISALIGNED, target)
        wb_rd, wb_val = self._set_reg(rd, next_pc)
        return wb_rd, wb_val, target

    def _exec_branch(
        self, insn: int, cur_pc: int, rs1_u: int, rs2_u: int, rs1_s: int, rs2_s: int, funct3: int, next_pc: int
    ) -> int | StepTrace:
        """Evaluate a B-type conditional branch and return `next_pc` or a trap `StepTrace`."""
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
        width_map = {0: 1, 1: 2, 2: 4, 4: 1, 5: 2}
        width = width_map.get(funct3)
        if width is None:
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

        addr = u32(rs1_u + sign_extend(insn >> 20, 12))
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

        imm = sign_extend(((insn >> 25) << 5) | ((insn >> 7) & 0x1F), 12)
        addr = u32(rs1_u + imm)
        if (addr & (width - 1)) != 0:
            return self._trap_trace(cur_pc, insn, CAUSE_STORE_MISALIGNED, addr)

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
        shamt = (insn >> 20) & 0x1F
        if funct3 == 0:
            res = rs1_u + imm
        elif funct3 == 2:
            res = 1 if rs1_s < imm else 0
        elif funct3 == 3:
            res = 1 if rs1_u < u32(imm) else 0
        elif funct3 == 4:
            res = rs1_u ^ u32(imm)
        elif funct3 == 6:
            res = rs1_u | u32(imm)
        elif funct3 == 7:
            res = rs1_u & u32(imm)
        elif funct3 == 1:
            if funct7 != 0x00:
                return None
            res = rs1_u << shamt
        elif funct3 == 5:
            if funct7 == 0x00:
                res = rs1_u >> shamt
            elif funct7 == 0x20:
                res = rs1_s >> shamt  # Python >> replicates sign bits; _set_reg wraps to 32b
            else:
                return None
        else:
            return None
        return self._set_reg(rd, res)

    def _exec_muldiv(self, rd: int, rs1_u: int, rs2_u: int, rs1_s: int, rs2_s: int, funct3: int) -> tuple[int, int]:
        """Execute all 8 RV32M multiply/divide instructions with RISC-V overflow/zero semantics."""
        if funct3 == 0:  # MUL
            res = rs1_s * rs2_s
        elif funct3 == 1:  # MULH
            res = (rs1_s * rs2_s) >> 32
        elif funct3 == 2:  # MULHSU
            res = (rs1_s * rs2_u) >> 32
        elif funct3 == 3:  # MULHU
            res = (rs1_u * rs2_u) >> 32
        elif funct3 == 4:  # DIV (truncates toward zero)
            if rs2_s == 0:
                res = -1
            elif rs1_s == INT32_MIN and rs2_s == -1:
                res = INT32_MIN
            else:
                q = abs(rs1_s) // abs(rs2_s)
                res = -q if (rs1_s < 0) ^ (rs2_s < 0) else q
        elif funct3 == 5:  # DIVU
            res = MASK32 if rs2_u == 0 else (rs1_u // rs2_u)
        elif funct3 == 6:  # REM (sign follows dividend)
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
        return None

    def _exec_system(
        self, insn: int, cur_pc: int, rd: int, rs1: int, rs1_u: int, funct3: int, next_pc: int
    ) -> tuple[int, int, int, bool] | StepTrace:
        """Execute `ECALL`/`EBREAK`/`MRET`/`WFI` and Zicsr instructions."""
        if funct3 == 0:
            if insn == 0x0000_0073:  # ECALL
                return self._trap_trace(cur_pc, insn, CAUSE_ECALL_M, 0)
            if insn == 0x0010_0073:  # EBREAK
                self.halted = True
                return self._trap_trace(cur_pc, insn, CAUSE_BREAKPOINT, cur_pc)
            if insn == 0x3020_0073:  # MRET
                mpie = bool(self.mstatus & MSTATUS_MPIE_BIT)
                self.mstatus = (
                    (self.mstatus & ~(MSTATUS_MIE_BIT | MSTATUS_MPIE_BIT))
                    | (MSTATUS_MIE_BIT if mpie else 0)
                    | MSTATUS_MPIE_BIT
                    | MSTATUS_MPP_M
                )
                return 0, 0, self.mepc & ~0x3, False
            if insn == 0x1050_0073:  # WFI
                return 0, 0, next_pc, False
            return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

        if funct3 in (1, 2, 3, 5, 6, 7):
            csr_addr = (insn >> 20) & 0xFFF
            old_val = self._read_csr(csr_addr)
            if old_val is None:
                return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)

            src_val = rs1 if (funct3 & 0x4) else rs1_u
            op = funct3 & 0x3
            if op == 1:  # CSRRW / CSRRWI
                new_val, do_write = src_val, True
            elif op == 2:  # CSRRS / CSRRSI
                new_val, do_write = old_val | src_val, (rs1 != 0)
            else:  # CSRRC / CSRRCI
                new_val, do_write = old_val & ~src_val, (rs1 != 0)

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
            a0 = s16(rs1_u)
            a1 = s16(rs1_u >> 16)
            b0 = s16(rs2_u)
            b1 = s16(rs2_u >> 16)
            base_acc = 0 if funct3 == 1 else self.mac_acc
            self.mac_acc = sat32(base_acc + a0 * b0 + a1 * b1)
            return self._set_reg(rd, self.mac_acc)
        if funct3 == 2:
            self.mac_acc = rs1_s
            return self._set_reg(rd, self.mac_acc)
        if funct3 == 3:
            return self._set_reg(rd, self.mac_acc)
        return None

    # -----------------------------------------------------------------------
    # Single-Instruction Execution & Run Loop
    # -----------------------------------------------------------------------
    # code-gate: allow-long-dispatch (flat single-level RISC-V major-opcode dispatch table)
    def step(self) -> StepTrace:
        """Advance CPU and CLINT timers by one instruction/trap and return its `StepTrace`."""
        cur_pc = self.pc
        self.mcycle += 1
        self.mtime += 1

        irq_trace = self._check_pending_interrupt(cur_pc)
        if irq_trace is not None:
            return irq_trace

        fetched = self._fetch_instruction(cur_pc)
        if isinstance(fetched, StepTrace):
            return fetched
        insn = fetched

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

        if opcode == 0x37:  # LUI
            wb_rd, wb_val = self._set_reg(rd, insn & 0xFFFF_F000)
        elif opcode == 0x17:  # AUIPC
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
        elif opcode == 0x0F:  # FENCE
            if funct3 not in (0, 1):
                return self._trap_trace(cur_pc, insn, CAUSE_ILLEGAL_INSN, insn)
        elif opcode == 0x73:  # SYSTEM
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
