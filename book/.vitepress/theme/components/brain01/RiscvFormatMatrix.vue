<script setup lang="ts">
import { computed, ref } from 'vue'

type FilterMode = 'all' | 'regs' | 'sign' | 'imms'

interface FormatCell {
  label: string
  range: string
  startBit: number
  cols: number
  kind: 'imm' | 'sign' | 'rs2' | 'rs1' | 'funct3' | 'rd' | 'opcode'
}

interface FormatRow {
  id: string
  title: string
  shortLabel: string
  summary: string
  cells: FormatCell[]
}

const filterMode = ref<FilterMode>('all')
const activeFormat = ref<string>('B')

const formatRows: FormatRow[] = [
  {
    id: 'R',
    title: 'R-Type (Registers)',
    shortLabel: 'R-Type',
    summary:
      'Three active register columns (rs1, rs2, rd) plus the 7-bit opcode leave 10 bits (funct7 + funct3) for sub-operation selection and no embedded constant.',
    cells: [
      { label: 'funct7', range: 'Bits 31..25', startBit: 31, cols: 7, kind: 'funct3' },
      { label: 'rs2', range: 'Bits 24..20', startBit: 24, cols: 5, kind: 'rs2' },
      { label: 'rs1', range: 'Bits 19..15', startBit: 19, cols: 5, kind: 'rs1' },
      { label: 'funct3', range: 'Bits 14..12', startBit: 14, cols: 3, kind: 'funct3' },
      { label: 'rd', range: 'Bits 11..7', startBit: 11, cols: 5, kind: 'rd' },
      { label: 'opcode', range: 'Bits 6..0', startBit: 6, cols: 7, kind: 'opcode' },
    ],
  },
  {
    id: 'I',
    title: 'I-Type (Immediate)',
    shortLabel: 'I-Type',
    summary:
      'Contiguous 12-bit constant replaces rs2 + funct7 while keeping rs1 (Bits 19..15) and rd (Bits 11..7) pinned in identical columns.',
    cells: [
      { label: 'S', range: '31', startBit: 31, cols: 1, kind: 'sign' },
      { label: 'Imm 10..5', range: 'Bits 30..25', startBit: 30, cols: 6, kind: 'imm' },
      { label: 'Imm 4..0', range: 'Bits 24..20', startBit: 24, cols: 5, kind: 'imm' },
      { label: 'rs1', range: 'Bits 19..15', startBit: 19, cols: 5, kind: 'rs1' },
      { label: 'funct3', range: 'Bits 14..12', startBit: 14, cols: 3, kind: 'funct3' },
      { label: 'rd', range: 'Bits 11..7', startBit: 11, cols: 5, kind: 'rd' },
      { label: 'opcode', range: 'Bits 6..0', startBit: 6, cols: 7, kind: 'opcode' },
    ],
  },
  {
    id: 'S',
    title: 'S-Type (Stores)',
    shortLabel: 'S-Type',
    summary:
      'Stores read rs1 (base) and rs2 (data) without writing rd; splitting the 12-bit offset into Bits 31..25 and Bits 11..7 keeps rs2 pinned.',
    cells: [
      { label: 'S', range: '31', startBit: 31, cols: 1, kind: 'sign' },
      { label: 'Off 10..5', range: 'Bits 30..25', startBit: 30, cols: 6, kind: 'imm' },
      { label: 'rs2', range: 'Bits 24..20', startBit: 24, cols: 5, kind: 'rs2' },
      { label: 'rs1', range: 'Bits 19..15', startBit: 19, cols: 5, kind: 'rs1' },
      { label: 'funct3', range: 'Bits 14..12', startBit: 14, cols: 3, kind: 'funct3' },
      { label: 'Off 4..0', range: 'Bits 11..7', startBit: 11, cols: 5, kind: 'imm' },
      { label: 'opcode', range: 'Bits 6..0', startBit: 6, cols: 7, kind: 'opcode' },
    ],
  },
  {
    id: 'B',
    title: 'B-Type (Branches)',
    shortLabel: 'B-Type',
    summary:
      'Splits a 13-bit signed branch offset (implicit Bit 0 = 0) across Bit 31 (Sign), Bits 30..25, Bits 11..8, and Bit 7 while keeping rs1, rs2, and funct3 pinned.',
    cells: [
      { label: 'S', range: '31', startBit: 31, cols: 1, kind: 'sign' },
      { label: 'Off 10..5', range: 'Bits 30..25', startBit: 30, cols: 6, kind: 'imm' },
      { label: 'rs2', range: 'Bits 24..20', startBit: 24, cols: 5, kind: 'rs2' },
      { label: 'rs1', range: 'Bits 19..15', startBit: 19, cols: 5, kind: 'rs1' },
      { label: 'funct3', range: 'Bits 14..12', startBit: 14, cols: 3, kind: 'funct3' },
      { label: 'Off 4..1', range: 'Bits 11..8', startBit: 11, cols: 4, kind: 'imm' },
      { label: '11', range: '7', startBit: 7, cols: 1, kind: 'imm' },
      { label: 'opcode', range: 'Bits 6..0', startBit: 6, cols: 7, kind: 'opcode' },
    ],
  },
  {
    id: 'U',
    title: 'U-Type (Upper)',
    shortLabel: 'U-Type',
    summary:
      'Drops funct7, rs2, rs1, and funct3 to free a contiguous 20-bit upper payload (Bits 31..12) directly aligned to destination Bits 31..12 with zero bit shuffling.',
    cells: [
      { label: 'S', range: '31', startBit: 31, cols: 1, kind: 'sign' },
      { label: 'Upper Constant 30..12', range: 'Bits 30..12', startBit: 30, cols: 19, kind: 'imm' },
      { label: 'rd', range: 'Bits 11..7', startBit: 11, cols: 5, kind: 'rd' },
      { label: 'opcode', range: 'Bits 6..0', startBit: 6, cols: 7, kind: 'opcode' },
    ],
  },
  {
    id: 'J',
    title: 'J-Type (Jumps)',
    shortLabel: 'J-Type',
    summary:
      'Packs a 21-bit signed jump offset (implicit Bit 0 = 0) across Bit 31 (Sign), Bits 19..12, Bit 20, and Bits 30..21 while keeping rd pinned at Bits 11..7.',
    cells: [
      { label: 'S', range: '31', startBit: 31, cols: 1, kind: 'sign' },
      { label: 'Off Bits 10..1', range: 'Bits 30..21', startBit: 30, cols: 10, kind: 'imm' },
      { label: '11', range: '20', startBit: 20, cols: 1, kind: 'imm' },
      { label: 'Off Bits 19..12', range: 'Bits 19..12', startBit: 19, cols: 8, kind: 'imm' },
      { label: 'rd', range: 'Bits 11..7', startBit: 11, cols: 5, kind: 'rd' },
      { label: 'opcode', range: 'Bits 6..0', startBit: 6, cols: 7, kind: 'opcode' },
    ],
  },
]

const selectedRow = computed(() => formatRows.find((r) => r.id === activeFormat.value) ?? formatRows[3])

// SVG layout geometry (viewBox 740 x 284)
const LABEL_W = 68
const COL_W = 20.6
const ROW_H = 38
const ROW_GAP = 6
const TOP_Y = 24

function bitX(bit: number): number {
  return LABEL_W + (31 - bit) * COL_W
}

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

const pinnedBands = [
  { label: 'Sign', startBit: 31, cols: 1, color: 'var(--hw-red)', mode: 'sign' as FilterMode },
  { label: 'rs2', startBit: 24, cols: 5, color: 'var(--hw-amber)', mode: 'regs' as FilterMode },
  { label: 'rs1', startBit: 19, cols: 5, color: 'var(--hw-green)', mode: 'regs' as FilterMode },
  { label: 'rd', startBit: 11, cols: 5, color: 'var(--vp-c-brand-1)', mode: 'regs' as FilterMode },
]
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">All Six 32-Bit RISC-V Instruction Formats Aligned by Wire Column</div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px">
        <button
          v-for="[mode, label] in [
            ['all', 'Show All Wires'],
            ['regs', 'Pinned Registers (rs1/rs2/rd)'],
            ['sign', 'Sign Wire (Bit 31)'],
            ['imms', 'Immediate & Offset Wires'],
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

    <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect all 32 wire columns</div>
    <div style="overflow-x: auto; padding-bottom: 4px">
      <svg
        viewBox="0 0 732 292"
        class="hw-svg-diagram"
        style="min-width: 550px"
        role="img"
        aria-label="Aligned 32-bit RISC-V instruction wire matrix for R, I, S, B, U, and J formats"
      >
        <!-- Vertical highlight bands for pinned columns -->
        <rect
          v-for="b in pinnedBands"
          v-show="filterMode === b.mode"
          :key="b.label"
          :x="bitX(b.startBit) - 1"
          :y="TOP_Y - 4"
          :width="b.cols * COL_W + 2"
          :height="6 * (ROW_H + ROW_GAP) + 2"
          rx="4"
          :fill="b.color"
          fill-opacity="0.11"
        />

        <!-- Bit index ruler 31 down to 0 -->
        <text
          x="6"
          y="15"
          font-size="9.5"
          font-weight="700"
          font-family="var(--vp-font-family-mono)"
          fill="var(--vp-c-text-2)"
        >
          Format
        </text>
        <text
          v-for="idx in 32"
          :key="`ruler-${idx}`"
          :x="bitX(32 - idx) + COL_W / 2"
          y="15"
          text-anchor="middle"
          font-size="8.5"
          font-weight="600"
          font-family="var(--vp-font-family-mono)"
          fill="var(--vp-c-text-2)"
        >
          {{ 32 - idx }}
        </text>

        <!-- Six format rows -->
        <g
          v-for="(row, rIdx) in formatRows"
          :key="row.id"
          style="cursor: pointer"
          @click="activeFormat = row.id"
        >
          <!-- Row selection highlight -->
          <rect
            x="2"
            :y="TOP_Y + rIdx * (ROW_H + ROW_GAP) - 2"
            width="726"
            :height="ROW_H + 4"
            rx="6"
            :fill="activeFormat === row.id ? 'var(--vp-c-brand-soft)' : 'transparent'"
          />

          <!-- Row label pill -->
          <rect
            x="5"
            :y="TOP_Y + rIdx * (ROW_H + ROW_GAP)"
            width="58"
            :height="ROW_H"
            rx="5"
            fill="var(--vp-c-bg)"
            :stroke="activeFormat === row.id ? 'var(--vp-c-brand-1)' : 'var(--vp-c-divider)'"
            :stroke-width="activeFormat === row.id ? 1.5 : 1"
          />
          <text
            x="34"
            :y="TOP_Y + rIdx * (ROW_H + ROW_GAP) + 23"
            text-anchor="middle"
            font-size="10.5"
            font-weight="700"
            :fill="activeFormat === row.id ? 'var(--vp-c-brand-1)' : 'var(--vp-c-text-1)'"
          >
            {{ row.shortLabel }}
          </text>

          <!-- Field boxes aligned strictly to bit columns -->
          <g
            v-for="(cell, cIdx) in row.cells"
            :key="`${row.id}-${cIdx}`"
            :opacity="isHighlighted(cell.kind) ? 1 : 0.34"
          >
            <rect
              :x="bitX(cell.startBit) + 1"
              :y="TOP_Y + rIdx * (ROW_H + ROW_GAP)"
              :width="cell.cols * COL_W - 2"
              :height="ROW_H"
              rx="4"
              fill="var(--vp-c-bg)"
              stroke="var(--vp-c-divider)"
              stroke-width="1"
            />
            <rect
              :x="bitX(cell.startBit) + 1"
              :y="TOP_Y + rIdx * (ROW_H + ROW_GAP)"
              :width="cell.cols * COL_W - 2"
              height="3.5"
              rx="1.5"
              :fill="cellColor(cell.kind)"
            />
            <text
              :x="bitX(cell.startBit) + (cell.cols * COL_W) / 2"
              :y="TOP_Y + rIdx * (ROW_H + ROW_GAP) + 16"
              text-anchor="middle"
              :font-size="cell.cols === 1 ? '8' : cell.cols <= 3 ? '8.5' : '9'"
              font-weight="700"
              font-family="var(--vp-font-family-mono)"
              :fill="cellColor(cell.kind)"
            >
              {{ cell.range }}
            </text>
            <text
              :x="bitX(cell.startBit) + (cell.cols * COL_W) / 2"
              :y="TOP_Y + rIdx * (ROW_H + ROW_GAP) + 30"
              text-anchor="middle"
              :font-size="cell.cols === 1 ? '9' : '10'"
              font-weight="700"
              fill="var(--vp-c-text-1)"
            >
              {{ cell.label }}
            </text>
          </g>
        </g>
      </svg>
    </div>

    <div class="hw-mono" style="font-size: 11px; color: var(--vp-c-text-2); margin: 4px 0 6px 0">
      Legend: <strong>Imm</strong> = Immediate bits; <strong>Off</strong> = Byte offset bits; <strong>S</strong> = Sign wire (Bit 31); <strong>11</strong> = Offset Bit 11 (Bit 7 or Bit 20); click any row to inspect.
    </div>

    <div class="hw-card" style="font-size: 13px">
      <span style="font-weight: 700; color: var(--vp-c-brand-1)">{{ selectedRow.title }}: </span>
      <span>{{ selectedRow.summary }}</span>
    </div>
  </div>
</template>
