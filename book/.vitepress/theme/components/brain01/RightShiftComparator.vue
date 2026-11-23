<script setup lang="ts">
import { computed, ref } from 'vue'

// Interactive 8-bit SVG shift-rail schematic illustrating logical (0-fill) vs. arithmetic (sign-wire copy) right shifts.
interface PresetInput {
  label: string
  u8: number
}

const presets: PresetInput[] = [
  { label: '+11 (0000_1011)', u8: 0b0000_1011 },
  { label: '-5 (1111_1011)', u8: 0b1111_1011 },
  { label: '-1 (1111_1111)', u8: 0b1111_1111 },
  { label: '-128 (1000_0000)', u8: 0b1000_0000 },
]

const inputU8 = ref<number>(0b1111_1011)
const shiftK = ref<number>(1)

function toggleBit(b: number) {
  inputU8.value = (inputU8.value ^ (1 << b)) & 0xff
}

const signBit = computed(() => (inputU8.value >> 7) & 1)
const inputS8 = computed(() => (signBit.value ? inputU8.value - 256 : inputU8.value))

const logOutU8 = computed(() => (inputU8.value >>> shiftK.value) & 0xff)
const logOutS8 = computed(() => ((logOutU8.value >> 7) & 1 ? logOutU8.value - 256 : logOutU8.value))

const arithOutS8 = computed(() => inputS8.value >> shiftK.value)
const arithOutU8 = computed(() => arithOutS8.value & 0xff)
const droppedRem = computed(() => (shiftK.value === 0 ? 0 : inputU8.value & ((1 << shiftK.value) - 1)))

function bitOf(val: number, b: number): number {
  return (val >> b) & 1
}

function fmtSigned(v: number): string {
  return v > 0 ? `+${v}` : `${v}`
}

// SVG layout geometry (viewBox 680 x 308)
const START_X = 114
const STEP_X = 50

function bitX(bitPos: number): number {
  return START_X + (7 - bitPos) * STEP_X
}

const keptBits = computed(() => {
  const k = shiftK.value
  const list: { src: number; dst: number; val: number }[] = []
  for (let b = 7; b >= k; b--) {
    list.push({ src: b, dst: b - k, val: bitOf(inputU8.value, b) })
  }
  return list
})

const vacatedBits = computed(() => {
  const k = shiftK.value
  const list: number[] = []
  for (let b = 7; b > 7 - k; b--) {
    list.push(b)
  }
  return list
})

const droppedBits = computed(() => {
  const k = shiftK.value
  const list: { bit: number; val: number }[] = []
  for (let b = k - 1; b >= 0; b--) {
    list.push({ bit: b, val: bitOf(inputU8.value, b) })
  }
  return list
})
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">8-Bit Logical vs. Arithmetic Right Shift Wire Rails</div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px">
        <button
          v-for="p in presets"
          :key="p.label"
          type="button"
          class="hw-btn hw-mono"
          :class="{ active: inputU8 === p.u8 }"
          @click="inputU8 = p.u8"
        >
          {{ p.label }}
        </button>
      </div>
    </div>

    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 10px">
      <div style="display: flex; align-items: center; gap: 8px">
        <span style="font-size: 12.5px; font-weight: 700; color: var(--vp-c-text-2)">
          Shift distance <code class="hw-mono">k = {{ shiftK }}</code> (divide by 2<sup>{{ shiftK }}</sup> = {{ 1 << shiftK }}):
        </span>
        <input v-model.number="shiftK" type="range" min="0" max="4" step="1" style="width: 130px; accent-color: var(--vp-c-brand-1)" />
      </div>
      <div class="hw-mono" style="font-size: 12px; color: var(--vp-c-text-2)">
        Click any input bit in the top row to toggle · U<sub>8</sub> = <strong>{{ inputU8 }}</strong> · S<sub>8</sub> = <strong>{{ fmtSigned(inputS8) }}</strong>
      </div>
    </div>

    <!-- True SVG Bit-Rail Shift Schematic -->
    <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect all 8 shift wire rails</div>
    <div style="overflow-x: auto; padding-bottom: 4px">
    <svg
      viewBox="0 0 680 312"
      class="hw-svg-diagram"
      style="min-width: 550px"
      role="img"
      aria-label="8-bit wire shift schematic showing kept bits sliding right by k, dropped low bits entering remainder bin, and vacated upper bits filled with 0 vs Bit 7 copy"
    >
      <defs>
        <marker id="shift-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="var(--vp-c-text-2)" />
        </marker>
        <marker id="shift-arrow-brand" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="var(--vp-c-brand-1)" />
        </marker>
        <marker id="shift-arrow-amber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="var(--hw-amber)" />
        </marker>
      </defs>

      <!-- Bit column header labels -->
      <text
        v-for="b in [7, 6, 5, 4, 3, 2, 1, 0]"
        :key="`hdr-${b}`"
        :x="bitX(b)"
        y="16"
        text-anchor="middle"
        font-size="9.5"
        font-weight="700"
        font-family="var(--vp-font-family-mono)"
        :fill="b === 7 ? 'var(--vp-c-brand-1)' : 'var(--vp-c-text-2)'"
      >
        Bit {{ b }}
      </text>

      <!-- ROW 1: INPUT 8-BIT WORD (clickable) -->
      <text x="12" y="42" font-size="11" font-weight="700" fill="var(--vp-c-text-1)">Input b</text>
      <text x="12" y="55" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">Bits 7..0</text>

      <g
        v-for="b in [7, 6, 5, 4, 3, 2, 1, 0]"
        :key="`src-${b}`"
        style="cursor: pointer"
        @click="toggleBit(b)"
      >
        <rect
          :x="bitX(b) - 18"
          y="24"
          width="36"
          height="32"
          rx="6"
          :fill="b < shiftK ? 'rgba(217, 119, 6, 0.14)' : b === 7 ? 'var(--vp-c-brand-soft)' : 'var(--vp-c-bg)'"
          :stroke="b < shiftK ? 'var(--hw-amber)' : b === 7 ? 'var(--vp-c-brand-1)' : 'var(--vp-c-divider)'"
          stroke-width="1.5"
        />
        <text
          :x="bitX(b)"
          y="45"
          text-anchor="middle"
          font-size="13.5"
          font-weight="700"
          font-family="var(--vp-font-family-mono)"
          :fill="b < shiftK ? 'var(--hw-amber)' : b === 7 ? 'var(--vp-c-brand-1)' : 'var(--vp-c-text-1)'"
        >
          {{ bitOf(inputU8, b) }}
        </text>
      </g>

      <!-- Remainder Bin on Right for Dropped Bits -->
      <rect x="518" y="24" width="152" height="58" rx="8" fill="var(--vp-c-bg)" stroke="var(--hw-amber)" stroke-width="1.4" stroke-dasharray="4 2" />
      <text x="594" y="42" text-anchor="middle" font-size="10" font-weight="700" fill="var(--hw-amber)">
        Dropped Remainder R
      </text>
      <text x="594" y="58" text-anchor="middle" font-size="11" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        {{ shiftK === 0 ? 'None (R = 0)' : `${droppedBits.map((d) => d.val).join('')} (R = ${droppedRem})` }}
      </text>
      <text x="594" y="73" text-anchor="middle" font-size="9" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">
        {{ shiftK === 0 ? 'k = 0 drops 0 bits' : shiftK === 1 ? 'Bit 0 discarded' : `Bits ${shiftK - 1}..0 discarded` }}
      </text>
      <!-- Arrow from dropped low bits into Remainder bin -->
      <path
        v-if="shiftK > 0"
        :d="`M ${bitX(0) + 18} 40 L 514 40`"
        fill="none"
        stroke="var(--hw-amber)"
        stroke-width="2"
        marker-end="url(#shift-arrow-amber)"
      />

      <!-- Diagonal Shift Arrows (Input -> Logical Right Shift row) -->
      <line
        v-for="item in keptBits"
        :key="`arr-log-${item.src}`"
        :x1="bitX(item.src)"
        y1="57"
        :x2="bitX(item.dst)"
        y2="112"
        stroke="var(--vp-c-text-2)"
        stroke-width="1.6"
        marker-end="url(#shift-arrow)"
      />

      <!-- Constant 0 Fill Rail into vacated upper slots for Logical Shift -->
      <g v-if="shiftK > 0">
        <rect x="12" y="78" width="70" height="22" rx="5" fill="var(--vp-c-bg-soft)" stroke="var(--vp-c-divider)" stroke-width="1.2" />
        <text x="47" y="93" text-anchor="middle" font-size="9.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">
          Fill = 0
        </text>
        <path
          :d="`M 82 89 L ${bitX(8 - shiftK)} 89`"
          fill="none"
          stroke="var(--vp-c-text-3)"
          stroke-width="1.8"
          stroke-dasharray="3 2"
        />
        <line
          v-for="vb in vacatedBits"
          :key="`zfill-${vb}`"
          :x1="bitX(vb)"
          y1="89"
          :x2="bitX(vb)"
          y2="112"
          stroke="var(--vp-c-text-3)"
          stroke-width="1.8"
          stroke-dasharray="3 2"
          marker-end="url(#shift-arrow)"
        />
      </g>

      <!-- ROW 2: LOGICAL RIGHT SHIFT (srl) -->
      <text x="12" y="131" font-size="11" font-weight="700" fill="var(--vp-c-text-1)">Logical (srl)</text>
      <text x="12" y="144" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">Zero-fill top</text>

      <g v-for="b in [7, 6, 5, 4, 3, 2, 1, 0]" :key="`log-${b}`">
        <rect
          :x="bitX(b) - 18"
          y="115"
          width="36"
          height="32"
          rx="6"
          :fill="b > 7 - shiftK ? 'var(--vp-c-bg-soft)' : 'var(--vp-c-bg)'"
          :stroke="b > 7 - shiftK ? 'var(--vp-c-text-3)' : 'var(--vp-c-divider)'"
          stroke-width="1.4"
        />
        <text
          :x="bitX(b)"
          y="136"
          text-anchor="middle"
          font-size="13.5"
          font-weight="700"
          font-family="var(--vp-font-family-mono)"
          :fill="b > 7 - shiftK ? 'var(--vp-c-text-2)' : 'var(--vp-c-text-1)'"
        >
          {{ bitOf(logOutU8, b) }}
        </text>
      </g>

      <!-- Logical result readout box -->
      <rect x="518" y="109" width="152" height="44" rx="7" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.2" />
      <text x="594" y="126" text-anchor="middle" font-size="10.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        U8 = {{ logOutU8 }} = ⌊{{ inputU8 }}/{{ 1 << shiftK }}⌋
      </text>
      <text
        x="594"
        y="144"
        text-anchor="middle"
        font-size="9.5"
        font-weight="600"
        :fill="signBit && shiftK > 0 ? 'var(--hw-red)' : 'var(--vp-c-text-2)'"
      >
        {{ signBit && shiftK > 0 ? `S8 flips to +${logOutS8}!` : `S8 = ${fmtSigned(logOutS8)}` }}
      </text>

      <!-- Divider line between Logical and Arithmetic -->
      <line x1="12" y1="170" x2="670" y2="170" stroke="var(--vp-c-divider)" stroke-width="1" stroke-dasharray="4 3" />

      <!-- Sign-Bit Fan-Out Rail for Arithmetic Shift -->
      <g v-if="shiftK > 0">
        <rect x="12" y="185" width="76" height="24" rx="5" fill="var(--vp-c-brand-soft)" stroke="var(--vp-c-brand-1)" stroke-width="1.3" />
        <text x="50" y="201" text-anchor="middle" font-size="9.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-brand-1)">
          Bit 7 = {{ signBit }}
        </text>
        <path
          :d="`M 88 197 L ${bitX(8 - shiftK)} 197`"
          fill="none"
          stroke="var(--vp-c-brand-1)"
          stroke-width="2"
        />
        <line
          v-for="vb in vacatedBits"
          :key="`sfill-${vb}`"
          :x1="bitX(vb)"
          y1="197"
          :x2="bitX(vb)"
          y2="225"
          stroke="var(--vp-c-brand-1)"
          stroke-width="2"
          marker-end="url(#shift-arrow-brand)"
        />
      </g>
      <!-- Vertical pass-through arrows showing kept slice matches logical row -->
      <line
        v-for="item in keptBits"
        :key="`arr-arith-${item.dst}`"
        :x1="bitX(item.dst)"
        y1="149"
        :x2="bitX(item.dst)"
        y2="225"
        stroke="var(--vp-c-text-2)"
        stroke-width="1.3"
        stroke-dasharray="2 2"
        marker-end="url(#shift-arrow)"
      />

      <!-- ROW 3: ARITHMETIC RIGHT SHIFT (sra) -->
      <text x="12" y="244" font-size="11" font-weight="700" fill="var(--vp-c-brand-1)">Arith. (sra)</text>
      <text x="12" y="257" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">Copy Bit 7</text>

      <g v-for="b in [7, 6, 5, 4, 3, 2, 1, 0]" :key="`arith-${b}`">
        <rect
          :x="bitX(b) - 18"
          y="228"
          width="36"
          height="32"
          rx="6"
          :fill="b > 7 - shiftK ? 'var(--vp-c-brand-soft)' : 'var(--vp-c-bg)'"
          :stroke="b > 7 - shiftK ? 'var(--vp-c-brand-1)' : 'var(--vp-c-divider)'"
          stroke-width="1.5"
        />
        <text
          :x="bitX(b)"
          y="249"
          text-anchor="middle"
          font-size="13.5"
          font-weight="700"
          font-family="var(--vp-font-family-mono)"
          :fill="b > 7 - shiftK ? 'var(--vp-c-brand-1)' : 'var(--vp-c-text-1)'"
        >
          {{ bitOf(arithOutU8, b) }}
        </text>
      </g>

      <!-- Arithmetic result readout box -->
      <rect x="518" y="222" width="152" height="44" rx="7" fill="var(--vp-c-bg)" stroke="var(--vp-c-brand-1)" stroke-width="1.4" />
      <text x="594" y="239" text-anchor="middle" font-size="10.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--hw-green)">
        S8 = {{ fmtSigned(arithOutS8) }} = ⌊{{ inputS8 }}/{{ 1 << shiftK }}⌋
      </text>
      <text x="594" y="257" text-anchor="middle" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">
        Raw U8 = {{ arithOutU8 }} (0x{{ arithOutU8.toString(16).toUpperCase().padStart(2, '0') }})
      </text>

      <!-- Bottom takeaway legend -->
      <text x="340" y="295" text-anchor="middle" font-size="10.5" fill="var(--vp-c-text-2)">
        {{
          shiftK === 0
            ? 'At k = 0, no bits drop or vacate; srl and sra return b unchanged.'
            : `Kept slice Bits 7..${shiftK} slides identically into Bits ${7 - shiftK}..0; only the vacated upper ${shiftK === 1 ? '1 slot diverges' : `${shiftK} slots diverge`} (0 vs. Bit 7).`
        }}
      </text>
    </svg>
    </div>
  </div>
</template>
