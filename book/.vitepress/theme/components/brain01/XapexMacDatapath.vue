<script setup lang="ts">
import { computed, ref } from 'vue'

interface MacPreset {
  label: string
  insn: string
  funct3: 0 | 1 | 2 | 3
  rd: number
  priorAcc: number
  rs1Scalar?: number
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
    label: '1. Neuron Dot (mac)',
    insn: 'mac x11, x2, x3',
    funct3: 0,
    rd: 11,
    priorAcc: 1000,
    a0: 10,
    a1: -20,
    b0: 5,
    b1: 6,
    explain: 'Dual 16-bit multiplier lanes compute (10×5) + (-20×6) = -70 in one instruction and add onto prior mac_acc (+1,000) → +930.',
  },
  {
    label: '2. Discard x0 (mac.clr)',
    insn: 'mac.clr x0, x3, x4',
    funct3: 1,
    rd: 0,
    priorAcc: 2147483647,
    a0: 3,
    a1: 4,
    b0: 10,
    b1: 20,
    explain: 'mac.clr selects 0 at the accumulator multiplexer, computes 3×10 + 4×20 = 110, updates mac_acc = 110, while x0 discards register writeback.',
  },
  {
    label: '3. Preload Bias (mac.set)',
    insn: 'mac.set x10, x1',
    funct3: 2,
    rd: 10,
    priorAcc: 999,
    rs1Scalar: -1024,
    a0: -1024,
    a1: -1,
    b0: 0,
    b1: 0,
    explain: 'mac.set bypasses both multipliers, loads s32(rs1) = -1,024 directly into mac_acc, and writes the copy to x10.',
  },
  {
    label: '4. Read Back (mac.get)',
    insn: 'mac.get x12',
    funct3: 3,
    rd: 12,
    priorAcc: 930,
    a0: 0,
    a1: 0,
    b0: 0,
    b1: 0,
    explain: 'mac.get reads mac_acc (+930) directly to x12 without altering mac_acc or reading rs1/rs2.',
  },
  {
    label: '5. +Sat Clamp (-32768²)',
    insn: 'mac.clr x10, x1, x1',
    funct3: 1,
    rd: 10,
    priorAcc: 0,
    a0: -32768,
    a1: -32768,
    b0: -32768,
    b1: -32768,
    explain: 'Raw sum = +2,147,483,648 (+2^31) exceeds INT32_MAX by 1; sat32 clamps to +2,147,483,647 instead of wrapping negative.',
  },
  {
    label: '6. -Sat Clamp (INT32_MIN)',
    insn: 'mac x11, x5, x1',
    funct3: 0,
    rd: 11,
    priorAcc: -2147418112,
    a0: 32767,
    a1: 32767,
    b0: -32768,
    b1: -32768,
    explain: 'Starting near -2.147B and adding -2.147B reaches -4,294,836,224; sat32 clamps strictly to INT32_MIN (-2,147,483,648).',
  },
]

const selectedIdx = ref(0)
const cur = computed(() => presets[selectedIdx.value])

function fmtPacked(lo: number, hi: number): string {
  const loHex = (lo & 0xffff).toString(16).toUpperCase().padStart(4, '0')
  const hiHex = (hi & 0xffff).toString(16).toUpperCase().padStart(4, '0')
  return `0x${hiHex}_${loHex}`
}

function fmtHex32(val: number): string {
  return `0x${(val >>> 0).toString(16).toUpperCase().padStart(8, '0').replace(/(.{4})(.{4})/, '$1_$2')}`
}

function fmtNum(n: number): string {
  return n.toLocaleString('en-US')
}

const trace = computed(() => {
  const c = cur.value
  const isMac = c.funct3 === 0 || c.funct3 === 1
  const isSet = c.funct3 === 2
  const isGet = c.funct3 === 3
  const p0 = isMac ? c.a0 * c.b0 : 0
  const p1 = isMac ? c.a1 * c.b1 : 0
  const baseAcc = c.funct3 === 1 ? 0 : c.priorAcc
  const rawSum = isSet ? (c.rs1Scalar ?? 0) : isGet ? c.priorAcc : baseAcc + p0 + p1
  const satPos = isMac && rawSum > INT32_MAX
  const satNeg = isMac && rawSum < INT32_MIN
  const clamped = satPos ? INT32_MAX : satNeg ? INT32_MIN : rawSum
  return {
    isMac,
    isClr: c.funct3 === 1,
    isSet,
    isGet,
    rs1Hex: isSet ? fmtHex32(c.rs1Scalar ?? 0) : fmtPacked(c.a0, c.a1),
    rs2Hex: fmtPacked(c.b0, c.b1),
    p0,
    p1,
    baseAcc,
    rawSum,
    clamped,
    didClamp: satPos || satNeg,
    clampStatus: isSet
      ? 'Bypass (load rs1)'
      : isGet
        ? 'Read Only'
        : satPos
          ? 'Clamped +MAX'
          : satNeg
            ? 'Clamped -MIN'
            : 'In Range',
  }
})
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">Xapex Dual-Lane Multiply-Accumulate Datapath</div>
    </div>

    <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px">
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

    <!-- True Interactive SVG Hardware Datapath Schematic -->
    <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect the full dual-lane multiply-accumulate datapath</div>
    <div style="overflow-x: auto; padding-bottom: 4px">
    <svg
      viewBox="0 0 726 286"
      class="hw-svg-diagram"
      style="min-width: 550px"
      role="img"
      aria-label="Xapex dual-lane multiply-accumulate hardware datapath schematic showing halfword lane slicing, twin multipliers, accumulator selector, sat32 clamp, and register writeback"
    >
      <defs>
        <marker id="mac-arr-on" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--vp-c-brand-1)" />
        </marker>
        <marker id="mac-arr-off" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--vp-c-text-3)" />
        </marker>
        <marker id="mac-arr-red" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--hw-red)" />
        </marker>
      </defs>

      <!-- Active instruction banner -->
      <rect x="8" y="6" width="710" height="26" rx="6" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1" />
      <text x="20" y="23" font-size="11.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-brand-1)">
        {{ cur.insn }}
      </text>
      <text x="706" y="23" text-anchor="end" font-size="10.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">
        funct3 = {{ cur.funct3 }} · prior mac_acc = {{ fmtNum(cur.priorAcc) }}
      </text>

      <!-- STAGE 1: PACKED INPUT REGISTERS rs1 & rs2 -->
      <!-- rs1 block -->
      <g :opacity="trace.isGet ? 0.35 : 1">
        <rect x="8" y="48" width="168" height="62" rx="7" fill="var(--vp-c-bg)" :stroke="trace.isGet ? 'var(--vp-c-divider)' : 'var(--hw-green)'" stroke-width="1.5" />
        <text x="92" y="64" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--hw-green)">
          rs1 ({{ trace.rs1Hex }})
        </text>
        <line x1="16" y1="71" x2="168" y2="71" stroke="var(--vp-c-divider)" stroke-width="1" />
        <template v-if="trace.isSet">
          <text x="92" y="92" text-anchor="middle" font-size="10.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
            s32 = {{ fmtNum(cur.rs1Scalar ?? 0) }}
          </text>
        </template>
        <template v-else>
          <text x="16" y="86" font-size="9" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">Bits 31..16 (a1):</text>
          <text x="168" y="86" text-anchor="end" font-size="9.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">{{ cur.a1 }}</text>
          <text x="16" y="102" font-size="9" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">Bits 15..0 (a0):</text>
          <text x="168" y="102" text-anchor="end" font-size="9.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">{{ cur.a0 }}</text>
        </template>
      </g>

      <!-- rs2 block -->
      <g :opacity="trace.isMac ? 1 : 0.35">
        <rect x="8" y="122" width="168" height="62" rx="7" fill="var(--vp-c-bg)" :stroke="trace.isMac ? 'var(--hw-green)' : 'var(--vp-c-divider)'" stroke-width="1.5" />
        <text x="92" y="138" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--hw-green)">
          rs2 ({{ trace.rs2Hex }})
        </text>
        <line x1="16" y1="145" x2="168" y2="145" stroke="var(--vp-c-divider)" stroke-width="1" />
        <text x="16" y="160" font-size="9" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">Bits 31..16 (b1):</text>
        <text x="168" y="160" text-anchor="end" font-size="9.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">{{ cur.b1 }}</text>
        <text x="16" y="176" font-size="9" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">Bits 15..0 (b0):</text>
        <text x="168" y="176" text-anchor="end" font-size="9.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">{{ cur.b0 }}</text>
      </g>

      <!-- Base Accumulator Selector (0 for mac.clr vs. prior mac_acc for mac) -->
      <g :opacity="trace.isSet ? 0.35 : 1">
        <rect x="8" y="198" width="168" height="54" rx="7" fill="var(--vp-c-bg)" :stroke="trace.isSet ? 'var(--vp-c-divider)' : 'var(--hw-amber)'" stroke-width="1.5" />
        <text x="92" y="214" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--hw-amber)">
          Base Selector ({{ trace.isClr ? '0' : 'prior mac_acc' }})
        </text>
        <text x="92" y="238" text-anchor="middle" font-size="10.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
          {{ fmtNum(trace.baseAcc) }}
        </text>
      </g>

      <!-- WIRES FROM rs1/rs2 TO TWIN MULTIPLIERS (distinct routing channels; clean single perpendicular crossing) -->
      <g :opacity="trace.isMac ? 1 : 0.25">
        <!-- Upper lane a1 (y=82) and b1 (y=162 -> x=204 -> y=100) -> Mult 1 -->
        <path d="M 176 82 L 216 82" fill="none" stroke="var(--vp-c-brand-1)" stroke-width="1.8" marker-end="url(#mac-arr-on)" />
        <path d="M 176 162 L 204 162 L 204 100 L 216 100" fill="none" stroke="var(--vp-c-brand-1)" stroke-width="1.8" marker-end="url(#mac-arr-on)" />
        <!-- Lower lane a0 (y=98 -> x=190 -> y=150) and b0 (y=174) -> Mult 0 -->
        <path d="M 176 98 L 190 98 L 190 150 L 216 150" fill="none" stroke="var(--vp-c-brand-1)" stroke-width="1.8" marker-end="url(#mac-arr-on)" />
        <path d="M 176 174 L 216 174" fill="none" stroke="var(--vp-c-brand-1)" stroke-width="1.8" marker-end="url(#mac-arr-on)" />
      </g>

      <!-- Bypass wire for mac.set (rs1 straight to sat32/mac_acc) -->
      <path
        v-if="trace.isSet"
        d="M 176 64 L 568 64 L 568 126"
        fill="none"
        stroke="var(--vp-c-brand-1)"
        stroke-width="2.2"
        stroke-dasharray="5 3"
        marker-end="url(#mac-arr-on)"
      />
      <text v-if="trace.isSet" x="372" y="57" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--vp-c-brand-1)">
        mac.set scalar bypass (s32(rs1) → mac_acc)
      </text>

      <!-- Bypass wire for mac.get (mac_acc straight to rd) -->
      <path
        v-if="trace.isGet"
        d="M 176 225 L 568 225 L 568 190"
        fill="none"
        stroke="var(--vp-c-brand-1)"
        stroke-width="2.2"
        stroke-dasharray="5 3"
        marker-end="url(#mac-arr-on)"
      />
      <text v-if="trace.isGet" x="372" y="218" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--vp-c-brand-1)">
        mac.get readback (mac_acc unchanged → rd)
      </text>

      <!-- STAGE 2: TWIN 16x16 SIGNED MULTIPLIERS -->
      <g :opacity="trace.isMac ? 1 : 0.25">
        <rect x="222" y="68" width="122" height="46" rx="7" fill="var(--vp-c-bg)" stroke="var(--hw-purple)" stroke-width="1.5" />
        <text x="283" y="85" text-anchor="middle" font-size="10" font-weight="700" fill="var(--hw-purple)">
          p1 = a1 × b1
        </text>
        <text x="283" y="103" text-anchor="middle" font-size="10" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
          {{ fmtNum(trace.p1) }}
        </text>

        <rect x="222" y="142" width="122" height="46" rx="7" fill="var(--vp-c-bg)" stroke="var(--hw-purple)" stroke-width="1.5" />
        <text x="283" y="159" text-anchor="middle" font-size="10" font-weight="700" fill="var(--hw-purple)">
          p0 = a0 × b0
        </text>
        <text x="283" y="177" text-anchor="middle" font-size="10" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
          {{ fmtNum(trace.p0) }}
        </text>

        <!-- Wires into 3-Input Adder -->
        <path d="M 344 91 L 372 91 L 372 138 L 384 138" fill="none" stroke="var(--vp-c-brand-1)" stroke-width="1.8" marker-end="url(#mac-arr-on)" />
        <path d="M 344 165 L 384 165" fill="none" stroke="var(--vp-c-brand-1)" stroke-width="1.8" marker-end="url(#mac-arr-on)" />
        <path d="M 176 225 L 372 225 L 372 182 L 384 182" fill="none" stroke="var(--vp-c-brand-1)" stroke-width="1.8" marker-end="url(#mac-arr-on)" />

        <!-- STAGE 3: EXACT SUMMING ADDER -->
        <rect x="388" y="122" width="108" height="72" rx="8" fill="var(--vp-c-bg)" stroke="var(--vp-c-brand-1)" stroke-width="1.5" />
        <text x="442" y="140" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--vp-c-brand-1)">
          Exact Sum (+)
        </text>
        <text x="442" y="158" text-anchor="middle" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">
          base + p0 + p1
        </text>
        <text
          x="442"
          y="178"
          text-anchor="middle"
          font-size="10"
          font-weight="700"
          font-family="var(--vp-font-family-mono)"
          :fill="!trace.isMac ? 'var(--vp-c-text-3)' : trace.didClamp ? 'var(--hw-red)' : 'var(--vp-c-text-1)'"
        >
          {{ trace.isMac ? fmtNum(trace.rawSum) : 'Bypassed' }}
        </text>

        <!-- Wire to sat32 clamp -->
        <path
          d="M 496 158 L 524 158"
          fill="none"
          :stroke="trace.didClamp ? 'var(--hw-red)' : 'var(--vp-c-brand-1)'"
          stroke-width="2"
          :marker-end="trace.didClamp ? 'url(#mac-arr-red)' : 'url(#mac-arr-on)'"
        />
      </g>

      <!-- STAGE 4: sat32 CLAMP & WRITEBACK -->
      <rect
        x="528"
        y="128"
        width="188"
        height="62"
        rx="8"
        :fill="trace.didClamp ? 'rgba(220, 38, 38, 0.08)' : 'var(--vp-c-bg)'"
        :stroke="trace.didClamp ? 'var(--hw-red)' : 'var(--vp-c-brand-1)'"
        stroke-width="1.8"
      />
      <text
        x="622"
        y="146"
        text-anchor="middle"
        font-size="10.5"
        font-weight="700"
        :fill="trace.didClamp ? 'var(--hw-red)' : 'var(--vp-c-brand-1)'"
      >
        sat32: {{ trace.clampStatus }}
      </text>
      <text x="622" y="166" text-anchor="middle" font-size="11.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        mac_acc = {{ fmtNum(trace.clamped) }}
      </text>
      <text x="622" y="182" text-anchor="middle" font-size="10" font-family="var(--vp-font-family-mono)" :fill="cur.rd === 0 ? 'var(--hw-amber)' : 'var(--hw-green)'">
        {{ cur.rd === 0 ? 'rd = x0 → write discarded (0)' : `x${cur.rd} ← ${fmtNum(trace.clamped)}` }}
      </text>

      <!-- Footer note inside SVG -->
      <text x="363" y="274" text-anchor="middle" font-size="10" fill="var(--vp-c-text-2)">
        Dedicated mac_acc supplies the third operand internally so the register file stays two-read, one-write (2R1W).
      </text>
    </svg>
    </div>

    <div class="hw-card" style="margin-top: 8px; font-size: 12.5px; color: var(--vp-c-text-2)">
      <strong class="hw-mono" style="color: var(--vp-c-brand-1)">{{ cur.insn }}: </strong>{{ cur.explain }}
    </div>
  </div>
</template>
