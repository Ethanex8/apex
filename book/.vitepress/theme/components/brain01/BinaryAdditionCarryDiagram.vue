<!--
  Purpose: Interactive 4-bit binary column-addition schematic showing right-to-left carry
           propagation and how carry-out past Bit 3 drops off an N-bit register modulo 16.
  Usage:   Inserted as <BinaryAdditionCarryDiagram /> in Section 2.2 before Euclidean division.
  Outputs: Visual column table (Carry In, Input A, Input B, dropped Carry-Out, kept Bits 3..0)
           and preset/bit-toggle controls with zero reliance on forward modulo notation.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

/** Bit width of the interactive unsigned register model. */
const BIT_WIDTH = 4
const MSB_INDEX = BIT_WIDTH - 1
const BIT_INDICES = [3, 2, 1, 0] as const
const NIBBLE_MASK = (1 << BIT_WIDTH) - 1
const MODULUS = 1 << BIT_WIDTH

/** SVG viewport and column geometry constants (pixels in SVG user space). */
const SVG_VIEWBOX = '0 0 680 286'
const COL_BASE_X = 278
const COL_STEP_X = 104
const CARRY_CELL_OFFSET_X = 18
const CARRY_LINE_Y = 102
const CARRY_OUT_CENTER_X = 150
const CARRY_OUT_TOP_Y = 202
const NEIGHBOR_CARRY_EDGE_X = 20

/** Preset pair of 4-bit unsigned addends highlighting wrap-around and no-carry cases. */
interface AddPreset {
  /** Human-readable preset button caption. */
  label: string
  /** First 4-bit unsigned addend in range `0..15`. */
  a: number
  /** Second 4-bit unsigned addend in range `0..15`. */
  b: number
}

const presets: AddPreset[] = [
  { label: '11 + 7 = 18 (wraps to 2)', a: 0b1011, b: 0b0111 },
  { label: '3 + 5 = 8 (no carry-out)', a: 0b0011, b: 0b0101 },
  { label: '15 + 1 = 16 (wraps to 0)', a: 0b1111, b: 0b0001 },
  { label: '11 + 14 = 25 (wraps to 9)', a: 0b1011, b: 0b1110 },
]

const aBits = ref<number>(presets[0].a)
const bBits = ref<number>(presets[0].b)

/** Load both 4-bit addends from a named preset example. */
function selectPreset(preset: AddPreset): void {
  aBits.value = preset.a
  bBits.value = preset.b
}

/** Toggle one bit (`bit` in `0..3`) of unsigned 4-bit operand `'a'` or `'b'`. */
function toggleBit(which: 'a' | 'b', bit: number): void {
  if (which === 'a') {
    aBits.value = (aBits.value ^ (1 << bit)) & NIBBLE_MASK
  } else {
    bBits.value = (bBits.value ^ (1 << bit)) & NIBBLE_MASK
  }
}

/** Extract single bit (`0 | 1`) at index `bit` (`0..3`) from unsigned value `val`. */
function bitAt(val: number, bit: number): number {
  return (val >> bit) & 1
}

/** Format the low 4 bits (`0..15`) of `val` as a zero-padded 4-character binary string. */
function bin4(val: number): string {
  return (val & NIBBLE_MASK).toString(2).padStart(BIT_WIDTH, '0')
}

/** Per-column arithmetic and SVG layout state for one bit position `0..3`. */
interface ColumnState {
  /** Bit position index (`0..3`, LSB to MSB). */
  bit: number
  /** Place weight `2^bit` (`1, 2, 4, 8`). */
  weight: number
  /** Horizontal center coordinate in SVG user space (px). */
  x: number
  /** Input A bit at this column (`0 | 1`). */
  a: number
  /** Input B bit at this column (`0 | 1`). */
  b: number
  /** Incoming carry from column `bit - 1` (`0 | 1`, always `0` at Bit 0). */
  cIn: number
  /** Kept sum bit `(a + b + cIn) & 1` (`0 | 1`). */
  sumBit: number
  /** Outgoing carry `(a + b + cIn) >> 1` forwarded to `bit + 1` or Carry-Out (`0 | 1`). */
  cOut: number
}

/** Map bit index (`0..3`) to left-to-right big-endian SVG x-center so carries flow right-to-left. */
function colX(bit: number): number {
  return COL_BASE_X + (MSB_INDEX - bit) * COL_STEP_X
}

/** Build the SVG path routing column `bit`'s outgoing carry arrow leftward or into Carry-Out. */
function carryPath(col: ColumnState): string {
  const startX = col.x - CARRY_CELL_OFFSET_X
  // Route Bit 3's carry-out across the 4-bit cutoff seam and down into the dropped Carry-Out cell.
  if (col.bit === MSB_INDEX) {
    return `M ${startX} ${CARRY_LINE_Y} L ${CARRY_OUT_CENTER_X} ${CARRY_LINE_Y} L ${CARRY_OUT_CENTER_X} ${CARRY_OUT_TOP_Y}`
  }
  return `M ${startX} ${CARRY_LINE_Y} L ${colX(col.bit + 1) + NEIGHBOR_CARRY_EDGE_X} ${CARRY_LINE_Y}`
}

/** Compute carry-ripple state from Bit 0 up to Bit 3, then reverse to big-endian left-to-right order. */
const columns = computed<ColumnState[]>(() => {
  const cols: ColumnState[] = []
  let carry = 0
  // Propagate carries LSB-to-MSB before reversing so rendered columns match standard big-endian Bits 3..0.
  for (let bit = 0; bit <= MSB_INDEX; bit++) {
    const a = bitAt(aBits.value, bit)
    const b = bitAt(bBits.value, bit)
    const total = a + b + carry
    const sumBit = total & 1
    const cOut = (total >> 1) & 1
    cols.push({
      bit,
      weight: 1 << bit,
      x: colX(bit),
      a,
      b,
      cIn: carry,
      sumBit,
      cOut,
    })
    carry = cOut
  }
  return cols.reverse()
})

const trueSum = computed<number>(() => aBits.value + bBits.value)
const sumLow4 = computed<number>(() => trueSum.value & NIBBLE_MASK)
const carryOut = computed<number>(() => (trueSum.value >> BIT_WIDTH) & 1)
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">4-Bit Binary Column Addition and Carry-Out Wrap-Around</div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px">
        <button
          v-for="p in presets"
          :key="p.label"
          type="button"
          class="hw-btn hw-mono"
          :class="{ active: aBits === p.a && bBits === p.b }"
          @click="selectPreset(p)"
        >
          {{ p.label }}
        </button>
      </div>
    </div>

    <div style="display: flex; flex-wrap: wrap; gap: 14px; align-items: center; justify-content: space-between; margin-bottom: 10px">
      <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap">
        <span style="font-size: 12.5px; font-weight: 700; color: var(--vp-c-text-2)">Input A (Bits 3..0):</span>
        <button
          v-for="b in BIT_INDICES"
          :key="`add-a-${b}`"
          type="button"
          class="hw-btn hw-mono"
          :class="{ active: bitAt(aBits, b) === 1 }"
          style="min-width: 44px; padding: 3px 7px"
          @click="toggleBit('a', b)"
        >
          b{{ b }}={{ bitAt(aBits, b) }}
        </button>
      </div>
      <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap">
        <span style="font-size: 12.5px; font-weight: 700; color: var(--vp-c-text-2)">Input B (Bits 3..0):</span>
        <button
          v-for="b in BIT_INDICES"
          :key="`add-b-${b}`"
          type="button"
          class="hw-btn hw-mono"
          :class="{ active: bitAt(bBits, b) === 1 }"
          style="min-width: 44px; padding: 3px 7px"
          @click="toggleBit('b', b)"
        >
          b{{ b }}={{ bitAt(bBits, b) }}
        </button>
      </div>
    </div>

    <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect every carry wire</div>
    <div style="overflow-x: auto; padding-bottom: 4px">
      <svg
        :viewBox="SVG_VIEWBOX"
        class="hw-svg-diagram"
        style="min-width: 550px"
        role="img"
        aria-label="4-bit binary column addition schematic showing right-to-left carries and dropped carry-out past Bit 3"
      >
        <defs>
          <marker id="binadd-arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--hw-amber)" />
          </marker>
          <marker id="binadd-arr-muted" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--vp-c-divider)" />
          </marker>
        </defs>

        <!-- Single-Bit Addition Rule Strip -->
        <rect x="10" y="6" width="660" height="28" rx="6" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.1" />
        <text x="340" y="24" text-anchor="middle" font-size="10.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
          1-Bit Column Rules:   0+0 = 0 (c=0)   |   0+1 = 1 (c=0)   |   1+1 = 0 (c=1)   |   1+1+1 = 1 (c=1)
        </text>

        <!-- Register cutoff seam between Carry-Out and Bit 3 -->
        <text x="220" y="50" text-anchor="middle" font-size="9" font-weight="700" fill="var(--hw-red)">
          4-Bit Cutoff
        </text>
        <line x1="220" y1="56" x2="220" y2="246" stroke="var(--hw-red)" stroke-width="1.6" stroke-dasharray="4 3" />

        <!-- Column Headers -->
        <text :x="CARRY_OUT_CENTER_X" y="72" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--hw-red)">
          Carry-Out (+{{ MODULUS }})
        </text>
        <g v-for="col in columns" :key="`hdr-${col.bit}`">
          <text :x="col.x" y="72" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--vp-c-text-1)">
            Bit {{ col.bit }} ({{ col.weight }})
          </text>
        </g>

        <!-- Row Labels -->
        <text x="14" y="106" font-size="10.5" font-weight="700" fill="var(--hw-amber)">Carry In</text>
        <text x="14" y="144" font-size="10.5" font-weight="700" fill="var(--vp-c-text-1)">Input A ({{ aBits }})</text>
        <text x="14" y="182" font-size="10.5" font-weight="700" fill="var(--vp-c-text-1)">+ Input B ({{ bBits }})</text>
        <text x="14" y="226" font-size="10.5" font-weight="700" fill="var(--vp-c-brand-1)">Sum ({{ trueSum }})</text>

        <!-- Carry propagation arrows right-to-left (from column bit i to bit i+1, and Bit 3 down to Carry-Out) -->
        <g v-for="col in columns" :key="`carry-arr-${col.bit}`">
          <path
            :d="carryPath(col)"
            fill="none"
            :stroke="col.cOut ? 'var(--hw-amber)' : 'var(--vp-c-divider)'"
            :stroke-width="col.cOut ? 2 : 1.2"
            :marker-end="col.cOut ? 'url(#binadd-arr)' : 'url(#binadd-arr-muted)'"
          />
        </g>

        <!-- Carry In cells above Bits 3..0 -->
        <g v-for="col in columns" :key="`cin-${col.bit}`">
          <rect
            :x="col.x - 16"
            y="88"
            width="32"
            height="24"
            rx="5"
            :fill="col.cIn ? 'rgba(180, 83, 9, 0.14)' : 'var(--vp-c-bg)'"
            :stroke="col.cIn ? 'var(--hw-amber)' : 'var(--vp-c-divider)'"
            stroke-width="1.2"
          />
          <text
            :x="col.x"
            y="104"
            text-anchor="middle"
            font-size="12"
            font-weight="700"
            font-family="var(--vp-font-family-mono)"
            :fill="col.cIn ? 'var(--hw-amber)' : 'var(--vp-c-text-3)'"
          >
            {{ col.cIn }}
          </text>
        </g>

        <!-- Input A cells -->
        <g v-for="col in columns" :key="`a-${col.bit}`">
          <rect
            :x="col.x - 20"
            y="124"
            width="40"
            height="28"
            rx="6"
            fill="var(--vp-c-bg)"
            stroke="var(--vp-c-divider)"
            stroke-width="1.3"
          />
          <text
            :x="col.x"
            y="143"
            text-anchor="middle"
            font-size="14"
            font-weight="700"
            font-family="var(--vp-font-family-mono)"
            fill="var(--vp-c-text-1)"
          >
            {{ col.a }}
          </text>
        </g>

        <!-- Input B cells -->
        <g v-for="col in columns" :key="`b-${col.bit}`">
          <rect
            :x="col.x - 20"
            y="162"
            width="40"
            height="28"
            rx="6"
            fill="var(--vp-c-bg)"
            stroke="var(--vp-c-divider)"
            stroke-width="1.3"
          />
          <text
            :x="col.x"
            y="181"
            text-anchor="middle"
            font-size="14"
            font-weight="700"
            font-family="var(--vp-font-family-mono)"
            fill="var(--vp-c-text-1)"
          >
            {{ col.b }}
          </text>
        </g>

        <!-- Addition Divider Bar -->
        <line x1="110" y1="198" x2="646" y2="198" stroke="var(--vp-c-text-2)" stroke-width="1.6" />

        <!-- Dropped Carry-Out Cell (2^4 = 16) -->
        <rect
          x="126"
          y="206"
          width="48"
          height="32"
          rx="6"
          :fill="carryOut ? 'rgba(220, 38, 38, 0.12)' : 'var(--vp-c-bg)'"
          :stroke="carryOut ? 'var(--hw-red)' : 'var(--vp-c-divider)'"
          stroke-width="1.5"
          stroke-dasharray="4 2"
        />
        <text
          :x="CARRY_OUT_CENTER_X"
          y="227"
          text-anchor="middle"
          font-size="15"
          font-weight="800"
          font-family="var(--vp-font-family-mono)"
          :fill="carryOut ? 'var(--hw-red)' : 'var(--vp-c-text-3)'"
        >
          {{ carryOut }}
        </text>

        <!-- Kept 4-Bit Register Frame -->
        <rect
          x="236"
          y="203"
          width="400"
          height="38"
          rx="8"
          fill="var(--vp-c-brand-soft)"
          stroke="var(--vp-c-brand-1)"
          stroke-width="1.5"
        />
        <g v-for="col in columns" :key="`sum-${col.bit}`">
          <rect
            :x="col.x - 20"
            y="208"
            width="40"
            height="28"
            rx="6"
            fill="var(--vp-c-bg)"
            stroke="var(--vp-c-brand-1)"
            stroke-width="1.3"
          />
          <text
            :x="col.x"
            y="227"
            text-anchor="middle"
            font-size="14"
            font-weight="800"
            font-family="var(--vp-font-family-mono)"
            fill="var(--vp-c-brand-1)"
          >
            {{ col.sumBit }}
          </text>
        </g>

        <!-- Bottom Summary Equation -->
        <text x="340" y="266" text-anchor="middle" font-size="11.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
          {{ aBits }} + {{ bBits }} = {{ trueSum }} = ({{ carryOut }} × {{ MODULUS }} dropped) + {{ sumLow4 }} (kept Bits 3..0 = {{ bin4(sumLow4) }})
        </text>
      </svg>
    </div>
  </div>
</template>
