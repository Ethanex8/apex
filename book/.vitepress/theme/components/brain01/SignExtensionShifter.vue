<script setup lang="ts">
import { computed, ref } from 'vue'

const imm12Signed = ref<number>(-5)
const shiftAmount = ref<number>(1)

const presets12 = [
  { label: '+5 (0x005)', val: 5 },
  { label: '-5 (0xFFB)', val: -5 },
  { label: '-1 (0xFFF)', val: -1 },
  { label: '+2047 (Max)', val: 2047 },
  { label: '-2048 (Min)', val: -2048 },
]

const raw12 = computed(() => imm12Signed.value & 0xfff)
const signBit12 = computed(() => (raw12.value >> 11) & 1)
const xorStep = computed(() => raw12.value ^ 0x800)
const subStep = computed(() => xorStep.value - 0x800)
const u32Extended = computed(() => subStep.value >>> 0)

const srlResult = computed(() => (u32Extended.value >>> shiftAmount.value) >>> 0)
const sraResult = computed(() => (subStep.value >> shiftAmount.value) >>> 0)
const sraSigned = computed(() => subStep.value >> shiftAmount.value)

function hex32(n: number): string {
  const h = (n >>> 0).toString(16).toUpperCase().padStart(8, '0')
  return `0x${h.slice(0, 4)}_${h.slice(4)}`
}

function hex12(n: number): string {
  return `0x${(n & 0xfff).toString(16).toUpperCase().padStart(3, '0')}`
}

const groupedUpper20 = computed(() => {
  const b = String(signBit12.value).repeat(20)
  return `${b.slice(0, 4)}_${b.slice(4, 8)}_${b.slice(8, 12)}_${b.slice(12, 16)}_${b.slice(16, 20)}`
})
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">
        <span class="hw-badge">Wire Fan-Out &amp; Shifts</span>
        <span>12-to-32-Bit Sign Extension &amp; Right-Shift Comparator</span>
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px">
        <button
          v-for="p in presets12"
          :key="p.val"
          type="button"
          class="hw-btn hw-mono"
          :class="{ active: imm12Signed === p.val }"
          @click="imm12Signed = p.val"
        >
          {{ p.label }}
        </button>
      </div>
    </div>

    <div class="hw-card" style="margin-bottom: 12px">
      <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap">
        <label style="font-size: 13px; font-weight: 600">
          12-Bit Signed Constant (<code>Bits 11..0</code>):
          <span class="hw-mono" style="color: var(--vp-c-brand-1)">
            {{ imm12Signed }} ({{ hex12(raw12) }})
          </span>
        </label>
        <input
          v-model.number="imm12Signed"
          type="range"
          min="-2048"
          max="2047"
          style="width: 220px; accent-color: var(--vp-c-brand-1)"
        />
      </div>

      <div style="margin-top: 10px">
        <div class="hw-label">Replicating Sign Wire (Bit 11 = {{ signBit12 }}) into Upper Wires 31..12</div>
        <div class="hw-mono" style="display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 12.5px; margin-top: 4px">
          <span
            style="
              padding: 4px 8px;
              border-radius: 6px;
              background: rgba(37, 99, 235, 0.14);
              border: 1px solid var(--vp-c-brand-1);
              font-weight: 700;
            "
            title="Wire 11 fanned out across Bits 31..12"
          >
            Bits 31..12: {{ groupedUpper20 }}
          </span>
          <span
            style="
              padding: 4px 8px;
              border-radius: 6px;
              background: var(--vp-c-bg-soft);
              border: 1px solid var(--vp-c-divider);
            "
            title="Original 12-bit constant"
          >
            Bits 11..0: <strong>{{ signBit12 }}</strong>{{ (raw12 & 0x7ff).toString(2).padStart(11, '0') }}
          </span>
          <span>→ <strong>{{ hex32(u32Extended) }}</strong></span>
        </div>
      </div>
    </div>

    <div class="hw-grid-2">
      <div class="hw-card">
        <div class="hw-label">Branchless Software Check: sign_extend(val, 12)</div>
        <ol class="hw-mono" style="margin: 6px 0 0 18px; padding: 0; font-size: 12.5px; line-height: 1.7">
          <li><code>val &amp; 0xFFF</code> = {{ raw12 }} (<code>{{ hex12(raw12) }}</code>)</li>
          <li><code>sign_bit = 1 &lt;&lt; 11</code> = 2048 (<code>0x800</code>)</li>
          <li><code>val ^ sign_bit</code> = {{ raw12 }} ^ 2048 = <strong>{{ xorStep }}</strong></li>
          <li>
            <code>(val ^ sign_bit) - sign_bit</code> = {{ xorStep }} - 2048 =
            <strong style="color: var(--vp-c-brand-1)">{{ subStep }}</strong>
          </li>
        </ol>
      </div>

      <div class="hw-card">
        <div style="display: flex; justify-content: space-between; align-items: center">
          <div class="hw-label">Right-Shift View (Shift Distance k = {{ shiftAmount }})</div>
          <input
            v-model.number="shiftAmount"
            type="range"
            min="1"
            max="8"
            style="width: 90px; accent-color: var(--vp-c-brand-1)"
          />
        </div>
        <div style="font-size: 12.5px; margin-top: 6px; display: flex; flex-direction: column; gap: 6px">
          <div>
            <strong>Logical Right Shift (<code>SRLI</code> — shifts in <code>0</code>s):</strong><br />
            <code class="hw-mono">{{ hex32(srlResult) }}</code> (unsigned {{ srlResult }})
          </div>
          <div>
            <strong>Arithmetic Right Shift (<code>SRAI</code> — copies Bit 31 = <code>{{ signBit12 }}</code>):</strong><br />
            <code class="hw-mono">{{ hex32(sraResult) }}</code> (signed <strong>{{ sraSigned }}</strong>)
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
