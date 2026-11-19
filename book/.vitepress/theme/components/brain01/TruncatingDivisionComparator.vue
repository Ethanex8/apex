<script setup lang="ts">
import { computed, ref } from 'vue'

interface DivPreset {
  label: string
  dividend: number
  divisor: number
  isSentinel?: boolean
  sentinelTitle?: string
  sentinelRows?: Array<{ insn: string; result: string; explain: string; color: string }>
}

const presets: DivPreset[] = [
  { label: '-7 ÷ +3 (Truncation vs Floor)', dividend: -7, divisor: 3 },
  { label: '+7 ÷ -3 (Positive Dividend)', dividend: 7, divisor: -3 },
  { label: '-7 ÷ -3 (Both Negative)', dividend: -7, divisor: -3 },
  {
    label: 'Divide by Zero (-7 ÷ 0)',
    dividend: -7,
    divisor: 0,
    isSentinel: true,
    sentinelTitle: 'Zero-Divisor Hardware Sentinel Outputs (No Hardware Trap)',
    sentinelRows: [
      {
        insn: 'div (-7 ÷ 0)',
        result: '-1 (0xFFFF_FFFF)',
        explain: 'Signed divide by zero always returns all-1s (-1) without jumping to a trap handler.',
        color: 'var(--vp-c-brand-1)',
      },
      {
        insn: 'divu (0xFFFF_FFF9 ÷ 0)',
        result: '0xFFFF_FFFF (UINT32_MAX)',
        explain: 'Unsigned divide by zero returns 2^32 - 1 so hardware never needs a division-fault line.',
        color: 'var(--hw-green)',
      },
      {
        insn: 'rem / remu (-7 % 0)',
        result: '-7 / 0xFFFF_FFF9 (Dividend)',
        explain: 'Preserves Euclidean identity q × 0 + rem = dividend cleanly by returning rs1 unchanged.',
        color: 'var(--hw-purple)',
      },
    ],
  },
  {
    label: 'Overflow (-2^31 ÷ -1)',
    dividend: -2147483648,
    divisor: -1,
    isSentinel: true,
    sentinelTitle: "Two's-Complement Asymmetric Range Overflow (-2^31 ÷ -1)",
    sentinelRows: [
      {
        insn: 'div (INT32_MIN ÷ -1)',
        result: 'INT32_MIN (-2,147,483,648)',
        explain: 'True quotient +2^31 exceeds INT32_MAX (2^31 - 1); signed hardware wraps once to INT32_MIN without trapping.',
        color: 'var(--hw-amber)',
      },
      {
        insn: 'rem (INT32_MIN % -1)',
        result: '0 (Zero Remainder)',
        explain: 'Exact divisibility holds (-1 divides -2^31 evenly), so remainder returns 0 cleanly.',
        color: 'var(--hw-green)',
      },
    ],
  },
]

const selectedIdx = ref(0)
const preset = computed(() => presets[selectedIdx.value])

const calc = computed(() => {
  const n = preset.value.dividend
  const d = preset.value.divisor
  if (d === 0 || preset.value.isSentinel) return null
  const exact = n / d
  const hwQ = Math.trunc(exact)
  const hwR = n - hwQ * d
  const pyQ = Math.floor(exact)
  const pyR = n - pyQ * d

  // Map [-4, +4] onto compact SVG x range [36, 364] inside viewBox 0..400 so mobile never clips
  const toX = (val: number) => 200 + val * 41
  const clampLabelX = (x: number, pad = 74) => Math.min(400 - pad, Math.max(pad, x))
  return {
    exactStr: exact.toFixed(2),
    exactX: toX(exact),
    exactLabelX: clampLabelX(toX(exact), 48),
    hwQ,
    hwR,
    hwX: toX(hwQ),
    hwLabelX: clampLabelX(toX(hwQ), 76),
    pyQ,
    pyR,
    pyX: toX(pyQ),
    pyLabelX: clampLabelX(toX(pyQ), 78),
    n,
    d,
    ticks: [-4, -3, -2, -1, 0, 1, 2, 3, 4].map((t) => ({ val: t, x: toX(t) })),
  }
})
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">
        <span class="hw-badge">Division Semantics</span>
        <span>Hardware Truncation Toward Zero vs. Python Floor Toward Negative Infinity</span>
      </div>
    </div>

    <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px">
      <button
        v-for="(p, idx) in presets"
        :key="p.label"
        type="button"
        class="hw-btn"
        :class="{ active: selectedIdx === idx }"
        @click="selectedIdx = idx"
      >
        {{ p.label }}
      </button>
    </div>

    <!-- Finite Division Visual Comparator -->
    <div v-if="calc">
      <div class="hw-card" style="margin-bottom: 10px">
        <div class="hw-label">Number-Line Step Direction (Real Quotient = {{ calc.exactStr }})</div>
        <svg viewBox="0 0 400 124" style="width: 100%; height: auto; display: block">
          <defs>
            <marker id="div-arrow-brand" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--vp-c-brand-1)" />
            </marker>
            <marker id="div-arrow-red" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--hw-red)" />
            </marker>
          </defs>

          <!-- Zero Baseline Highlight (split cleanly around the '0' tick label) -->
          <line x1="200" y1="14" x2="200" y2="62" stroke="var(--vp-c-divider)" stroke-width="2" stroke-dasharray="4 3" />
          <line x1="200" y1="82" x2="200" y2="96" stroke="var(--vp-c-divider)" stroke-width="2" stroke-dasharray="4 3" />
          <line x1="20" y1="56" x2="380" y2="56" stroke="var(--vp-c-text-2)" stroke-width="2" />

          <!-- Integer Ticks -->
          <g v-for="t in calc.ticks" :key="t.val">
            <line :x1="t.x" y1="50" :x2="t.x" y2="62" stroke="var(--vp-c-text-2)" stroke-width="1.5" />
            <text
              :x="t.x"
              y="76"
              text-anchor="middle"
              font-size="10.5"
              font-family="var(--vp-font-family-mono)"
              :font-weight="t.val === 0 ? '800' : '600'"
              :fill="t.val === 0 ? 'var(--vp-c-text-1)' : 'var(--vp-c-text-2)'"
            >
              {{ t.val }}
            </text>
          </g>

          <!-- Hardware Truncation Arrow (Toward Zero) -->
          <line
            :x1="calc.exactX"
            y1="28"
            :x2="calc.hwX"
            y2="28"
            stroke="var(--vp-c-brand-1)"
            stroke-width="2.5"
            marker-end="url(#div-arrow-brand)"
          />
          <circle :cx="calc.hwX" cy="56" r="5.5" fill="var(--vp-c-brand-1)" />
          <text
            :x="calc.hwLabelX"
            y="18"
            text-anchor="middle"
            font-size="10"
            font-weight="800"
            fill="var(--vp-c-brand-1)"
          >
            RV32M div = {{ calc.hwQ }} (Toward 0)
          </text>

          <!-- Exact Real Quotient Marker -->
          <circle :cx="calc.exactX" cy="56" r="4.5" fill="var(--hw-amber)" />
          <text
            :x="calc.exactLabelX"
            y="45"
            text-anchor="middle"
            font-size="9.5"
            font-weight="700"
            fill="var(--hw-amber)"
          >
            Exact = {{ calc.exactStr }}
          </text>

          <!-- Python Floor Arrow (Toward -Infinity) -->
          <line
            v-if="calc.pyQ !== calc.hwQ"
            :x1="calc.exactX"
            y1="92"
            :x2="calc.pyX"
            y2="92"
            stroke="var(--hw-red)"
            stroke-width="2.5"
            marker-end="url(#div-arrow-red)"
          />
          <circle v-if="calc.pyQ !== calc.hwQ" :cx="calc.pyX" cy="56" r="5" fill="var(--hw-red)" opacity="0.85" />
          <text
            v-if="calc.pyQ !== calc.hwQ"
            :x="calc.pyLabelX"
            y="110"
            text-anchor="middle"
            font-size="9.5"
            font-weight="800"
            fill="var(--hw-red)"
          >
            Python // = {{ calc.pyQ }} (Toward -∞)
          </text>
        </svg>
      </div>

      <div class="hw-grid-2">
        <div class="hw-card" style="border-left: 3px solid var(--vp-c-brand-1)">
          <div class="hw-label" style="color: var(--vp-c-brand-1)">RISC-V Hardware (Truncates Toward Zero)</div>
          <div class="hw-mono" style="font-size: 13.5px; font-weight: 700; margin-bottom: 4px">
            div = {{ calc.hwQ }}, rem = {{ calc.hwR }}
          </div>
          <div class="hw-mono" style="font-size: 12px; color: var(--vp-c-text-2)">
            Check: ({{ calc.hwQ }}) × ({{ calc.d }}) + ({{ calc.hwR }}) = {{ calc.hwQ * calc.d + calc.hwR }}
          </div>
          <div style="font-size: 12px; color: var(--vp-c-text-2); margin-top: 4px">
            Remainder takes the sign of the dividend ({{ calc.n }}).
          </div>
        </div>

        <div class="hw-card" style="border-left: 3px solid var(--hw-red)">
          <div class="hw-label" style="color: var(--hw-red)">Naive Python <code>//</code> (Floors Toward -∞)</div>
          <div class="hw-mono" style="font-size: 13.5px; font-weight: 700; margin-bottom: 4px">
            {{ calc.n }} // {{ calc.d }} = {{ calc.pyQ }}, {{ calc.n }} % {{ calc.d }} = {{ calc.pyR }}
          </div>
          <div class="hw-mono" style="font-size: 12px; color: var(--vp-c-text-2)">
            Check: ({{ calc.pyQ }}) × ({{ calc.d }}) + ({{ calc.pyR }}) = {{ calc.pyQ * calc.d + calc.pyR }}
          </div>
          <div style="font-size: 12px; color: var(--vp-c-text-2); margin-top: 4px">
            {{ calc.hwQ === calc.pyQ ? 'Coincides here only because quotient is positive.' : 'Differs from RISC-V; the oracle uses trunc_div_s32().' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Sentinel Preset View -->
    <div v-else class="hw-card">
      <div class="hw-label">{{ preset.sentinelTitle }}</div>
      <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 6px">
        <div
          v-for="row in preset.sentinelRows"
          :key="row.insn"
          style="padding: 8px 10px; border-radius: 6px; border: 1px solid var(--vp-c-divider); background: var(--vp-c-bg)"
          :style="{ borderLeft: `4px solid ${row.color}` }"
        >
          <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 6px; margin-bottom: 2px">
            <span class="hw-mono" style="font-weight: 800; font-size: 13px" :style="{ color: row.color }">{{ row.insn }}</span>
            <span class="hw-mono" style="font-weight: 700; font-size: 13px">{{ row.result }}</span>
          </div>
          <div style="font-size: 12.5px; color: var(--vp-c-text-2)">{{ row.explain }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
