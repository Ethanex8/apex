<script setup lang="ts">
import { computed, ref } from 'vue'

interface MacPreset {
  label: string
  insn: string
  funct3: 0 | 1 | 2 | 3
  rd: number
  priorAcc: number
  a0: number
  a1: number
  b0: number
  b1: number
  explain: string
}

const INT32_MIN = -2147483648
const INT32_MAX = 2147483647

const presets: MacPreset[] = [
  {
    label: '1. Neuron Dot Step (mac)',
    insn: 'mac x11, x2, x3',
    funct3: 0,
    rd: 11,
    priorAcc: 1000,
    a0: 10,
    a1: -20,
    b0: 5,
    b1: 6,
    explain: 'Dual 16-bit multiplier lanes compute (10×5) + (-20×6) = -70 in one cycle and add onto preloaded bias +1000 → +930.',
  },
  {
    label: '2. Discard rd = x0 (mac.clr)',
    insn: 'mac.clr x0, x3, x4',
    funct3: 1,
    rd: 0,
    priorAcc: 2147483647,
    a0: 3,
    a1: 4,
    b0: 10,
    b1: 20,
    explain: 'mac.clr sets base_acc = 0, computes 3×10 + 4×20 = 110, updates internal mac_acc = 110, while x0 stays hardwired to 0.',
  },
  {
    label: '3. +Sat Clamp (-32768 × -32768)',
    insn: 'mac.clr x10, x1, x1',
    funct3: 1,
    rd: 10,
    priorAcc: 0,
    a0: -32768,
    a1: -32768,
    b0: -32768,
    b1: -32768,
    explain: 'Unclamped sum = +2,147,483,648 (+2^31), which exceeds INT32_MAX by 1; sat32 clamps to +2,147,483,647 instead of wrapping negative.',
  },
  {
    label: '4. -Sat Clamp (INT32_MIN Guard)',
    insn: 'mac x11, x5, x1',
    funct3: 0,
    rd: 11,
    priorAcc: -2147418112,
    a0: 32767,
    a1: 32767,
    b0: -32768,
    b1: -32768,
    explain: 'Starting near -2.147B and accumulating another -2.147B hits -4,294,836,224; sat32 clamps strictly to INT32_MIN (-2,147,483,648).',
  },
]

const selectedIdx = ref(0)
const cur = computed(() => presets[selectedIdx.value])

function fmtPacked(lo: number, hi: number): string {
  const loHex = (lo & 0xffff).toString(16).toUpperCase().padStart(4, '0')
  const hiHex = (hi & 0xffff).toString(16).toUpperCase().padStart(4, '0')
  return `0x${hiHex}_${loHex}`
}

const trace = computed(() => {
  const c = cur.value
  const p0 = c.a0 * c.b0
  const p1 = c.a1 * c.b1
  const baseAcc = c.funct3 === 1 ? 0 : c.priorAcc
  const rawSum = baseAcc + p0 + p1
  const saturatedPos = rawSum > INT32_MAX
  const saturatedNeg = rawSum < INT32_MIN
  const clamped = saturatedPos ? INT32_MAX : saturatedNeg ? INT32_MIN : rawSum
  return {
    rs1Hex: fmtPacked(c.a0, c.a1),
    rs2Hex: fmtPacked(c.b0, c.b1),
    p0,
    p1,
    baseAcc,
    rawSum,
    clamped,
    didClamp: saturatedPos || saturatedNeg,
    clampLabel: saturatedPos ? 'CLAMPED TO INT32_MAX' : saturatedNeg ? 'CLAMPED TO INT32_MIN' : 'NO OVERFLOW (EXACT)',
  }
})
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">
        <span class="hw-badge">Xapex custom-0 Datapath</span>
        <span>Dual-Int16 Packed Lanes, Twin Multipliers & Saturating Accumulator</span>
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

    <!-- Stage Flow Grid -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(168px, 1fr)); gap: 8px; margin-bottom: 10px">
      <!-- Stage 1: Lane Unpack -->
      <div class="hw-card" style="border-top: 3px solid var(--hw-green)">
        <div class="hw-label" style="color: var(--hw-green)">1. Unpack Two 16-Bit Signed Lanes</div>
        <div class="hw-mono" style="font-size: 12px; margin-bottom: 2px">
          <strong>rs1</strong> ({{ trace.rs1Hex }}):
        </div>
        <div class="hw-mono" style="font-size: 11px; color: var(--vp-c-text-2); margin-bottom: 6px; line-height: 1.45">
          <div style="white-space: nowrap">Bits 31..16 (a1) = {{ cur.a1 }}</div>
          <div style="white-space: nowrap">Bits 15..0 (a0) = {{ cur.a0 }}</div>
        </div>
        <div class="hw-mono" style="font-size: 12px; margin-bottom: 2px">
          <strong>rs2</strong> ({{ trace.rs2Hex }}):
        </div>
        <div class="hw-mono" style="font-size: 11px; color: var(--vp-c-text-2); line-height: 1.45">
          <div style="white-space: nowrap">Bits 31..16 (b1) = {{ cur.b1 }}</div>
          <div style="white-space: nowrap">Bits 15..0 (b0) = {{ cur.b0 }}</div>
        </div>
      </div>

      <!-- Stage 2: Twin 18x18 Multipliers & Accumulate -->
      <div class="hw-card" style="border-top: 3px solid var(--hw-purple)">
        <div class="hw-label" style="color: var(--hw-purple)">2. Twin 18×18 DSP Products + Base</div>
        <div class="hw-mono" style="font-size: 11.5px; margin-bottom: 3px">
          <span style="white-space: nowrap">Lane 0: {{ cur.a0 }} × {{ cur.b0 }} =</span>{{ ' ' }}<strong style="white-space: nowrap">{{ trace.p0.toLocaleString() }}</strong>
        </div>
        <div class="hw-mono" style="font-size: 11.5px; margin-bottom: 3px">
          <span style="white-space: nowrap">Lane 1: {{ cur.a1 }} × {{ cur.b1 }} =</span>{{ ' ' }}<strong style="white-space: nowrap">{{ trace.p1.toLocaleString() }}</strong>
        </div>
        <div class="hw-mono" style="font-size: 11.5px; margin-bottom: 3px">
          base_acc: <strong>{{ trace.baseAcc.toLocaleString() }}</strong>{{ ' ' }}<span style="color: var(--vp-c-text-2)">({{ cur.funct3 === 1 ? 'cleared' : 'prior mac_acc' }})</span>
        </div>
        <div class="hw-mono" style="font-size: 11px; color: var(--hw-amber); margin-top: 4px">
          <span style="white-space: nowrap">Raw Sum =</span>{{ ' ' }}<span style="white-space: nowrap">{{ trace.rawSum.toLocaleString() }}</span>
        </div>
      </div>

      <!-- Stage 3: sat32 Clamp + Dual Writeback -->
      <div
        class="hw-card"
        :style="{ borderTop: `3px solid ${trace.didClamp ? 'var(--hw-red)' : 'var(--vp-c-brand-1)'}` }"
      >
        <div class="hw-label" :style="{ color: trace.didClamp ? 'var(--hw-red)' : 'var(--vp-c-brand-1)' }">
          3. <code>sat32</code> Clamp → <code>mac_acc</code> &amp; <code>x{{ cur.rd }}</code>
        </div>
        <div
          class="hw-mono"
          style="font-size: 11px; font-weight: 800; margin-bottom: 4px"
          :style="{ color: trace.didClamp ? 'var(--hw-red)' : 'var(--hw-green)' }"
        >
          {{ trace.clampLabel }}
        </div>
        <div class="hw-mono" style="font-size: 11.5px; font-weight: 700; margin-bottom: 4px">
          <span style="white-space: nowrap">mac_acc =</span>{{ ' ' }}<span style="white-space: nowrap">{{ trace.clamped.toLocaleString() }}</span>
        </div>
        <div class="hw-mono" style="font-size: 11px; color: var(--vp-c-text-2)">
          Register x{{ cur.rd }} = {{ cur.rd === 0 ? '0 (discarded by x0)' : trace.clamped.toLocaleString() }}
        </div>
      </div>
    </div>

    <div class="hw-card" style="font-size: 13px">
      <strong class="hw-mono" style="color: var(--vp-c-brand-1)">{{ cur.insn }}: </strong>
      <span>{{ cur.explain }}</span>
    </div>
  </div>
</template>
