<script setup lang="ts">
import { computed, ref } from 'vue'

interface PresetInsn {
  label: string
  asm: string
  word: number
}

const presets: PresetInsn[] = [
  { label: 'I-Type: addi', asm: 'addi x1, x0, -5', word: 0xffb00093 },
  { label: 'Shift-Imm: srai', asm: 'srai x7, x1, 1', word: 0x4010d393 },
  { label: 'R-Type: add', asm: 'add x3, x1, x2', word: 0x002081b3 },
  { label: 'R-Type: sub', asm: 'sub x4, x1, x2', word: 0x40208233 },
  { label: 'RV32M: div', asm: 'div x14, x1, x2', word: 0x0220c733 },
  { label: 'Xapex: mac', asm: 'mac x11, x2, x3', word: 0x0031058b },
  { label: 'Load: lh', asm: 'lh x6, 0(x1)', word: 0x00009303 },
  { label: 'S-Type: sw', asm: 'sw x2, 12(x1)', word: 0x0020a623 },
  { label: 'B-Type: blt', asm: 'blt x2, x3, -8', word: 0xfe314ce3 },
  { label: 'U-Type: lui', asm: 'lui x22, 0x12345', word: 0x12345b37 },
  { label: 'J-Type: jal', asm: 'jal x5, +8', word: 0x008002ef },
  { label: 'Zicsr: csrrs', asm: 'csrrs x25, mcause, x0', word: 0x34202cf3 },
]

const insnWord = ref<number>(0xffb00093)
const hexInput = ref<string>('0xFFB00093')

function selectPreset(p: PresetInsn) {
  insnWord.value = p.word >>> 0
  hexInput.value = `0x${(p.word >>> 0).toString(16).toUpperCase().padStart(8, '0')}`
}

function onHexChange() {
  const cleaned = hexInput.value.replace(/[^0-9a-fA-F]/g, '')
  if (cleaned.length > 0) {
    insnWord.value = Number.parseInt(cleaned.slice(-8), 16) >>> 0
  }
}

function flipBit(bit: number) {
  insnWord.value = (insnWord.value ^ (1 << bit)) >>> 0
  hexInput.value = `0x${insnWord.value.toString(16).toUpperCase().padStart(8, '0')}`
}

function signExtend(val: number, bits: number): number {
  const signBit = 1 << (bits - 1)
  const mask = (1 << bits) - 1
  const masked = val & mask
  return (masked ^ signBit) - signBit
}

interface FieldSpan {
  name: string
  range: string
  bits: string
  value: string
  color: string
  widthCols: number
  title?: string
}

function fmtHex2(n: number): string {
  return `0x${n.toString(16).toUpperCase().padStart(2, '0')}`
}

function rdSuffix(rd: number): string {
  return rd === 0 ? ' (discarded because x0 stays 0)' : ''
}

const rAluNames: Record<number, string> = {
  0: 'add (Add Registers)',
  1: 'sll (Shift Left Logical)',
  2: 'slt (Set if Signed Less Than)',
  3: 'sltu (Set if Unsigned Less Than)',
  4: 'xor (Bitwise Exclusive-OR)',
  5: 'srl (Shift Right Logical)',
  6: 'or (Bitwise OR)',
  7: 'and (Bitwise AND)',
}

const rMulNames: Record<number, string> = {
  0: 'mul (Multiply Lower 32 Bits)',
  1: 'mulh (Multiply Upper 32 Bits, Signed × Signed)',
  2: 'mulhsu (Multiply Upper 32 Bits, Signed × Unsigned)',
  3: 'mulhu (Multiply Upper 32 Bits, Unsigned × Unsigned)',
  4: 'div (Signed Divide Toward Zero)',
  5: 'divu (Unsigned Divide)',
  6: 'rem (Signed Remainder)',
  7: 'remu (Unsigned Remainder)',
}

const decoded = computed(() => {
  const w = insnWord.value >>> 0
  const opcode = w & 0x7f
  const rd = (w >>> 7) & 0x1f
  const funct3 = (w >>> 12) & 0x7
  const rs1 = (w >>> 15) & 0x1f
  const rs2 = (w >>> 20) & 0x1f
  const funct7 = (w >>> 25) & 0x7f

  const b = (hi: number, lo: number) =>
    ((w >>> lo) & ((1 << (hi - lo + 1)) - 1)).toString(2).padStart(hi - lo + 1, '0')

  // R-Type & Custom-0 Xapex MAC
  if (opcode === 0x33 || opcode === 0x0b) {
    const isMac = opcode === 0x0b
    let opName = 'Illegal R-Type Instruction (Raises Trap Cause 2)'
    let effect = 'Traps to mtvec with mcause = 2 (Illegal Instruction).'
    if (isMac && funct7 === 0x00) {
      if (funct3 === 0) {
        opName = 'mac (Dual-Int16 Multiply-Accumulate)'
        effect = `Reads x${rs1} and x${rs2} as packed int16 pairs, accumulates into mac_acc with sat32 clamp, and writes x${rd}${rdSuffix(rd)}.`
      } else if (funct3 === 1) {
        opName = 'mac.clr (Zero Accumulator & Multiply-Accumulate)'
        effect = `Reads x${rs1} and x${rs2} as packed int16 pairs, ignores prior mac_acc, writes clamped product sum to mac_acc and x${rd}${rdSuffix(rd)}.`
      } else if (funct3 === 2) {
        opName = 'mac.set (Preload 32-Bit Bias into Accumulator)'
        effect = `Reads signed x${rs1}, stores into mac_acc, and writes x${rd}${rdSuffix(rd)} (rs2 unused).`
      } else if (funct3 === 3) {
        opName = 'mac.get (Read Accumulator into Register)'
        effect = `Copies internal mac_acc without modifying it into x${rd}${rdSuffix(rd)} (rs1 and rs2 unused).`
      } else {
        opName = 'Illegal Xapex Sub-Operation (Trap Cause 2)'
      }
    } else if (!isMac && funct7 === 0x01) {
      opName = rMulNames[funct3]
      effect = `Reads x${rs1} and x${rs2}, computes ${opName}, and writes x${rd}${rdSuffix(rd)}.`
    } else if (!isMac && funct7 === 0x00) {
      opName = rAluNames[funct3]
      effect = `Reads x${rs1} and x${rs2}, computes ${opName}, and writes x${rd}${rdSuffix(rd)}.`
    } else if (!isMac && funct7 === 0x20) {
      if (funct3 === 0) {
        opName = 'sub (Subtract Registers)'
        effect = `Computes x${rs1} - x${rs2} and writes x${rd}${rdSuffix(rd)}.`
      } else if (funct3 === 5) {
        opName = 'sra (Shift Right Arithmetic)'
        effect = `Arithmetic-shifts x${rs1} right by (x${rs2} & 0x1F) and writes x${rd}${rdSuffix(rd)}.`
      } else {
        opName = 'Illegal funct7/funct3 Combination (Trap Cause 2)'
      }
    }
    const spans: FieldSpan[] = [
      { name: 'funct7', range: 'Bits 31..25', bits: b(31, 25), value: fmtHex2(funct7), color: 'var(--hw-purple)', widthCols: 7 },
      { name: 'rs2 (Src 2)', range: 'Bits 24..20', bits: b(24, 20), value: `x${rs2}`, color: 'var(--hw-amber)', widthCols: 5 },
      { name: 'rs1 (Src 1)', range: 'Bits 19..15', bits: b(19, 15), value: `x${rs1}`, color: 'var(--hw-green)', widthCols: 5 },
      { name: 'funct3', range: 'Bits 14..12', bits: b(14, 12), value: `${funct3}`, color: 'var(--hw-cyan)', widthCols: 3 },
      { name: 'rd (Dest)', range: 'Bits 11..7', bits: b(11, 7), value: `x${rd}`, color: 'var(--vp-c-brand-1)', widthCols: 5 },
      { name: 'opcode', range: 'Bits 6..0', bits: b(6, 0), value: fmtHex2(opcode), color: 'var(--hw-pink)', widthCols: 7 },
    ]
    return {
      format: isMac ? 'R-Type (Custom-0 Xapex Neural Extension)' : 'R-Type (Register-Register)',
      mnemonic: opName,
      immExplain: isMac
        ? `Custom-0 neural instruction: mac and mac.clr read rs1 and rs2; mac.set reads rs1 (ignores rs2); mac.get ignores rs1 and rs2.`
        : 'No embedded constant — all three 5-bit register columns (rd, rs1, rs2) are active, leaving 10 bits (funct7 + funct3) to select the exact operation.',
      effect,
      spans,
    }
  }

  // Shift-Immediate Specialization (OP-IMM with funct3 == 1 or 5)
  if (opcode === 0x13 && (funct3 === 1 || funct3 === 5)) {
    const shamt = rs2
    let opName = 'Illegal Shift-Immediate (Trap Cause 2)'
    if (funct3 === 1 && funct7 === 0x00) opName = 'slli (Shift Left Logical Immediate)'
    else if (funct3 === 5 && funct7 === 0x00) opName = 'srli (Shift Right Logical Immediate)'
    else if (funct3 === 5 && funct7 === 0x20) opName = 'srai (Shift Right Arithmetic Immediate)'

    return {
      format: 'I-Type (Shift-Immediate Specialization)',
      mnemonic: opName,
      immExplain: `Bits 24..20 hold the 5-bit shift amount (shamt = ${shamt}), leaving Bits 31..25 as funct7 (${fmtHex2(funct7)}) to select shift mode (0x00 for slli/srli vs 0x20 for srai).`,
      effect: opName.startsWith('Illegal')
        ? 'Traps to mtvec with mcause = 2 (Illegal Instruction).'
        : `Shifts x${rs1} by ${shamt} bit(s) and writes result into x${rd}${rdSuffix(rd)}.`,
      spans: [
        { name: 'funct7 (Shift Mode)', range: 'Bits 31..25', bits: b(31, 25), value: fmtHex2(funct7), color: 'var(--hw-purple)', widthCols: 7 },
        { name: 'shamt (Count)', range: 'Bits 24..20', bits: b(24, 20), value: `${shamt}`, color: 'var(--hw-amber)', widthCols: 5 },
        { name: 'rs1 (Src 1)', range: 'Bits 19..15', bits: b(19, 15), value: `x${rs1}`, color: 'var(--hw-green)', widthCols: 5 },
        { name: 'funct3', range: 'Bits 14..12', bits: b(14, 12), value: `${funct3}`, color: 'var(--hw-cyan)', widthCols: 3 },
        { name: 'rd (Dest)', range: 'Bits 11..7', bits: b(11, 7), value: `x${rd}`, color: 'var(--vp-c-brand-1)', widthCols: 5 },
        { name: 'opcode', range: 'Bits 6..0', bits: b(6, 0), value: '0x13', color: 'var(--hw-pink)', widthCols: 7 },
      ],
    }
  }

  // SYSTEM & Zicsr (opcode 0x73)
  if (opcode === 0x73) {
    const csrAddr = (w >>> 20) & 0xfff
    const csrHex = `0x${csrAddr.toString(16).toUpperCase().padStart(3, '0')}`
    if (funct3 === 0) {
      const sysMap: Record<number, [string, string]> = {
        0x00000073: ['ecall (Environment Call)', 'Raises synchronous trap (mcause = 11) jumping PC to mtvec.'],
        0x00100073: ['ebreak (Environment Breakpoint)', 'Sets halted = True and raises breakpoint trap (mcause = 3).'],
        0x30200073: ['mret (Machine Trap Return)', 'Restores mstatus.MIE from MPIE and jumps PC back to mepc.'],
        0x10500073: ['wfi (Wait For Interrupt)', 'Idle wait hint; advances PC to PC + 4 as a sequential no-op in the oracle.'],
      }
      const hit = sysMap[w] ?? [
        'Illegal SYSTEM Instruction (Trap Cause 2)',
        `Unassigned SYSTEM encoding (Bits 31..20 = ${csrHex}, rs1 = x${rs1}, rd = x${rd}; valid SYSTEM words require rs1 = x0 and rd = x0); traps to mtvec with mcause = 2.`,
      ]
      return {
        format: 'I-Type (Privileged SYSTEM Instruction)',
        mnemonic: hit[0],
        immExplain: `Bits 31..20 = ${csrHex} with rs1 = x${rs1} and rd = x${rd} (privileged encodings require rs1 = x0 and rd = x0).`,
        effect: hit[1],
        spans: [
          { name: 'System Function', range: 'Bits 31..20', bits: b(31, 20), value: csrHex, color: 'var(--hw-purple)', widthCols: 12 },
          { name: 'rs1', range: 'Bits 19..15', bits: b(19, 15), value: `x${rs1}`, color: 'var(--hw-green)', widthCols: 5 },
          { name: 'funct3', range: 'Bits 14..12', bits: b(14, 12), value: '0', color: 'var(--hw-cyan)', widthCols: 3 },
          { name: 'rd', range: 'Bits 11..7', bits: b(11, 7), value: `x${rd}`, color: 'var(--vp-c-brand-1)', widthCols: 5 },
          { name: 'opcode', range: 'Bits 6..0', bits: b(6, 0), value: '0x73', color: 'var(--hw-pink)', widthCols: 7 },
        ],
      }
    }

    const rwCsrs: Record<number, string> = {
      0x300: 'mstatus',
      0x304: 'mie',
      0x305: 'mtvec',
      0x340: 'mscratch',
      0x341: 'mepc',
      0x342: 'mcause',
      0x343: 'mtval',
      0x344: 'mip',
      0xb00: 'mcycle',
      0xb02: 'minstret',
      0xb80: 'mcycleh',
      0xb82: 'minstreth',
    }
    const roCsrs: Record<number, string> = {
      0x301: 'misa',
      0xf11: 'mvendorid',
      0xf12: 'marchid',
      0xf13: 'mimpid',
      0xf14: 'mhartid',
    }
    const csrOps: Record<number, string> = {
      1: 'csrrw (Atomic CSR Read & Write)',
      2: 'csrrs (Atomic CSR Read & Set Bits)',
      3: 'csrrc (Atomic CSR Read & Clear Bits)',
      5: 'csrrwi (Atomic CSR Read & Write 5-Bit Constant)',
      6: 'csrrsi (Atomic CSR Read & Set 5-Bit Constant)',
      7: 'csrrci (Atomic CSR Read & Clear 5-Bit Constant)',
    }
    const isImm = (funct3 & 0x4) !== 0
    const isSetOrClear = (funct3 & 0x3) === 2 || (funct3 & 0x3) === 3
    const suppressWrite = isSetOrClear && rs1 === 0
    const csrName = rwCsrs[csrAddr] ?? roCsrs[csrAddr]
    const isReadOnly = csrAddr in roCsrs
    let opName = csrOps[funct3] ?? 'Illegal Zicsr funct3=4 (Trap Cause 2)'
    let csrEffect = 'Traps with mcause = 2 (Illegal Instruction).'
    if (funct3 !== 4) {
      if (!csrName) {
        opName = `Illegal Unimplemented CSR ${csrHex} (Trap Cause 2)`
        csrEffect = `CSR address ${csrHex} is unimplemented in RV32Oracle; traps to mtvec with mcause = 2 without updating x${rd}.`
      } else if (isReadOnly && !suppressWrite) {
        opName = `Illegal Write to Read-Only CSR ${csrName} (Trap Cause 2)`
        csrEffect = `CSR ${csrName} (${csrHex}) is read-only and write is not suppressed (${isImm ? 'uimm' : 'rs1'} != 0 or csrrw/csrrwi); traps with mcause = 2.`
      } else if (suppressWrite) {
        csrEffect = `Reads CSR ${csrName} (${csrHex}) into x${rd}${rdSuffix(rd)} and suppresses write (safe read-only query because ${isImm ? 'uimm' : 'rs1'} == 0).`
      } else {
        csrEffect = `Atomically reads CSR ${csrName} (${csrHex}) into x${rd}${rdSuffix(rd)} and writes updated value using ${isImm ? `constant ${rs1}` : `x${rs1}`}.`
      }
    }
    return {
      format: 'I-Type (Zicsr Control & Status Register Access)',
      mnemonic: opName,
      immExplain: `Bits 31..20 hold unsigned 12-bit CSR address ${csrHex}${isImm ? `; Bits 19..15 hold unsigned 5-bit constant uimm = ${rs1}` : ''}.`,
      effect: csrEffect,
      spans: [
        { name: 'CSR Address (12-Bit)', range: 'Bits 31..20', bits: b(31, 20), value: csrHex, color: 'var(--hw-purple)', widthCols: 12 },
        { name: isImm ? 'uimm (5-Bit)' : 'rs1 (Src 1)', range: 'Bits 19..15', bits: b(19, 15), value: isImm ? `${rs1}` : `x${rs1}`, color: 'var(--hw-green)', widthCols: 5 },
        { name: 'funct3', range: 'Bits 14..12', bits: b(14, 12), value: `${funct3}`, color: 'var(--hw-cyan)', widthCols: 3 },
        { name: 'rd (Dest)', range: 'Bits 11..7', bits: b(11, 7), value: `x${rd}`, color: 'var(--vp-c-brand-1)', widthCols: 5 },
        { name: 'opcode', range: 'Bits 6..0', bits: b(6, 0), value: '0x73', color: 'var(--hw-pink)', widthCols: 7 },
      ],
    }
  }

  // Standard I-Type (OP-IMM, LOAD, JALR, FENCE)
  if (opcode === 0x13 || opcode === 0x03 || opcode === 0x67 || opcode === 0x0f) {
    const imm12Raw = (w >>> 20) & 0xfff
    const imm12 = signExtend(imm12Raw, 12)
    let opName = 'I-Type Operation'
    let effect = ''
    if (opcode === 0x13) {
      const iNames: Record<number, string> = {
        0: 'addi (Add 12-Bit Immediate)',
        2: 'slti (Set if Signed Less Than Immediate)',
        3: 'sltiu (Set if Unsigned Less Than Immediate)',
        4: 'xori (Bitwise Exclusive-OR Immediate)',
        6: 'ori (Bitwise OR Immediate)',
        7: 'andi (Bitwise AND Immediate)',
      }
      opName = iNames[funct3]
      effect = `Reads x${rs1}, combines with sign-extended 12-bit constant (${imm12}), and writes x${rd}${rdSuffix(rd)}.`
    } else if (opcode === 0x03) {
      const lNames: Record<number, string> = {
        0: 'lb (Load Signed 8-Bit Byte)',
        1: 'lh (Load Signed 16-Bit Halfword)',
        2: 'lw (Load 32-Bit Word)',
        4: 'lbu (Load Unsigned 8-Bit Byte)',
        5: 'lhu (Load Unsigned 16-Bit Halfword)',
      }
      opName = lNames[funct3] ?? 'Illegal Load Width (Trap Cause 2)'
      effect = lNames[funct3]
        ? `Computes byte address x${rs1} + (${imm12}), reads little-endian memory, and writes x${rd}${rdSuffix(rd)}.`
        : 'Traps with mcause = 2 (Illegal Instruction).'
    } else if (opcode === 0x67) {
      opName = funct3 === 0 ? 'jalr (Jump and Link Register)' : 'Illegal jalr funct3 (Trap Cause 2)'
      effect = funct3 === 0
        ? `Saves return address (PC + 4) into x${rd}${rdSuffix(rd)} and jumps to (x${rs1} + (${imm12})) & 0xFFFF_FFFE (traps with mcause = 0 if Bit 1 is 1).`
        : 'Traps with mcause = 2 (Illegal Instruction).'
    } else {
      const fenceHex = `0x${imm12Raw.toString(16).toUpperCase().padStart(3, '0')}`
      opName =
        funct3 === 0
          ? 'fence (Memory Ordering Barrier)'
          : funct3 === 1
            ? 'fence.i (Instruction Stream Barrier)'
            : 'Illegal fence funct3 (Trap Cause 2)'
      effect =
        funct3 === 0 || funct3 === 1
          ? 'Synchronizes memory/instruction order; advances PC to PC + 4 in sequential oracle.'
          : 'Traps with mcause = 2 (Illegal Instruction).'
      return {
        format: 'I-Type (Memory / Instruction Stream Barrier)',
        mnemonic: opName,
        immExplain: `Bits 31..20 hold ordering mode/predecessor/successor bits (${fenceHex}) rather than an arithmetic offset.`,
        effect,
        spans: [
          { name: 'Ordering Flags', range: 'Bits 31..20', bits: b(31, 20), value: fenceHex, color: 'var(--hw-purple)', widthCols: 12 },
          { name: 'rs1 (Src 1)', range: 'Bits 19..15', bits: b(19, 15), value: `x${rs1}`, color: 'var(--hw-green)', widthCols: 5 },
          { name: 'funct3', range: 'Bits 14..12', bits: b(14, 12), value: `${funct3}`, color: 'var(--hw-cyan)', widthCols: 3 },
          { name: 'rd (Dest)', range: 'Bits 11..7', bits: b(11, 7), value: `x${rd}`, color: 'var(--vp-c-brand-1)', widthCols: 5 },
          { name: 'opcode', range: 'Bits 6..0', bits: b(6, 0), value: '0x0F', color: 'var(--hw-pink)', widthCols: 7 },
        ],
      }
    }
    return {
      format: 'I-Type (12-Bit Signed Constant)',
      mnemonic: opName,
      immExplain: `Bits 31..20 hold 12-bit constant 0x${imm12Raw.toString(16).toUpperCase().padStart(3, '0')} → sign_extend(..., 12) = ${imm12}.`,
      effect,
      spans: [
        { name: '12-Bit Constant', range: 'Bits 31..20', bits: b(31, 20), value: `${imm12}`, color: 'var(--hw-purple)', widthCols: 12 },
        { name: 'rs1 (Src 1)', range: 'Bits 19..15', bits: b(19, 15), value: `x${rs1}`, color: 'var(--hw-green)', widthCols: 5 },
        { name: 'funct3', range: 'Bits 14..12', bits: b(14, 12), value: `${funct3}`, color: 'var(--hw-cyan)', widthCols: 3 },
        { name: 'rd (Dest)', range: 'Bits 11..7', bits: b(11, 7), value: `x${rd}`, color: 'var(--vp-c-brand-1)', widthCols: 5 },
        { name: 'opcode', range: 'Bits 6..0', bits: b(6, 0), value: fmtHex2(opcode), color: 'var(--hw-pink)', widthCols: 7 },
      ],
    }
  }

  // S-Type
  if (opcode === 0x23) {
    const imm12Raw = (funct7 << 5) | rd
    const imm12 = signExtend(imm12Raw, 12)
    const names: Record<number, string> = {
      0: 'sb (Store 8-Bit Byte)',
      1: 'sh (Store 16-Bit Halfword)',
      2: 'sw (Store 32-Bit Word)',
    }
    return {
      format: 'S-Type (Memory Store — Split 12-Bit Offset)',
      mnemonic: names[funct3] ?? 'Illegal Store Width (Trap Cause 2)',
      immExplain: `Stores read both rs1 (base) and rs2 (data) with no rd, so the 12-bit offset splits across Bits 31..25 (${b(31, 25)}) and Bits 11..7 (${b(11, 7)}) → signed offset ${imm12}.`,
      effect: names[funct3]
        ? `Writes low byte(s) of x${rs2} to memory address x${rs1} + (${imm12}).`
        : 'Traps with mcause = 2 (Illegal Instruction).',
      scrambleNote: `Reassembly: Bits 31..25 (${b(31, 25)}) + Bits 11..7 (${b(11, 7)}) → 0b${imm12Raw.toString(2).padStart(12, '0')} = ${imm12}`,
      spans: [
        { name: 'Off Bits 11..5', range: 'Bits 31..25', bits: b(31, 25), value: `0b${b(31, 25)}`, color: 'var(--hw-purple)', widthCols: 7 },
        { name: 'rs2 (Data)', range: 'Bits 24..20', bits: b(24, 20), value: `x${rs2}`, color: 'var(--hw-amber)', widthCols: 5 },
        { name: 'rs1 (Base)', range: 'Bits 19..15', bits: b(19, 15), value: `x${rs1}`, color: 'var(--hw-green)', widthCols: 5 },
        { name: 'funct3', range: 'Bits 14..12', bits: b(14, 12), value: `${funct3}`, color: 'var(--hw-cyan)', widthCols: 3 },
        { name: 'Off Bits 4..0', range: 'Bits 11..7', bits: b(11, 7), value: `0b${b(11, 7)}`, color: 'var(--hw-purple)', widthCols: 5 },
        { name: 'opcode', range: 'Bits 6..0', bits: b(6, 0), value: '0x23', color: 'var(--hw-pink)', widthCols: 7 },
      ],
    }
  }

  // B-Type (explicit contiguous bit columns)
  if (opcode === 0x63) {
    const imm13Raw =
      (((w >>> 31) & 1) << 12) |
      (((w >>> 7) & 1) << 11) |
      (((w >>> 25) & 0x3f) << 5) |
      (((w >>> 8) & 0xf) << 1)
    const imm13 = signExtend(imm13Raw, 13)
    const names: Record<number, string> = {
      0: 'beq (Branch if Equal)',
      1: 'bne (Branch if Not Equal)',
      4: 'blt (Branch if Signed Less Than)',
      5: 'bge (Branch if Signed Greater or Equal)',
      6: 'bltu (Branch if Unsigned Less Than)',
      7: 'bgeu (Branch if Unsigned Greater or Equal)',
    }
    return {
      format: 'B-Type (PC-Relative Conditional Branch)',
      mnemonic: names[funct3] ?? 'Illegal Branch Condition (Trap Cause 2)',
      immExplain: `Bit 31 → Off Bit 12 (sign), Bit 7 → Off Bit 11, Bits 30..25 → Off Bits 10..5, Bits 11..8 → Off Bits 4..1, plus implicit Off Bit 0 = 0 → ${imm13 >= 0 ? `+${imm13}` : imm13} bytes.`,
      effect: names[funct3]
        ? `Compares x${rs1} and x${rs2}; if condition holds, jumps to PC + (${imm13}), else advances to PC + 4.`
        : 'Traps with mcause = 2 (Illegal Instruction).',
      scrambleNote: `Reassembly: Bit 31 (${b(31, 31)}) · Bit 7 (${b(7, 7)}) · Bits 30..25 (${b(30, 25)}) · Bits 11..8 (${b(11, 8)}) · 0 → ${imm13 >= 0 ? `+${imm13}` : imm13} B`,
      spans: [
        { name: 'S', range: '31', bits: b(31, 31), value: b(31, 31), color: 'var(--hw-purple)', widthCols: 1, title: 'Bit 31 -> Offset Bit 12 (Sign)' },
        { name: 'Off Bits 10..5', range: 'Bits 30..25', bits: b(30, 25), value: `0b${b(30, 25)}`, color: 'var(--hw-purple)', widthCols: 6 },
        { name: 'rs2 (Src 2)', range: 'Bits 24..20', bits: b(24, 20), value: `x${rs2}`, color: 'var(--hw-amber)', widthCols: 5 },
        { name: 'rs1 (Src 1)', range: 'Bits 19..15', bits: b(19, 15), value: `x${rs1}`, color: 'var(--hw-green)', widthCols: 5 },
        { name: 'funct3', range: 'Bits 14..12', bits: b(14, 12), value: `${funct3}`, color: 'var(--hw-cyan)', widthCols: 3 },
        { name: 'Off Bits 4..1', range: 'Bits 11..8', bits: b(11, 8), value: `0b${b(11, 8)}`, color: 'var(--hw-purple)', widthCols: 4 },
        { name: '11', range: '7', bits: b(7, 7), value: b(7, 7), color: 'var(--hw-purple)', widthCols: 1, title: 'Bit 7 -> Offset Bit 11' },
        { name: 'opcode', range: 'Bits 6..0', bits: b(6, 0), value: '0x63', color: 'var(--hw-pink)', widthCols: 7 },
      ],
    }
  }

  // U-Type
  if (opcode === 0x37 || opcode === 0x17) {
    const upper = (w & 0xfffff000) >>> 0
    const upper20Hex = `0x${(upper >>> 12).toString(16).toUpperCase().padStart(5, '0')}`
    const fullHex = `0x${upper.toString(16).toUpperCase().padStart(8, '0')}`
    const isLui = opcode === 0x37
    return {
      format: 'U-Type (20-Bit Upper Constant)',
      mnemonic: isLui ? 'lui (Load Upper Immediate)' : 'auipc (Add Upper Immediate to Program Counter)',
      immExplain: `Bits 31..12 supply upper 20 bits (${upper20Hex}), placed in Bits 31..12 with Bits 11..0 zeroed → ${fullHex}.`,
      effect: isLui
        ? `Writes ${fullHex} into x${rd}${rdSuffix(rd)}.`
        : `Writes PC + ${fullHex} into x${rd}${rdSuffix(rd)}.`,
      spans: [
        { name: 'Upper 20-Bit Constant', range: 'Bits 31..12', bits: b(31, 12), value: upper20Hex, color: 'var(--hw-purple)', widthCols: 20 },
        { name: 'rd (Dest)', range: 'Bits 11..7', bits: b(11, 7), value: `x${rd}`, color: 'var(--vp-c-brand-1)', widthCols: 5 },
        { name: 'opcode', range: 'Bits 6..0', bits: b(6, 0), value: fmtHex2(opcode), color: 'var(--hw-pink)', widthCols: 7 },
      ],
    }
  }

  // J-Type (explicit 4 scrambled bit slices across Bits 31..12)
  if (opcode === 0x6f) {
    const imm21Raw =
      (((w >>> 31) & 1) << 20) |
      (((w >>> 12) & 0xff) << 12) |
      (((w >>> 20) & 1) << 11) |
      (((w >>> 21) & 0x3ff) << 1)
    const imm21 = signExtend(imm21Raw, 21)
    return {
      format: 'J-Type (21-Bit PC-Relative Jump)',
      mnemonic: 'jal (Jump and Link Subroutine)',
      immExplain: `Bit 31 → Off Bit 20 (sign), Bits 19..12 → Off Bits 19..12, Bit 20 → Off Bit 11, Bits 30..21 → Off Bits 10..1, plus implicit Off Bit 0 = 0 → ${imm21 >= 0 ? `+${imm21}` : imm21} bytes.`,
      effect: `Saves return link address (PC + 4) into x${rd}${rdSuffix(rd)} and jumps to PC + (${imm21}).`,
      scrambleNote: `Reassembly: Bit 31 (${b(31, 31)}) · Bits 19..12 (${b(19, 12)}) · Bit 20 (${b(20, 20)}) · Bits 30..21 (${b(30, 21)}) · 0 → ${imm21 >= 0 ? `+${imm21}` : imm21} B`,
      spans: [
        { name: 'S', range: '31', bits: b(31, 31), value: b(31, 31), color: 'var(--hw-purple)', widthCols: 1, title: 'Bit 31 -> Offset Bit 20 (Sign)' },
        { name: 'Off Bits 10..1', range: 'Bits 30..21', bits: b(30, 21), value: `0b${b(30, 21)}`, color: 'var(--hw-purple)', widthCols: 10 },
        { name: '11', range: '20', bits: b(20, 20), value: b(20, 20), color: 'var(--hw-purple)', widthCols: 1, title: 'Bit 20 -> Offset Bit 11' },
        { name: 'Off Bits 19..12', range: 'Bits 19..12', bits: b(19, 12), value: `0b${b(19, 12)}`, color: 'var(--hw-purple)', widthCols: 8 },
        { name: 'rd (Link)', range: 'Bits 11..7', bits: b(11, 7), value: `x${rd}`, color: 'var(--vp-c-brand-1)', widthCols: 5 },
        { name: 'opcode', range: 'Bits 6..0', bits: b(6, 0), value: '0x6F', color: 'var(--hw-pink)', widthCols: 7 },
      ],
    }
  }

  return {
    format: 'Unknown / Illegal Opcode',
    mnemonic: 'Raises CAUSE_ILLEGAL_INSN (Trap Cause 2)',
    immExplain: `Opcode ${fmtHex2(opcode)} is unassigned in RV32IM + Zicsr + Xapex.`,
    effect: 'Redirects PC to mtvec trap handler with mcause = 2 and mtval = offending 32-bit instruction word.',
    spans: [
      { name: 'Upper Bits', range: 'Bits 31..7', bits: b(31, 7), value: '—', color: 'var(--vp-c-text-2)', widthCols: 25 },
      { name: 'opcode', range: 'Bits 6..0', bits: b(6, 0), value: fmtHex2(opcode), color: 'var(--hw-red)', widthCols: 7 },
    ],
  }
})

// Precompute SVG geometry for each decoded field span across 32 columns (viewBox 716 x 122)
const COL_W = 22
const LEFT_PAD = 6
const positionedSpans = computed(() => {
  let cursor = 0
  return decoded.value.spans.map((sp) => {
    const x = LEFT_PAD + cursor * COL_W
    const w = sp.widthCols * COL_W
    cursor += sp.widthCols
    return { ...sp, x, w }
  })
})
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">32-Bit Instruction Bitfield Decoder (Bits 31..0)</div>
      <div style="display: flex; align-items: center; gap: 6px">
        <span style="font-size: 12px; color: var(--vp-c-text-2)">Hex Word:</span>
        <input
          v-model="hexInput"
          type="text"
          class="hw-mono"
          style="
            width: 118px;
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid var(--vp-c-divider);
            background: var(--vp-c-bg);
            font-size: 13px;
            font-weight: 700;
          "
          @input="onHexChange"
        />
      </div>
    </div>

    <!-- Preset Buttons -->
    <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px">
      <button
        v-for="p in presets"
        :key="p.label"
        type="button"
        class="hw-btn"
        :class="{ active: (insnWord >>> 0) === (p.word >>> 0) }"
        :title="p.asm"
        @click="selectPreset(p)"
      >
        {{ p.label }}
      </button>
    </div>

    <!-- Interactive 32-bit SVG wire & field schematic -->
    <div class="hw-label">Click any wire cell (Bit 31 down to Bit 0) to flip its bit and watch fields re-decode:</div>
    <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect all 32 bit wires</div>
    <div style="overflow-x: auto; padding-bottom: 4px; margin-bottom: 8px">
      <svg
        viewBox="0 0 716 126"
        class="hw-svg-diagram"
        style="min-width: 550px"
        role="img"
        aria-label="Interactive 32-bit instruction wire decoder showing clickable bits 31 down to 0 wired to aligned field boxes"
      >
        <!-- Row 1: 32 clickable bit switches -->
        <g
          v-for="bitIdx in 32"
          :key="`wire-${bitIdx}`"
          style="cursor: pointer"
          @click="flipBit(32 - bitIdx)"
        >
          <rect
            :x="LEFT_PAD + (bitIdx - 1) * COL_W + 1"
            y="4"
            :width="COL_W - 2"
            height="34"
            rx="4"
            :fill="((insnWord >>> (32 - bitIdx)) & 1) ? 'var(--vp-c-brand-soft)' : 'var(--vp-c-bg)'"
            stroke="var(--vp-c-divider)"
            stroke-width="1"
          />
          <text
            :x="LEFT_PAD + (bitIdx - 1) * COL_W + COL_W / 2"
            y="16"
            text-anchor="middle"
            font-size="8"
            font-family="var(--vp-font-family-mono)"
            fill="var(--vp-c-text-2)"
          >
            {{ 32 - bitIdx }}
          </text>
          <text
            :x="LEFT_PAD + (bitIdx - 1) * COL_W + COL_W / 2"
            y="32"
            text-anchor="middle"
            font-size="11.5"
            font-weight="700"
            font-family="var(--vp-font-family-mono)"
            fill="var(--vp-c-brand-1)"
          >
            {{ (insnWord >>> (32 - bitIdx)) & 1 }}
          </text>
        </g>

        <!-- Bracket connectors & Aligned Field Spans -->
        <g v-for="(sp, idx) in positionedSpans" :key="`span-${idx}`">
          <!-- Wire group bracket dropping from bit cells into field box -->
          <path
            :d="`M ${sp.x + 3} 41 L ${sp.x + 3} 47 L ${sp.x + sp.w - 3} 47 L ${sp.x + sp.w - 3} 41 M ${sp.x + sp.w / 2} 47 L ${sp.x + sp.w / 2} 55`"
            fill="none"
            :stroke="sp.color"
            stroke-width="1.3"
          />
          <rect
            :x="sp.x + 1"
            y="56"
            :width="sp.w - 2"
            height="64"
            rx="5"
            fill="var(--vp-c-bg)"
            stroke="var(--vp-c-divider)"
            stroke-width="1"
          />
          <rect
            :x="sp.x + 1"
            y="56"
            :width="sp.w - 2"
            height="3.5"
            rx="1.5"
            :fill="sp.color"
          />
          <text
            :x="sp.x + sp.w / 2"
            y="74"
            text-anchor="middle"
            :font-size="sp.widthCols === 1 ? '8.5' : sp.widthCols <= 3 ? '9' : '9.5'"
            font-weight="700"
            font-family="var(--vp-font-family-mono)"
            :fill="sp.color"
          >
            {{ sp.range }}
          </text>
          <text
            :x="sp.x + sp.w / 2"
            y="92"
            text-anchor="middle"
            :font-size="sp.widthCols === 1 ? '9.5' : sp.widthCols <= 4 ? '9.5' : '10.5'"
            font-weight="700"
            fill="var(--vp-c-text-1)"
          >
            {{ sp.name }}
          </text>
          <text
            :x="sp.x + sp.w / 2"
            y="110"
            text-anchor="middle"
            :font-size="sp.widthCols === 1 ? '9.5' : sp.widthCols <= 4 ? '9.5' : '10.5'"
            font-family="var(--vp-font-family-mono)"
            fill="var(--vp-c-text-2)"
          >
            {{ sp.value }}
          </text>
        </g>
      </svg>

      <div
        v-if="decoded.spans.some((sp) => sp.widthCols === 1)"
        class="hw-mono"
        style="margin-top: 4px; font-size: 11px; color: var(--vp-c-text-2)"
      >
        <template v-if="(insnWord & 0x7f) === 0x63">
          Legend: <strong>S</strong> = Sign bit pinned at Bit 31 (Offset Bit 12); <strong>11</strong> = Offset Bit 11 at Bit 7.
        </template>
        <template v-else>
          Legend: <strong>S</strong> = Sign bit pinned at Bit 31 (Offset Bit 20); <strong>11</strong> = Offset Bit 11 at Bit 20.
        </template>
      </div>

      <div
        v-if="'scrambleNote' in decoded && decoded.scrambleNote"
        class="hw-mono"
        style="
          margin-top: 6px;
          padding: 5px 8px;
          border-radius: 6px;
          background: rgba(139, 92, 246, 0.08);
          border: 1px solid rgba(139, 92, 246, 0.3);
          font-size: 11.5px;
        "
      >
        {{ decoded.scrambleNote }}
      </div>
    </div>

    <!-- Decoded Meaning Cards -->
    <div class="hw-grid-2">
      <div class="hw-card">
        <div class="hw-label">{{ decoded.format }}</div>
        <div style="font-size: 14px; font-weight: 700; color: var(--vp-c-brand-1); margin-bottom: 4px">
          {{ decoded.mnemonic }}
        </div>
        <div style="font-size: 12.5px; color: var(--vp-c-text-2)">
          {{ decoded.immExplain }}
        </div>
      </div>
      <div class="hw-card">
        <div class="hw-label">What <code>RV32Oracle.step()</code> Executes</div>
        <div style="font-size: 13px">
          {{ decoded.effect }}
        </div>
      </div>
    </div>
  </div>
</template>
