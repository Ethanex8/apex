<script setup lang="ts">
import { ref } from 'vue'

type FilterMode = 'all' | 'regs' | 'sign' | 'imms'

interface FormatCell {
  label: string
  range: string
  cols: number
  kind: 'imm' | 'sign' | 'rs2' | 'rs1' | 'funct3' | 'rd' | 'opcode'
}

interface FormatRow {
  id: string
  title: string
  summary: string
  cells: FormatCell[]
}

const filterMode = ref<FilterMode>('all')
const activeFormat = ref<string>('B')

const formatRows: FormatRow[] = [
  {
    id: 'R',
    title: 'R-Type (Registers)',
    summary: 'Three active register columns (rs1, rs2, rd) leave 10 bits (funct7 + funct3) for operation selection and no embedded constant.',
    cells: [
      { label: 'funct7 (Op Mode)', range: 'Bits 31..25', cols: 7, kind: 'funct3' },
      { label: 'rs2', range: 'Bits 24..20', cols: 5, kind: 'rs2' },
      { label: 'rs1', range: 'Bits 19..15', cols: 5, kind: 'rs1' },
      { label: 'funct3', range: 'Bits 14..12', cols: 3, kind: 'funct3' },
      { label: 'rd', range: 'Bits 11..7', cols: 5, kind: 'rd' },
      { label: 'opcode', range: 'Bits 6..0', cols: 7, kind: 'opcode' },
    ],
  },
  {
    id: 'I',
    title: 'I-Type (Immediate)',
    summary: 'Contiguous 12-bit constant replaces rs2 + funct7 while keeping rs1 (Bits 19..15) and rd (Bits 11..7) pinned in identical columns.',
    cells: [
      { label: 'S', range: 'Bit\n31', cols: 1, kind: 'sign' },
      { label: 'Imm 10..5', range: 'Bits 30..25', cols: 6, kind: 'imm' },
      { label: 'Imm 4..0', range: 'Bits 24..20', cols: 5, kind: 'imm' },
      { label: 'rs1', range: 'Bits 19..15', cols: 5, kind: 'rs1' },
      { label: 'funct3', range: 'Bits 14..12', cols: 3, kind: 'funct3' },
      { label: 'rd', range: 'Bits 11..7', cols: 5, kind: 'rd' },
      { label: 'opcode', range: 'Bits 6..0', cols: 7, kind: 'opcode' },
    ],
  },
  {
    id: 'S',
    title: 'S-Type (Stores)',
    summary: 'Stores read rs1 (base) and rs2 (data) without writing rd; splitting the 12-bit offset into Bits 31..25 and Bits 11..7 keeps rs2 pinned.',
    cells: [
      { label: 'S', range: 'Bit\n31', cols: 1, kind: 'sign' },
      { label: 'Off 10..5', range: 'Bits 30..25', cols: 6, kind: 'imm' },
      { label: 'rs2 (Data)', range: 'Bits 24..20', cols: 5, kind: 'rs2' },
      { label: 'rs1 (Base)', range: 'Bits 19..15', cols: 5, kind: 'rs1' },
      { label: 'funct3', range: 'Bits 14..12', cols: 3, kind: 'funct3' },
      { label: 'Off 4..0', range: 'Bits 11..7', cols: 5, kind: 'imm' },
      { label: 'opcode', range: 'Bits 6..0', cols: 7, kind: 'opcode' },
    ],
  },
  {
    id: 'B',
    title: 'B-Type (Branches)',
    summary: 'Reuses S-type hardware wires: Bit 7 carries Offset Bit 11 instead of Bit 0 (implicit 0 for 2-byte step alignment) while Bit 31 stays Sign.',
    cells: [
      { label: 'S', range: 'Bit\n31', cols: 1, kind: 'sign' },
      { label: 'Off 10..5', range: 'Bits 30..25', cols: 6, kind: 'imm' },
      { label: 'rs2', range: 'Bits 24..20', cols: 5, kind: 'rs2' },
      { label: 'rs1', range: 'Bits 19..15', cols: 5, kind: 'rs1' },
      { label: 'funct3', range: 'Bits 14..12', cols: 3, kind: 'funct3' },
      { label: 'Off 4..1', range: 'Bits 11..8', cols: 4, kind: 'imm' },
      { label: '11', range: 'Bit\n7', cols: 1, kind: 'imm' },
      { label: 'opcode', range: 'Bits 6..0', cols: 7, kind: 'opcode' },
    ],
  },
  {
    id: 'U',
    title: 'U-Type (Upper)',
    summary: 'Drops rs1 and rs2 to free a contiguous 20-bit upper payload (Bits 31..12) directly aligned to destination Bits 31..12 with zero bit shuffling.',
    cells: [
      { label: 'S', range: 'Bit\n31', cols: 1, kind: 'sign' },
      { label: 'Upper Constant Bits 30..12', range: 'Bits 30..12', cols: 19, kind: 'imm' },
      { label: 'rd', range: 'Bits 11..7', cols: 5, kind: 'rd' },
      { label: 'opcode', range: 'Bits 6..0', cols: 7, kind: 'opcode' },
    ],
  },
  {
    id: 'J',
    title: 'J-Type (Jumps)',
    summary: 'Slices Bits 19..12, Bit 20, and Bits 10..1 to share wire positions with U-type (Bits 19..12) and I-type (Bits 30..21, matching S/B-type on Bits 30..25) while keeping Bit 31 Sign.',
    cells: [
      { label: 'S', range: 'Bit\n31', cols: 1, kind: 'sign' },
      { label: 'Off Bits 10..1', range: 'Bits 30..21', cols: 10, kind: 'imm' },
      { label: '11', range: 'Bit\n20', cols: 1, kind: 'imm' },
      { label: 'Off Bits 19..12', range: 'Bits 19..12', cols: 8, kind: 'imm' },
      { label: 'rd', range: 'Bits 11..7', cols: 5, kind: 'rd' },
      { label: 'opcode', range: 'Bits 6..0', cols: 7, kind: 'opcode' },
    ],
  },
]

const selectedRow = () => formatRows.find((r) => r.id === activeFormat.value) ?? formatRows[3]

function isHighlighted(kind: FormatCell['kind']): boolean {
  if (filterMode.value === 'all') return true
  if (filterMode.value === 'regs') return kind === 'rs1' || kind === 'rs2' || kind === 'rd'
  if (filterMode.value === 'sign') return kind === 'sign'
  return kind === 'imm' || kind === 'sign'
}

function cellColor(kind: FormatCell['kind']): string {
  switch (kind) {
    case 'sign':
      return 'var(--hw-red)'
    case 'imm':
      return 'var(--hw-purple)'
    case 'rs2':
      return 'var(--hw-amber)'
    case 'rs1':
      return 'var(--hw-green)'
    case 'rd':
      return 'var(--vp-c-brand-1)'
    case 'funct3':
      return 'var(--hw-cyan)'
    case 'opcode':
      return 'var(--hw-pink)'
  }
}
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">
        <span class="hw-badge">Hardware Wire Matrix</span>
        <span>All Six 32-Bit RISC-V Formats Aligned by Wire Column</span>
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px">
        <button
          v-for="[mode, label] in [
            ['all', 'Show All Wires'],
            ['regs', 'Pinned Registers (rs1/rs2/rd)'],
            ['sign', 'Fixed Sign Wire (Bit 31)'],
            ['imms', 'Split Constant Slices'],
          ] as const"
          :key="mode"
          type="button"
          class="hw-btn"
          :class="{ active: filterMode === mode }"
          @click="filterMode = mode"
        >
          {{ label }}
        </button>
      </div>
    </div>

    <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect all 32 bit columns</div>
    <div style="overflow-x: auto; padding-bottom: 6px">
      <div class="hw-grid-32-scroll">
        <!-- Column Bit Index Ruler -->
        <div
          class="hw-mono"
          style="
            display: grid;
            grid-template-columns: 80px repeat(32, minmax(0, 1fr));
            gap: 1px;
            font-size: 8px;
            color: var(--vp-c-text-2);
            margin-bottom: 4px;
            text-align: center;
          "
        >
          <div style="text-align: left; font-weight: 700; padding-left: 4px">Format</div>
          <div v-for="bitIdx in 32" :key="bitIdx" style="font-weight: 600">
            {{ 32 - bitIdx }}
          </div>
        </div>

        <!-- Six Format Rows -->
        <div
          v-for="row in formatRows"
          :key="row.id"
          role="button"
          tabindex="0"
          :style="{
            display: 'grid',
            gridTemplateColumns: '80px repeat(32, minmax(0, 1fr))',
            gap: '1px',
            marginBottom: '5px',
            alignItems: 'stretch',
            cursor: 'pointer',
            padding: '2px',
            borderRadius: '6px',
            background: activeFormat === row.id ? 'var(--vp-c-brand-soft)' : 'transparent',
          }"
          @click="activeFormat = row.id"
          @keydown.enter="activeFormat = row.id"
        >
          <div
            style="
              display: flex;
              align-items: center;
              font-size: 9px;
              font-weight: 700;
              padding: 4px 3px;
              border-radius: 5px;
              border: 1px solid var(--vp-c-divider);
              background: var(--vp-c-bg);
            "
            :style="{ color: activeFormat === row.id ? 'var(--vp-c-brand-1)' : 'var(--vp-c-text-1)' }"
          >
            {{ row.title }}
          </div>

          <div
            v-for="(cell, cIdx) in row.cells"
            :key="cIdx"
            :title="`${row.id}-Type ${cell.range}: ${cell.label}`"
            :style="{
              gridColumn: `span ${cell.cols}`,
              borderTop: `3px solid ${cellColor(cell.kind)}`,
              borderLeft: '1px solid var(--vp-c-divider)',
              borderRight: '1px solid var(--vp-c-divider)',
              borderBottom: '1px solid var(--vp-c-divider)',
              borderRadius: '5px',
              background: 'var(--vp-c-bg)',
              padding: cell.cols === 1 ? '4px 0' : '4px 2px',
              textAlign: 'center',
              opacity: isHighlighted(cell.kind) ? 1 : 0.3,
              transition: 'opacity 0.15s ease',
              overflow: 'hidden',
            }"
          >
            <div
              style="font-weight: 700; white-space: pre-line; line-height: 1.05"
              :style="{
                color: cellColor(cell.kind),
                fontSize: cell.cols === 1 ? '6px' : cell.cols <= 3 ? '7.5px' : '8.5px',
              }"
            >
              {{ cell.range }}
            </div>
            <div
              style="font-weight: 700; white-space: nowrap"
              :style="{ fontSize: cell.cols === 1 ? '7.5px' : '9.5px' }"
            >
              {{ cell.label }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="hw-mono" style="font-size: 11px; color: var(--vp-c-text-2); margin-bottom: 6px">
      Legend: <strong>S</strong> = Sign bit pinned at Bit 31; <strong>11</strong> = Offset Bit 11 (Bit 7 or Bit 20); <strong>funct3</strong> = sub-operation selector (Bits 14..12).
    </div>

    <div class="hw-card" style="margin-top: 4px; font-size: 13px">
      <span style="font-weight: 700; color: var(--vp-c-brand-1)">{{ selectedRow().title }}: </span>
      <span>{{ selectedRow().summary }}</span>
    </div>
  </div>
</template>
