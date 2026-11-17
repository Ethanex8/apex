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
    BOOT_ROM_SIZE,
    BRAM_BASE,
    BRAM_SIZE,
    CAUSE_BREAKPOINT,
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
    CLINT_SIZE,
    CSR_MARCHID,
    CSR_MCAUSE,
    CSR_MCYCLE,
    CSR_MCYCLEH,
    CSR_MEPC,
    CSR_MHARTID,
    CSR_MIE,
    CSR_MIMPID,
    CSR_MINSTRET,
    CSR_MINSTRETH,
    CSR_MIP,
    CSR_MISA,
    CSR_MSCRATCH,
    CSR_MSTATUS,
    CSR_MTVAL,
    CSR_MTVEC,
    CSR_MVENDORID,
    F3_ADD_SUB,
    F3_AND,
    F3_BEQ,
    F3_BGE,
    F3_BGEU,
    F3_BLT,
    F3_BLTU,
    F3_BNE,
    F3_CSRRC,
    F3_CSRRCI,
    F3_CSRRS,
    F3_CSRRSI,
    F3_CSRRW,
    F3_CSRRWI,
    F3_DIV,
    F3_DIVU,
    F3_JALR,
    F3_LB,
    F3_LBU,
    F3_LH,
    F3_LHU,
    F3_LW,
    F3_MUL,
    F3_MULH,
    F3_MULHSU,
    F3_MULHU,
    F3_OR,
    F3_REM,
    F3_REMU,
    F3_SB,
    F3_SH,
    F3_SLL,
    F3_SLT,
    F3_SLTU,
    F3_SRL_SRA,
    F3_SW,
    F3_XOR,
    F7_ALT,
    F7_BASE,
    F7_MULDIV,
    FUNCT7_MASK,
    INSN_EBREAK,
    INSN_ECALL,
    INSN_FENCE,
    INSN_FENCE_I,
    INSN_MRET,
    INSN_SIZE_BYTES,
    INSN_WFI,
    INT32_MAX,
    INT32_MIN,
    MAC_F3_ACC,
    MAC_F3_CLR,
    MAC_F3_GET,
    MAC_F3_SET,
    MASK64,
    MCAUSE_CODE_MASK,
    MIE_MEIE_BIT,
    MIE_MSIE_BIT,
    MIE_MTIE_BIT,
    MISA_RV32IMX,
    MMIO_STUB_BASE,
    MMIO_STUB_END,
    MSTATUS_MIE_BIT,
    MSTATUS_MPIE_BIT,
    MSTATUS_MPP_M,
    MTVEC_MODE_MASK,
    MTVEC_MODE_VECTORED,
    OPCODE_AUIPC,
    OPCODE_BRANCH,
    OPCODE_CUSTOM0,
    OPCODE_JAL,
    OPCODE_JALR,
    OPCODE_LOAD,
    OPCODE_LUI,
    OPCODE_MISC_MEM,
    OPCODE_OP,
    OPCODE_OP_IMM,
    OPCODE_STORE,
    OPCODE_SYSTEM,
    QSPI_BASE,
    QSPI_SIZE,
    REG_MASK,
    SDRAM_BASE,
    SDRAM_SIZE,
    UART0_BASE,
    UART0_BAUDDIV,
    UART0_RXDATA,
    UART0_SIZE,
    UART0_STATUS,
    UART0_STATUS_RX_VALID,
    UART0_TXDATA,
    UINT32_MAX,
    WORD_ALIGN_MASK,
    MemoryAccessFault,
    RV32Oracle,
    SparseMemory,
    enc_b,
    enc_i,
    enc_j,
    enc_mac,
    enc_r,
    enc_s,
    enc_u,
    u32,
)

UNIMPLEMENTED_CSR = 0x999
UNMAPPED_BUS_ADDR = 0x7000_0000
UNMAPPED_MMIO_OFFSET = 0x20
INVALID_INSN_WORD = 0xFFFF_FFFF
INVALID_JALR_FUNCT3 = 1
INVALID_BRANCH_FUNCT3 = 2
INVALID_MISC_MEM_FUNCT3 = 2
INVALID_FUNCT3 = 3
INVALID_MAC_FUNCT3 = 7
RESERVED_ZICSR_FUNCT3 = 4
INVALID_FUNCT7 = 0x7F
SYSTEM_UNKNOWN_PRIV = 0x7FF0_0073


def pack_i16(lo: int, hi: int) -> int:
    """Pack two signed 16-bit integers into one 32-bit word `[hi:lo]`."""
    return ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)


def _alu_i(funct3: int, rd: int, rs1: int, imm: int) -> int:
    """Encode an `OP-IMM` instruction (`ADDI`/`SLTI`/`SLTIU`/`XORI`/`ORI`/`ANDI`)."""
    return enc_i(imm, rs1, funct3, rd, OPCODE_OP_IMM)


def _shift_i(funct3: int, rd: int, rs1: int, shamt: int, funct7: int = F7_BASE) -> int:
    """Encode a shift-immediate instruction (`SLLI`/`SRLI`/`SRAI`) with `funct7` mode bits."""
    return enc_i(((funct7 & FUNCT7_MASK) << 5) | (shamt & REG_MASK), rs1, funct3, rd, OPCODE_OP_IMM)


def _alu_r(funct3: int, rd: int, rs1: int, rs2: int, funct7: int = F7_BASE) -> int:
    """Encode an RV32I register-register ALU instruction (`ADD`/`SUB`/`SLL`/etc.)."""
    return enc_r(funct7, rs2, rs1, funct3, rd, OPCODE_OP)


def _muldiv(funct3: int, rd: int, rs1: int, rs2: int) -> int:
    """Encode an RV32M multiply/divide instruction (`MUL`/`MULH*`/`DIV*`/`REM*`)."""
    return enc_r(F7_MULDIV, rs2, rs1, funct3, rd, OPCODE_OP)


def _load(funct3: int, rd: int, rs1: int, offset: int) -> int:
    """Encode a memory load instruction (`LB`/`LH`/`LW`/`LBU`/`LHU`)."""
    return enc_i(offset, rs1, funct3, rd, OPCODE_LOAD)


def _store(funct3: int, rs2: int, rs1: int, offset: int) -> int:
    """Encode a memory store instruction (`SB`/`SH`/`SW`)."""
    return enc_s(offset, rs2, rs1, funct3, OPCODE_STORE)


def _branch(funct3: int, rs1: int, rs2: int, offset: int) -> int:
    """Encode a B-type conditional branch (`BEQ`/`BNE`/`BLT`/`BGE`/`BLTU`/`BGEU`)."""
    return enc_b(offset, rs2, rs1, funct3, OPCODE_BRANCH)


def _jal(rd: int, offset: int) -> int:
    """Encode a J-type direct jump-and-link (`JAL`) instruction."""
    return enc_j(offset, rd, OPCODE_JAL)


def _jalr(rd: int, rs1: int, offset: int) -> int:
    """Encode an I-type indirect jump-and-link (`JALR`) instruction."""
    return enc_i(offset, rs1, F3_JALR, rd, OPCODE_JALR)


def _lui(rd: int, upper_bits: int) -> int:
    """Encode a `LUI` instruction with `Bits 31..12` pre-aligned."""
    return enc_u(upper_bits, rd, OPCODE_LUI)


def _auipc(rd: int, upper_bits: int) -> int:
    """Encode an `AUIPC` instruction with `Bits 31..12` pre-aligned."""
    return enc_u(upper_bits, rd, OPCODE_AUIPC)


def _csr_reg(funct3: int, rd: int, csr_addr: int, rs1: int) -> int:
    """Encode a register-operand `Zicsr` instruction (`CSRRW`/`CSRRS`/`CSRRC`)."""
    return enc_i(csr_addr, rs1, funct3, rd, OPCODE_SYSTEM)


def _csr_imm(funct3: int, rd: int, csr_addr: int, uimm: int) -> int:
    """Encode an immediate-operand `Zicsr` instruction (`CSRRWI`/`CSRRSI`/`CSRRCI`)."""
    return enc_i(csr_addr, uimm, funct3, rd, OPCODE_SYSTEM)


def _mac_op(funct3: int, rd: int, rs1: int = 0, rs2: int = 0) -> int:
    """Encode an Xapex `custom-0` dual-int16 MAC instruction."""
    return enc_mac(rd, rs1, rs2, funct3=funct3)


def test_rv32i_arithmetic_shifts_and_x0() -> None:
    """Verify RV32I ALU/immediate ops, barrel-shift sign rules, LUI/AUIPC, and hardwired x0."""
    cpu = RV32Oracle()
    r_neg5, r_three, r_mask = 1, 2, 3
    r_add, r_sub, r_slt, r_sltu = 4, 5, 6, 7
    r_srai, r_srli, r_slli = 8, 9, 10
    r_slti, r_sltiu, r_xori, r_ori, r_andi = 11, 12, 13, 14, 15
    r_sll, r_xor, r_srl, r_or, r_and, r_sra = 16, 17, 18, 19, 20, 21
    r_lui, r_auipc = 22, 23
    cpu.regs[r_mask] = 0x0000_00FF

    auipc_insn = _auipc(rd=r_auipc, upper_bits=0x0000_1000)
    prog = [
        _alu_i(F3_ADD_SUB, rd=0, rs1=0, imm=10),              # addi x0 discards write
        _alu_i(F3_ADD_SUB, rd=r_neg5, rs1=0, imm=-5),         # r_neg5 = -5
        _alu_i(F3_ADD_SUB, rd=r_three, rs1=0, imm=3),         # r_three = 3
        _alu_r(F3_ADD_SUB, rd=r_add, rs1=r_neg5, rs2=r_three),
        _alu_r(F3_ADD_SUB, rd=r_sub, rs1=r_neg5, rs2=r_three, funct7=F7_ALT),
        _alu_r(F3_SLT, rd=r_slt, rs1=r_neg5, rs2=r_three),
        _alu_r(F3_SLTU, rd=r_sltu, rs1=r_neg5, rs2=r_three),
        _shift_i(F3_SRL_SRA, rd=r_srai, rs1=r_neg5, shamt=1, funct7=F7_ALT),
        _shift_i(F3_SRL_SRA, rd=r_srli, rs1=r_neg5, shamt=1),
        _shift_i(F3_SLL, rd=r_slli, rs1=r_three, shamt=2),    # 3 << 2 = 12
        _alu_i(F3_SLT, rd=r_slti, rs1=r_neg5, imm=-1),
        _alu_i(F3_SLTU, rd=r_sltiu, rs1=r_neg5, imm=1),
        _alu_i(F3_XOR, rd=r_xori, rs1=r_mask, imm=0x0F),
        _alu_i(F3_OR, rd=r_ori, rs1=r_mask, imm=0x100),
        _alu_i(F3_AND, rd=r_andi, rs1=r_mask, imm=0x0F),
        _alu_r(F3_SLL, rd=r_sll, rs1=r_slli, rs2=r_three),    # 12 << 3 = 96
        _alu_r(F3_XOR, rd=r_xor, rs1=r_mask, rs2=r_three),
        _alu_r(F3_SRL_SRA, rd=r_srl, rs1=r_slli, rs2=r_three),  # 12 >> 3 = 1
        _alu_r(F3_OR, rd=r_or, rs1=r_mask, rs2=r_three),
        _alu_r(F3_AND, rd=r_and, rs1=r_mask, rs2=r_three),
        _alu_r(F3_SRL_SRA, rd=r_sra, rs1=r_neg5, rs2=r_three, funct7=F7_ALT),
        _lui(rd=r_lui, upper_bits=0x1234_5000),
        auipc_insn,
        INSN_EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[0] == 0
    assert cpu.regs[r_add] == u32(-2)
    assert cpu.regs[r_sub] == u32(-8)
    assert cpu.regs[r_slt] == 1
    assert cpu.regs[r_sltu] == 0
    assert cpu.regs[r_srai] == u32(-3)
    assert cpu.regs[r_srli] == 0x7FFF_FFFD
    assert cpu.regs[r_slli] == 12
    assert cpu.regs[r_slti] == 1
    assert cpu.regs[r_sltiu] == 0
    assert cpu.regs[r_xori] == 0xF0
    assert cpu.regs[r_ori] == 0x1FF
    assert cpu.regs[r_andi] == 0x0F
    assert cpu.regs[r_sll] == 96
    assert cpu.regs[r_xor] == 0xFC
    assert cpu.regs[r_srl] == 1
    assert cpu.regs[r_or] == 0xFF
    assert cpu.regs[r_and] == 0x03
    assert cpu.regs[r_sra] == u32(-1)
    assert cpu.regs[r_lui] == 0x1234_5000
    assert cpu.regs[r_auipc] == BOOT_ROM_BASE + prog.index(auipc_insn) * INSN_SIZE_BYTES + 0x1000


def test_alu_wraparound_large_shifts_and_sltiu_sign_extend() -> None:
    """Verify 32-bit modulo arithmetic wrap, barrel-shift masking for rs2 >= 32, and SLTIU -1."""
    cpu = RV32Oracle()
    r_max, r_seven, r_sh35, r_neg16, r_msb = 1, 2, 3, 4, 5
    r_addi_w, r_add_w, r_sub_w, r_sll, r_srl, r_sra, r_sltiu = 10, 11, 12, 13, 14, 15, 16
    r_auipc_wrap = 17
    cpu.regs[r_max] = UINT32_MAX
    cpu.regs[r_seven] = 7
    cpu.regs[r_sh35] = 35                                # low 5 bits = 35 & 31 = 3
    cpu.regs[r_neg16] = u32(-16)
    cpu.regs[r_msb] = 0x8000_0000
    cpu.load_words(
        BOOT_ROM_BASE,
        [
            _alu_i(F3_ADD_SUB, rd=r_addi_w, rs1=r_max, imm=1),
            _alu_r(F3_ADD_SUB, rd=r_add_w, rs1=r_max, rs2=r_seven),
            _alu_r(F3_ADD_SUB, rd=r_sub_w, rs1=0, rs2=r_seven, funct7=F7_ALT),
            _alu_r(F3_SLL, rd=r_sll, rs1=r_seven, rs2=r_sh35),
            _alu_r(F3_SRL_SRA, rd=r_srl, rs1=r_msb, rs2=r_sh35),
            _alu_r(F3_SRL_SRA, rd=r_sra, rs1=r_neg16, rs2=r_sh35, funct7=F7_ALT),
            _alu_i(F3_SLTU, rd=r_sltiu, rs1=r_seven, imm=-1),  # 7 < u32(-1) == 0xFFFF_FFFF -> 1
            INSN_EBREAK,
        ],
    )
    cpu.run()

    assert cpu.regs[r_addi_w] == 0
    assert cpu.regs[r_add_w] == 6
    assert cpu.regs[r_sub_w] == u32(-7)
    assert cpu.regs[r_sll] == 56
    assert cpu.regs[r_srl] == 0x1000_0000
    assert cpu.regs[r_sra] == u32(-2)
    assert cpu.regs[r_sltiu] == 1

    # AUIPC wraps cleanly modulo 2^32 when upper20 pushes past 0xFFFF_FFFF (BRAM + 0xF000_1000)
    cpu.reset(reset_pc=BRAM_BASE)
    cpu.load_words(BRAM_BASE, [_auipc(rd=r_auipc_wrap, upper_bits=0xF000_1000)])
    cpu.step()
    assert cpu.regs[r_auipc_wrap] == 0x0000_1000


def test_barrier_and_wait_nops() -> None:
    """Verify FENCE, FENCE.I, and WFI retire cleanly as sequential no-ops advancing PC + 4."""
    cpu = RV32Oracle()
    cpu.load_words(BOOT_ROM_BASE, [INSN_FENCE, INSN_FENCE_I, INSN_WFI])
    for step_idx in range(3):
        tr = cpu.step()
        assert tr.trap_cause is None
        assert tr.pc == BOOT_ROM_BASE + step_idx * INSN_SIZE_BYTES
        assert tr.next_pc == BOOT_ROM_BASE + (step_idx + 1) * INSN_SIZE_BYTES
    assert cpu.minstret == 3


def test_rv32m_multiplication_variants_and_truncation() -> None:
    """Verify MUL low-word truncation plus MULH/MULHSU/MULHU upper-32-bit sign divergence."""
    cpu = RV32Oracle()
    r_neg7, r_three, r_neg1, r_msb, r_pow16 = 1, 2, 3, 4, 5
    r_mul_lo, r_mul_wrap, r_mulhu_carry = 10, 11, 12
    r_mulh_7, r_mulhsu_7, r_mulhu_7 = 13, 14, 15
    r_mulh_edge, r_mulhsu_edge, r_mulhu_edge = 16, 17, 18
    cpu.regs[r_neg7] = u32(-7)
    cpu.regs[r_three] = 3
    cpu.regs[r_neg1] = u32(-1)
    cpu.regs[r_msb] = 0x8000_0000
    cpu.regs[r_pow16] = 0x1_0000

    cpu.load_words(
        BOOT_ROM_BASE,
        [
            _muldiv(F3_MUL, rd=r_mul_lo, rs1=r_neg7, rs2=r_three),          # -7 * 3 -> -21
            _muldiv(F3_MUL, rd=r_mul_wrap, rs1=r_pow16, rs2=r_pow16),       # 2^16 * 2^16 low = 0
            _muldiv(F3_MULHU, rd=r_mulhu_carry, rs1=r_pow16, rs2=r_pow16),  # 2^16 * 2^16 high = 1
            _muldiv(F3_MULH, rd=r_mulh_7, rs1=r_neg7, rs2=r_three),         # -1
            _muldiv(F3_MULHSU, rd=r_mulhsu_7, rs1=r_neg7, rs2=r_three),     # -1
            _muldiv(F3_MULHU, rd=r_mulhu_7, rs1=r_neg7, rs2=r_three),       # 2
            _muldiv(F3_MULH, rd=r_mulh_edge, rs1=r_neg1, rs2=r_msb),        # (-1)*(-2^31) -> hi 0
            _muldiv(F3_MULHSU, rd=r_mulhsu_edge, rs1=r_neg1, rs2=r_msb),    # (-1)*(+2^31) -> hi -1
            _muldiv(F3_MULHU, rd=r_mulhu_edge, rs1=r_neg1, rs2=r_msb),      # (2^32-1)*2^31 -> 0x7FFF_FFFF
            INSN_EBREAK,
        ],
    )
    cpu.run()

    assert cpu.regs[r_mul_lo] == u32(-21)
    assert cpu.regs[r_mul_wrap] == 0
    assert cpu.regs[r_mulhu_carry] == 1
    assert cpu.regs[r_mulh_7] == u32(-1)
    assert cpu.regs[r_mulhsu_7] == u32(-1)
    assert cpu.regs[r_mulhu_7] == 2
    assert cpu.regs[r_mulh_edge] == 0
    assert cpu.regs[r_mulhsu_edge] == UINT32_MAX
    assert cpu.regs[r_mulhu_edge] == 0x7FFF_FFFF


def test_rv32m_division_truncation_overflow_and_div_by_zero() -> None:
    """Verify truncation-toward-zero DIV/REM, unsigned MSB=1 DIVU/REMU, /0, and INT32_MIN/-1."""
    cpu = RV32Oracle()
    r_pos7, r_neg7, r_pos3, r_neg3 = 1, 2, 3, 4
    r_imin, r_neg1, r_zero, r_big_u = 5, 6, 7, 8
    r_div_np, r_rem_np, r_div_pn, r_rem_pn, r_div_nn, r_rem_nn = 10, 11, 12, 13, 14, 15
    r_div_ovf, r_rem_ovf, r_div0, r_divu0, r_rem0, r_remu0, r_divu_hi, r_remu_hi = (
        16, 17, 18, 19, 20, 21, 22, 23
    )
    cpu.regs[r_pos7] = 7
    cpu.regs[r_neg7] = u32(-7)
    cpu.regs[r_pos3] = 3
    cpu.regs[r_neg3] = u32(-3)
    cpu.regs[r_imin] = u32(INT32_MIN)
    cpu.regs[r_neg1] = u32(-1)
    cpu.regs[r_zero] = 0
    cpu.regs[r_big_u] = 0x8000_0005                       # Bit 31 set: tests unsigned DIVU/REMU

    cpu.load_words(
        BOOT_ROM_BASE,
        [
            _muldiv(F3_DIV, rd=r_div_np, rs1=r_neg7, rs2=r_pos3),   # -7 / 3 -> -2
            _muldiv(F3_REM, rd=r_rem_np, rs1=r_neg7, rs2=r_pos3),   # -7 % 3 -> -1
            _muldiv(F3_DIV, rd=r_div_pn, rs1=r_pos7, rs2=r_neg3),   # +7 / -3 -> -2
            _muldiv(F3_REM, rd=r_rem_pn, rs1=r_pos7, rs2=r_neg3),   # +7 % -3 -> +1
            _muldiv(F3_DIV, rd=r_div_nn, rs1=r_neg7, rs2=r_neg3),   # -7 / -3 -> +2
            _muldiv(F3_REM, rd=r_rem_nn, rs1=r_neg7, rs2=r_neg3),   # -7 % -3 -> -1
            _muldiv(F3_DIV, rd=r_div_ovf, rs1=r_imin, rs2=r_neg1),  # INT32_MIN / -1 -> INT32_MIN
            _muldiv(F3_REM, rd=r_rem_ovf, rs1=r_imin, rs2=r_neg1),  # INT32_MIN % -1 -> 0
            _muldiv(F3_DIV, rd=r_div0, rs1=r_neg7, rs2=r_zero),     # -7 / 0 -> -1
            _muldiv(F3_DIVU, rd=r_divu0, rs1=r_neg7, rs2=r_zero),   # u32(-7) / 0 -> UINT32_MAX
            _muldiv(F3_REM, rd=r_rem0, rs1=r_neg7, rs2=r_zero),     # -7 % 0 -> -7
            _muldiv(F3_REMU, rd=r_remu0, rs1=r_neg7, rs2=r_zero),   # u32(-7) % 0 -> u32(-7)
            _muldiv(F3_DIVU, rd=r_divu_hi, rs1=r_big_u, rs2=r_pos3),
            _muldiv(F3_REMU, rd=r_remu_hi, rs1=r_big_u, rs2=r_pos3),
            INSN_EBREAK,
        ],
    )
    cpu.run()

    assert cpu.regs[r_div_np] == u32(-2)
    assert cpu.regs[r_rem_np] == u32(-1)
    assert cpu.regs[r_div_pn] == u32(-2)
    assert cpu.regs[r_rem_pn] == 1
    assert cpu.regs[r_div_nn] == 2
    assert cpu.regs[r_rem_nn] == u32(-1)
    assert cpu.regs[r_div_ovf] == u32(INT32_MIN)
    assert cpu.regs[r_rem_ovf] == 0
    assert cpu.regs[r_div0] == UINT32_MAX
    assert cpu.regs[r_divu0] == UINT32_MAX
    assert cpu.regs[r_rem0] == u32(-7)
    assert cpu.regs[r_remu0] == u32(-7)
    assert cpu.regs[r_divu_hi] == 0x8000_0005 // 3
    assert cpu.regs[r_remu_hi] == 0x8000_0005 % 3


def test_conditional_branches_and_subroutine_calls() -> None:
    """Verify all six branch conditions (taken & untaken) and JAL/JALR subroutine linkage."""
    cpu = RV32Oracle()
    r_sum, r_i, r_limit, r_link = 1, 2, 3, 5
    r_neg1, r_pos1 = 10, 11
    cpu.regs[r_neg1] = u32(-1)
    cpu.regs[r_pos1] = 1
    prog = [
        _alu_i(F3_ADD_SUB, rd=r_sum, rs1=0, imm=0),      # 0x00: sum = 0
        _alu_i(F3_ADD_SUB, rd=r_i, rs1=0, imm=1),        # 0x04: i = 1
        _alu_i(F3_ADD_SUB, rd=r_limit, rs1=0, imm=6),    # 0x08: limit = 6
        _alu_r(F3_ADD_SUB, rd=r_sum, rs1=r_sum, rs2=r_i),  # 0x0C: sum += i
        _alu_i(F3_ADD_SUB, rd=r_i, rs1=r_i, imm=1),      # 0x10: i += 1
        _branch(F3_BLT, rs1=r_i, rs2=r_limit, offset=-8),  # 0x14: loop -> 0x0C while i < 6
        _branch(F3_BEQ, rs1=r_i, rs2=r_limit, offset=8),   # 0x18: beq 6, 6 (taken -> 0x20)
        INSN_EBREAK,                                     # 0x1C: skipped
        _branch(F3_BNE, rs1=r_i, rs2=r_limit, offset=8),   # 0x20: bne 6, 6 (untaken -> 0x24)
        _branch(F3_BGE, rs1=r_neg1, rs2=r_pos1, offset=8),   # 0x24: untaken
        _branch(F3_BLTU, rs1=r_neg1, rs2=r_pos1, offset=8),  # 0x28: untaken
        _branch(F3_BGEU, rs1=r_pos1, rs2=r_neg1, offset=8),  # 0x2C: untaken
        _branch(F3_BGE, rs1=r_pos1, rs2=r_neg1, offset=8),   # 0x30: taken -> 0x38
        INSN_EBREAK,                                     # 0x34: skipped
        _branch(F3_BLTU, rs1=r_pos1, rs2=r_neg1, offset=8),  # 0x38: taken -> 0x40
        INSN_EBREAK,                                     # 0x3C: skipped
        _branch(F3_BGEU, rs1=r_neg1, rs2=r_pos1, offset=8),  # 0x40: taken -> 0x48
        INSN_EBREAK,                                     # 0x44: skipped
        _jal(rd=r_link, offset=8),                       # 0x48: call 0x50 (r_link = 0x4C)
        INSN_EBREAK,                                     # 0x4C: halt after return
        _alu_i(F3_ADD_SUB, rd=r_sum, rs1=r_sum, imm=100),  # 0x50: sum += 100
        _jalr(rd=0, rs1=r_link, offset=0),               # 0x54: return -> 0x4C
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[r_sum] == 115
    assert cpu.regs[r_link] == BOOT_ROM_BASE + 0x4C


def test_large_branch_and_jal_immediate_encodings() -> None:
    """Exercise upper scrambled immediate bits (B-type Bits 11..12; J-type Bits 11 & 19..12)."""
    cpu = RV32Oracle()
    r_link_fwd, r_link_back, r_ok = 1, 2, 3
    # 1. BRAM (64 KB): forward B-type +2052 exercises Bit 11; negative -2048 hits Bit 12
    branch_fwd_pc = BRAM_BASE
    branch_target_pc = branch_fwd_pc + 2052               # +0x804 -> Bit 11 = 1
    back_landing_pc = branch_target_pc - 2048             # BRAM+4 -> Bit 12 = 1 (-4096 + 2048)
    cpu.reset(reset_pc=branch_fwd_pc)
    cpu.load_words(branch_fwd_pc, [_branch(F3_BEQ, rs1=0, rs2=0, offset=2052)])
    cpu.load_words(branch_target_pc, [_branch(F3_BEQ, rs1=0, rs2=0, offset=-2048)])
    cpu.load_words(back_landing_pc, [INSN_EBREAK])
    cpu.run(max_steps=3)
    assert cpu.halted
    assert cpu.mepc == back_landing_pc

    # 2. SDRAM (32 MB): forward +0x2_2800 & backward -0x2_27FC hit Bits 19..12, Bit 11, and Bit 20
    sdram_start = SDRAM_BASE + 0x0010_0000
    jal_target = sdram_start + 0x0002_2800
    cpu.reset(reset_pc=sdram_start)
    cpu.load_words(sdram_start, [_jal(rd=r_link_fwd, offset=0x0002_2800)])
    cpu.load_words(jal_target, [_jal(rd=r_link_back, offset=INSN_SIZE_BYTES - 0x0002_2800)])
    cpu.load_words(sdram_start + INSN_SIZE_BYTES, [_alu_i(F3_ADD_SUB, rd=r_ok, rs1=0, imm=99), INSN_EBREAK])
    cpu.run(max_steps=4)
    assert cpu.halted
    assert cpu.mepc == sdram_start + 2 * INSN_SIZE_BYTES
    assert cpu.regs[r_link_fwd] == sdram_start + INSN_SIZE_BYTES
    assert cpu.regs[r_link_back] == jal_target + INSN_SIZE_BYTES
    assert cpu.regs[r_ok] == 99


def test_negative_jal_jalr_offsets() -> None:
    """Verify negative JAL and JALR byte offsets preserve return addresses cleanly."""
    cpu = RV32Oracle()
    r_fwd, r_back = 6, 7
    cpu.reset(reset_pc=BRAM_BASE)
    cpu.load_words(
        BRAM_BASE,
        [
            _jal(rd=r_fwd, offset=8),                    # step 1: 0x00 -> 0x08 (r_fwd = BRAM+4)
            _jalr(rd=r_back, rs1=r_fwd, offset=-4),      # step 3: 0x04 -> 0x00 (r_back = BRAM+8)
            _jal(rd=0, offset=-4),                       # step 2: 0x08 -> 0x04
        ],
    )
    cpu.run(max_steps=3, stop_on_ebreak=False)
    assert cpu.regs[r_fwd] == BRAM_BASE + 4
    assert cpu.regs[r_back] == BRAM_BASE + 8
    assert cpu.pc == BRAM_BASE


def test_load_bytes_and_stop_on_pc() -> None:
    """Verify host load_bytes image loading and exact run(stop_on_pc=...) termination."""
    cpu = RV32Oracle()
    r_out = 10
    cpu.reset(reset_pc=BRAM_BASE)
    cpu.load_bytes(BRAM_BASE, _alu_i(F3_ADD_SUB, rd=r_out, rs1=0, imm=37).to_bytes(4, "little"))
    cpu.run(stop_on_pc=BRAM_BASE + INSN_SIZE_BYTES)
    assert cpu.regs[r_out] == 37


def test_memory_loads_stores_and_mmio_stub() -> None:
    """Verify little-endian byte/half/word loads & stores plus all 5 reserved MMIO stub pages."""
    cpu = RV32Oracle()
    r_bram, r_val, r_sdram, r_stub, r_stub_hi = 1, 2, 3, 10, 12
    r_lb, r_lbu, r_lh, r_lhu, r_sh_lhu, r_mixed_lw, r_stub_lw, r_stub_lb, r_stub_lh = (
        4, 5, 6, 7, 8, 9, 11, 13, 14
    )
    cpu.regs[r_bram] = BRAM_BASE + 8
    cpu.regs[r_val] = 0x1122_80FF
    cpu.regs[r_sdram] = SDRAM_BASE + 0x1000
    cpu.regs[r_stub] = MMIO_STUB_BASE
    cpu.regs[r_stub_hi] = MMIO_STUB_BASE + 0x4_0000     # 5th stub page (0x8006_0000)

    # Little-endian byte layout at SDRAM+0x1000: SW 0 -> SH 0x80FF at +2 -> SB 0xFF at +1 => 0x80FF_FF00
    prog = [
        _store(F3_SW, rs2=r_val, rs1=r_bram, offset=-8),
        _load(F3_LB, rd=r_lb, rs1=r_bram, offset=-8),
        _load(F3_LBU, rd=r_lbu, rs1=r_bram, offset=-8),
        _load(F3_LH, rd=r_lh, rs1=r_bram, offset=-8),
        _load(F3_LHU, rd=r_lhu, rs1=r_bram, offset=-8),
        _store(F3_SW, rs2=0, rs1=r_sdram, offset=0),
        _store(F3_SH, rs2=r_val, rs1=r_sdram, offset=2),
        _load(F3_LHU, rd=r_sh_lhu, rs1=r_sdram, offset=2),
        _store(F3_SB, rs2=r_val, rs1=r_sdram, offset=1),
        _load(F3_LW, rd=r_mixed_lw, rs1=r_sdram, offset=0),
        _store(F3_SW, rs2=r_val, rs1=r_stub, offset=0),
        _load(F3_LW, rd=r_stub_lw, rs1=r_stub, offset=0),
        _store(F3_SB, rs2=r_val, rs1=r_stub_hi, offset=0),
        _load(F3_LB, rd=r_stub_lb, rs1=r_stub_hi, offset=0),
        _store(F3_SH, rs2=r_val, rs1=r_stub_hi, offset=2),
        _load(F3_LH, rd=r_stub_lh, rs1=r_stub_hi, offset=2),
        INSN_EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[r_lb] == UINT32_MAX
    assert cpu.regs[r_lbu] == 0x0000_00FF
    assert cpu.regs[r_lh] == 0xFFFF_80FF
    assert cpu.regs[r_lhu] == 0x0000_80FF
    assert cpu.regs[r_sh_lhu] == 0x0000_80FF
    assert cpu.regs[r_mixed_lw] == 0x80FF_FF00
    assert cpu.regs[r_stub_lw] == 0x1122_80FF
    assert cpu.regs[r_stub_lb] == UINT32_MAX
    assert cpu.regs[r_stub_lh] == 0xFFFF_80FF

    # Verify middle stub pages (SPI0/CAN0/CAN1/SYNC) retain data independently
    for page_offset in (0x1_0000, 0x2_0000, 0x3_0000):
        cpu.write_u32(MMIO_STUB_BASE + page_offset, 0xA5A5_0000 | page_offset)
        assert cpu.read_u32(MMIO_STUB_BASE + page_offset) == (0xA5A5_0000 | page_offset)

    cpu.write_u32(BRAM_BASE + 0x20, 0xDEAD_BEEF)
    assert cpu.read_u32(BRAM_BASE + 0x20) == 0xDEAD_BEEF


def test_memory_region_bounds_and_qspi_xip_exec() -> None:
    """Verify valid region end words, unmapped boundary faults, QSPI XIP exec, and loader bounds."""
    cpu = RV32Oracle()
    r_qspi = 5
    for base, size in [
        (BOOT_ROM_BASE, BOOT_ROM_SIZE),
        (BRAM_BASE, BRAM_SIZE),
        (QSPI_BASE, QSPI_SIZE),
        (SDRAM_BASE, SDRAM_SIZE),
        (CLINT_BASE, CLINT_SIZE),
        (UART0_BASE, UART0_SIZE),
        (MMIO_STUB_BASE, MMIO_STUB_END - MMIO_STUB_BASE),
    ]:
        last_valid = base + size - INSN_SIZE_BYTES
        assert cpu.read_u32(last_valid) == 0

    # First byte past each disjoint block (CLINT -> UART0 -> MMIO_STUB are contiguous) faults
    for first_unmapped in [
        BOOT_ROM_BASE + BOOT_ROM_SIZE,
        BRAM_BASE + BRAM_SIZE,
        QSPI_BASE + QSPI_SIZE,
        SDRAM_BASE + SDRAM_SIZE,
        MMIO_STUB_END,
    ]:
        with pytest.raises(MemoryAccessFault):
            cpu.read_u32(first_unmapped)

    # Read and execute directly from QSPI NOR Flash XIP window at its last valid word
    qspi_last_word = QSPI_BASE + QSPI_SIZE - INSN_SIZE_BYTES
    cpu.reset(reset_pc=qspi_last_word)
    cpu.load_words(qspi_last_word, [_alu_i(F3_ADD_SUB, rd=r_qspi, rs1=0, imm=77)])
    assert cpu.step().trap_cause is None
    assert cpu.regs[r_qspi] == 77

    with pytest.raises(MemoryAccessFault):
        cpu.load_bytes(UNMAPPED_BUS_ADDR, b"\x00")
    with pytest.raises(MemoryAccessFault):
        cpu.load_words(UNMAPPED_BUS_ADDR, [0])


def test_load_store_alignment_and_ro_traps() -> None:
    """Verify misalignment/RO/unmapped traps preserve rd & minstret and set exact mtval/mepc."""
    cpu = RV32Oracle()
    r_addr, r_data = 1, 2
    cases = [
        (_load(F3_LW, rd=r_data, rs1=r_addr, offset=0), BRAM_BASE + 1, CAUSE_LOAD_MISALIGNED),
        (_load(F3_LH, rd=r_data, rs1=r_addr, offset=1), BRAM_BASE, CAUSE_LOAD_MISALIGNED),
        (_store(F3_SH, rs2=r_data, rs1=r_addr, offset=1), BRAM_BASE, CAUSE_STORE_MISALIGNED),
        (_store(F3_SW, rs2=r_data, rs1=r_addr, offset=0), BRAM_BASE + 2, CAUSE_STORE_MISALIGNED),
        (_load(F3_LW, rd=r_data, rs1=r_addr, offset=0), UNMAPPED_BUS_ADDR, CAUSE_LOAD_ACCESS_FAULT),
        (_store(F3_SW, rs2=r_data, rs1=r_addr, offset=0), BOOT_ROM_BASE, CAUSE_STORE_ACCESS_FAULT),
        (_store(F3_SW, rs2=r_data, rs1=r_addr, offset=0), QSPI_BASE, CAUSE_STORE_ACCESS_FAULT),
        (_store(F3_SW, rs2=r_data, rs1=r_addr, offset=0), UNMAPPED_BUS_ADDR, CAUSE_STORE_ACCESS_FAULT),
    ]
    for insn, fault_addr, expected_cause in cases:
        cpu.reset(reset_pc=BOOT_ROM_BASE)
        cpu.regs[r_addr] = fault_addr
        cpu.regs[r_data] = 0xCAFE_BABE
        # Cases with offset=1 put BRAM_BASE in r_addr so effective fault address is BRAM_BASE + 1
        expected_mtval = fault_addr + 1 if fault_addr == BRAM_BASE else fault_addr
        cpu.load_words(BOOT_ROM_BASE, [insn])
        tr = cpu.step()
        assert tr.trap_cause == expected_cause
        assert cpu.mcause == expected_cause
        assert cpu.mepc == BOOT_ROM_BASE
        assert cpu.mtval == expected_mtval
        assert cpu.regs[r_data] == 0xCAFE_BABE
        assert cpu.minstret == 0


def test_step_trace_store_load_and_misalign_payloads() -> None:
    """Verify StepTrace fields across byte store, sign-extended load, and misaligned trap."""
    cpu = RV32Oracle()
    r_base, r_val, r_lb, r_lh = 1, 2, 3, 4
    cpu.regs[r_base] = BRAM_BASE
    cpu.regs[r_val] = 0x1234_80FF
    sb_insn = _store(F3_SB, rs2=r_val, rs1=r_base, offset=0)
    lb_insn = _load(F3_LB, rd=r_lb, rs1=r_base, offset=0)
    lh_insn = _load(F3_LH, rd=r_lh, rs1=r_base, offset=1)
    cpu.load_words(BOOT_ROM_BASE, [sb_insn, lb_insn, lh_insn])

    t_sb, t_lb, t_lh = cpu.step(), cpu.step(), cpu.step()
    assert t_sb.pc == BOOT_ROM_BASE
    assert t_sb.insn == sb_insn
    assert t_sb.mem_addr == BRAM_BASE
    assert t_sb.mem_val == 0xFF
    assert t_sb.mem_write
    assert t_lb.rd == r_lb
    assert t_lb.rd_val == UINT32_MAX
    assert t_lb.mem_val == UINT32_MAX
    assert not t_lb.mem_write
    assert t_lh.trap_cause == CAUSE_LOAD_MISALIGNED
    assert cpu.mtval == BRAM_BASE + 1


def test_jalr_bit0_snap_and_untaken_misaligned_branch() -> None:
    """Verify JALR Bit-0 snap with rd == rs1 and untaken misaligned branch skipping trap."""
    cpu = RV32Oracle()
    r_link_ptr = 2
    cpu.regs[r_link_ptr] = BRAM_BASE
    cpu.load_words(BOOT_ROM_BASE, [_jalr(rd=r_link_ptr, rs1=r_link_ptr, offset=1)])
    # Untaken branch with misaligned offset=2 must not trap because alignment applies only when taken
    cpu.load_words(BRAM_BASE, [_branch(F3_BNE, rs1=0, rs2=0, offset=2), INSN_EBREAK])
    traces = cpu.run(max_steps=2, stop_on_ebreak=False)
    assert len(traces) == 2
    assert traces[1].trap_cause is None
    assert cpu.regs[r_link_ptr] == BOOT_ROM_BASE + INSN_SIZE_BYTES
    assert cpu.pc == BRAM_BASE + INSN_SIZE_BYTES


def test_sparse_memory_4kb_page_crossing() -> None:
    """Verify SparseMemory multi-byte reads across a 4 KB page boundary."""
    cpu = RV32Oracle()
    r_ptr, r_lo, r_hi = 1, 5, 6
    cross_addr = BRAM_BASE + SparseMemory.PAGE_SIZE - 2
    cpu.load_bytes(cross_addr, b"\x11\x22\x33\x44")
    cpu.regs[r_ptr] = cross_addr
    cpu.load_words(
        BOOT_ROM_BASE,
        [
            _load(F3_LHU, rd=r_lo, rs1=r_ptr, offset=0),
            _load(F3_LHU, rd=r_hi, rs1=r_ptr, offset=2),
            INSN_EBREAK,
        ],
    )
    cpu.run()
    assert cpu.regs[r_lo] == 0x2211
    assert cpu.regs[r_hi] == 0x4433
    assert cpu.bus_read(cross_addr + 1, 2) == 0x3322


def test_clint_timer_interrupt_and_ecall_handler() -> None:
    """Verify synchronous ECALL + asynchronous CLINT timer IRQ inside a shared M-mode handler."""
    cpu = RV32Oracle()
    handler_addr = BRAM_BASE
    r_done, r_timer_cause, r_clint, r_clint_max = 20, 21, 22, 23
    r_cause, r_scratch = 25, 26
    cpu.regs[r_timer_cause] = CAUSE_INT_M_TIMER
    cpu.regs[r_clint] = CLINT_BASE
    cpu.regs[r_clint_max] = UINT32_MAX

    # Shared handler dispatches on mcause: timer branch skips 7 sync insns (8 * 4 = 32 bytes incl. BEQ)
    timer_branch_offset = 8 * INSN_SIZE_BYTES
    handler = [
        _csr_reg(F3_CSRRS, rd=r_cause, csr_addr=CSR_MCAUSE, rs1=0),
        _branch(F3_BEQ, rs1=r_cause, rs2=r_timer_cause, offset=timer_branch_offset),
        _csr_reg(F3_CSRRS, rd=r_scratch, csr_addr=CSR_MSCRATCH, rs1=0),
        _alu_i(F3_ADD_SUB, rd=r_scratch, rs1=r_scratch, imm=1),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MSCRATCH, rs1=r_scratch),
        _csr_reg(F3_CSRRS, rd=r_scratch, csr_addr=CSR_MEPC, rs1=0),
        _alu_i(F3_ADD_SUB, rd=r_scratch, rs1=r_scratch, imm=INSN_SIZE_BYTES),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MEPC, rs1=r_scratch),
        INSN_MRET,
        _store(F3_SW, rs2=r_clint_max, rs1=r_clint, offset=CLINT_MTIMECMP_LO),
        _store(F3_SW, rs2=r_clint_max, rs1=r_clint, offset=CLINT_MTIMECMP_HI),
        _alu_i(F3_ADD_SUB, rd=r_done, rs1=0, imm=0x123),
        INSN_MRET,
    ]
    cpu.load_words(handler_addr, handler)

    r_mtvec, r_main_clint, r_alarm, r_mie, r_mstatus, r_target, r_spins = 1, 2, 3, 4, 5, 6, 7
    cpu.regs[r_mtvec] = handler_addr
    cpu.regs[r_main_clint] = CLINT_BASE
    cpu.regs[r_alarm] = 30
    cpu.regs[r_mie] = MIE_MTIE_BIT
    cpu.regs[r_mstatus] = MSTATUS_MIE_BIT
    cpu.regs[r_target] = 0x123

    main_prog = [
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MTVEC, rs1=r_mtvec),
        _store(F3_SW, rs2=0, rs1=r_main_clint, offset=CLINT_MTIMECMP_HI),
        _store(F3_SW, rs2=r_alarm, rs1=r_main_clint, offset=CLINT_MTIMECMP_LO),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MIE, rs1=r_mie),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MSTATUS, rs1=r_mstatus),
        INSN_ECALL,
        _alu_i(F3_ADD_SUB, rd=r_spins, rs1=r_spins, imm=1),        # spin loop body
        _branch(F3_BNE, rs1=r_done, rs2=r_target, offset=-INSN_SIZE_BYTES),  # loop while r_done != r_target
        INSN_EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, main_prog)
    traces = cpu.run(max_steps=200)

    assert cpu.halted
    assert cpu.mscratch == 1
    # 5 setup + 1 ECALL + 9 ECALL-ISR = 15 cycles before loop; timer fires at mtime=30 (7 full iters + exit pass)
    assert cpu.regs[r_spins] == 8
    assert cpu.regs[r_done] == 0x123
    assert any(t.trap_cause == CAUSE_ECALL_M for t in traces)
    assert any(t.interrupt and t.trap_cause == CAUSE_INT_M_TIMER for t in traces)
    assert cpu.mcycle > cpu.minstret


def test_vectored_mtvec_dispatch_and_sync_ecall_fallback() -> None:
    """Verify vectored mtvec interrupt slot jumps, CSR trap entry fields, and sync ECALL fallback."""
    cpu = RV32Oracle()
    for irq_bit, cause in [
        (MIE_MTIE_BIT, CAUSE_INT_M_TIMER),
        (MIE_MSIE_BIT, CAUSE_INT_M_SW),
        (MIE_MEIE_BIT, CAUSE_INT_M_EXT),
    ]:
        cpu.reset(reset_pc=BOOT_ROM_BASE)
        cpu.mtvec = BRAM_BASE | MTVEC_MODE_VECTORED
        cpu.mie = irq_bit
        cpu.mstatus = MSTATUS_MIE_BIT
        if irq_bit == MIE_MTIE_BIT:
            cpu.mtimecmp = 0
        else:
            cpu.mip_sw_ext = irq_bit
        tr_irq = cpu.step()
        assert tr_irq.interrupt
        assert tr_irq.insn == 0
        assert tr_irq.next_pc == BRAM_BASE + INSN_SIZE_BYTES * (cause & MCAUSE_CODE_MASK)
        assert cpu.mcause == cause
        assert cpu.mepc == BOOT_ROM_BASE
        assert cpu.mtval == 0
        assert cpu.mstatus == (MSTATUS_MPIE_BIT | MSTATUS_MPP_M)

    # Vectored mode (MODE=1): synchronous ECALL still jumps to base (not base + 4 * 11)
    cpu.reset(reset_pc=BOOT_ROM_BASE)
    cpu.mtvec = BRAM_BASE | MTVEC_MODE_VECTORED
    cpu.load_words(BOOT_ROM_BASE, [INSN_ECALL])
    tr_ecall = cpu.step()
    assert not tr_ecall.interrupt
    assert tr_ecall.trap_cause == CAUSE_ECALL_M
    assert tr_ecall.next_pc == BRAM_BASE
    assert cpu.mcause == CAUSE_ECALL_M
    assert cpu.mepc == BOOT_ROM_BASE


def test_interrupt_masking_and_64bit_timer_threshold() -> None:
    """Verify mstatus.MIE / mie masking, 64-bit Bit-63 threshold, and EBREAK preemption + MRET."""
    cpu = RV32Oracle()
    r_out, r_ok = 10, 1
    for mstatus_val, mie_val in [(0, MIE_MTIE_BIT), (MSTATUS_MIE_BIT, 0)]:
        cpu.reset(reset_pc=BOOT_ROM_BASE)
        cpu.mstatus = mstatus_val
        cpu.mie = mie_val
        cpu.mtimecmp = 0
        cpu.load_words(BOOT_ROM_BASE, [_alu_i(F3_ADD_SUB, rd=r_out, rs1=0, imm=42)])
        tr_suppressed = cpu.step()
        assert tr_suppressed.trap_cause is None
        assert cpu.regs[r_out] == 42

    # Exact 64-bit Bit-63 threshold: timer preempts EBREAK pre-fetch, ISR MRETs back to run EBREAK
    cpu.reset(reset_pc=BOOT_ROM_BASE)
    cpu.mtvec = BRAM_BASE
    cpu.mstatus = MSTATUS_MIE_BIT
    cpu.mie = MIE_MTIE_BIT
    cpu.mtimecmp = 0x8000_0000_0000_0005
    cpu.mtime = cpu.mtimecmp - 2
    r_clint, r_max = 2, 3
    cpu.regs[r_clint] = CLINT_BASE
    cpu.regs[r_max] = UINT32_MAX
    cpu.load_words(BOOT_ROM_BASE, [_alu_i(F3_ADD_SUB, rd=r_ok, rs1=0, imm=7), INSN_EBREAK])
    cpu.load_words(
        BRAM_BASE,
        [_store(F3_SW, rs2=r_max, rs1=r_clint, offset=CLINT_MTIMECMP_HI), INSN_MRET],
    )
    assert cpu.step().trap_cause is None                 # mtime reaches mtimecmp - 1 (< mtimecmp)
    assert cpu.regs[r_ok] == 7
    tr_irq = cpu.step()                                  # mtime hits mtimecmp -> preempts EBREAK!
    assert tr_irq.trap_cause == CAUSE_INT_M_TIMER
    assert not cpu.halted
    assert cpu.mepc == BOOT_ROM_BASE + INSN_SIZE_BYTES
    cpu.run(max_steps=5)                                 # clears timer, MRETs to EBREAK, halts
    assert cpu.halted
    assert cpu.mcause == CAUSE_BREAKPOINT


def test_interrupt_priority_and_masked_fallthrough() -> None:
    """Verify MEIP > MSIP > MTIP priority ordering and masked higher-IRQ fallthrough via CSR_MIP."""
    r_mip, r_mie, r_mstatus = 1, 2, 3
    for mie_mask, expected_cause in [
        (MIE_MEIE_BIT | MIE_MSIE_BIT | MIE_MTIE_BIT, CAUSE_INT_M_EXT),
        (MIE_MSIE_BIT | MIE_MTIE_BIT, CAUSE_INT_M_SW),
    ]:
        cpu = RV32Oracle()
        cpu.regs[r_mip] = MIE_MEIE_BIT | MIE_MSIE_BIT
        cpu.regs[r_mie] = mie_mask
        cpu.regs[r_mstatus] = MSTATUS_MIE_BIT
        cpu.mtimecmp = 0
        cpu.load_words(
            BOOT_ROM_BASE,
            [
                _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MIP, rs1=r_mip),
                _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MIE, rs1=r_mie),
                _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MSTATUS, rs1=r_mstatus),
            ],
        )
        cpu.run(max_steps=3, stop_on_ebreak=False)
        tr = cpu.step()
        assert tr.interrupt
        assert tr.trap_cause == expected_cause
        assert cpu.mcause == expected_cause
        assert cpu.mtval == 0
        assert cpu.mepc == BOOT_ROM_BASE + 3 * INSN_SIZE_BYTES
        assert cpu.mstatus == (MSTATUS_MPIE_BIT | MSTATUS_MPP_M)


def test_zicsr_immediate_variants_and_rd_eq_rs1_swap() -> None:
    """Verify CSRRWI/CSRRSI/CSRRCI, safe uimm=0/rs1=0 RO queries, and atomic CSRRW rd == rs1."""
    cpu = RV32Oracle()
    r_swap, r_pat, r_cwr, r_csi, r_cci, r_ro_i, r_ro_c, r_cause = 1, 2, 3, 4, 5, 6, 8, 7
    cpu.regs[r_swap] = 0xAA
    cpu.regs[r_pat] = 0x55
    prog = [
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MCAUSE, rs1=r_pat),
        _csr_reg(F3_CSRRS, rd=r_cause, csr_addr=CSR_MCAUSE, rs1=0),
        _csr_reg(F3_CSRRW, rd=r_swap, csr_addr=CSR_MSCRATCH, rs1=r_swap),   # swap preserves x1 pre-write
        _csr_imm(F3_CSRRWI, rd=r_cwr, csr_addr=CSR_MSCRATCH, uimm=0x0A),
        _csr_imm(F3_CSRRSI, rd=r_csi, csr_addr=CSR_MSCRATCH, uimm=0x05),
        _csr_imm(F3_CSRRCI, rd=r_cci, csr_addr=CSR_MSCRATCH, uimm=0x03),
        _csr_imm(F3_CSRRSI, rd=r_ro_i, csr_addr=CSR_MISA, uimm=0),         # uimm=0 safely reads misa
        _csr_imm(F3_CSRRCI, rd=r_ro_c, csr_addr=CSR_MISA, uimm=0),         # uimm=0 CSRRCI also safe
        INSN_EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[r_cause] == 0x55
    assert cpu.regs[r_swap] == 0
    assert cpu.regs[r_cwr] == 0xAA
    assert cpu.regs[r_csi] == 0x0A
    assert cpu.regs[r_cci] == 0x0F
    assert cpu.mscratch == 0x0C
    assert cpu.regs[r_ro_i] == cpu.misa
    assert cpu.regs[r_ro_c] == cpu.misa


def test_zicsr_csrrc_mtval_mip_and_counters() -> None:
    """Verify CSRRC, mtval/mip CSR access, exact mcycle cadence, and minstret suppression."""
    cpu = RV32Oracle()
    r_0f, r_03, r_csrrc, r_mtval, r_mip, r_cyc_lo, r_cyc_hi, r_ret_lo, r_ret_hi, r_ret_wi = (
        1, 2, 10, 11, 12, 13, 14, 15, 16, 17
    )
    cpu.regs[r_0f] = 0x0F
    cpu.regs[r_03] = 0x03
    # Index 6 sets mcycle=0x0F; index 7 ticks to 0x10; index 8 reads pre-retire mcycle (0x11)
    prog = [
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MSCRATCH, rs1=r_0f),
        _csr_reg(F3_CSRRC, rd=r_csrrc, csr_addr=CSR_MSCRATCH, rs1=r_03),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MTVAL, rs1=r_0f),
        _csr_reg(F3_CSRRS, rd=r_mtval, csr_addr=CSR_MTVAL, rs1=0),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MIP, rs1=0),
        _csr_reg(F3_CSRRS, rd=r_mip, csr_addr=CSR_MIP, rs1=0),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MCYCLE, rs1=r_0f),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MCYCLEH, rs1=r_03),
        _csr_reg(F3_CSRRS, rd=r_cyc_lo, csr_addr=CSR_MCYCLE, rs1=0),
        _csr_reg(F3_CSRRS, rd=r_cyc_hi, csr_addr=CSR_MCYCLEH, rs1=0),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MINSTRET, rs1=r_0f),        # suppresses +1 this step
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MINSTRETH, rs1=r_03),       # suppresses +1 this step
        _csr_reg(F3_CSRRS, rd=r_ret_lo, csr_addr=CSR_MINSTRET, rs1=0),
        _csr_reg(F3_CSRRS, rd=r_ret_hi, csr_addr=CSR_MINSTRETH, rs1=0),
        _csr_imm(F3_CSRRWI, rd=r_ret_wi, csr_addr=CSR_MINSTRET, uimm=5),  # uimm write suppresses +1
        INSN_EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[r_csrrc] == 0x0F
    assert cpu.mscratch == 0x0C
    assert cpu.regs[r_mtval] == 0x0F
    assert cpu.regs[r_mip] == 0
    assert cpu.regs[r_cyc_lo] == 0x11
    assert cpu.regs[r_cyc_hi] == 0x03
    assert cpu.regs[r_ret_lo] == 0x0F
    assert cpu.regs[r_ret_hi] == 0x03
    assert cpu.regs[r_ret_wi] == 0x11
    assert cpu.minstret == (0x03 << 32) | 5


def test_clint_lo_hi_register_reads_and_writes() -> None:
    """Verify 32-bit CLINT mtime/mtimecmp LO/HI R/W, mtime tick advance, and unused offset reads."""
    cpu = RV32Oracle()
    r_0f, r_03, r_clint, r_mt_lo, r_mt_hi, r_cmp_lo, r_cmp_hi = 1, 2, 3, 18, 19, 20, 21
    cpu.regs[r_0f] = 0x0F
    cpu.regs[r_03] = 0x03
    cpu.regs[r_clint] = CLINT_BASE
    cpu.mtimecmp = 0x1122_3344_5566_7788
    # Store MTIME_LO=0x0F, then store MTIME_HI ticks mtime->0x10, then load MTIME_LO ticks->0x11
    prog = [
        _store(F3_SW, rs2=r_0f, rs1=r_clint, offset=CLINT_MTIME_LO),
        _store(F3_SW, rs2=r_03, rs1=r_clint, offset=CLINT_MTIME_HI),
        _load(F3_LW, rd=r_mt_lo, rs1=r_clint, offset=CLINT_MTIME_LO),
        _load(F3_LW, rd=r_mt_hi, rs1=r_clint, offset=CLINT_MTIME_HI),
        _load(F3_LW, rd=r_cmp_lo, rs1=r_clint, offset=CLINT_MTIMECMP_LO),
        _load(F3_LW, rd=r_cmp_hi, rs1=r_clint, offset=CLINT_MTIMECMP_HI),
        INSN_EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[r_mt_lo] == 0x11
    assert cpu.regs[r_mt_hi] == 0x03
    assert cpu.regs[r_cmp_lo] == 0x5566_7788
    assert cpu.regs[r_cmp_hi] == 0x1122_3344

    # Unused CLINT offsets read 0 and silently ignore writes
    assert cpu.read_u32(CLINT_BASE + UNMAPPED_MMIO_OFFSET) == 0
    cpu.write_u32(CLINT_BASE + UNMAPPED_MMIO_OFFSET, 0x1234)
    assert cpu.read_u32(CLINT_BASE + UNMAPPED_MMIO_OFFSET) == 0


def test_counter_carry_and_64bit_rollover() -> None:
    """Verify 32-bit low->high carry on mtime/mcycle/minstret and full 64-bit MASK64 rollover."""
    cpu = RV32Oracle()
    r_tmp = 1
    cpu.mtime = UINT32_MAX
    cpu.mcycle = UINT32_MAX
    cpu.minstret = UINT32_MAX
    cpu.load_words(BOOT_ROM_BASE, [_alu_i(F3_ADD_SUB, rd=r_tmp, rs1=0, imm=1)])
    cpu.step()
    assert cpu.mtime == 0x1_0000_0000
    assert cpu.mcycle == 0x1_0000_0000
    assert cpu.minstret == 0x1_0000_0000
    assert cpu.read_u32(CLINT_BASE + CLINT_MTIME_LO) == 0
    assert cpu.read_u32(CLINT_BASE + CLINT_MTIME_HI) == 1

    cpu.reset(reset_pc=BOOT_ROM_BASE)
    cpu.mtime = MASK64
    cpu.mcycle = MASK64
    cpu.minstret = MASK64
    cpu.load_words(BOOT_ROM_BASE, [_alu_i(F3_ADD_SUB, rd=r_tmp, rs1=0, imm=1)])
    cpu.step()
    assert cpu.mtime == 0
    assert cpu.mcycle == 0
    assert cpu.minstret == 0


def test_csr_warl_masks_and_mret_stack() -> None:
    """Verify CSR WARL masking, mtvec mode snapping, EBREAK MPIE push, and MRET MPIE->MIE pop."""
    cpu = RV32Oracle()
    r_all1, r_mode2, r_mode3, r_mip_rd = 1, 2, 3, 10
    cpu.regs[r_all1] = UINT32_MAX
    cpu.regs[r_mode2] = BRAM_BASE | 2                    # Reserved mtvec.mode=2 snaps to 0
    cpu.regs[r_mode3] = BRAM_BASE | 3                    # Reserved mtvec.mode=3 snaps to 0
    prog = [
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MSTATUS, rs1=r_all1),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MIE, rs1=r_all1),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MEPC, rs1=r_all1),
        INSN_EBREAK,                                     # index 3: stops run(), pushes MIE->MPIE
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MIP, rs1=r_all1),
        _csr_reg(F3_CSRRS, rd=r_mip_rd, csr_addr=CSR_MIP, rs1=0),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MTVEC, rs1=r_mode2),
        _csr_reg(F3_CSRRW, rd=0, csr_addr=CSR_MTVEC, rs1=r_mode3),
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    ebreak_pc = BOOT_ROM_BASE + 3 * INSN_SIZE_BYTES
    post_ebreak_pc = ebreak_pc + INSN_SIZE_BYTES
    cpu.run(stop_on_pc=ebreak_pc)

    assert cpu.mstatus == (MSTATUS_MIE_BIT | MSTATUS_MPIE_BIT | MSTATUS_MPP_M)
    assert cpu.mie == (MIE_MSIE_BIT | MIE_MTIE_BIT | MIE_MEIE_BIT)
    assert cpu.mepc == WORD_ALIGN_MASK

    assert cpu.step().trap_cause == CAUSE_BREAKPOINT
    assert cpu.mstatus == (MSTATUS_MPIE_BIT | MSTATUS_MPP_M)
    cpu.pc = post_ebreak_pc
    cpu.run(max_steps=4, stop_on_ebreak=False)
    assert cpu.regs[r_mip_rd] == (MIE_MSIE_BIT | MIE_MEIE_BIT)
    assert (cpu.mtvec & MTVEC_MODE_MASK) == 0

    cpu.reset(reset_pc=BOOT_ROM_BASE)
    cpu.mstatus = MSTATUS_MIE_BIT | MSTATUS_MPP_M
    cpu.mepc = BRAM_BASE
    cpu.load_words(BOOT_ROM_BASE, [INSN_MRET])
    cpu.step()
    assert cpu.mstatus == (MSTATUS_MPIE_BIT | MSTATUS_MPP_M)
    assert cpu.pc == BRAM_BASE


def test_ro_and_unimplemented_csr_trap_rules() -> None:
    """Verify RO CSRs allow rs1=x0 reads and trap on non-zero rs1 writes (even if reg == 0)."""
    cpu = RV32Oracle()
    r_wr_src, r_zero_reg, r_ro_dst = 1, 2, 10
    for ro_csr in (CSR_MISA, CSR_MVENDORID, CSR_MARCHID, CSR_MIMPID, CSR_MHARTID):
        cpu.reset(reset_pc=BOOT_ROM_BASE)
        cpu.load_words(
            BOOT_ROM_BASE,
            [
                _csr_reg(F3_CSRRS, rd=r_ro_dst, csr_addr=ro_csr, rs1=0),
                _csr_reg(F3_CSRRC, rd=r_ro_dst, csr_addr=ro_csr, rs1=0),
                _csr_reg(F3_CSRRW, rd=0, csr_addr=ro_csr, rs1=r_wr_src),
            ],
        )
        assert cpu.step().trap_cause is None
        assert cpu.regs[r_ro_dst] == (MISA_RV32IMX if ro_csr == CSR_MISA else 0)
        assert cpu.step().trap_cause is None
        assert cpu.step().trap_cause == CAUSE_ILLEGAL_INSN

    for trap_insn in [
        _csr_reg(F3_CSRRS, rd=r_ro_dst, csr_addr=CSR_MISA, rs1=r_zero_reg),
        _csr_reg(F3_CSRRC, rd=r_ro_dst, csr_addr=CSR_MISA, rs1=r_zero_reg),
        _csr_imm(F3_CSRRWI, rd=r_ro_dst, csr_addr=CSR_MISA, uimm=0),
        _csr_reg(F3_CSRRS, rd=r_ro_dst, csr_addr=UNIMPLEMENTED_CSR, rs1=0),
    ]:
        cpu.reset(reset_pc=BOOT_ROM_BASE)
        cpu.regs[r_ro_dst] = 0xBEEF_1234
        cpu.load_words(BOOT_ROM_BASE, [trap_insn])
        tr = cpu.step()
        assert tr.trap_cause == CAUSE_ILLEGAL_INSN
        assert cpu.regs[r_ro_dst] == 0xBEEF_1234
        assert cpu.mtval == trap_insn


def test_uart0_console_tx_rx_and_mmio_bounds() -> None:
    """Verify UART0 TX/RX FIFOs, SW byte mask, LB sign-ext, lw x0 pop, STATUS RO, and BAUDDIV."""
    tx_seen: list[int] = []
    cpu = RV32Oracle(uart_tx_callback=tx_seen.append)
    cpu.push_uart_rx(bytes([ord("O"), ord("K"), ord("Z"), 0x80, ord("Q")]))

    r_uart, r_h, r_i, r_sw_a, r_baud_set = 1, 2, 3, 4, 5
    r_baud_rd, r_stat_pre, r_rx1, r_rx2, r_rx3, r_rx_lb, r_tx_rd, r_stat_post = (
        8, 9, 10, 11, 12, 13, 14, 15
    )
    cpu.regs[r_uart] = UART0_BASE
    cpu.regs[r_h] = ord("H")
    cpu.regs[r_i] = ord("i")
    cpu.regs[r_sw_a] = 0xDEAD_0021                        # Low byte '!' (0x21)
    cpu.regs[r_baud_set] = 25

    prog = [
        _store(F3_SB, rs2=r_h, rs1=r_uart, offset=UART0_TXDATA),
        _store(F3_SB, rs2=r_i, rs1=r_uart, offset=UART0_TXDATA),
        _store(F3_SW, rs2=r_sw_a, rs1=r_uart, offset=UART0_TXDATA),
        _store(F3_SW, rs2=r_baud_set, rs1=r_uart, offset=UART0_BAUDDIV),
        _load(F3_LW, rd=r_baud_rd, rs1=r_uart, offset=UART0_BAUDDIV),
        _store(F3_SW, rs2=r_baud_set, rs1=r_uart, offset=UART0_STATUS),  # RO ignored
        _load(F3_LW, rd=r_stat_pre, rs1=r_uart, offset=UART0_STATUS),
        _load(F3_LW, rd=r_rx1, rs1=r_uart, offset=UART0_RXDATA),
        _load(F3_LW, rd=r_rx2, rs1=r_uart, offset=UART0_RXDATA),
        _load(F3_LBU, rd=r_rx3, rs1=r_uart, offset=UART0_RXDATA),
        _load(F3_LB, rd=r_rx_lb, rs1=r_uart, offset=UART0_RXDATA),       # 0x80 -> 0xFFFF_FF80
        _load(F3_LW, rd=0, rs1=r_uart, offset=UART0_RXDATA),             # pops 'Q' even if rd==x0
        _load(F3_LW, rd=r_tx_rd, rs1=r_uart, offset=UART0_TXDATA),       # WO TXDATA reads 0
        _load(F3_LW, rd=r_stat_post, rs1=r_uart, offset=UART0_STATUS),
        INSN_EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.read_uart_tx(clear=True) == b"Hi!"
    assert cpu.read_uart_tx() == b""
    assert bytes(tx_seen) == b"Hi!"
    assert cpu.regs[r_baud_rd] == 25
    assert (cpu.regs[r_stat_pre] & UART0_STATUS_RX_VALID) == UART0_STATUS_RX_VALID
    assert cpu.regs[r_rx1] == ord("O")
    assert cpu.regs[r_rx2] == ord("K")
    assert cpu.regs[r_rx3] == ord("Z")
    assert cpu.regs[r_rx_lb] == u32(-128)
    assert cpu.regs[0] == 0
    assert cpu.regs[r_tx_rd] == 0
    assert (cpu.regs[r_stat_post] & UART0_STATUS_RX_VALID) == 0

    cpu.write_u32(UART0_BASE + UART0_BAUDDIV, 0)
    assert cpu.read_u32(UART0_BASE + UART0_BAUDDIV) == 1
    assert cpu.read_u32(UART0_BASE + UNMAPPED_MMIO_OFFSET) == 0
    cpu.write_u32(UART0_BASE + UNMAPPED_MMIO_OFFSET, 0x1234)
    assert cpu.read_u32(UART0_BASE + UNMAPPED_MMIO_OFFSET) == 0
    assert cpu.read_u32(UART0_BASE + UART0_RXDATA) == 0


def test_bus_invalid_widths_and_sparse_region_faults() -> None:
    """Verify host bus_read/bus_write and SparseMemory reject bad widths or unmapped addresses."""
    cpu = RV32Oracle()
    for bad_addr, width in [
        (CLINT_BASE + 1, 4),
        (CLINT_BASE, 1),
        (UART0_BASE + 1, 1),
        (UART0_BASE, 2),
        (UART0_BASE + UART0_STATUS, 1),
        (UART0_BASE + UART0_BAUDDIV, 1),
        (BRAM_BASE, 3),
    ]:
        with pytest.raises(MemoryAccessFault):
            cpu.bus_read(bad_addr, width)
        with pytest.raises(MemoryAccessFault):
            cpu.bus_write(bad_addr, width, 0)

    with pytest.raises(MemoryAccessFault):
        cpu.bram.read_bytes(UNMAPPED_BUS_ADDR, 1)
    with pytest.raises(MemoryAccessFault):
        cpu.bram.write_bytes(UNMAPPED_BUS_ADDR, 1, 0)


def test_cpu_mmio_width_traps_and_non_executable_fetches() -> None:
    """Verify CPU traps on bad CLINT/UART widths and refuses to execute CLINT/UART/stub/unmapped."""
    cpu = RV32Oracle()
    r_ptr, r_dst = 1, 2
    for bad_insn, ptr, expected_cause in [
        (_load(F3_LB, rd=r_dst, rs1=r_ptr, offset=0), CLINT_BASE, CAUSE_LOAD_ACCESS_FAULT),
        (_load(F3_LH, rd=r_dst, rs1=r_ptr, offset=0), UART0_BASE, CAUSE_LOAD_ACCESS_FAULT),
        (_store(F3_SB, rs2=0, rs1=r_ptr, offset=UART0_STATUS), UART0_BASE, CAUSE_STORE_ACCESS_FAULT),
        (_store(F3_SB, rs2=0, rs1=r_ptr, offset=UART0_BAUDDIV), UART0_BASE, CAUSE_STORE_ACCESS_FAULT),
    ]:
        cpu.reset(reset_pc=BOOT_ROM_BASE)
        cpu.regs[r_ptr] = ptr
        cpu.load_words(BOOT_ROM_BASE, [bad_insn])
        assert cpu.step().trap_cause == expected_cause

    # Fetching from UART0_RXDATA must trap WITHOUT popping queued RX FIFO
    cpu.reset(reset_pc=UART0_BASE + UART0_RXDATA)
    cpu.push_uart_rx("A")
    assert cpu.step().trap_cause == CAUSE_INSN_ACCESS_FAULT
    assert cpu.read_u32(UART0_BASE + UART0_RXDATA) == ord("A")

    for non_exec_pc in (CLINT_BASE, MMIO_STUB_BASE, UNMAPPED_BUS_ADDR):
        cpu.reset(reset_pc=non_exec_pc)
        assert cpu.step().trap_cause == CAUSE_INSN_ACCESS_FAULT


def test_xapex_custom_mac_dot_product_and_saturation() -> None:
    """Verify Xapex dual-int16 SIMD MAC ops (mac, mac.clr, mac.set, mac.get), x0 wb, and +/- sat."""
    cpu = RV32Oracle()
    r_bias, r_p1_a, r_p1_b, r_p2_a, r_p2_b, r_max, r_min = 1, 2, 3, 4, 5, 6, 7
    r_set, r_acc1, r_acc2, r_get, r_hi, r_pos_sat, r_neg_sat, r_neg_stay = (
        10, 11, 12, 13, 14, 15, 16, 17
    )
    cpu.regs[r_bias] = 1000
    cpu.regs[r_p1_a] = pack_i16(10, -20)
    cpu.regs[r_p1_b] = pack_i16(5, 6)
    cpu.regs[r_p2_a] = pack_i16(30, -40)
    cpu.regs[r_p2_b] = pack_i16(-7, 8)
    cpu.regs[r_max] = pack_i16(32767, 32767)
    cpu.regs[r_min] = pack_i16(-32768, -32768)

    prog = [
        _mac_op(MAC_F3_SET, rd=r_set, rs1=r_bias),               # mac.set -> 1000
        _mac_op(MAC_F3_ACC, rd=r_acc1, rs1=r_p1_a, rs2=r_p1_b),  # 1000 + (50 - 120) = 930
        _mac_op(MAC_F3_ACC, rd=r_acc2, rs1=r_p2_a, rs2=r_p2_b),  # 930 + (-210 - 320) = 400
        _mac_op(MAC_F3_GET, rd=r_get),                           # 400
        _mac_op(MAC_F3_CLR, rd=r_hi, rs1=r_max, rs2=r_max),      # 2 * 32767^2
        _mac_op(MAC_F3_ACC, rd=r_pos_sat, rs1=r_max, rs2=r_max), # + clamp -> INT32_MAX
        _mac_op(MAC_F3_CLR, rd=0, rs1=r_min, rs2=r_min),         # (-32768)^2 * 2 -> INT32_MAX, x0=0
        _mac_op(MAC_F3_CLR, rd=r_neg_sat, rs1=r_max, rs2=r_min), # -2 * 32767 * 32768
        _mac_op(MAC_F3_ACC, rd=r_neg_sat, rs1=r_max, rs2=r_min), # - clamp -> INT32_MIN
        _mac_op(MAC_F3_ACC, rd=r_neg_stay, rs1=r_max, rs2=r_min),# remains INT32_MIN
        INSN_EBREAK,
    ]
    cpu.load_words(BOOT_ROM_BASE, prog)
    cpu.run()

    assert cpu.regs[r_set] == 1000
    assert cpu.regs[r_acc1] == 930
    assert cpu.regs[r_acc2] == 400
    assert cpu.regs[r_get] == 400
    assert cpu.regs[r_hi] == u32(2 * 32767 * 32767)
    assert cpu.regs[r_pos_sat] == INT32_MAX
    assert cpu.regs[0] == 0
    assert cpu.regs[r_neg_sat] == u32(INT32_MIN)
    assert cpu.regs[r_neg_stay] == u32(INT32_MIN)
    assert cpu.mac_acc == INT32_MIN


def test_illegal_instructions_and_misaligned_pc_traps() -> None:
    """Verify illegal opcodes/funct fields, misaligned targets, and exact mtval/mepc/mcause."""
    cpu = RV32Oracle()
    r_base, r_dst = 1, 2
    cpu.reset(reset_pc=BOOT_ROM_BASE + 2)
    assert cpu.step().trap_cause == CAUSE_INSN_MISALIGNED
    assert cpu.mepc == BOOT_ROM_BASE
    assert cpu.mtval == BOOT_ROM_BASE + 2
    assert cpu.minstret == 0

    trap_cases = [
        (_branch(F3_BEQ, rs1=0, rs2=0, offset=2), 0, CAUSE_INSN_MISALIGNED, BOOT_ROM_BASE + 2),
        (_jal(rd=r_dst, offset=2), 0, CAUSE_INSN_MISALIGNED, BOOT_ROM_BASE + 2),
        (_jalr(rd=r_dst, rs1=r_base, offset=2), BRAM_BASE, CAUSE_INSN_MISALIGNED, BRAM_BASE + 2),
        (enc_i(0, r_base, INVALID_JALR_FUNCT3, r_dst, OPCODE_JALR), BRAM_BASE, CAUSE_ILLEGAL_INSN, None),
        (_alu_r(F3_ADD_SUB, rd=r_dst, rs1=0, rs2=0, funct7=INVALID_FUNCT7), 0, CAUSE_ILLEGAL_INSN, None),
        (enc_r(F7_BASE, 0, 0, INVALID_MAC_FUNCT3, r_dst, OPCODE_CUSTOM0), 0, CAUSE_ILLEGAL_INSN, None),
        (enc_r(F7_MULDIV, 0, 0, 0, r_dst, OPCODE_CUSTOM0), 0, CAUSE_ILLEGAL_INSN, None),
        (_branch(INVALID_BRANCH_FUNCT3, rs1=0, rs2=0, offset=4), 0, CAUSE_ILLEGAL_INSN, None),
        (_load(INVALID_FUNCT3, rd=r_dst, rs1=r_base, offset=0), BRAM_BASE, CAUSE_ILLEGAL_INSN, None),
        (_store(INVALID_FUNCT3, rs2=r_dst, rs1=r_base, offset=0), BRAM_BASE, CAUSE_ILLEGAL_INSN, None),
        (_shift_i(F3_SLL, rd=r_dst, rs1=0, shamt=0, funct7=F7_MULDIV), 0, CAUSE_ILLEGAL_INSN, None),
        (_shift_i(F3_SRL_SRA, rd=r_dst, rs1=0, shamt=0, funct7=F7_MULDIV), 0, CAUSE_ILLEGAL_INSN, None),
        (_alu_r(F3_SLL, rd=r_dst, rs1=0, rs2=0, funct7=F7_ALT), 0, CAUSE_ILLEGAL_INSN, None),
        (enc_i(0, 0, INVALID_MISC_MEM_FUNCT3, r_dst, OPCODE_MISC_MEM), 0, CAUSE_ILLEGAL_INSN, None),
        (SYSTEM_UNKNOWN_PRIV, 0, CAUSE_ILLEGAL_INSN, None),
        (_csr_reg(RESERVED_ZICSR_FUNCT3, rd=r_dst, csr_addr=CSR_MISA, rs1=0), 0, CAUSE_ILLEGAL_INSN, None),
        (INVALID_INSN_WORD, 0, CAUSE_ILLEGAL_INSN, None),
    ]
    for insn, base_val, expected_cause, mtval_override in trap_cases:
        cpu.reset(reset_pc=BOOT_ROM_BASE)
        cpu.regs[r_base] = base_val
        cpu.regs[r_dst] = 0x1234_5678
        cpu.load_words(BOOT_ROM_BASE, [insn])
        tr = cpu.step()
        assert tr.trap_cause == expected_cause
        assert cpu.mcause == expected_cause
        assert cpu.mepc == BOOT_ROM_BASE
        assert cpu.mtval == (insn if mtval_override is None else mtval_override)
        assert cpu.regs[r_dst] == 0x1234_5678
        assert cpu.minstret == 0


def test_run_after_ebreak_trap_dispatch() -> None:
    """Verify run(stop_on_ebreak=False) continues stepping inside the trap handler."""
    cpu = RV32Oracle()
    r_handler_ran = 10
    cpu.mtvec = BRAM_BASE
    cpu.load_words(BOOT_ROM_BASE, [INSN_EBREAK])
    cpu.load_words(BRAM_BASE, [_alu_i(F3_ADD_SUB, rd=r_handler_ran, rs1=0, imm=99)])
    cpu.run(max_steps=2, stop_on_ebreak=False)
    assert cpu.halted
    assert cpu.regs[r_handler_ran] == 99
