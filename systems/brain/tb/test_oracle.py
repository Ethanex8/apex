"""Unit tests for the golden RV32IM + Zicsr + CLINT + UART0 + Xapex MAC emulator.

Purpose:
  Verify every instruction family, arithmetic/overflow edge case, CSR WARL mask,
  CLINT timer and priority interrupts, UART0 FIFO handshake, Xapex MAC accumulator,
  and alignment/bus fault trap in `systems/brain/sim/oracle.py`.

Usage:
  uv run --with pytest --with pytest-cov pytest -v \\
    --cov=systems/brain/sim --cov-fail-under=95 systems/brain/tb/test_oracle.py

Invariants:
  - Achieves >=95% line coverage across `systems/brain/sim/oracle.py`.
  - Validates exact RISC-V trap causes, priority ordering (`MEIP > MSIP > MTIP`), and MMIO bounds.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BRAIN_SIM_DIR = Path(__file__).resolve().parents[1] / "sim"
if str(BRAIN_SIM_DIR) not in sys.path:
    sys.path.insert(0, str(BRAIN_SIM_DIR))

from oracle import (  # noqa: E402 — sys.path adjusted for repo-local sim package
    BOOT_ROM_BASE,
    BRAM_BASE,
    CAUSE_ECALL_M,
    CAUSE_ILLEGAL_INSN,
    CAUSE_INSN_ACCESS_FAULT,
    CAUSE_INSN_MISALIGNED,
    CAUSE_INT_M_EXT,
    CAUSE_INT_M_SW,
    CAUSE_INT_M_TIMER,
    CAUSE_LOAD_ACCESS_FAULT,
    CAUSE_LOAD_MISALIGNED,
    CAUSE_STORE_ACCESS_FAULT,
    CAUSE_STORE_MISALIGNED,
    CLINT_BASE,
    CLINT_MTIME_HI,
    CLINT_MTIME_LO,
    CLINT_MTIMECMP_HI,
    CLINT_MTIMECMP_LO,
    CSR_MCAUSE,
    CSR_MCYCLE,
    CSR_MCYCLEH,
    CSR_MEPC,
    CSR_MHARTID,
    CSR_MIE,
    CSR_MINSTRET,
    CSR_MINSTRETH,
    CSR_MIP,
    CSR_MISA,
    CSR_MSCRATCH,
    CSR_MSTATUS,
    CSR_MTVAL,
    CSR_MTVEC,
    INT32_MAX,
    INT32_MIN,
    MIE_MEIE_BIT,
    MIE_MSIE_BIT,
    MIE_MTIE_BIT,
    MMIO_STUB_BASE,
    MSTATUS_MIE_BIT,
    SDRAM_BASE,
    UART0_BASE,
    UART0_BAUDDIV,
    UART0_RXDATA,
    UART0_STATUS,
    UART0_TXDATA,
    MemoryAccessFault,
    RV32Oracle,
    enc_b,
    enc_i,
    enc_j,
    enc_mac,
    enc_r,
    enc_s,
    enc_u,
    u32,
)

EBREAK = 0x0010_0073
ECALL = 0x0000_0073
MRET = 0x3020_0073
WFI = 0x1050_0073
FENCE = 0x0000_000F


def pack_i16(lo: int, hi: int) -> int:
    """Pack two signed 16-bit integers into one 32-bit word `[hi:lo]`."""
    return ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)


def test_rv32i_arithmetic_shifts_and_x0() -> None:
    """Verify RV32I ALU/immediate ops, barrel-shift sign rules, LUI/AUIPC, and hardwired x0."""
    cpu = RV32Oracle()
    cpu.regs[20] = 0x0000_00FF
    prog = [
        enc_i(10, 0, 0, 0, 0x13),          # addi  x0, x0, 10 (x0 stays 0)
        enc_i(-5, 0, 0, 1, 0x13),          # addi  x1, x0, -5
        enc_i(3, 0, 0, 2, 0x13),           # addi  x2, x0, 3
        enc_r(0x00, 2, 1, 0, 3, 0x33),     # add   x3, x1, x2 (-2)
        enc_r(0x20, 2, 1, 0, 4, 0x33),     # sub   x4, x1, x2 (-8)
        enc_r(0x00, 2, 1, 2, 5, 0x33),     # slt   x5, x1, x2 (1)
        enc_r(0x00, 2, 1, 3, 6, 0x33),     # sltu  x6, x1, x2 (0)
        enc_i(0x400 | 1, 1, 5, 7, 0x13),   # srai  x7, x1, 1 (-3)
        enc_i(1, 1, 5, 8, 0x13),           # srli  x8, x1, 1
        enc_i(2, 2, 1, 9, 0x13),           # slli  x9, x2, 2 (12)
        enc_i(-1, 1, 2, 10, 0x13),         # slti  x10, x1, -1 (1)
        enc_i(1, 1, 3, 11, 0x13),          # sltiu x11, x1, 1 (0)
        enc_i(0x0F, 20, 4, 12, 0x13),      # xori  x12, x20, 0x0F (0xF0)
        enc_i(0x100, 20, 6, 13, 0x13),     # ori   x13, x20, 0x100 (0x1FF)
        enc_i(0x0F, 20, 7, 14, 0x13),      # andi  x14, x20, 0x0F (0x0F)
        enc_r(0x00, 2, 9, 1, 15, 0x33),    # sll   x15, x9, x2 (12 << 3 = 96)
        enc_r(0x00, 2, 20, 4, 16, 0x33),   # xor   x16, x20, x2 (0xFC)
        enc_r(0x00, 2, 9, 5, 17, 0x33),    # srl   x17, x9, x2 (12 >> 3 = 1)
        enc_r(0x00, 2, 20, 6, 18, 0x33),   # or    x18, x20, x2 (0xFF)
        enc_r(0x00, 2, 20, 7, 19, 0x33),   # and   x19, x20, x2 (0x03)
        enc_r(0x20, 2, 1, 5, 21, 0x33),    # sra   x21, x1, x2 (-5 >> 3 = -1)
        enc_u(0x1234_5000, 22, 0x37),      # lui   x22, 0x12345
        enc_u(0x0000_1000, 23, 0x17),      # auipc x23, 0x1000
        FENCE,
        WFI,
        EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[0] == 0
    assert cpu.regs[3] == u32(-2)
    assert cpu.regs[4] == u32(-8)
    assert cpu.regs[5] == 1
    assert cpu.regs[6] == 0
    assert cpu.regs[7] == u32(-3)
    assert cpu.regs[8] == 0x7FFF_FFFD
    assert cpu.regs[9] == 12
    assert cpu.regs[10] == 1
    assert cpu.regs[11] == 0
    assert cpu.regs[12] == 0xF0
    assert cpu.regs[13] == 0x1FF
    assert cpu.regs[14] == 0x0F
    assert cpu.regs[15] == 96
    assert cpu.regs[16] == 0xFC
    assert cpu.regs[17] == 1
    assert cpu.regs[18] == 0xFF
    assert cpu.regs[19] == 0x03
    assert cpu.regs[21] == u32(-1)
    assert cpu.regs[22] == 0x1234_5000
    assert cpu.regs[23] == BOOT_ROM_BASE + 22 * 4 + 0x1000


def test_rv32m_multiply_and_division_edge_cases() -> None:
    """Verify RV32M 64-bit products, truncation-toward-zero division, div-by-zero, and INT32_MIN/-1."""
    cpu = RV32Oracle()
    cpu.regs[1] = u32(-7)
    cpu.regs[2] = 3
    cpu.regs[3] = 0x8000_0000  # INT32_MIN
    cpu.regs[4] = u32(-1)
    cpu.regs[5] = 0
    cpu.regs[6] = 20

    prog = [
        enc_r(0x01, 2, 1, 0, 10, 0x33),  # mul    x10, x1, x2   -> -21
        enc_r(0x01, 2, 1, 1, 11, 0x33),  # mulh   x11, x1, x2   -> -1
        enc_r(0x01, 2, 1, 2, 12, 0x33),  # mulhsu x12, x1, x2   -> -1
        enc_r(0x01, 2, 1, 3, 13, 0x33),  # mulhu  x13, x1, x2   -> 2
        enc_r(0x01, 2, 1, 4, 14, 0x33),  # div    x14, x1, x2   -> -2
        enc_r(0x01, 2, 1, 6, 15, 0x33),  # rem    x15, x1, x2   -> -1
        enc_r(0x01, 4, 3, 4, 16, 0x33),  # div    x16, INT_MIN, -1 -> INT_MIN
        enc_r(0x01, 4, 3, 6, 17, 0x33),  # rem    x17, INT_MIN, -1 -> 0
        enc_r(0x01, 5, 1, 4, 18, 0x33),  # div    x18, -7, 0    -> -1
        enc_r(0x01, 5, 1, 5, 19, 0x33),  # divu   x19, -7, 0    -> 0xFFFF_FFFF
        enc_r(0x01, 5, 1, 6, 20, 0x33),  # rem    x20, -7, 0    -> -7
        enc_r(0x01, 5, 1, 7, 21, 0x33),  # remu   x21, -7, 0    -> 0xFFFF_FFF9
        enc_r(0x01, 2, 6, 5, 22, 0x33),  # divu   x22, 20, 3    -> 6
        enc_r(0x01, 2, 6, 7, 23, 0x33),  # remu   x23, 20, 3    -> 2
        EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[10] == u32(-21)
    assert cpu.regs[11] == u32(-1)
    assert cpu.regs[12] == u32(-1)
    assert cpu.regs[13] == 2
    assert cpu.regs[14] == u32(-2)
    assert cpu.regs[15] == u32(-1)
    assert cpu.regs[16] == 0x8000_0000
    assert cpu.regs[17] == 0
    assert cpu.regs[18] == 0xFFFF_FFFF
    assert cpu.regs[19] == 0xFFFF_FFFF
    assert cpu.regs[20] == u32(-7)
    assert cpu.regs[21] == u32(-7)
    assert cpu.regs[22] == 6
    assert cpu.regs[23] == 2


def test_branches_and_jumps_all_conditions() -> None:
    """Verify signed/unsigned branches, JAL/JALR link addresses, reset_pc, and stop_on_pc."""
    cpu = RV32Oracle()
    # Test sum(1..5) loop + subroutine call + bge/bltu/bgeu branches + stop_on_pc
    cpu.regs[10] = u32(-1)
    cpu.regs[11] = 1
    prog = [
        enc_i(0, 0, 0, 1, 0x13),       # 0x00: addi x1, x0, 0     (sum)
        enc_i(1, 0, 0, 2, 0x13),       # 0x04: addi x2, x0, 1     (i)
        enc_i(6, 0, 0, 3, 0x13),       # 0x08: addi x3, x0, 6     (limit)
        enc_r(0x00, 2, 1, 0, 1, 0x33), # 0x0C: add  x1, x1, x2
        enc_i(1, 2, 0, 2, 0x13),       # 0x10: addi x2, x2, 1
        enc_b(-8, 3, 2, 4),            # 0x14: blt  x2, x3, -8    (-> 0x0C)
        enc_b(8, 10, 11, 5),           # 0x18: bge  1, -1, +8     (taken -> 0x20)
        EBREAK,                        # 0x1C: skipped
        enc_b(8, 10, 11, 6),           # 0x20: bltu 1, 0xFFFF_FFFF, +8 (taken -> 0x28)
        EBREAK,                        # 0x24: skipped
        enc_b(8, 11, 10, 7),           # 0x28: bgeu 0xFFFF_FFFF, 1, +8 (taken -> 0x30)
        EBREAK,                        # 0x2C: skipped
        enc_j(8, 5),                   # 0x30: jal  x5, +8        (-> 0x38, x5=0x34)
        EBREAK,                        # 0x34: halt after return
        enc_i(100, 1, 0, 1, 0x13),     # 0x38: addi x1, x1, 100
        enc_i(0, 5, 0, 0, 0x67),       # 0x3C: jalr x0, 0(x5)     (-> 0x34)
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[1] == 115
    assert cpu.regs[5] == BOOT_ROM_BASE + 0x34

    # Verify stop_on_pc and reset(reset_pc=...)
    cpu.reset(reset_pc=BRAM_BASE)
    cpu.load_bytes(BRAM_BASE, b"\x13\x05\x50\x02")  # addi x10, x0, 37
    cpu.run(stop_on_pc=BRAM_BASE + 4)
    assert cpu.regs[10] == 37


def test_memory_loads_stores_mmio_stub_and_faults() -> None:
    """Verify little-endian byte/half/word accesses, MMIO stub R/W, and alignment/ROM fault traps."""
    cpu = RV32Oracle()
    cpu.regs[1] = BRAM_BASE
    cpu.regs[2] = 0x1122_80FF
    cpu.regs[3] = SDRAM_BASE + 0x1000
    cpu.regs[10] = MMIO_STUB_BASE

    prog = [
        enc_s(0, 2, 1, 2, 0x23),   # sw  x2, 0(BRAM)
        enc_i(0, 1, 0, 4, 0x03),   # lb  x4, 0(BRAM) -> 0xFFFF_FFFF
        enc_i(0, 1, 4, 5, 0x03),   # lbu x5, 0(BRAM) -> 0x0000_00FF
        enc_i(0, 1, 1, 6, 0x03),   # lh  x6, 0(BRAM) -> 0xFFFF_80FF
        enc_i(0, 1, 5, 7, 0x03),   # lhu x7, 0(BRAM) -> 0x0000_80FF
        enc_s(2, 2, 3, 1, 0x23),   # sh  x2, 2(SDRAM+0x1000)
        enc_i(2, 3, 5, 8, 0x03),   # lhu x8, 2(SDRAM+0x1000) -> 0x80FF
        enc_s(1, 2, 3, 0, 0x23),   # sb  x2, 1(SDRAM+0x1000)
        enc_i(0, 3, 2, 9, 0x03),   # lw  x9, 0(SDRAM+0x1000) -> 0x80FF_FF00
        enc_s(0, 2, 10, 2, 0x23),  # sw  x2, 0(MMIO_STUB)
        enc_i(0, 10, 2, 11, 0x03), # lw  x11, 0(MMIO_STUB)
        EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[4] == 0xFFFF_FFFF
    assert cpu.regs[5] == 0x0000_00FF
    assert cpu.regs[6] == 0xFFFF_80FF
    assert cpu.regs[7] == 0x0000_80FF
    assert cpu.regs[8] == 0x0000_80FF
    assert cpu.regs[9] == 0x80FF_FF00
    assert cpu.regs[11] == 0x1122_80FF

    # Host read_u32 / write_u32 helpers
    cpu.write_u32(BRAM_BASE + 0x20, 0xDEAD_BEEF)
    assert cpu.read_u32(BRAM_BASE + 0x20) == 0xDEAD_BEEF

    # Misaligned load/store, unmapped access faults, and ROM write fault
    for insn, reg_val, expected_cause in [
        (enc_i(0, 1, 2, 2, 0x03), BRAM_BASE + 1, CAUSE_LOAD_MISALIGNED),
        (enc_s(0, 2, 1, 2, 0x23), BRAM_BASE + 2, CAUSE_STORE_MISALIGNED),
        (enc_i(0, 1, 2, 2, 0x03), 0x7000_0000, CAUSE_LOAD_ACCESS_FAULT),
        (enc_s(0, 2, 1, 2, 0x23), BOOT_ROM_BASE, CAUSE_STORE_ACCESS_FAULT),
        (enc_s(0, 2, 1, 2, 0x23), 0x7000_0000, CAUSE_STORE_ACCESS_FAULT),
    ]:
        cpu.reset()
        cpu.regs[1] = reg_val
        cpu.load_words(BOOT_ROM_BASE, [insn])
        tr = cpu.step()
        assert tr.trap_cause == expected_cause

    with pytest.raises(MemoryAccessFault):
        cpu.load_bytes(0x7000_0000, b"\x00")
    with pytest.raises(MemoryAccessFault):
        cpu.load_words(0x7000_0000, [0])


def test_clint_timer_interrupt_and_ecall_traps() -> None:
    """Verify ECALL trap handling, MRET return, mcycle > minstret invariant, and CLINT timer IRQ."""
    cpu = RV32Oracle()
    handler_addr = BRAM_BASE
    cpu.regs[21] = CAUSE_INT_M_TIMER
    cpu.regs[22] = CLINT_BASE
    cpu.regs[23] = 0xFFFF_FFFF

    handler = [
        enc_i(CSR_MCAUSE, 0, 2, 25, 0x73),          # csrr  x25, mcause
        enc_b(32, 21, 25, 0),                       # beq   x25, x21, timer_isr (+32)
        enc_i(CSR_MSCRATCH, 0, 2, 26, 0x73),        # csrr  x26, mscratch
        enc_i(1, 26, 0, 26, 0x13),                  # addi  x26, x26, 1
        enc_i(CSR_MSCRATCH, 26, 1, 0, 0x73),        # csrw  mscratch, x26
        enc_i(CSR_MEPC, 0, 2, 26, 0x73),            # csrr  x26, mepc
        enc_i(4, 26, 0, 26, 0x13),                  # addi  x26, x26, 4
        enc_i(CSR_MEPC, 26, 1, 0, 0x73),            # csrw  mepc, x26
        MRET,
        enc_s(CLINT_MTIMECMP_LO, 23, 22, 2, 0x23),  # sw x23, mtimecmp_lo(CLINT)
        enc_s(CLINT_MTIMECMP_HI, 23, 22, 2, 0x23),  # sw x23, mtimecmp_hi(CLINT)
        enc_i(0x123, 0, 0, 20, 0x13),               # addi x20, x0, 0x123
        MRET,
    ]
    cpu.load_words(handler_addr, handler)

    cpu.regs[1] = handler_addr
    cpu.regs[2] = CLINT_BASE
    cpu.regs[3] = 15
    cpu.regs[4] = MIE_MTIE_BIT
    cpu.regs[5] = MSTATUS_MIE_BIT
    cpu.regs[6] = 0x123

    main_prog = [
        enc_i(CSR_MTVEC, 1, 1, 0, 0x73),           # csrw mtvec, x1
        enc_s(CLINT_MTIMECMP_HI, 0, 2, 2, 0x23),   # sw x0, mtimecmp_hi
        enc_s(CLINT_MTIMECMP_LO, 3, 2, 2, 0x23),   # sw x3, mtimecmp_lo (15)
        enc_i(CSR_MIE, 4, 1, 0, 0x73),             # csrw mie, x4
        enc_i(CSR_MSTATUS, 5, 1, 0, 0x73),         # csrw mstatus, x5
        ECALL,                                     # triggers ECALL -> mscratch = 1
        enc_b(-4, 6, 20, 1),                       # spin until timer IRQ sets x20 = 0x123
        EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, main_prog)
    traces = cpu.run(max_steps=200)

    assert cpu.halted
    assert cpu.mscratch == 1
    assert cpu.regs[20] == 0x123
    assert any(t.trap_cause == CAUSE_ECALL_M for t in traces)
    assert any(t.interrupt and t.trap_cause == CAUSE_INT_M_TIMER for t in traces)
    assert cpu.mcycle > cpu.minstret

    # Vectored MTVEC mode jumps to base + 4 * cause_code on interrupt
    cpu.reset()
    cpu.mtvec = BRAM_BASE | 1
    cpu.mie = MIE_MTIE_BIT
    cpu.mstatus = MSTATUS_MIE_BIT
    cpu.mtimecmp = 0
    tr = cpu.step()
    assert tr.interrupt
    assert tr.next_pc == BRAM_BASE + 4 * (CAUSE_INT_M_TIMER & 0x7FFF_FFFF)


def test_zicsr_read_modify_write_and_warl_masks() -> None:
    """Verify CSRRC, minstret write-suppression rule, CLINT hi/lo reads, and read-only CSR traps."""
    cpu = RV32Oracle()
    cpu.regs[1] = 0x0F
    cpu.regs[2] = 0x03
    cpu.regs[3] = CLINT_BASE
    csr_prog = [
        enc_i(CSR_MSCRATCH, 1, 1, 0, 0x73),       # csrw mscratch, 0x0F
        enc_i(CSR_MSCRATCH, 2, 3, 10, 0x73),      # csrrc x10, mscratch, 0x03 -> x10=0x0F, mscratch=0x0C
        enc_i(CSR_MTVAL, 1, 1, 0, 0x73),          # csrw mtval, 0x0F
        enc_i(CSR_MTVAL, 0, 2, 11, 0x73),         # csrr x11, mtval
        enc_i(CSR_MIP, 0, 1, 0, 0x73),            # csrw mip, 0
        enc_i(CSR_MIP, 0, 2, 12, 0x73),           # csrr x12, mip
        enc_i(CSR_MCYCLE, 1, 1, 0, 0x73),         # csrw mcycle, 0x0F
        enc_i(CSR_MCYCLEH, 2, 1, 0, 0x73),        # csrw mcycleh, 0x03
        enc_i(CSR_MCYCLE, 0, 2, 13, 0x73),        # csrr x13, mcycle
        enc_i(CSR_MCYCLEH, 0, 2, 14, 0x73),       # csrr x14, mcycleh
        enc_i(CSR_MINSTRET, 1, 1, 0, 0x73),       # csrw minstret, 0x0F
        enc_i(CSR_MINSTRETH, 2, 1, 0, 0x73),      # csrw minstreth, 0x03
        enc_i(CSR_MINSTRET, 0, 2, 15, 0x73),      # csrr x15, minstret
        enc_i(CSR_MINSTRETH, 0, 2, 16, 0x73),     # csrr x16, minstreth
        enc_i(CSR_MHARTID, 0, 2, 17, 0x73),       # csrr x17, mhartid -> 0
        enc_s(CLINT_MTIME_LO, 1, 3, 2, 0x23),     # sw 0x0F -> mtime_lo
        enc_s(CLINT_MTIME_HI, 2, 3, 2, 0x23),     # sw 0x03 -> mtime_hi
        enc_i(CLINT_MTIME_LO, 3, 2, 18, 0x03),    # lw mtime_lo
        enc_i(CLINT_MTIME_HI, 3, 2, 19, 0x03),    # lw mtime_hi
        enc_i(CLINT_MTIMECMP_LO, 3, 2, 20, 0x03), # lw mtimecmp_lo
        enc_i(CLINT_MTIMECMP_HI, 3, 2, 21, 0x03), # lw mtimecmp_hi
        EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, csr_prog)
    cpu.run()
    assert cpu.regs[10] == 0x0F
    assert cpu.mscratch == 0x0C
    assert cpu.regs[11] == 0x0F
    assert cpu.regs[14] == 0x03
    assert cpu.regs[15] == 0x0F
    assert cpu.regs[16] == 0x03
    assert cpu.regs[17] == 0
    assert cpu.regs[18] >= 0x10
    assert cpu.regs[19] == 0x03

    # Read-only CSR write & unknown CSR read raise illegal instruction
    for bad_insn in [
        enc_i(CSR_MISA, 1, 1, 0, 0x73),
        enc_i(0x999, 0, 2, 1, 0x73),
    ]:
        cpu.reset()
        cpu.load_words(BOOT_ROM_BASE, [bad_insn])
        assert cpu.step().trap_cause == CAUSE_ILLEGAL_INSN


def test_uart0_console_tx_rx_and_bauddiv() -> None:
    """Verify UART0 byte TX buffer/callback, RX FIFO ordering, STATUS bits, and BAUDDIV clamping."""
    tx_seen: list[int] = []
    cpu = RV32Oracle(uart_tx_callback=tx_seen.append)
    cpu.push_uart_rx("OK")

    cpu.regs[1] = UART0_BASE
    cpu.regs[2] = ord("H")
    cpu.regs[3] = ord("i")
    cpu.regs[8] = 25
    prog = [
        enc_s(UART0_TXDATA, 2, 1, 0, 0x23),
        enc_s(UART0_TXDATA, 3, 1, 0, 0x23),
        enc_s(UART0_BAUDDIV, 8, 1, 2, 0x23),
        enc_i(UART0_BAUDDIV, 1, 2, 9, 0x03),
        enc_i(UART0_STATUS, 1, 2, 4, 0x03),
        enc_i(UART0_RXDATA, 1, 2, 5, 0x03),
        enc_i(UART0_RXDATA, 1, 2, 6, 0x03),
        enc_i(UART0_STATUS, 1, 2, 7, 0x03),
        EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.read_uart_tx(clear=True) == b"Hi"
    assert cpu.read_uart_tx() == b""
    assert bytes(tx_seen) == b"Hi"
    assert cpu.regs[9] == 25
    assert cpu.regs[4] & 0x4 == 0x4
    assert cpu.regs[5] == ord("O")
    assert cpu.regs[6] == ord("K")
    assert cpu.regs[7] & 0x4 == 0


def test_xapex_custom_mac_dot_product_and_saturation() -> None:
    """Verify Xapex dual-int16 SIMD MAC ops (mac, mac.clr, mac.set, mac.get) and +/- saturation."""
    cpu = RV32Oracle()
    cpu.regs[1] = 1000
    cpu.regs[2] = pack_i16(10, -20)
    cpu.regs[3] = pack_i16(5, 6)
    cpu.regs[4] = pack_i16(30, -40)
    cpu.regs[5] = pack_i16(-7, 8)
    cpu.regs[6] = pack_i16(32767, 32767)
    cpu.regs[7] = pack_i16(-32768, -32768)

    prog = [
        enc_mac(10, 1, 0, funct3=2),  # mac.set x10, x1      -> 1000
        enc_mac(11, 2, 3, funct3=0),  # mac     x11, x2, x3  -> 930
        enc_mac(12, 4, 5, funct3=0),  # mac     x12, x4, x5  -> 400
        enc_mac(13, 0, 0, funct3=3),  # mac.get x13          -> 400
        enc_mac(14, 6, 6, funct3=1),  # mac.clr x14, x6, x6
        enc_mac(15, 6, 6, funct3=0),  # mac     x15, x6, x6  -> INT32_MAX
        enc_mac(16, 6, 7, funct3=1),  # mac.clr x16, x6, x7
        enc_mac(17, 6, 7, funct3=0),  # mac     x17, x6, x7  -> INT32_MIN
        EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[10] == 1000
    assert cpu.regs[11] == 930
    assert cpu.regs[12] == 400
    assert cpu.regs[13] == 400
    assert cpu.regs[14] == u32(2 * 32767 * 32767)
    assert cpu.regs[15] == INT32_MAX
    assert cpu.regs[16] == u32(-2 * 32767 * 32768)
    assert cpu.regs[17] == u32(INT32_MIN)


def test_illegal_instructions_and_misaligned_pc_traps() -> None:
    """Verify illegal opcodes/funct fields and misaligned fetch/jump targets raise exact traps."""
    cpu = RV32Oracle()
    # Misaligned taken branch, misaligned JAL, misaligned JALR, and unmapped PC
    for insn, reg1, expected in [
        (enc_b(2, 0, 0, 0), 0, CAUSE_INSN_MISALIGNED),
        (enc_j(2, 1), 0, CAUSE_INSN_MISALIGNED),
        (enc_i(2, 1, 0, 0, 0x67), BRAM_BASE, CAUSE_INSN_MISALIGNED),
        (enc_i(0, 1, 1, 0, 0x67), BRAM_BASE, CAUSE_ILLEGAL_INSN),  # JALR bad funct3
        (enc_r(0x7F, 0, 0, 0, 1, 0x33), 0, CAUSE_ILLEGAL_INSN),    # OP bad funct7
        (enc_r(0x00, 0, 0, 7, 1, 0x0B), 0, CAUSE_ILLEGAL_INSN),    # MAC bad funct3
        (enc_r(0x01, 0, 0, 0, 1, 0x0B), 0, CAUSE_ILLEGAL_INSN),    # MAC bad funct7
        (0xFFFF_FFFF, 0, CAUSE_ILLEGAL_INSN),                      # unknown opcode
    ]:
        cpu.reset()
        cpu.regs[1] = reg1
        cpu.load_words(BOOT_ROM_BASE, [insn])
        assert cpu.step().trap_cause == expected

    cpu.reset(reset_pc=BOOT_ROM_BASE + 2)
    assert cpu.step().trap_cause == CAUSE_INSN_MISALIGNED
    cpu.reset(reset_pc=0x7000_0000)
    assert cpu.step().trap_cause == CAUSE_INSN_ACCESS_FAULT

    # Cover illegal funct3/funct7 across BRANCH, LOAD, STORE, OP-IMM, OP, FENCE, and SYSTEM
    illegal_cases = [
        enc_b(4, 0, 0, 2),                # BRANCH invalid funct3
        enc_i(0, 1, 3, 2, 0x03),           # LOAD invalid funct3
        enc_s(0, 2, 1, 3, 0x23),           # STORE invalid funct3
        enc_i(0x020, 0, 1, 2, 0x13),       # SLLI invalid funct7
        enc_i(0x020, 0, 5, 2, 0x13),       # SRLI/SRAI invalid funct7
        enc_r(0x20, 0, 0, 1, 2, 0x33),     # OP invalid funct3 under funct7=0x20
        enc_i(0, 0, 2, 0, 0x0F),           # FENCE invalid funct3
        0x7FF0_0073,                       # SYSTEM funct3=0 unknown imm
        enc_i(CSR_MISA, 0, 4, 2, 0x73),    # SYSTEM invalid funct3=4
    ]
    for insn in illegal_cases:
        cpu.reset(reset_pc=BOOT_ROM_BASE)
        cpu.regs[1] = BRAM_BASE
        cpu.load_words(BOOT_ROM_BASE, [insn])
        assert cpu.step().trap_cause == CAUSE_ILLEGAL_INSN


def test_interrupt_priority_csr_variants_and_mmio_bounds() -> None:
    """Verify MEIP > MSIP > MTIP priority, Zicsr immediate ops, WARL edges, and CLINT/UART0 bounds."""
    cpu = RV32Oracle()
    # 1. MEIP > MSIP > MTIP priority ordering when all three are pending & enabled
    cpu.mstatus = MSTATUS_MIE_BIT
    cpu.mie = MIE_MEIE_BIT | MIE_MSIE_BIT | MIE_MTIE_BIT
    cpu.mip_sw_ext = MIE_MEIE_BIT | MIE_MSIE_BIT
    cpu.mtimecmp = 0
    assert cpu.step().trap_cause == CAUSE_INT_M_EXT

    cpu.reset()
    cpu.mstatus = MSTATUS_MIE_BIT
    cpu.mie = MIE_MSIE_BIT | MIE_MTIE_BIT
    cpu.mip_sw_ext = MIE_MSIE_BIT
    cpu.mtimecmp = 0
    assert cpu.step().trap_cause == CAUSE_INT_M_SW

    # 2. mtvec WARL snap (mode 3 -> 0), mcause R/W, Zicsr imm ops, and uimm=0 CSRRSI on MISA
    cpu.reset()
    cpu.regs[1] = BRAM_BASE | 3
    cpu.regs[2] = 0x55
    prog = [
        enc_i(CSR_MTVEC, 1, 1, 0, 0x73),       # csrw mtvec, BRAM|3 -> mode snaps to 0
        enc_i(CSR_MCAUSE, 2, 1, 0, 0x73),      # csrw mcause, 0x55
        enc_i(CSR_MCAUSE, 0, 2, 7, 0x73),      # csrr x7, mcause -> 0x55
        enc_i(CSR_MSCRATCH, 0x0A, 5, 3, 0x73), # csrrwi x3, mscratch, 0x0A
        enc_i(CSR_MSCRATCH, 0x05, 6, 4, 0x73), # csrrsi x4, mscratch, 0x05 -> 0x0F
        enc_i(CSR_MSCRATCH, 0x03, 7, 5, 0x73), # csrrci x5, mscratch, 0x03 -> 0x0C
        enc_i(CSR_MISA, 0, 6, 6, 0x73),        # csrrsi x6, misa, 0 (read-only uimm=0 succeeds)
        EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()
    assert cpu.mtvec == BRAM_BASE
    assert cpu.regs[7] == 0x55
    assert cpu.regs[4] == 0x0A
    assert cpu.regs[5] == 0x0F
    assert cpu.mscratch == 0x0C
    assert cpu.regs[6] == cpu.misa

    # 3. CLINT/UART0 unused register offsets, empty RX FIFO read, and misaligned MMIO traps
    assert cpu.read_u32(CLINT_BASE + 0x20) == 0
    cpu.write_u32(CLINT_BASE + 0x20, 0x1234)
    assert cpu.read_u32(UART0_BASE + 0x20) == 0
    cpu.write_u32(UART0_BASE + 0x20, 0x1234)
    assert cpu.read_u32(UART0_BASE + UART0_RXDATA) == 0
    for bad_addr, width in [
        (CLINT_BASE + 1, 4),
        (CLINT_BASE, 1),
        (UART0_BASE + 1, 1),
        (UART0_BASE, 2),
    ]:
        with pytest.raises(MemoryAccessFault):
            cpu.bus_read(bad_addr, width)
        with pytest.raises(MemoryAccessFault):
            cpu.bus_write(bad_addr, width, 0)

    # 4. Signed (-32768)^2 * 2 positive MAC saturation edge case
    cpu.reset()
    cpu.regs[1] = pack_i16(-32768, -32768)
    cpu.load_words(BOOT_ROM_BASE, [enc_mac(10, 1, 1, funct3=1), EBREAK])
    cpu.run()
    assert cpu.regs[10] == INT32_MAX
