"""Golden instruction-by-instruction RISC-V reference emulator (RV32IM + Zicsr + Xapex MAC).

This oracle serves as the single source of truth for verifying every SystemVerilog CPU
core (single-cycle and 5-stage pipelined) and the scratch SysC compiler toolchain.

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
from dataclasses import dataclass
from typing import Callable

# ---------------------------------------------------------------------------
# Address Map & Peripheral Register Offsets
# ---------------------------------------------------------------------------
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
CAUSE_ILLEGAL_INSN = 2
CAUSE_BREAKPOINT = 3
CAUSE_LOAD_MISALIGNED = 4
CAUSE_LOAD_ACCESS_FAULT = 5
CAUSE_STORE_MISALIGNED = 6
CAUSE_STORE_ACCESS_FAULT = 7
CAUSE_ECALL_M = 11
CAUSE_INT_M_TIMER = 0x8000_0007

MSTATUS_MIE_BIT = 1 << 3
MSTATUS_MPIE_BIT = 1 << 7
MSTATUS_MPP_M = 0b11 << 11

MIE_MSIE_BIT = 1 << 3
MIE_MTIE_BIT = 1 << 7
MIE_MEIE_BIT = 1 << 11

# Custom opcode
OPCODE_CUSTOM0 = 0x0B

MASK32 = 0xFFFF_FFFF
INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1


def u32(val: int) -> int:
    return val & MASK32


def s32(val: int) -> int:
    val &= MASK32
    return val - 0x1_0000_0000 if (val & 0x8000_0000) else val


def s16(val: int) -> int:
    val &= 0xFFFF
    return val - 0x1_0000 if (val & 0x8000) else val


def sat32(val: int) -> int:
    if val < INT32_MIN:
        return INT32_MIN
    if val > INT32_MAX:
        return INT32_MAX
    return val


def sign_extend(val: int, bits: int) -> int:
    sign_bit = 1 << (bits - 1)
    mask = (1 << bits) - 1
    val &= mask
    return (val ^ sign_bit) - sign_bit


class MemoryAccessFault(Exception):
    """Raised internally when a bus transaction targets an unmapped or read-only region."""


class SparseMemory:
    """Page-backed little-endian memory allowing multi-megabyte regions with zero upfront bloat."""

    PAGE_SIZE = 4096

    def __init__(self, base: int, size: int, writable: bool = True) -> None:
        self.base = base
        self.size = size
        self.writable = writable
        self._pages: dict[int, bytearray] = {}

    def contains(self, addr: int, width: int) -> bool:
        return self.base <= addr and (addr + width) <= (self.base + self.size)

    def _get_page(self, page_idx: int, create: bool) -> bytearray | None:
        page = self._pages.get(page_idx)
        if page is None and create:
            page = bytearray(self.PAGE_SIZE)
            self._pages[page_idx] = page
        return page

    def read_bytes(self, addr: int, width: int) -> int:
        val = 0
        for i in range(width):
            offset = (addr + i) - self.base
            page = self._pages.get(offset // self.PAGE_SIZE)
            byte = page[offset % self.PAGE_SIZE] if page is not None else 0
            val |= byte << (8 * i)
        return val

    def write_bytes(self, addr: int, width: int, val: int, bypass_ro: bool = False) -> None:
        if not self.writable and not bypass_ro:
            raise MemoryAccessFault(f"Write to read-only region at 0x{addr:08x}")
        for i in range(width):
            offset = (addr + i) - self.base
            page = self._get_page(offset // self.PAGE_SIZE, create=True)
            assert page is not None
            page[offset % self.PAGE_SIZE] = (val >> (8 * i)) & 0xFF


@dataclass
class StepTrace:
    """Architectural commit record for lockstep RTL co-simulation."""

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


class RV32Oracle:
    """Instruction-accurate RISC-V RV32IM + Zicsr + Xapex MAC reference CPU & SoC."""

    def __init__(
        self,
        reset_pc: int = BOOT_ROM_BASE,
        uart_tx_callback: Callable[[int], None] | None = None,
    ) -> None:
        self.reset_pc = u32(reset_pc)
        self.uart_tx_callback = uart_tx_callback

        # Memory regions
        self.rom = SparseMemory(BOOT_ROM_BASE, BOOT_ROM_SIZE, writable=False)
        self.bram = SparseMemory(BRAM_BASE, BRAM_SIZE, writable=True)
        self.qspi = SparseMemory(QSPI_BASE, QSPI_SIZE, writable=False)
        self.sdram = SparseMemory(SDRAM_BASE, SDRAM_SIZE, writable=True)
        self.mmio_stub = SparseMemory(MMIO_STUB_BASE, MMIO_STUB_END - MMIO_STUB_BASE, writable=True)
        self._mem_regions = (self.rom, self.bram, self.qspi, self.sdram)

        self.reset()

    def reset(self, reset_pc: int | None = None) -> None:
        if reset_pc is not None:
            self.reset_pc = u32(reset_pc)
        self.pc: int = self.reset_pc
        self.regs: list[int] = [0] * 32
        self.mac_acc: int = 0

        # Machine CSRs
        self.mstatus: int = MSTATUS_MPP_M
        self.misa: int = 0x4080_1100  # RV32I + M + X (custom extension)
        self.mie: int = 0
        self.mtvec: int = 0
        self.mscratch: int = 0
        self.mepc: int = 0
        self.mcause: int = 0
        self.mtval: int = 0
        self.mip_sw_ext: int = 0  # Software/external pending bits (MTIP is computed live)
        self.mcycle: int = 0
        self.minstret: int = 0

        # CLINT 64-bit timer & alarm
        self.mtime: int = 0
        self.mtimecmp: int = (1 << 64) - 1

        # UART0 console FIFOs
        self.uart_tx_buf: bytearray = bytearray()
        self.uart_rx_fifo: deque[int] = deque()
        self.uart_bauddiv: int = 50_000_000 // 115_200

        self.halted: bool = False

    # -----------------------------------------------------------------------
    # Loader & Host Inspection Helpers
    # -----------------------------------------------------------------------
    def _find_mem_region(self, addr: int, width: int) -> SparseMemory | None:
        for region in self._mem_regions:
            if region.contains(addr, width):
                return region
        return None

    def load_bytes(self, addr: int, data: bytes | bytearray) -> None:
        """Load raw bytes into any memory region (including ROM/QSPI) bypassing RO protection."""
        for i, b in enumerate(data):
            cur = u32(addr + i)
            region = self._find_mem_region(cur, 1)
            if region is None:
                raise MemoryAccessFault(f"Cannot load byte to unmapped address 0x{cur:08x}")
            region.write_bytes(cur, 1, b, bypass_ro=True)

    def load_words(self, addr: int, words: list[int] | tuple[int, ...]) -> None:
        """Load 32-bit little-endian instruction/data words into memory."""
        for idx, word in enumerate(words):
            cur = u32(addr + idx * 4)
            region = self._find_mem_region(cur, 4)
            if region is None:
                raise MemoryAccessFault(f"Cannot load word to unmapped address 0x{cur:08x}")
            region.write_bytes(cur, 4, u32(word), bypass_ro=True)

    def push_uart_rx(self, data: bytes | bytearray | str) -> None:
        raw = data.encode("latin-1") if isinstance(data, str) else data
        for b in raw:
            self.uart_rx_fifo.append(b & 0xFF)

    def read_uart_tx(self, clear: bool = False) -> bytes:
        out = bytes(self.uart_tx_buf)
        if clear:
            self.uart_tx_buf.clear()
        return out

    # -----------------------------------------------------------------------
    # Bus Read / Write (Memory + MMIO)
    # -----------------------------------------------------------------------
    def _clint_read(self, offset: int) -> int:
        if offset == CLINT_MTIME_LO:
            return self.mtime & MASK32
        if offset == CLINT_MTIME_HI:
            return (self.mtime >> 32) & MASK32
        if offset == CLINT_MTIMECMP_LO:
            return self.mtimecmp & MASK32
        if offset == CLINT_MTIMECMP_HI:
            return (self.mtimecmp >> 32) & MASK32
        return 0

    def _clint_write(self, offset: int, val: int) -> None:
        val = u32(val)
        if offset == CLINT_MTIME_LO:
            self.mtime = (self.mtime & ~MASK32) | val
        elif offset == CLINT_MTIME_HI:
            self.mtime = (self.mtime & MASK32) | (val << 32)
        elif offset == CLINT_MTIMECMP_LO:
            self.mtimecmp = (self.mtimecmp & ~MASK32) | val
        elif offset == CLINT_MTIMECMP_HI:
            self.mtimecmp = (self.mtimecmp & MASK32) | (val << 32)

    def _uart_read(self, offset: int) -> int:
        if offset == UART0_RXDATA:
            return self.uart_rx_fifo.popleft() if self.uart_rx_fifo else 0
        if offset == UART0_STATUS:
            rx_valid = 1 if self.uart_rx_fifo else 0
            # bit0: tx_ready=1, bit1: tx_empty=1, bit2: rx_valid
            return 0x03 | (rx_valid << 2)
        if offset == UART0_BAUDDIV:
            return self.uart_bauddiv
        return 0

    def _uart_write(self, offset: int, val: int) -> None:
        if offset == UART0_TXDATA:
            byte = val & 0xFF
            self.uart_tx_buf.append(byte)
            if self.uart_tx_callback is not None:
                self.uart_tx_callback(byte)
        elif offset == UART0_BAUDDIV:
            self.uart_bauddiv = max(1, u32(val))

    def bus_read(self, addr: int, width: int) -> int:
        addr = u32(addr)
        region = self._find_mem_region(addr, width)
        if region is not None:
            return region.read_bytes(addr, width)
        if CLINT_BASE <= addr and (addr + width) <= CLINT_BASE + CLINT_SIZE:
            if width != 4 or (addr & 3) != 0:
                raise MemoryAccessFault(f"CLINT requires 32-bit aligned access at 0x{addr:08x}")
            return self._clint_read(addr - CLINT_BASE)
        if UART0_BASE <= addr and (addr + width) <= UART0_BASE + UART0_SIZE:
            if (addr & 3) != 0 and width != 1:
                raise MemoryAccessFault(f"UART misaligned access at 0x{addr:08x}")
            return self._uart_read((addr - UART0_BASE) & ~3)
        if self.mmio_stub.contains(addr, width):
            return self.mmio_stub.read_bytes(addr, width)
        raise MemoryAccessFault(f"Load access fault at 0x{addr:08x}")

    def bus_write(self, addr: int, width: int, val: int) -> None:
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
            if (addr & 3) != 0 and width != 1:
                raise MemoryAccessFault(f"UART misaligned access at 0x{addr:08x}")
            self._uart_write((addr - UART0_BASE) & ~3, val)
            return
        if self.mmio_stub.contains(addr, width):
            self.mmio_stub.write_bytes(addr, width, val)
            return
        raise MemoryAccessFault(f"Store access fault at 0x{addr:08x}")

    def read_u32(self, addr: int) -> int:
        return self.bus_read(addr, 4)

    def write_u32(self, addr: int, val: int) -> None:
        self.bus_write(addr, 4, val)

    # -----------------------------------------------------------------------
    # CSRs & Traps
    # -----------------------------------------------------------------------
    def _live_mip(self) -> int:
        mtip = (1 << 7) if (self.mtime >= self.mtimecmp) else 0
        return (self.mip_sw_ext & (MIE_MSIE_BIT | MIE_MEIE_BIT)) | mtip

    def _read_csr(self, addr: int) -> int | None:
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
            return self.mcycle & MASK32
        if addr == CSR_MCYCLEH:
            return (self.mcycle >> 32) & MASK32
        if addr == CSR_MINSTRET:
            return self.minstret & MASK32
        if addr == CSR_MINSTRETH:
            return (self.minstret >> 32) & MASK32
        if addr in (CSR_MVENDORID, CSR_MARCHID, CSR_MIMPID, CSR_MHARTID):
            return 0
        return None

    def _write_csr(self, addr: int, val: int) -> bool:
        val = u32(val)
        if addr == CSR_MSTATUS:
            # Keep MPP fixed to M-mode (0b11); track MIE (bit 3) and MPIE (bit 7).
            self.mstatus = (val & (MSTATUS_MIE_BIT | MSTATUS_MPIE_BIT)) | MSTATUS_MPP_M
            return True
        if addr == CSR_MIE:
            self.mie = val & (MIE_MSIE_BIT | MIE_MTIE_BIT | MIE_MEIE_BIT)
            return True
        if addr == CSR_MTVEC:
            mode = val & 0x3
            # Support Direct (0) and Vectored (1); clamp reserved modes to 0
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
            # MTIP (bit 7) is read-only driven by CLINT; MSIP/MEIP writable by software/tb
            self.mip_sw_ext = val & (MIE_MSIE_BIT | MIE_MEIE_BIT)
            return True
        if addr == CSR_MCYCLE:
            self.mcycle = (self.mcycle & ~MASK32) | val
            return True
        if addr == CSR_MCYCLEH:
            self.mcycle = (self.mcycle & MASK32) | (val << 32)
            return True
        if addr == CSR_MINSTRET:
            self.minstret = (self.minstret & ~MASK32) | val
            return True
        if addr == CSR_MINSTRETH:
            self.minstret = (self.minstret & MASK32) | (val << 32)
            return True
        return False

    def _take_trap(self, cause: int, tval: int, is_interrupt: bool) -> int:
        self.mepc = self.pc
        self.mcause = u32(cause)
        self.mtval = u32(tval)

        mie_was = 1 if (self.mstatus & MSTATUS_MIE_BIT) else 0
        self.mstatus = (self.mstatus & ~(MSTATUS_MIE_BIT | MSTATUS_MPIE_BIT)) | (
            MSTATUS_MPIE_BIT if mie_was else 0
        ) | MSTATUS_MPP_M

        base = self.mtvec & ~0x3
        mode = self.mtvec & 0x3
        if is_interrupt and mode == 1:
            target = u32(base + 4 * (cause & 0x7FFF_FFFF))
        else:
            target = base
        self.pc = target
        return target

    def _set_reg(self, rd: int, val: int) -> tuple[int, int]:
        val = u32(val)
        if rd != 0:
            self.regs[rd] = val
        return rd, (0 if rd == 0 else val)

    # -----------------------------------------------------------------------
    # Single-Instruction Execution Step
    # -----------------------------------------------------------------------
    def step(self) -> StepTrace:
        cur_pc = self.pc
        self.mcycle += 1
        self.mtime += 1

        # 1. Check pending machine-mode interrupts before instruction fetch
        if self.mstatus & MSTATUS_MIE_BIT:
            pending = self._live_mip() & self.mie
            if pending & MIE_MTIE_BIT:
                target = self._take_trap(CAUSE_INT_M_TIMER, 0, is_interrupt=True)
                return StepTrace(pc=cur_pc, insn=0, next_pc=target, trap_cause=CAUSE_INT_M_TIMER, interrupt=True)

        # 2. Fetch 32-bit instruction
        if (cur_pc & 3) != 0:
            target = self._take_trap(CAUSE_INSN_MISALIGNED, cur_pc, is_interrupt=False)
            return StepTrace(pc=cur_pc, insn=0, next_pc=target, trap_cause=CAUSE_INSN_MISALIGNED)

        try:
            insn = self.bus_read(cur_pc, 4)
        except MemoryAccessFault:
            target = self._take_trap(CAUSE_ILLEGAL_INSN, cur_pc, is_interrupt=False)
            return StepTrace(pc=cur_pc, insn=0, next_pc=target, trap_cause=CAUSE_ILLEGAL_INSN)

        opcode = insn & 0x7F
        rd = (insn >> 7) & 0x1F
        funct3 = (insn >> 12) & 0x7
        rs1 = (insn >> 15) & 0x1F
        rs2 = (insn >> 20) & 0x1F
        funct7 = (insn >> 25) & 0x7F

        rs1_u = self.regs[rs1]
        rs2_u = self.regs[rs2]
        rs1_s = s32(rs1_u)
        rs2_s = s32(rs2_u)

        next_pc = u32(cur_pc + 4)
        wb_rd = 0
        wb_val = 0
        mem_addr: int | None = None
        mem_val: int | None = None
        mem_write = False
        csr_wrote_minstret = False

        def illegal() -> StepTrace:
            target = self._take_trap(CAUSE_ILLEGAL_INSN, insn, is_interrupt=False)
            return StepTrace(pc=cur_pc, insn=insn, next_pc=target, trap_cause=CAUSE_ILLEGAL_INSN)

        # LUI
        if opcode == 0x37:
            wb_rd, wb_val = self._set_reg(rd, insn & 0xFFFF_F000)

        # AUIPC
        elif opcode == 0x17:
            wb_rd, wb_val = self._set_reg(rd, cur_pc + (insn & 0xFFFF_F000))

        # JAL
        elif opcode == 0x6F:
            imm = sign_extend(
                (((insn >> 31) & 1) << 20)
                | (((insn >> 12) & 0xFF) << 12)
                | (((insn >> 20) & 1) << 11)
                | (((insn >> 21) & 0x3FF) << 1),
                21,
            )
            target = u32(cur_pc + imm)
            if target & 3:
                trap_pc = self._take_trap(CAUSE_INSN_MISALIGNED, target, is_interrupt=False)
                return StepTrace(pc=cur_pc, insn=insn, next_pc=trap_pc, trap_cause=CAUSE_INSN_MISALIGNED)
            wb_rd, wb_val = self._set_reg(rd, next_pc)
            next_pc = target

        # JALR
        elif opcode == 0x67:
            if funct3 != 0:
                return illegal()
            imm = sign_extend(insn >> 20, 12)
            target = u32((rs1_u + imm) & ~1)
            if target & 3:
                trap_pc = self._take_trap(CAUSE_INSN_MISALIGNED, target, is_interrupt=False)
                return StepTrace(pc=cur_pc, insn=insn, next_pc=trap_pc, trap_cause=CAUSE_INSN_MISALIGNED)
            wb_rd, wb_val = self._set_reg(rd, next_pc)
            next_pc = target

        # BRANCH
        elif opcode == 0x63:
            imm = sign_extend(
                (((insn >> 31) & 1) << 12)
                | (((insn >> 7) & 1) << 11)
                | (((insn >> 25) & 0x3F) << 5)
                | (((insn >> 8) & 0xF) << 1),
                13,
            )
            if funct3 == 0:
                taken = rs1_u == rs2_u
            elif funct3 == 1:
                taken = rs1_u != rs2_u
            elif funct3 == 4:
                taken = rs1_s < rs2_s
            elif funct3 == 5:
                taken = rs1_s >= rs2_s
            elif funct3 == 6:
                taken = rs1_u < rs2_u
            elif funct3 == 7:
                taken = rs1_u >= rs2_u
            else:
                return illegal()

            if taken:
                target = u32(cur_pc + imm)
                if target & 3:
                    trap_pc = self._take_trap(CAUSE_INSN_MISALIGNED, target, is_interrupt=False)
                    return StepTrace(pc=cur_pc, insn=insn, next_pc=trap_pc, trap_cause=CAUSE_INSN_MISALIGNED)
                next_pc = target

        # LOAD
        elif opcode == 0x03:
            imm = sign_extend(insn >> 20, 12)
            addr = u32(rs1_u + imm)
            if funct3 in (0, 4):
                width = 1
            elif funct3 in (1, 5):
                width = 2
            elif funct3 == 2:
                width = 4
            else:
                return illegal()

            if (addr & (width - 1)) != 0:
                trap_pc = self._take_trap(CAUSE_LOAD_MISALIGNED, addr, is_interrupt=False)
                return StepTrace(pc=cur_pc, insn=insn, next_pc=trap_pc, trap_cause=CAUSE_LOAD_MISALIGNED)

            try:
                raw = self.bus_read(addr, width)
            except MemoryAccessFault:
                trap_pc = self._take_trap(CAUSE_LOAD_ACCESS_FAULT, addr, is_interrupt=False)
                return StepTrace(pc=cur_pc, insn=insn, next_pc=trap_pc, trap_cause=CAUSE_LOAD_ACCESS_FAULT)

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

            mem_addr = addr
            mem_val = u32(val)
            wb_rd, wb_val = self._set_reg(rd, val)

        # STORE
        elif opcode == 0x23:
            imm = sign_extend(((insn >> 25) << 5) | ((insn >> 7) & 0x1F), 12)
            addr = u32(rs1_u + imm)
            if funct3 == 0:
                width = 1
            elif funct3 == 1:
                width = 2
            elif funct3 == 2:
                width = 4
            else:
                return illegal()

            if (addr & (width - 1)) != 0:
                trap_pc = self._take_trap(CAUSE_STORE_MISALIGNED, addr, is_interrupt=False)
                return StepTrace(pc=cur_pc, insn=insn, next_pc=trap_pc, trap_cause=CAUSE_STORE_MISALIGNED)

            store_val = rs2_u & ((1 << (8 * width)) - 1)
            try:
                self.bus_write(addr, width, store_val)
            except MemoryAccessFault:
                trap_pc = self._take_trap(CAUSE_STORE_ACCESS_FAULT, addr, is_interrupt=False)
                return StepTrace(pc=cur_pc, insn=insn, next_pc=trap_pc, trap_cause=CAUSE_STORE_ACCESS_FAULT)

            mem_addr = addr
            mem_val = store_val
            mem_write = True

        # OP-IMM
        elif opcode == 0x13:
            imm = sign_extend(insn >> 20, 12)
            shamt = rs2
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
                    return illegal()
                res = rs1_u << shamt
            elif funct3 == 5:
                if funct7 == 0x00:
                    res = rs1_u >> shamt
                elif funct7 == 0x20:
                    res = rs1_s >> shamt
                else:
                    return illegal()
            else:
                return illegal()
            wb_rd, wb_val = self._set_reg(rd, res)

        # OP (RV32I + RV32M)
        elif opcode == 0x33:
            if funct7 == 0x01:
                # RV32M
                if funct3 == 0:  # MUL
                    res = rs1_s * rs2_s
                elif funct3 == 1:  # MULH
                    res = (rs1_s * rs2_s) >> 32
                elif funct3 == 2:  # MULHSU
                    res = (rs1_s * rs2_u) >> 32
                elif funct3 == 3:  # MULHU
                    res = (rs1_u * rs2_u) >> 32
                elif funct3 == 4:  # DIV
                    if rs2_s == 0:
                        res = -1
                    elif rs1_s == INT32_MIN and rs2_s == -1:
                        res = INT32_MIN
                    else:
                        q = abs(rs1_s) // abs(rs2_s)
                        res = -q if (rs1_s < 0) ^ (rs2_s < 0) else q
                elif funct3 == 5:  # DIVU
                    res = MASK32 if rs2_u == 0 else (rs1_u // rs2_u)
                elif funct3 == 6:  # REM
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
                wb_rd, wb_val = self._set_reg(rd, res)
            elif funct7 == 0x00:
                if funct3 == 0:
                    res = rs1_u + rs2_u
                elif funct3 == 1:
                    res = rs1_u << (rs2_u & 0x1F)
                elif funct3 == 2:
                    res = 1 if rs1_s < rs2_s else 0
                elif funct3 == 3:
                    res = 1 if rs1_u < rs2_u else 0
                elif funct3 == 4:
                    res = rs1_u ^ rs2_u
                elif funct3 == 5:
                    res = rs1_u >> (rs2_u & 0x1F)
                elif funct3 == 6:
                    res = rs1_u | rs2_u
                else:
                    res = rs1_u & rs2_u
                wb_rd, wb_val = self._set_reg(rd, res)
            elif funct7 == 0x20:
                if funct3 == 0:
                    res = rs1_u - rs2_u
                elif funct3 == 5:
                    res = rs1_s >> (rs2_u & 0x1F)
                else:
                    return illegal()
                wb_rd, wb_val = self._set_reg(rd, res)
            else:
                return illegal()

        # FENCE
        elif opcode == 0x0F:
            if funct3 not in (0, 1):
                return illegal()

        # SYSTEM (ECALL / EBREAK / MRET / WFI / Zicsr)
        elif opcode == 0x73:
            if funct3 == 0:
                if insn == 0x0000_0073:  # ECALL
                    trap_pc = self._take_trap(CAUSE_ECALL_M, 0, is_interrupt=False)
                    return StepTrace(pc=cur_pc, insn=insn, next_pc=trap_pc, trap_cause=CAUSE_ECALL_M)
                if insn == 0x0010_0073:  # EBREAK
                    self.halted = True
                    trap_pc = self._take_trap(CAUSE_BREAKPOINT, cur_pc, is_interrupt=False)
                    return StepTrace(pc=cur_pc, insn=insn, next_pc=trap_pc, trap_cause=CAUSE_BREAKPOINT)
                if insn == 0x3020_0073:  # MRET
                    mpie = 1 if (self.mstatus & MSTATUS_MPIE_BIT) else 0
                    self.mstatus = (
                        (self.mstatus & ~(MSTATUS_MIE_BIT | MSTATUS_MPIE_BIT))
                        | (MSTATUS_MIE_BIT if mpie else 0)
                        | MSTATUS_MPIE_BIT
                        | MSTATUS_MPP_M
                    )
                    next_pc = self.mepc & ~0x3
                elif insn == 0x1050_0073:  # WFI
                    pass
                else:
                    return illegal()
            elif funct3 in (1, 2, 3, 5, 6, 7):
                csr_addr = (insn >> 20) & 0xFFF
                old_val = self._read_csr(csr_addr)
                if old_val is None:
                    return illegal()

                is_imm = (funct3 & 0x4) != 0
                op = funct3 & 0x3
                src_val = rs1 if is_imm else rs1_u

                if op == 1:  # CSRRW / CSRRWI
                    new_val = src_val
                    do_write = True
                elif op == 2:  # CSRRS / CSRRSI
                    new_val = old_val | src_val
                    do_write = rs1 != 0
                else:  # CSRRC / CSRRCI
                    new_val = old_val & ~src_val
                    do_write = rs1 != 0

                if do_write:
                    if not self._write_csr(csr_addr, new_val):
                        return illegal()
                    if csr_addr in (CSR_MINSTRET, CSR_MINSTRETH):
                        csr_wrote_minstret = True

                wb_rd, wb_val = self._set_reg(rd, old_val)
            else:
                return illegal()

        # CUSTOM-0: Xapex packed dual-int16 saturating MAC
        elif opcode == OPCODE_CUSTOM0:
            if funct7 != 0x00:
                return illegal()
            if funct3 in (0, 1):
                a0 = s16(rs1_u & 0xFFFF)
                a1 = s16((rs1_u >> 16) & 0xFFFF)
                b0 = s16(rs2_u & 0xFFFF)
                b1 = s16((rs2_u >> 16) & 0xFFFF)
                base_acc = 0 if funct3 == 1 else self.mac_acc
                acc = sat32(base_acc + a0 * b0 + a1 * b1)
                self.mac_acc = acc
                wb_rd, wb_val = self._set_reg(rd, acc)
            elif funct3 == 2:
                self.mac_acc = rs1_s
                wb_rd, wb_val = self._set_reg(rd, self.mac_acc)
            elif funct3 == 3:
                wb_rd, wb_val = self._set_reg(rd, self.mac_acc)
            else:
                return illegal()

        else:
            return illegal()

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
        """Run up to max_steps instructions and return execution trace."""
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


# ---------------------------------------------------------------------------
# Compact RV32IM + Zicsr + Xapex MAC Instruction Encoders (for testbenches)
# ---------------------------------------------------------------------------
def enc_r(funct7: int, rs2: int, rs1: int, funct3: int, rd: int, opcode: int) -> int:
    return (
        ((funct7 & 0x7F) << 25)
        | ((rs2 & 0x1F) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | ((rd & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def enc_i(imm: int, rs1: int, funct3: int, rd: int, opcode: int) -> int:
    return (
        ((imm & 0xFFF) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | ((rd & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def enc_s(imm: int, rs2: int, rs1: int, funct3: int, opcode: int) -> int:
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
    return (imm20_shifted & 0xFFFF_F000) | ((rd & 0x1F) << 7) | (opcode & 0x7F)


def enc_j(imm: int, rd: int, opcode: int = 0x6F) -> int:
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
    return enc_r(0x00, rs2, rs1, funct3, rd, OPCODE_CUSTOM0)
