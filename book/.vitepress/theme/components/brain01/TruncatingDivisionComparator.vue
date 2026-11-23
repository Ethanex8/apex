<script setup lang="ts">
import { computed, ref } from 'vue'

interface DivPreset {
  label: string
  n: number
  d: number
  note: string
}

const presets: DivPreset[] = [
  {
    label: '-7 ÷ +3 (Opposite Signs)',
    n: -7,
    d: 3,
    note: 'Exact quotient ≈ -2.33: hardware truncates right toward 0 (-2, rem -1), whereas Python floors left toward -∞ (-3, rem +2).',
  },
  {
    label: '+7 ÷ -3 (Negative Divisor)',
    n: 7,
    d: -3,
    note: 'Exact quotient ≈ -2.33: hardware keeps dividend sign on remainder (+1), whereas Python keeps divisor sign (-2).',
  },
  {
    label: '-7 ÷ -3 (Both Negative)',
    n: -7,
    d: -3,
    note: 'Exact quotient ≈ +2.33: both rules agree on quotient +2 and remainder -1 because the quotient is positive.',
  },
  {
    label: '+7 ÷ +3 (Both Positive)',
    n: 7,
    d: 3,
    note: 'Exact quotient ≈ +2.33: both rules agree on quotient +2 and remainder +1.',
  },
]

const selectedIdx = ref<number>(0)
const active = computed(() => presets[selectedIdx.value])

const calc = computed(() => {
  const { n, d } = active.value
  const exact = n / d
  const hwQ = Math.trunc(exact)
  const hwR = n - hwQ * d
  const pyQ = Math.floor(exact)
  const pyR = n - pyQ * d

  // Wide SVG coordinate system (viewBox 560 x 154) so arrows and labels have generous spacing
  const toX = (val: number) => 280 + val * 62
  const clampX = (x: number, pad = 92) => Math.min(560 - pad, Math.max(pad, x))
  return {
    exactStr: exact > 0 ? `+${exact.toFixed(2)}` : exact.toFixed(2),
    exactX: toX(exact),
    exactLabelX: clampX(toX(exact), 60),
    hwQ,
    hwR,
    hwX: toX(hwQ),
    hwLabelX: clampX(toX(hwQ), 96),
    pyQ,
    pyR,
    pyX: toX(pyQ),
    pyLabelX: clampX(toX(pyQ), 96),
    agree: hwQ === pyQ,
    n,
    d,
    ticks: [-4, -3, -2, -1, 0, 1, 2, 3, 4].map((t) => ({ val: t, x: toX(t) })),
  }
})

function fmtSigned(v: number): string {
  return v > 0 ? `+${v}` : `${v}`
}
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">Hardware Truncation Toward Zero vs. Python Floor Division</div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px">
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
    </div>

    <div class="hw-card" style="margin-bottom: 10px">
      <div class="hw-label">
        Number-Line Rounding Direction for {{ calc.n }} ÷ {{ calc.d }} (Exact Quotient ≈ {{ calc.exactStr }})
      </div>
      <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect full number line</div>
      <div style="overflow-x: auto; padding-bottom: 2px">
      <svg
        viewBox="0 0 560 154"
        class="hw-svg-diagram"
        style="min-width: 440px"
        role="img"
        aria-label="Number line comparing hardware truncation toward zero against Python floor division toward negative infinity"
      >
        <defs>
          <marker id="div-arrow-brand" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--vp-c-brand-1)" />
          </marker>
          <marker id="div-arrow-red" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--hw-red)" />
          </marker>
        </defs>

        <!-- Zero reference axis -->
        <line x1="280" y1="12" x2="280" y2="68" stroke="var(--vp-c-divider)" stroke-width="1.8" stroke-dasharray="4 3" />
        <line x1="280" y1="104" x2="280" y2="144" stroke="var(--vp-c-divider)" stroke-width="1.8" stroke-dasharray="4 3" />
        <!-- Main number line -->
        <line x1="22" y1="76" x2="538" y2="76" stroke="var(--vp-c-text-2)" stroke-width="2" />

        <!-- Integer ticks -->
        <g v-for="t in calc.ticks" :key="t.val">
          <line :x1="t.x" y1="70" :x2="t.x" y2="82" stroke="var(--vp-c-text-2)" stroke-width="1.5" />
          <text
            :x="t.x"
            y="99"
            text-anchor="middle"
            font-size="12.5"
            font-family="var(--vp-font-family-mono)"
            :font-weight="t.val === 0 ? '800' : '600'"
            :fill="t.val === 0 ? 'var(--vp-c-text-1)' : 'var(--vp-c-text-2)'"
          >
            {{ t.val }}
          </text>
        </g>

        <!-- Dashed vertical drop guides connecting exact point and rounded targets to arrows -->
        <line :x1="calc.exactX" y1="38" :x2="calc.exactX" y2="118" stroke="var(--hw-amber)" stroke-width="1.4" stroke-dasharray="3 2" />
        <line :x1="calc.hwX" y1="38" :x2="calc.hwX" y2="70" stroke="var(--vp-c-brand-1)" stroke-width="1.4" stroke-dasharray="3 2" />
        <line :x1="calc.pyX" y1="104" :x2="calc.pyX" y2="118" stroke="var(--hw-red)" stroke-width="1.4" stroke-dasharray="3 2" />

        <!-- Hardware Truncation Arrow (Top, Toward 0) -->
        <line
          :x1="calc.exactX"
          y1="38"
          :x2="calc.hwX"
          y2="38"
          stroke="var(--vp-c-brand-1)"
          stroke-width="2.6"
          marker-end="url(#div-arrow-brand)"
        />
        <circle :cx="calc.hwX" cy="76" r="5.5" fill="var(--vp-c-brand-1)" />
        <text
          :x="calc.hwLabelX"
          y="23"
          text-anchor="middle"
          font-size="12.5"
          font-weight="700"
          fill="var(--vp-c-brand-1)"
        >
          RISC-V div = {{ fmtSigned(calc.hwQ) }} (rem {{ fmtSigned(calc.hwR) }})
        </text>

        <!-- Python Floor Arrow (Bottom, Toward -∞) -->
        <line
          :x1="calc.exactX"
          y1="118"
          :x2="calc.pyX"
          y2="118"
          stroke="var(--hw-red)"
          stroke-width="2.6"
          marker-end="url(#div-arrow-red)"
        />
        <circle :cx="calc.pyX" cy="76" r="5.5" :fill="calc.agree ? 'var(--vp-c-brand-1)' : 'var(--hw-red)'" />
        <text
          :x="calc.pyLabelX"
          y="142"
          text-anchor="middle"
          font-size="12.5"
          font-weight="700"
          fill="var(--hw-red)"
        >
          Python // = {{ fmtSigned(calc.pyQ) }} (% = {{ fmtSigned(calc.pyR) }})
        </text>

        <!-- Exact real-number marker on axis -->
        <circle :cx="calc.exactX" cy="76" r="5" fill="var(--hw-amber)" stroke="var(--vp-c-bg)" stroke-width="1.5" />
      </svg>
      </div>
    </div>

    <div class="hw-card" style="font-size: 12.5px; color: var(--vp-c-text-2)">
      <strong style="color: var(--vp-c-text-1)">Takeaway: </strong>{{ active.note }}
    </div>
  </div>
</template>
