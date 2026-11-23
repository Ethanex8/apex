<script setup lang="ts">
import { computed, ref } from 'vue'

// Interactive 4-bit -> 8-bit wire fan-out schematic illustrating passive sign-wire replication vs. grounded 0 tie-offs.
const bits4 = ref<number>(0b1011) // -5 signed, 11 unsigned

const presets = [
  { label: '+5 (0101)', val: 0b0101 },
  { label: '-5 (1011)', val: 0b1011 },
  { label: '-1 (1111)', val: 0b1111 },
  { label: '-8 (1000)', val: 0b1000 },
  { label: '+7 (0111)', val: 0b0111 },
]

function toggleBit(idx: number) {
  bits4.value = (bits4.value ^ (1 << idx)) & 0xf
}

const signBit = computed(() => (bits4.value >> 3) & 1)
const u4 = computed(() => bits4.value & 0xf)
const s4 = computed(() => (signBit.value ? u4.value - 16 : u4.value))

const zextBits = computed(() =>
  Array.from({ length: 8 }, (_, idx) => {
    const bitIdx = 7 - idx
    return bitIdx >= 4 ? 0 : (bits4.value >> bitIdx) & 1
  })
)

const sextBits = computed(() =>
  Array.from({ length: 8 }, (_, idx) => {
    const bitIdx = 7 - idx
    return bitIdx >= 4 ? signBit.value : (bits4.value >> bitIdx) & 1
  })
)

const zextU8 = computed(() => u4.value)
const sextU8 = computed(() => (signBit.value ? 0xf0 | u4.value : u4.value))
const sextS8 = computed(() => s4.value)

function fmtSigned(v: number): string {
  return v > 0 ? `+${v}` : `${v}`
}

// SVG lane coordinates for 8 bits inside a half-panel (width 310)
function laneX(panelOffset: number, bitPos: number): number {
  return panelOffset + (7 - bitPos) * 34 + 28
}
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">Zero Extension vs. Sign Extension Wire Copying (4-Bit to 8-Bit)</div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px">
        <button
          v-for="p in presets"
          :key="p.label"
          type="button"
          class="hw-btn hw-mono"
          :class="{ active: bits4 === p.val }"
          @click="bits4 = p.val"
        >
          {{ p.label }}
        </button>
      </div>
    </div>

    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 10px">
      <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap">
        <span style="font-size: 12.5px; font-weight: 700; color: var(--vp-c-text-2)">Click 4-Bit Input (Bits 3..0):</span>
        <button
          v-for="b in [3, 2, 1, 0]"
          :key="`in-${b}`"
          type="button"
          class="hw-btn hw-mono"
          :class="{ active: ((bits4 >> b) & 1) === 1 }"
          style="min-width: 46px; padding: 4px 8px"
          @click="toggleBit(b)"
        >
          b{{ b }}={{ (bits4 >> b) & 1 }}
        </button>
      </div>
      <div class="hw-mono" style="font-size: 12.5px; color: var(--vp-c-text-2)">
        U<sub>4</sub> = <strong style="color: var(--vp-c-text-1)">{{ u4 }}</strong> · S<sub>4</sub> =
        <strong :style="{ color: signBit ? 'var(--hw-red)' : 'var(--hw-green)' }">{{ fmtSigned(s4) }}</strong>
        (Sign wire Bit 3 = <strong>{{ signBit }}</strong>)
      </div>
    </div>

    <!-- True SVG Wire Schematic comparing Zero Extension vs. Sign Extension -->
    <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect both 8-bit wire schematics</div>
    <div style="overflow-x: auto; padding-bottom: 4px">
    <svg
      viewBox="0 0 680 236"
      class="hw-svg-diagram"
      style="min-width: 550px"
      role="img"
      aria-label="Wire schematic comparing zero extension tied to constant 0 against passive sign-bit copying across upper bits"
    >
      <!-- LEFT PANEL: ZERO EXTENSION -->
      <rect x="6" y="6" width="324" height="224" rx="10" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.2" />
      <text x="168" y="27" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--vp-c-text-1)">
        Zero Extension (Bits 7..4 tied to constant 0)
      </text>

      <!-- Constant 0 Rail on Left -->
      <rect x="22" y="42" width="128" height="24" rx="6" fill="var(--vp-c-bg-soft)" stroke="var(--vp-c-divider)" stroke-width="1.2" />
      <text x="86" y="58" text-anchor="middle" font-size="10.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">
        Constant 0 Rail
      </text>
      <!-- Bus drop wires to Bits 7..4 -->
      <line x1="36" y1="66" x2="36" y2="122" stroke="var(--vp-c-text-3)" stroke-width="1.8" stroke-dasharray="3 2" />
      <line x1="70" y1="66" x2="70" y2="122" stroke="var(--vp-c-text-3)" stroke-width="1.8" stroke-dasharray="3 2" />
      <line x1="104" y1="66" x2="104" y2="122" stroke="var(--vp-c-text-3)" stroke-width="1.8" stroke-dasharray="3 2" />
      <line x1="138" y1="66" x2="138" y2="122" stroke="var(--vp-c-text-3)" stroke-width="1.8" stroke-dasharray="3 2" />

      <!-- Input 4-bit cells on Left (Bits 3..0) -->
      <g v-for="b in [3, 2, 1, 0]" :key="`z-in-${b}`">
        <rect
          :x="laneX(8, b) - 13"
          y="42"
          width="26"
          height="24"
          rx="5"
          fill="var(--vp-c-bg-soft)"
          stroke="var(--vp-c-divider)"
          stroke-width="1.2"
        />
        <text
          :x="laneX(8, b)"
          y="58"
          text-anchor="middle"
          font-size="11.5"
          font-weight="700"
          font-family="var(--vp-font-family-mono)"
          fill="var(--vp-c-text-1)"
        >
          {{ (bits4 >> b) & 1 }}
        </text>
        <!-- Straight pass-through wire -->
        <line
          :x1="laneX(8, b)"
          y1="66"
          :x2="laneX(8, b)"
          y2="122"
          stroke="var(--vp-c-text-2)"
          stroke-width="2"
        />
      </g>

      <!-- Output 8-bit row on Left -->
      <g v-for="(val, idx) in zextBits" :key="`z-out-${idx}`">
        <rect
          :x="laneX(8, 7 - idx) - 13"
          y="124"
          width="26"
          height="28"
          rx="5"
          :fill="idx < 4 ? 'var(--vp-c-bg-soft)' : 'var(--vp-c-bg)'"
          :stroke="idx < 4 ? 'var(--vp-c-text-3)' : 'var(--vp-c-brand-1)'"
          stroke-width="1.4"
        />
        <text
          :x="laneX(8, 7 - idx)"
          y="142"
          text-anchor="middle"
          font-size="12"
          font-weight="700"
          font-family="var(--vp-font-family-mono)"
          :fill="idx < 4 ? 'var(--vp-c-text-2)' : 'var(--vp-c-text-1)'"
        >
          {{ val }}
        </text>
        <text
          :x="laneX(8, 7 - idx)"
          y="165"
          text-anchor="middle"
          font-size="8.5"
          font-family="var(--vp-font-family-mono)"
          fill="var(--vp-c-text-2)"
        >
          b{{ 7 - idx }}
        </text>
      </g>

      <text x="168" y="191" text-anchor="middle" font-size="11.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        U8 = {{ zextU8 }} (0x{{ zextU8.toString(16).toUpperCase().padStart(2, '0') }}) · S8 = {{ fmtSigned(zextU8) }}
      </text>
      <text
        x="168"
        y="211"
        text-anchor="middle"
        font-size="10.5"
        font-weight="600"
        :fill="signBit ? 'var(--hw-red)' : 'var(--hw-green)'"
      >
        {{ signBit ? 'Preserves U4, shifts negative S4 by +16' : 'Non-negative: preserves both U4 and S4' }}
      </text>

      <!-- RIGHT PANEL: SIGN EXTENSION -->
      <rect x="350" y="6" width="324" height="224" rx="10" fill="var(--vp-c-bg)" stroke="var(--vp-c-brand-1)" stroke-width="1.4" />
      <text x="512" y="27" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--vp-c-text-1)">
        Sign Extension (Passive Bit 3 wire copy)
      </text>

      <!-- Passive Copy Tree from Bit 3 (laneX(352, 3)) across Bits 7..4 -->
      <path
        :d="`M ${laneX(352, 3)} 66 L ${laneX(352, 3)} 92 L ${laneX(352, 7)} 92 L ${laneX(352, 7)} 122 M ${laneX(352, 6)} 92 L ${laneX(352, 6)} 122 M ${laneX(352, 5)} 92 L ${laneX(352, 5)} 122 M ${laneX(352, 4)} 92 L ${laneX(352, 4)} 122`"
        fill="none"
        :stroke="signBit ? 'var(--vp-c-brand-1)' : 'var(--hw-green)'"
        stroke-width="2.2"
        stroke-linejoin="round"
      />
      <!-- Wire junction dot on Bit 3 -->
      <circle :cx="laneX(352, 3)" cy="92" r="4" :fill="signBit ? 'var(--vp-c-brand-1)' : 'var(--hw-green)'" />
      <text
        x="432"
        y="84"
        text-anchor="middle"
        font-size="9.5"
        font-weight="700"
        :fill="signBit ? 'var(--vp-c-brand-1)' : 'var(--hw-green)'"
      >
        Copy Bit 3 = {{ signBit }} to Bits 7..4
      </text>

      <!-- Input 4-bit cells on Right (Bits 3..0) -->
      <g v-for="b in [3, 2, 1, 0]" :key="`s-in-${b}`">
        <rect
          :x="laneX(352, b) - 13"
          y="42"
          width="26"
          height="24"
          rx="5"
          :fill="b === 3 ? 'var(--vp-c-brand-soft)' : 'var(--vp-c-bg-soft)'"
          :stroke="b === 3 ? 'var(--vp-c-brand-1)' : 'var(--vp-c-divider)'"
          :stroke-width="b === 3 ? 1.8 : 1.2"
        />
        <text
          :x="laneX(352, b)"
          y="58"
          text-anchor="middle"
          font-size="11.5"
          font-weight="700"
          font-family="var(--vp-font-family-mono)"
          :fill="b === 3 ? 'var(--vp-c-brand-1)' : 'var(--vp-c-text-1)'"
        >
          {{ (bits4 >> b) & 1 }}
        </text>
        <line
          :x1="laneX(352, b)"
          y1="66"
          :x2="laneX(352, b)"
          y2="122"
          :stroke="b === 3 ? (signBit ? 'var(--vp-c-brand-1)' : 'var(--hw-green)') : 'var(--vp-c-text-2)'"
          stroke-width="2"
        />
      </g>

      <!-- Output 8-bit row on Right -->
      <g v-for="(val, idx) in sextBits" :key="`s-out-${idx}`">
        <rect
          :x="laneX(352, 7 - idx) - 13"
          y="124"
          width="26"
          height="28"
          rx="5"
          :fill="idx < 4 ? 'var(--vp-c-brand-soft)' : 'var(--vp-c-bg)'"
          :stroke="idx < 4 ? (signBit ? 'var(--vp-c-brand-1)' : 'var(--hw-green)') : 'var(--vp-c-divider)'"
          stroke-width="1.4"
        />
        <text
          :x="laneX(352, 7 - idx)"
          y="142"
          text-anchor="middle"
          font-size="12"
          font-weight="700"
          font-family="var(--vp-font-family-mono)"
          :fill="idx < 4 ? (signBit ? 'var(--vp-c-brand-1)' : 'var(--hw-green)') : 'var(--vp-c-text-1)'"
        >
          {{ val }}
        </text>
        <text
          :x="laneX(352, 7 - idx)"
          y="165"
          text-anchor="middle"
          font-size="8.5"
          font-family="var(--vp-font-family-mono)"
          fill="var(--vp-c-text-2)"
        >
          b{{ 7 - idx }}
        </text>
      </g>

      <text x="512" y="191" text-anchor="middle" font-size="11.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        S8 = {{ fmtSigned(sextS8) }} (0x{{ sextU8.toString(16).toUpperCase().padStart(2, '0') }}) · U8 = {{ sextU8 }}
      </text>
      <text x="512" y="211" text-anchor="middle" font-size="10.5" font-weight="600" fill="var(--hw-green)">
        Preserves signed S4 = {{ fmtSigned(s4) }} across all widths
      </text>
    </svg>
    </div>
  </div>
</template>
