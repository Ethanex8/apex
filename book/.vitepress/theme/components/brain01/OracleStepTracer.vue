<script setup lang="ts">
import { computed, ref } from 'vue'

interface TraceFrame {
  stepNum: number
  asm: string
  stageNote: string
  pc: string
  insnHex: string
  nextPc: string
  regs: Record<string, string>
  changedKey: string
  csrs: Record<string, string>
  memBytes?: { addr: string; byteHex: string }[]
  traceReceipt: string
}

interface Scenario {
  id: string
  title: string
  summary: string
  frames: TraceFrame[]
}

const scenarios: Scenario[] = [
  {
    id: 'loop_call',
    title: '1. Subroutine Call & Return (jal, jalr & Hardwired x0)',
    summary:
      'Loads 1 and 2, calls a helper via jal (saving return link PC + 4 in x5), and returns via jalr x0, 0(x5) (discarding the unused link write into hardwired x0).',
    frames: [
      {
        stepNum: 0,
        asm: 'Power-On Reset (Before Step 1)',
        stageNote: 'reset() sets PC = 0x0000_0000 (Boot ROM), all regs[0..31] = 0, mcycle = 0.',
        pc: '0x0000_0000',
        insnHex: '—',
        nextPc: '0x0000_0000',
        regs: { x0: '0x0000_0000', x1: '0x0000_0000', x2: '0x0000_0000', x5: '0x0000_0000' },
        changedKey: '',
        csrs: { mcycle: '0', minstret: '0' },
        traceReceipt: 'Ready at BOOT_ROM_BASE (0x0000_0000)',
      },
      {
        stepNum: 1,
        asm: '0x00: addi x1, x0, 1   # Add Immediate: x1 = 0 + 1',
        stageNote: 'Reads x0 (0) + sign_extend(1, 12) → commits 1 to x1; PC advances to 0x04.',
        pc: '0x0000_0000',
        insnHex: '0x0010_0093',
        nextPc: '0x0000_0004',
        regs: { x0: '0x0000_0000', x1: '0x0000_0001', x2: '0x0000_0000', x5: '0x0000_0000' },
        changedKey: 'x1',
        csrs: { mcycle: '1', minstret: '1' },
        traceReceipt: 'StepTrace(pc=0x00, insn=0x00100093, next_pc=0x04, rd=1, rd_val=1)',
      },
      {
        stepNum: 2,
        asm: '0x04: addi x2, x0, 2   # Add Immediate: x2 = 0 + 2',
        stageNote: 'Reads x0 (0) + 2 → commits 2 to x2; PC advances to 0x08.',
        pc: '0x0000_0004',
        insnHex: '0x0020_0113',
        nextPc: '0x0000_0008',
        regs: { x0: '0x0000_0000', x1: '0x0000_0001', x2: '0x0000_0002', x5: '0x0000_0000' },
        changedKey: 'x2',
        csrs: { mcycle: '2', minstret: '2' },
        traceReceipt: 'StepTrace(pc=0x04, insn=0x00200113, next_pc=0x08, rd=2, rd_val=2)',
      },
      {
        stepNum: 3,
        asm: '0x08: jal x5, +8       # Jump and Link to helper at 0x10',
        stageNote: 'Saves return link (0x08 + 4 = 0x0C) into x5 and jumps PC to 0x08 + 8 = 0x10.',
        pc: '0x0000_0008',
        insnHex: '0x0080_02EF',
        nextPc: '0x0000_0010',
        regs: { x0: '0x0000_0000', x1: '0x0000_0001', x2: '0x0000_0002', x5: '0x0000_000C' },
        changedKey: 'x5',
        csrs: { mcycle: '3', minstret: '3' },
        traceReceipt: 'StepTrace(pc=0x08, insn=0x008002EF, next_pc=0x10, rd=5, rd_val=0x0C)',
      },
      {
        stepNum: 4,
        asm: '0x10: add x1, x1, x2   # Add Registers: x1 = 1 + 2 = 3',
        stageNote: 'Adds x1 (1) + x2 (2) → writes 3 to x1; PC advances to 0x14.',
        pc: '0x0000_0010',
        insnHex: '0x0020_80B3',
        nextPc: '0x0000_0014',
        regs: { x0: '0x0000_0000', x1: '0x0000_0003', x2: '0x0000_0002', x5: '0x0000_000C' },
        changedKey: 'x1',
        csrs: { mcycle: '4', minstret: '4' },
        traceReceipt: 'StepTrace(pc=0x10, insn=0x002080B3, next_pc=0x14, rd=1, rd_val=3)',
      },
      {
        stepNum: 5,
        asm: '0x14: jalr x0, 0(x5)   # Jump and Link Register: return to 0x0C',
        stageNote: '_set_reg(0, 0x18) discards write so x0 remains 0x0000_0000; PC jumps back to caller at 0x0C.',
        pc: '0x0000_0014',
        insnHex: '0x0002_8067',
        nextPc: '0x0000_000C',
        regs: { x0: '0x0000_0000', x1: '0x0000_0003', x2: '0x0000_0002', x5: '0x0000_000C' },
        changedKey: '',
        csrs: { mcycle: '5', minstret: '5' },
        traceReceipt: 'StepTrace(pc=0x14, insn=0x00028067, next_pc=0x0C, rd=0, rd_val=0)',
      },
    ],
  },
  {
    id: 'endian_mem',
    title: '2. Little-Endian Byte Lanes (sw, lb vs lbu & sh)',
    summary:
      'Stores 0x1122_80FF at BRAM (0x1000_0000), compares signed byte load lb (-1) vs unsigned lbu (+255), and overwrites upper halfword (+2..+3) via sh.',
    frames: [
      {
        stepNum: 0,
        asm: 'Preloaded Test Setup: x1 = 0x1000_0000 (BRAM), x2 = 0x1122_80FF',
        stageNote:
          'Test setup preloads x1 (BRAM base) and x2 (4-byte test pattern) at PC = 0; 4 unwritten bytes at 0x1000_0000..03 start at 0.',
        pc: '0x0000_0000',
        insnHex: '—',
        nextPc: '0x0000_0000',
        regs: { x1: '0x1000_0000', x2: '0x1122_80FF', x4: '0x0000_0000', x5: '0x0000_0000' },
        changedKey: '',
        csrs: { mcycle: '0', minstret: '0' },
        memBytes: [
          { addr: '+0', byteHex: '0x00' },
          { addr: '+1', byteHex: '0x00' },
          { addr: '+2', byteHex: '0x00' },
          { addr: '+3', byteHex: '0x00' },
        ],
        traceReceipt: 'Ready — unwritten BRAM bytes default to 0',
      },
      {
        stepNum: 1,
        asm: '0x00: sw x2, 0(x1)     # Store 32-Bit Word in little-endian order',
        stageNote: 'Least-significant byte 0xFF lands at +0; most-significant byte 0x11 lands at +3.',
        pc: '0x0000_0000',
        insnHex: '0x0020_A023',
        nextPc: '0x0000_0004',
        regs: { x1: '0x1000_0000', x2: '0x1122_80FF', x4: '0x0000_0000', x5: '0x0000_0000' },
        changedKey: '',
        csrs: { mcycle: '1', minstret: '1' },
        memBytes: [
          { addr: '+0', byteHex: '0xFF' },
          { addr: '+1', byteHex: '0x80' },
          { addr: '+2', byteHex: '0x22' },
          { addr: '+3', byteHex: '0x11' },
        ],
        traceReceipt: 'StepTrace(pc=0x00, mem_addr=0x10000000, mem_val=0x112280FF, mem_write=True)',
      },
      {
        stepNum: 2,
        asm: '0x04: lb x4, 0(x1)     # Load Signed Byte from +0',
        stageNote: 'Reads 0xFF (Bit 7 = 1) → sign_extend(0xFF, 8) = -1 → 0xFFFF_FFFF in x4.',
        pc: '0x0000_0004',
        insnHex: '0x0000_8203',
        nextPc: '0x0000_0008',
        regs: { x1: '0x1000_0000', x2: '0x1122_80FF', x4: '0xFFFF_FFFF', x5: '0x0000_0000' },
        changedKey: 'x4',
        csrs: { mcycle: '2', minstret: '2' },
        memBytes: [
          { addr: '+0', byteHex: '0xFF' },
          { addr: '+1', byteHex: '0x80' },
          { addr: '+2', byteHex: '0x22' },
          { addr: '+3', byteHex: '0x11' },
        ],
        traceReceipt: 'StepTrace(pc=0x04, rd=4, rd_val=0xFFFFFFFF, mem_addr=0x10000000)',
      },
      {
        stepNum: 3,
        asm: '0x08: lbu x5, 0(x1)    # Load Unsigned Byte from +0',
        stageNote: 'Reads same 0xFF byte → zero-extends Bits 31..8 → 0x0000_00FF (255) in x5.',
        pc: '0x0000_0008',
        insnHex: '0x0000_C283',
        nextPc: '0x0000_000C',
        regs: { x1: '0x1000_0000', x2: '0x1122_80FF', x4: '0xFFFF_FFFF', x5: '0x0000_00FF' },
        changedKey: 'x5',
        csrs: { mcycle: '3', minstret: '3' },
        memBytes: [
          { addr: '+0', byteHex: '0xFF' },
          { addr: '+1', byteHex: '0x80' },
          { addr: '+2', byteHex: '0x22' },
          { addr: '+3', byteHex: '0x11' },
        ],
        traceReceipt: 'StepTrace(pc=0x08, rd=5, rd_val=0x000000FF, mem_addr=0x10000000)',
      },
      {
        stepNum: 4,
        asm: '0x0C: sh x2, 2(x1)     # Store 16-Bit Halfword (0x80FF) at +2..+3',
        stageNote: 'Overwrites bytes +2 (0xFF) and +3 (0x80), turning the 32-bit word into 0x80FF_80FF.',
        pc: '0x0000_000C',
        insnHex: '0x0020_9123',
        nextPc: '0x0000_0010',
        regs: { x1: '0x1000_0000', x2: '0x1122_80FF', x4: '0xFFFF_FFFF', x5: '0x0000_00FF' },
        changedKey: '',
        csrs: { mcycle: '4', minstret: '4' },
        memBytes: [
          { addr: '+0', byteHex: '0xFF' },
          { addr: '+1', byteHex: '0x80' },
          { addr: '+2', byteHex: '0xFF' },
          { addr: '+3', byteHex: '0x80' },
        ],
        traceReceipt: 'StepTrace(pc=0x0C, mem_addr=0x10000002, mem_val=0x80FF, mem_write=True)',
      },
    ],
  },
  {
    id: 'trap_irq',
    title: '3. Exact Trap & Timer Preemption (1 Instruction per Step)',
    summary:
      'Executes one Oracle.step() call per frame with vectored mtvec = 0x1000_0001: ecall traps to 0x1000_0000 (advancing mepc to 0x18), then CLINT preempts 0x18 at mtime = 4 and branches to 0x1000_001C.',
    frames: [
      {
        stepNum: 0,
        asm: 'Initial State: PC=0x14, mtvec=0x1000_0001 (Vectored), mtimecmp=4',
        stageNote: 'Preloaded: x1=0x18 (next PC after ecall), x2=0x8000_0000 (CLINT), x3=0xFFFF_FFFF.',
        pc: '0x0000_0014',
        insnHex: '—',
        nextPc: '0x0000_0014',
        regs: { x1: '0x0000_0018', x2: '0x8000_0000', x3: '0xFFFF_FFFF', x20: '0x0000_0000' },
        changedKey: '',
        csrs: {
          mtvec: '0x1000_0001 (Vectored)',
          mstatus: 'MIE=1, MPIE=0',
          mie: 'MTIE=1 (Bit 7)',
          mepc: '0x0000_0000',
          mcause: '0x0',
          'mtime / cmp': '0 / 0x0000_0000_0000_0004',
          'mcycle / minstret': '0 / 0',
        },
        traceReceipt: 'Interrupts enabled; main program at PC = 0x14',
      },
      {
        stepNum: 1,
        asm: '0x0000_0014: ecall                  # Synchronous Environment Call',
        stageNote: 'Saves mepc=0x14, mcause=11, shifts MIE→MPIE, clears MIE=0, jumps to mtvec base 0x1000_0000 (minstret stays 0).',
        pc: '0x0000_0014',
        insnHex: '0x0000_0073',
        nextPc: '0x1000_0000',
        regs: { x1: '0x0000_0018', x2: '0x8000_0000', x3: '0xFFFF_FFFF', x20: '0x0000_0000' },
        changedKey: '',
        csrs: {
          mtvec: '0x1000_0001 (Vectored)',
          mstatus: 'MIE=0, MPIE=1',
          mie: 'MTIE=1 (Bit 7)',
          mepc: '0x0000_0014',
          mcause: '11 (ecall)',
          'mtime / cmp': '1 / 0x0000_0000_0000_0004',
          'mcycle / minstret': '1 / 0',
        },
        traceReceipt: 'StepTrace(pc=0x14, insn=0x00000073, next_pc=0x10000000, trap_cause=11)',
      },
      {
        stepNum: 2,
        asm: '0x1000_0000: csrrw x0, mepc, x1     # Advance mepc to 0x18 (past ecall)',
        stageNote: 'Exception handler writes x1 (0x18) into mepc so mret will not re-run ecall.',
        pc: '0x1000_0000',
        insnHex: '0x3410_9073',
        nextPc: '0x1000_0004',
        regs: { x1: '0x0000_0018', x2: '0x8000_0000', x3: '0xFFFF_FFFF', x20: '0x0000_0000' },
        changedKey: '',
        csrs: {
          mtvec: '0x1000_0001 (Vectored)',
          mstatus: 'MIE=0, MPIE=1',
          mie: 'MTIE=1 (Bit 7)',
          mepc: '0x0000_0018',
          mcause: '11 (ecall)',
          'mtime / cmp': '2 / 0x0000_0000_0000_0004',
          'mcycle / minstret': '2 / 1',
        },
        traceReceipt: 'StepTrace(pc=0x10000000, insn=0x34109073, next_pc=0x10000004)',
      },
      {
        stepNum: 3,
        asm: '0x1000_0004: mret                   # Return from ecall handler',
        stageNote: 'Restores mstatus.MIE = 1 (from MPIE) and jumps PC back to mepc = 0x18.',
        pc: '0x1000_0004',
        insnHex: '0x3020_0073',
        nextPc: '0x0000_0018',
        regs: { x1: '0x0000_0018', x2: '0x8000_0000', x3: '0xFFFF_FFFF', x20: '0x0000_0000' },
        changedKey: '',
        csrs: {
          mtvec: '0x1000_0001 (Vectored)',
          mstatus: 'MIE=1, MPIE=1',
          mie: 'MTIE=1 (Bit 7)',
          mepc: '0x0000_0018',
          mcause: '11 (ecall)',
          'mtime / cmp': '3 / 0x0000_0000_0000_0004',
          'mcycle / minstret': '3 / 2',
        },
        traceReceipt: 'StepTrace(pc=0x10000004, insn=0x30200073, next_pc=0x00000018)',
      },
      {
        stepNum: 4,
        asm: '[Interrupt] mtime reaches 4 (>= mtimecmp) before fetching 0x18',
        stageNote: 'Saves unexecuted mepc=0x18, mcause=0x8000_0007, and vectored mtvec branches directly to base + 4*7 = 0x1000_001C.',
        pc: '0x0000_0018',
        insnHex: '0x0000_0000 (Timer Interrupt)',
        nextPc: '0x1000_001C',
        regs: { x1: '0x0000_0018', x2: '0x8000_0000', x3: '0xFFFF_FFFF', x20: '0x0000_0000' },
        changedKey: '',
        csrs: {
          mtvec: '0x1000_0001 (Vectored)',
          mstatus: 'MIE=0, MPIE=1',
          mie: 'MTIE=1 (Bit 7)',
          mepc: '0x0000_0018',
          mcause: '0x8000_0007',
          'mtime / cmp': '4 / 0x0000_0000_0000_0004',
          'mcycle / minstret': '4 / 2',
        },
        traceReceipt: 'StepTrace(pc=0x18, next_pc=0x1000001C, trap_cause=0x80000007, interrupt=True)',
      },
      {
        stepNum: 5,
        asm: '0x1000_001C: sw x3, 12(x2)          # Write 0xFFFF_FFFF to mtimecmp_hi',
        stageNote: 'Raises upper 32 bits of mtimecmp to 0xFFFF_FFFF_0000_0004, silencing the alarm while keeping mepc = 0x18.',
        pc: '0x1000_001C',
        insnHex: '0x0031_2623',
        nextPc: '0x1000_0020',
        regs: { x1: '0x0000_0018', x2: '0x8000_0000', x3: '0xFFFF_FFFF', x20: '0x0000_0000' },
        changedKey: '',
        csrs: {
          mtvec: '0x1000_0001 (Vectored)',
          mstatus: 'MIE=0, MPIE=1',
          mie: 'MTIE=1 (Bit 7)',
          mepc: '0x0000_0018',
          mcause: '0x8000_0007',
          'mtime / cmp': '5 / 0xFFFF_FFFF_0000_0004',
          'mcycle / minstret': '5 / 3',
        },
        traceReceipt: 'StepTrace(pc=0x1000001C, mem_addr=0x8000000C, mem_val=0xFFFFFFFF, mem_write=True)',
      },
      {
        stepNum: 6,
        asm: '0x1000_0020: mret                   # Return from Timer Interrupt',
        stageNote: 'Restores MIE=1 and jumps back to mepc=0x18 so the preempted instruction executes.',
        pc: '0x1000_0020',
        insnHex: '0x3020_0073',
        nextPc: '0x0000_0018',
        regs: { x1: '0x0000_0018', x2: '0x8000_0000', x3: '0xFFFF_FFFF', x20: '0x0000_0000' },
        changedKey: '',
        csrs: {
          mtvec: '0x1000_0001 (Vectored)',
          mstatus: 'MIE=1, MPIE=1',
          mie: 'MTIE=1 (Bit 7)',
          mepc: '0x0000_0018',
          mcause: '0x8000_0007',
          'mtime / cmp': '6 / 0xFFFF_FFFF_0000_0004',
          'mcycle / minstret': '6 / 4',
        },
        traceReceipt: 'StepTrace(pc=0x10000020, insn=0x30200073, next_pc=0x00000018)',
      },
      {
        stepNum: 7,
        asm: '0x0000_0018: addi x20, x0, 42       # Preempted main instruction executes',
        stageNote: 'Commits 42 to x20. Note mcycle (7) > minstret (5) by the 2 trap entries.',
        pc: '0x0000_0018',
        insnHex: '0x02A0_0A13',
        nextPc: '0x0000_001C',
        regs: { x1: '0x0000_0018', x2: '0x8000_0000', x3: '0xFFFF_FFFF', x20: '0x0000_002A (+42)' },
        changedKey: 'x20',
        csrs: {
          mtvec: '0x1000_0001 (Vectored)',
          mstatus: 'MIE=1, MPIE=1',
          mie: 'MTIE=1 (Bit 7)',
          mepc: '0x0000_0018',
          mcause: '0x8000_0007',
          'mtime / cmp': '7 / 0xFFFF_FFFF_0000_0004',
          'mcycle / minstret': '7 / 5',
        },
        traceReceipt: 'StepTrace(pc=0x18, insn=0x02A00A13, next_pc=0x1C, rd=20, rd_val=42)',
      },
    ],
  },
  {
    id: 'xapex_mac',
    title: '4. Custom Xapex MAC (Parallel Dual-Int16 Lanes & Saturation)',
    summary:
      'Displays all packed input registers alongside destination registers, executing one Xapex instruction per step and saturating overflow at INT32_MAX.',
    frames: [
      {
        stepNum: 0,
        asm: 'Initial State: Preloaded Bias & Packed Dual-Int16 Vectors',
        stageNote: 'x1 = +1000 (bias); packed dual-16-bit pairs (Bits 31..16, Bits 15..0): x2 = (-20, +10), x3 = (+6, +5), x6 = (+32767, +32767).',
        pc: '0x0000_0000',
        insnHex: '—',
        nextPc: '0x0000_0000',
        regs: {
          'x1 (bias)': '+1,000',
          'x2 (a1,a0)': '0xFFEC_000A (-20,+10)',
          'x3 (b1,b0)': '0x0006_0005 (+6,+5)',
          'x6 (max)': '0x7FFF_7FFF (+32767,+32767)',
          x10: '0',
          x11: '0',
          x14: '0',
          x15: '0',
        },
        changedKey: '',
        csrs: { mac_acc: '0', 'mcycle / minstret': '0 / 0' },
        traceReceipt: 'Ready — internal accumulator mac_acc = 0',
      },
      {
        stepNum: 1,
        asm: '0x00: mac.set x10, x1       # Preload bias (+1000) into mac_acc',
        stageNote: 'funct3=2 copies signed x1 (+1000) into internal mac_acc and writes +1000 to x10.',
        pc: '0x0000_0000',
        insnHex: '0x0000_A50B',
        nextPc: '0x0000_0004',
        regs: {
          'x1 (bias)': '+1,000',
          'x2 (a1,a0)': '0xFFEC_000A (-20,+10)',
          'x3 (b1,b0)': '0x0006_0005 (+6,+5)',
          'x6 (max)': '0x7FFF_7FFF (+32767,+32767)',
          x10: '+1,000',
          x11: '0',
          x14: '0',
          x15: '0',
        },
        changedKey: 'x10',
        csrs: { mac_acc: '+1,000', 'mcycle / minstret': '1 / 1' },
        traceReceipt: 'StepTrace(pc=0x00, insn=0x0000A50B, next_pc=0x04, rd=10, rd_val=1000)',
      },
      {
        stepNum: 2,
        asm: '0x04: mac x11, x2, x3       # 1000 + (10*5) + (-20*6) = +930',
        stageNote: 'funct3=0 multiplies both int16 lanes in parallel and adds into mac_acc (+930).',
        pc: '0x0000_0004',
        insnHex: '0x0031_058B',
        nextPc: '0x0000_0008',
        regs: {
          'x1 (bias)': '+1,000',
          'x2 (a1,a0)': '0xFFEC_000A (-20,+10)',
          'x3 (b1,b0)': '0x0006_0005 (+6,+5)',
          'x6 (max)': '0x7FFF_7FFF (+32767,+32767)',
          x10: '+1,000',
          x11: '+930',
          x14: '0',
          x15: '0',
        },
        changedKey: 'x11',
        csrs: { mac_acc: '+930', 'mcycle / minstret': '2 / 2' },
        traceReceipt: 'StepTrace(pc=0x04, insn=0x0031058B, next_pc=0x08, rd=11, rd_val=930)',
      },
      {
        stepNum: 3,
        asm: '0x08: mac.clr x14, x6, x6   # 0 + 32767*32767 + 32767*32767',
        stageNote: 'funct3=1 zeros previous accumulator and computes 2 * 32767^2 = +2,147,352,578.',
        pc: '0x0000_0008',
        insnHex: '0x0063_170B',
        nextPc: '0x0000_000C',
        regs: {
          'x1 (bias)': '+1,000',
          'x2 (a1,a0)': '0xFFEC_000A (-20,+10)',
          'x3 (b1,b0)': '0x0006_0005 (+6,+5)',
          'x6 (max)': '0x7FFF_7FFF (+32767,+32767)',
          x10: '+1,000',
          x11: '+930',
          x14: '+2,147,352,578',
          x15: '0',
        },
        changedKey: 'x14',
        csrs: { mac_acc: '+2,147,352,578', 'mcycle / minstret': '3 / 3' },
        traceReceipt: 'StepTrace(pc=0x08, insn=0x0063170B, next_pc=0x0C, rd=14, rd_val=2147352578)',
      },
      {
        stepNum: 4,
        asm: '0x0C: mac x15, x6, x6       # + 2,147,352,578 → Clamps at INT32_MAX',
        stageNote: 'True sum +4,294,705,156 exceeds INT32_MAX; sat32() clamps at +2,147,483,647 rather than wrapping negative.',
        pc: '0x0000_000C',
        insnHex: '0x0063_078B',
        nextPc: '0x0000_0010',
        regs: {
          'x1 (bias)': '+1,000',
          'x2 (a1,a0)': '0xFFEC_000A (-20,+10)',
          'x3 (b1,b0)': '0x0006_0005 (+6,+5)',
          'x6 (max)': '0x7FFF_7FFF (+32767,+32767)',
          x10: '+1,000',
          x11: '+930',
          x14: '+2,147,352,578',
          x15: '+2,147,483,647 (Clamped)',
        },
        changedKey: 'x15',
        csrs: { mac_acc: '+2,147,483,647 (Clamped)', 'mcycle / minstret': '4 / 4' },
        traceReceipt: 'StepTrace(pc=0x0C, insn=0x0063078B, next_pc=0x10, rd=15, rd_val=2147483647)',
      },
    ],
  },
]

const selectedId = ref<string>('loop_call')
const frameIdx = ref<number>(0)

const currentScenario = computed(
  () => scenarios.find((s) => s.id === selectedId.value) ?? scenarios[0],
)
const currentFrame = computed(() => currentScenario.value.frames[frameIdx.value])

function pickScenario(id: string) {
  selectedId.value = id
  frameIdx.value = 0
}

const flowState = computed(() => {
  const f = currentFrame.value
  const isIdle = f.stepNum === 0
  const receipt = f.traceReceipt.toLowerCase()
  const isIrq = !isIdle && (receipt.includes('interrupt=true') || receipt.includes('irq'))
  const isTrap = !isIdle && !isIrq && (receipt.includes('trap_cause=') && !receipt.includes('trap_cause=none'))
  const isNormal = !isIdle && !isIrq && !isTrap
  return { isIdle, isIrq, isTrap, isNormal }
})
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">Oracle.step() Single-Step Execution Tracer</div>
      <div style="display: flex; gap: 6px">
        <button
          type="button"
          class="hw-btn"
          :disabled="frameIdx === 0"
          @click="frameIdx = 0"
        >
          Reset
        </button>
        <button
          type="button"
          class="hw-btn"
          :disabled="frameIdx === 0"
          @click="frameIdx--"
        >
          ← Prev
        </button>
        <button
          type="button"
          class="hw-btn active"
          :disabled="frameIdx >= currentScenario.frames.length - 1"
          @click="frameIdx++"
        >
          step() →
        </button>
      </div>
    </div>

    <!-- Scenario Picker -->
    <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px">
      <button
        v-for="sc in scenarios"
        :key="sc.id"
        type="button"
        class="hw-btn"
        :class="{ active: selectedId === sc.id }"
        @click="pickScenario(sc.id)"
      >
        {{ sc.title }}
      </button>
    </div>

    <p style="margin: 0 0 10px 0; font-size: 13px; color: var(--vp-c-text-2)">
      {{ currentScenario.summary }}
    </p>

    <!-- Live Interactive SVG Single-Step Flow Schematic -->
    <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect all 5 execution stages</div>
    <div style="overflow-x: auto; padding-bottom: 4px; margin-bottom: 10px">
    <svg
      viewBox="0 0 680 96"
      class="hw-svg-diagram"
      style="min-width: 550px"
      role="img"
      aria-label="Single-step execution flow diagram highlighting clock advance, interrupt preemption check, fetch and decode, execute, and commit or trap"
    >
      <defs>
        <marker id="tr-arr-on" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--vp-c-brand-1)" />
        </marker>
        <marker id="tr-arr-red" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--hw-red)" />
        </marker>
        <marker id="tr-arr-off" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--vp-c-text-3)" />
        </marker>
      </defs>

      <!-- Stage 1: Clock Tick -->
      <rect
        x="8"
        y="12"
        width="108"
        height="42"
        rx="6"
        :fill="flowState.isIdle ? 'var(--vp-c-bg)' : 'var(--vp-c-brand-soft)'"
        :stroke="flowState.isIdle ? 'var(--vp-c-divider)' : 'var(--vp-c-brand-1)'"
        stroke-width="1.4"
      />
      <text x="62" y="29" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--vp-c-text-1)">1. Clock Tick</text>
      <text x="62" y="44" text-anchor="middle" font-size="8.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">mcycle, mtime +1</text>

      <line x1="116" y1="33" x2="140" y2="33" :stroke="flowState.isIdle ? 'var(--vp-c-text-3)' : 'var(--vp-c-brand-1)'" stroke-width="1.8" :marker-end="flowState.isIdle ? 'url(#tr-arr-off)' : 'url(#tr-arr-on)'" />

      <!-- Stage 2: IRQ Check -->
      <rect
        x="144"
        y="12"
        width="112"
        height="42"
        rx="6"
        :fill="flowState.isIrq ? 'rgba(220, 38, 38, 0.12)' : flowState.isIdle ? 'var(--vp-c-bg)' : 'var(--vp-c-brand-soft)'"
        :stroke="flowState.isIrq ? 'var(--hw-red)' : flowState.isIdle ? 'var(--vp-c-divider)' : 'var(--vp-c-brand-1)'"
        stroke-width="1.4"
      />
      <text x="200" y="29" text-anchor="middle" font-size="9.5" font-weight="700" :fill="flowState.isIrq ? 'var(--hw-red)' : 'var(--vp-c-text-1)'">2. Interrupt</text>
      <text x="200" y="44" text-anchor="middle" font-size="8.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">{{ flowState.isIrq ? 'PREEMPT!' : 'mip & mie' }}</text>

      <!-- Arrow 2 -> 3 (Normal / Sync path) -->
      <line x1="256" y1="33" x2="280" y2="33" :stroke="flowState.isNormal || flowState.isTrap ? 'var(--vp-c-brand-1)' : 'var(--vp-c-text-3)'" stroke-width="1.8" :marker-end="flowState.isNormal || flowState.isTrap ? 'url(#tr-arr-on)' : 'url(#tr-arr-off)'" />

      <!-- Stage 3: Fetch & Decode -->
      <rect
        x="284"
        y="12"
        width="114"
        height="42"
        rx="6"
        :fill="flowState.isNormal || flowState.isTrap ? 'var(--vp-c-brand-soft)' : 'var(--vp-c-bg)'"
        :stroke="flowState.isNormal || flowState.isTrap ? 'var(--vp-c-brand-1)' : 'var(--vp-c-divider)'"
        stroke-width="1.4"
        :opacity="flowState.isIrq ? 0.4 : 1"
      />
      <text x="341" y="29" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--vp-c-text-1)">3. Fetch/Decode</text>
      <text x="341" y="44" text-anchor="middle" font-size="8.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">{{ flowState.isIrq ? 'Skipped' : currentFrame.insnHex }}</text>

      <line x1="398" y1="33" x2="422" y2="33" :stroke="flowState.isNormal || flowState.isTrap ? 'var(--vp-c-brand-1)' : 'var(--vp-c-text-3)'" stroke-width="1.8" :marker-end="flowState.isNormal || flowState.isTrap ? 'url(#tr-arr-on)' : 'url(#tr-arr-off)'" />

      <!-- Stage 4: Execute -->
      <rect
        x="426"
        y="12"
        width="104"
        height="42"
        rx="6"
        :fill="flowState.isTrap ? 'rgba(220, 38, 38, 0.12)' : flowState.isNormal ? 'var(--vp-c-brand-soft)' : 'var(--vp-c-bg)'"
        :stroke="flowState.isTrap ? 'var(--hw-red)' : flowState.isNormal ? 'var(--vp-c-brand-1)' : 'var(--vp-c-divider)'"
        stroke-width="1.4"
        :opacity="flowState.isIrq ? 0.4 : 1"
      />
      <text x="478" y="29" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--vp-c-text-1)">4. Execute</text>
      <text x="478" y="44" text-anchor="middle" font-size="8.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">{{ flowState.isTrap ? 'Trap Abort' : 'Int/Mem/CSR' }}</text>

      <line x1="530" y1="33" x2="554" y2="33" :stroke="flowState.isNormal ? 'var(--vp-c-brand-1)' : flowState.isTrap ? 'var(--hw-red)' : 'var(--vp-c-text-3)'" stroke-width="1.8" :marker-end="flowState.isNormal ? 'url(#tr-arr-on)' : flowState.isTrap ? 'url(#tr-arr-red)' : 'url(#tr-arr-off)'" />

      <!-- Stage 5: Commit / Trap -->
      <rect
        x="558"
        y="12"
        width="114"
        height="42"
        rx="6"
        :fill="flowState.isIrq || flowState.isTrap ? 'rgba(220, 38, 38, 0.12)' : flowState.isNormal ? 'rgba(5, 150, 105, 0.12)' : 'var(--vp-c-bg)'"
        :stroke="flowState.isIrq || flowState.isTrap ? 'var(--hw-red)' : flowState.isNormal ? 'var(--hw-green)' : 'var(--vp-c-divider)'"
        stroke-width="1.5"
      />
      <text
        x="615"
        y="29"
        text-anchor="middle"
        font-size="9.5"
        font-weight="700"
        :fill="flowState.isIrq || flowState.isTrap ? 'var(--hw-red)' : flowState.isNormal ? 'var(--hw-green)' : 'var(--vp-c-text-1)'"
      >
        {{ flowState.isIrq ? '5. Interrupt' : flowState.isTrap ? '5. Sync Trap' : flowState.isNormal ? '5. Retire' : '5. Commit' }}
      </text>
      <text x="615" y="44" text-anchor="middle" font-size="8.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">
        {{ flowState.isIdle ? 'Reset State' : `→ ${currentFrame.nextPc}` }}
      </text>

      <!-- Pre-fetch interrupt bypass arc from Stage 2 straight to Stage 5 -->
      <path
        v-if="flowState.isIrq"
        d="M 200 54 L 200 72 L 615 72 L 615 58"
        fill="none"
        stroke="var(--hw-red)"
        stroke-width="2"
        stroke-dasharray="4 2"
        marker-end="url(#tr-arr-red)"
      />
      <text x="340" y="88" text-anchor="middle" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">
        {{ flowState.isIrq ? 'Pre-fetch interrupt skips fetch & writeback → jumps directly to mtvec' : `PC: ${currentFrame.pc} → Next PC: ${currentFrame.nextPc} · Step ${currentFrame.stepNum} / ${currentScenario.frames.length - 1}` }}
      </text>
    </svg>
    </div>

    <!-- Active Instruction Banner -->
    <div class="hw-card" style="margin-bottom: 12px; border-color: var(--vp-c-brand-1)">
      <div class="hw-mono" style="font-size: 14px; font-weight: 700; color: var(--vp-c-brand-1); margin-bottom: 4px">
        {{ currentFrame.asm }}
      </div>
      <div style="font-size: 13px">{{ currentFrame.stageNote }}</div>
    </div>

    <!-- Registers, CSRs, and Optional Byte Lanes -->
    <div class="hw-grid-2">
      <div class="hw-card">
        <div class="hw-label">Architectural Registers</div>
        <div
          v-for="(val, reg) in currentFrame.regs"
          :key="reg"
          class="hw-mono"
          style="
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 6px;
            padding: 3px 4px;
            border-radius: 4px;
            font-size: 11px;
          "
          :style="{
            background: currentFrame.changedKey === reg ? 'var(--vp-c-brand-soft)' : 'transparent',
            fontWeight: currentFrame.changedKey === reg ? '700' : '400',
          }"
        >
          <span style="white-space: nowrap; flex-shrink: 0">{{ reg }}</span>
          <span style="text-align: right; min-width: 0; overflow-wrap: anywhere">{{ val }}</span>
        </div>
      </div>

      <div class="hw-card">
        <div class="hw-label">Control / Accumulator State</div>
        <div
          v-for="(val, csr) in currentFrame.csrs"
          :key="csr"
          class="hw-mono"
          style="
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 10px;
            padding: 3px 6px;
            border-radius: 4px;
            font-size: 12px;
          "
          :style="{
            background:
              frameIdx > 0 && currentScenario.frames[frameIdx - 1]?.csrs[csr] !== val
                ? 'var(--vp-c-brand-soft)'
                : 'transparent',
          }"
        >
          <span style="white-space: nowrap; flex-shrink: 0">{{ csr }}</span>
          <strong style="text-align: right; min-width: 0; overflow-wrap: anywhere">{{ val }}</strong>
        </div>

        <div v-if="currentFrame.memBytes" style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--vp-c-divider)">
          <div class="hw-label">BRAM Byte Lanes @ <code>0x1000_0000</code> (Little-Endian)</div>
          <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; text-align: center">
            <div
              v-for="cell in currentFrame.memBytes"
              :key="cell.addr"
              class="hw-mono"
              style="padding: 4px; border-radius: 4px; border: 1px solid var(--vp-c-divider); font-size: 11.5px"
            >
              <div style="font-size: 10px; opacity: 0.7">{{ cell.addr }}</div>
              <strong>{{ cell.byteHex }}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      class="hw-mono"
      style="
        margin-top: 10px;
        padding: 7px 10px;
        border-radius: 6px;
        background: var(--vp-c-bg);
        border: 1px dashed var(--vp-c-divider);
        font-size: 12px;
        color: var(--vp-c-text-2);
      "
    >
      <strong>Commit Receipt:</strong> {{ currentFrame.traceReceipt }}
    </div>
  </div>
</template>
