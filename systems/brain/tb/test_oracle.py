"""Unit tests for the golden RV32IM + Zicsr + CLINT + UART0 + Xapex MAC emulator."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

BRAIN_SIM_DIR = Path(__file__).resolve().parents[1] / "sim"
if str(BRAIN_SIM_DIR) not in sys.path:
    sys.path.insert(0, str(BRAIN_SIM_DIR))

from rv32_oracle import (  # noqa: E402
    BOOT_ROM_BASE,
    BRAM_BASE,
    CAUSE_ECALL_M,
    CAUSE_ILLEGAL_INSN,
    CAUSE_INSN_MISALIGNED,
    CAUSE_INT_M_TIMER,
    CAUSE_LOAD_MISALIGNED,
    CAUSE_STORE_ACCESS_FAULT,
    CAUSE_STORE_MISALIGNED,
    CLINT_BASE,
    CLINT_MTIMECMP_HI,
    CLINT_MTIMECMP_LO,
    CLINT_MTIME_LO,
    CSR_MCAUSE,
    CSR_MCYCLE,
    CSR_MEPC,
    CSR_MIE,
    CSR_MINSTRET,
    CSR_MISA,
    CSR_MSCRATCH,
    CSR_MSTATUS,
    CSR_MTVAL,
    CSR_MTVEC,
    INT32_MAX,
    INT32_MIN,
    MIE_MTIE_BIT,
    MSTATUS_MIE_BIT,
    SDRAM_BASE,
    UART0_BASE,
    UART0_RXDATA,
    UART0_STATUS,
    UART0_TXDATA,
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


def pack_i16(lo: int, hi: int) -> int:
    return ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)


def test_rv32i_arithmetic_shifts_and_x0() -> None:
    cpu = RV32Oracle()
    prog = [
        enc_i(10, 0, 0, 0, 0x13),          # addi x0, x0, 10  (must keep x0 == 0)
        enc_i(-5, 0, 0, 1, 0x13),          # addi x1, x0, -5  (0xFFFF_FFFB)
        enc_i(3, 0, 0, 2, 0x13),           # addi x2, x0, 3
        enc_r(0x00, 2, 1, 0, 3, 0x33),     # add  x3, x1, x2  (-2)
        enc_r(0x20, 2, 1, 0, 4, 0x33),     # sub  x4, x1, x2  (-8)
        enc_r(0x00, 2, 1, 2, 5, 0x33),     # slt  x5, x1, x2  (-5 < 3 -> 1)
        enc_r(0x00, 2, 1, 3, 6, 0x33),     # sltu x6, x1, x2  (0xFFFFFFFB < 3 -> 0)
        enc_i(0x400 | 1, 1, 5, 7, 0x13),   # srai x7, x1, 1   (-5 >> 1 == -3)
        enc_i(1, 1, 5, 8, 0x13),           # srli x8, x1, 1   (0x7FFF_FFFD)
        enc_u(0x1234_5000, 9, 0x37),       # lui  x9, 0x12345
        enc_u(0x0000_1000, 10, 0x17),      # auipc x10, 0x1000 (PC = 40 -> 0x1028)
        EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[0] == 0
    assert cpu.regs[1] == u32(-5)
    assert cpu.regs[3] == u32(-2)
    assert cpu.regs[4] == u32(-8)
    assert cpu.regs[5] == 1
    assert cpu.regs[6] == 0
    assert cpu.regs[7] == u32(-3)
    assert cpu.regs[8] == 0x7FFF_FFFD
    assert cpu.regs[9] == 0x1234_5000
    assert cpu.regs[10] == BOOT_ROM_BASE + 10 * 4 + 0x1000


def test_rv32m_multiply_and_division_edge_cases() -> None:
    cpu = RV32Oracle()
    cpu.regs[1] = u32(-7)
    cpu.regs[2] = 3
    cpu.regs[3] = 0x8000_0000  # INT32_MIN
    cpu.regs[4] = u32(-1)
    cpu.regs[5] = 0

    prog = [
        enc_r(0x01, 2, 1, 0, 10, 0x33),  # mul    x10, x1, x2   -> -21
        enc_r(0x01, 2, 1, 1, 11, 0x33),  # mulh   x11, x1, x2   -> -1
        enc_r(0x01, 2, 1, 2, 12, 0x33),  # mulhsu x12, x1, x2   -> -1
        enc_r(0x01, 2, 1, 3, 13, 0x33),  # mulhu  x13, x1, x2   -> (0xFFFFFFF9 * 3) >> 32 == 2
        enc_r(0x01, 2, 1, 4, 14, 0x33),  # div    x14, x1, x2   -> -2 (trunc toward 0)
        enc_r(0x01, 2, 1, 6, 15, 0x33),  # rem    x15, x1, x2   -> -1 (sign of dividend)
        enc_r(0x01, 4, 3, 4, 16, 0x33),  # div    x16, INT_MIN, -1 -> INT_MIN
        enc_r(0x01, 4, 3, 6, 17, 0x33),  # rem    x17, INT_MIN, -1 -> 0
        enc_r(0x01, 5, 1, 4, 18, 0x33),  # div    x18, -7, 0       -> -1
        enc_r(0x01, 5, 1, 5, 19, 0x33),  # divu   x19, -7, 0       -> 0xFFFF_FFFF
        enc_r(0x01, 5, 1, 6, 20, 0x33),  # rem    x20, -7, 0       -> -7
        enc_r(0x01, 5, 1, 7, 21, 0x33),  # remu   x21, -7, 0       -> 0xFFFF_FFF9
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


def test_branches_and_jumps_sum_loop() -> None:
    cpu = RV32Oracle()
    # Compute sum(1..5) = 15 via loop, plus JAL/JALR subroutine call adding 100
    prog = [
        enc_i(0, 0, 0, 1, 0x13),       # 0x00: addi x1, x0, 0     (sum)
        enc_i(1, 0, 0, 2, 0x13),       # 0x04: addi x2, x0, 1     (i)
        enc_i(6, 0, 0, 3, 0x13),       # 0x08: addi x3, x0, 6     (limit)
        # loop (0x0C):
        enc_r(0x00, 2, 1, 0, 1, 0x33), # 0x0C: add  x1, x1, x2
        enc_i(1, 2, 0, 2, 0x13),       # 0x10: addi x2, x2, 1
        enc_b(-8, 3, 2, 4),            # 0x14: blt  x2, x3, -8    (-> 0x0C)
        enc_j(8, 5),                   # 0x18: jal  x5, +8        (-> 0x20, x5=0x1C)
        EBREAK,                        # 0x1C: halt after return
        # subroutine (0x20):
        enc_i(100, 1, 0, 1, 0x13),     # 0x20: addi x1, x1, 100
        enc_i(0, 5, 0, 0, 0x67),       # 0x24: jalr x0, 0(x5)     (return -> 0x1C)
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[1] == 115
    assert cpu.regs[5] == BOOT_ROM_BASE + 0x1C


def test_memory_loads_stores_and_alignment_traps() -> None:
    cpu = RV32Oracle()
    cpu.regs[1] = BRAM_BASE
    cpu.regs[2] = 0x1122_80FF  # byte0 = 0xFF (-1 signed), half0 = 0x80FF (-32513 signed)
    cpu.regs[3] = SDRAM_BASE + 0x1000

    prog = [
        enc_s(0, 2, 1, 2, 0x23),  # sw  x2, 0(x1)
        enc_i(0, 1, 0, 4, 0x03),  # lb  x4, 0(x1) -> 0xFFFF_FFFF
        enc_i(0, 1, 4, 5, 0x03),  # lbu x5, 0(x1) -> 0x0000_00FF
        enc_i(0, 1, 1, 6, 0x03),  # lh  x6, 0(x1) -> 0xFFFF_80FF
        enc_i(0, 1, 5, 7, 0x03),  # lhu x7, 0(x1) -> 0x0000_80FF
        enc_s(2, 2, 3, 1, 0x23),  # sh  x2, 2(x3) (aligned to 2 bytes in SDRAM)
        enc_i(2, 3, 5, 8, 0x03),  # lhu x8, 2(x3) -> 0x80FF
        enc_s(1, 2, 3, 0, 0x23),  # sb  x2, 1(x3) -> overwrites byte 1 of SDRAM+0x1000
        enc_i(0, 3, 2, 9, 0x03),  # lw  x9, 0(x3) -> 0x80FF_FF00
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

    # Verify misaligned load, misaligned store, and ROM write protection raise traps
    cpu.reset()
    cpu.regs[1] = BRAM_BASE + 1
    cpu.load_words(BOOT_ROM_BASE, [enc_i(0, 1, 2, 2, 0x03)])  # lw x2, 0(BRAM+1)
    tr = cpu.step()
    assert tr.trap_cause == CAUSE_LOAD_MISALIGNED
    assert cpu.mtval == BRAM_BASE + 1

    cpu.reset()
    cpu.regs[1] = BRAM_BASE + 2
    cpu.load_words(BOOT_ROM_BASE, [enc_s(0, 2, 1, 2, 0x23)])  # sw x2, 0(BRAM+2)
    tr = cpu.step()
    assert tr.trap_cause == CAUSE_STORE_MISALIGNED

    cpu.reset()
    cpu.regs[1] = BOOT_ROM_BASE
    cpu.load_words(BOOT_ROM_BASE, [enc_s(0, 2, 1, 2, 0x23)])  # sw into Boot ROM
    tr = cpu.step()
    assert tr.trap_cause == CAUSE_STORE_ACCESS_FAULT


def test_zicsr_ecall_trap_and_clint_timer_interrupt() -> None:
    cpu = RV32Oracle()
    # Trap handler placed at BRAM_BASE (0x1000_0000):
    #   - If mcause == CAUSE_ECALL_M: increment mscratch, advance mepc by 4, mret
    #   - If mcause == CAUSE_INT_M_TIMER: bump mtimecmp far into future, set x20 = 0xCAFE, mret
    handler_addr = BRAM_BASE
    cpu.regs[21] = CAUSE_INT_M_TIMER
    cpu.regs[22] = CLINT_BASE
    cpu.regs[23] = 0xFFFF_FFFF

    handler = [
        enc_i(CSR_MCAUSE, 0, 2, 25, 0x73),    # csrr  x25, mcause
        enc_b(20, 21, 25, 0),                 # beq   x25, x21, +20 (timer branch -> +5 insns)
        # ECALL branch:
        enc_i(CSR_MSCRATCH, 0, 2, 26, 0x73),  # csrr  x26, mscratch
        enc_i(1, 26, 0, 26, 0x13),            # addi  x26, x26, 1
        enc_i(CSR_MSCRATCH, 26, 1, 0, 0x73),  # csrw  mscratch, x26
        enc_i(CSR_MEPC, 0, 2, 26, 0x73),      # csrr  x26, mepc
        enc_i(4, 26, 0, 26, 0x13),            # addi  x26, x26, 4
        enc_i(CSR_MEPC, 26, 1, 0, 0x73),      # csrw  mepc, x26
        MRET,
        # Timer interrupt branch (offset +20 from beq at idx 1 -> idx 6? Wait: 1+5=6!):
    ]
    # Recompute exact branch offset cleanly:
    # idx 0: csrr x25, mcause
    # idx 1: beq  x25, x21, timer_isr (idx 9 -> offset = (9 - 1)*4 = 32)
    # idx 2..7: ecall path (6 insns)
    # idx 8: mret
    # idx 9: timer_isr
    handler[1] = enc_b(32, 21, 25, 0)
    handler.extend([
        enc_s(CLINT_MTIMECMP_LO, 23, 22, 2, 0x23),  # sw x23, mtimecmp_lo(CLINT)
        enc_s(CLINT_MTIMECMP_HI, 23, 22, 2, 0x23),  # sw x23, mtimecmp_hi(CLINT)
        enc_i(0x123, 0, 0, 20, 0x13),               # addi x20, x0, 0x123
        MRET,
    ])
    cpu.load_words(handler_addr, handler)

    # Main program at BOOT_ROM_BASE:
    #   mtvec = BRAM_BASE
    #   mtimecmp = 12
    #   mie = MTIE, mstatus = MIE
    #   ecall
    #   loop until x20 == 0x123, then ebreak
    cpu.regs[1] = handler_addr
    cpu.regs[2] = CLINT_BASE
    cpu.regs[3] = 15  # mtimecmp_lo
    cpu.regs[4] = MIE_MTIE_BIT
    cpu.regs[5] = MSTATUS_MIE_BIT
    cpu.regs[6] = 0x123

    main_prog = [
        enc_i(CSR_MTVEC, 1, 1, 0, 0x73),           # 0x00: csrw mtvec, x1
        enc_s(CLINT_MTIMECMP_HI, 0, 2, 2, 0x23),   # 0x04: sw x0, mtimecmp_hi
        enc_s(CLINT_MTIMECMP_LO, 3, 2, 2, 0x23),   # 0x08: sw x3, mtimecmp_lo (15)
        enc_i(CSR_MIE, 4, 1, 0, 0x73),             # 0x0C: csrw mie, x4
        enc_i(CSR_MSTATUS, 5, 1, 0, 0x73),         # 0x10: csrw mstatus, x5
        ECALL,                                     # 0x14: ecall -> increments mscratch to 1
        # spin (0x18):
        enc_b(-4, 6, 20, 1),                       # 0x18: bne x20, x6, -4 (wait for timer IRQ)
        EBREAK,                                    # 0x1C: done
    ]
    cpu.load_words(BOOT_ROM_BASE, main_prog)
    traces = cpu.run(max_steps=200)

    assert cpu.halted
    assert cpu.mscratch == 1
    assert cpu.regs[20] == 0x123
    assert any(t.trap_cause == CAUSE_ECALL_M for t in traces)
    assert any(t.interrupt and t.trap_cause == CAUSE_INT_M_TIMER for t in traces)
    assert cpu.mcycle > cpu.minstret  # traps do not increment minstret

    # Verify writing to read-only misa CSR triggers illegal instruction
    cpu.reset()
    cpu.load_words(BOOT_ROM_BASE, [enc_i(CSR_MISA, 1, 1, 0, 0x73)])
    tr = cpu.step()
    assert tr.trap_cause == CAUSE_ILLEGAL_INSN


def test_uart0_console_tx_rx() -> None:
    tx_seen: list[int] = []
    cpu = RV32Oracle(uart_tx_callback=tx_seen.append)
    cpu.push_uart_rx("OK")

    cpu.regs[1] = UART0_BASE
    cpu.regs[2] = ord("H")
    cpu.regs[3] = ord("i")
    prog = [
        enc_s(UART0_TXDATA, 2, 1, 0, 0x23),  # sb 'H'
        enc_s(UART0_TXDATA, 3, 1, 0, 0x23),  # sb 'i'
        enc_i(UART0_STATUS, 1, 2, 4, 0x03),  # lw x4, STATUS -> rx_valid bit 2 == 1
        enc_i(UART0_RXDATA, 1, 2, 5, 0x03),  # lw x5, RXDATA -> 'O'
        enc_i(UART0_RXDATA, 1, 2, 6, 0x03),  # lw x6, RXDATA -> 'K'
        enc_i(UART0_STATUS, 1, 2, 7, 0x03),  # lw x7, STATUS -> rx_valid bit 2 == 0
        EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.read_uart_tx() == b"Hi"
    assert bytes(tx_seen) == b"Hi"
    assert cpu.regs[4] & 0x4 == 0x4
    assert cpu.regs[5] == ord("O")
    assert cpu.regs[6] == ord("K")
    assert cpu.regs[7] & 0x4 == 0


def test_xapex_custom_mac_dot_product_and_saturation() -> None:
    cpu = RV32Oracle()
    # Dot product of [10, -20, 30, -40] and [5, 6, -7, 8] with bias 1000:
    # 1000 + (10*5 + (-20)*6) + (30*(-7) + (-40)*8) = 1000 - 70 - 530 = 400
    cpu.regs[1] = 1000
    cpu.regs[2] = pack_i16(10, -20)
    cpu.regs[3] = pack_i16(5, 6)
    cpu.regs[4] = pack_i16(30, -40)
    cpu.regs[5] = pack_i16(-7, 8)
    # Saturation test inputs: 32767 * 32767 + 32767 * 32767 = 2,147,352,578 (~2^31 - 131070)
    # Two accumulations overflow INT32_MAX and must clamp cleanly to INT32_MAX.
    cpu.regs[6] = pack_i16(32767, 32767)
    cpu.regs[7] = pack_i16(-32768, -32768)

    prog = [
        enc_mac(10, 1, 0, funct3=2),  # mac.set x10, x1      -> acc = 1000
        enc_mac(11, 2, 3, funct3=0),  # mac     x11, x2, x3  -> acc = 930
        enc_mac(12, 4, 5, funct3=0),  # mac     x12, x4, x5  -> acc = 400
        enc_mac(13, 0, 0, funct3=3),  # mac.get x13          -> 400
        enc_mac(14, 6, 6, funct3=1),  # mac.clr x14, x6, x6  -> fresh acc = 2 * 32767^2
        enc_mac(15, 6, 6, funct3=0),  # mac     x15, x6, x6  -> saturates at INT32_MAX
        enc_mac(16, 6, 7, funct3=1),  # mac.clr x16, x6, x7  -> -2 * 32767 * 32768
        enc_mac(17, 6, 7, funct3=0),  # mac     x17, x6, x7  -> saturates at INT32_MIN
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


def test_misaligned_taken_branch_raises_exception() -> None:
    cpu = RV32Oracle()
    cpu.load_words(BOOT_ROM_BASE, [enc_b(2, 0, 0, 0)])  # beq x0, x0, +2 (misaligned target)
    tr = cpu.step()
    assert tr.trap_cause == CAUSE_INSN_MISALIGNED
    assert cpu.mepc == BOOT_ROM_BASE
    assert cpu.mtval == BOOT_ROM_BASE + 2
