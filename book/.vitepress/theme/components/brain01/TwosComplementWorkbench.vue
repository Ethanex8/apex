<script setup lang="ts">
import { computed, ref } from 'vue'

const activeTab = ref<'ring' | 'signext'>('ring')

// Tab 1: 4-bit Two's Complement Ring & Adder
const aBits = ref<number>(0b1011) // 11 unsigned, -5 signed
const bBits = ref<number>(0b0011) // 3 unsigned, +3 signed

function toggleBit4(which: 'a' | 'b', bit: number) {
  if (which === 'a') {
    aBits.value = (aBits.value ^ (1 << bit)) & 0xf
  } else {
    bBits.value = (bBits.value ^ (1 << bit)) & 0xf
  }
}

function toSigned4(u: number): number {
  const v = u & 0xf
  return v & 0x8 ? v - 16 : v
}

function bin4(u: number): string {
  return (u & 0xf).toString(2).padStart(4, '0')
}

const aU4 = computed(() => aBits.value & 0xf)
const bU4 = computed(() => bBits.value & 0xf)
const aS4 = computed(() => toSigned4(aU4.value))
const bS4 = computed(() => toSigned4(bU4.value))

const rawSumU = computed(() => aU4.value + bU4.value)
const sumBits4 = computed(() => rawSumU.value & 0xf)
const sumU4 = computed(() => sumBits4.value)
const sumS4 = computed(() => toSigned4(sumBits4.value))
const unsignedOverflow = computed(() => rawSumU.value > 15)
const signedOverflow = computed(() => aS4.value + bS4.value < -8 || aS4.value + bS4.value > 7)

const wheelSlots = computed(() => {
  return Array.from({ length: 16 }, (_, u) => {
    const angle = (u / 16) * Math.PI * 2 - Math.PI / 2
    const r = 86
    return {
      u,
      s: toSigned4(u),
      bits: bin4(u),
      x: 115 + r * Math.cos(angle),
      y: 115 + r * Math.sin(angle),
    }
  })
})

// Tab 2: 12-bit Sign Extension & Right Shifts (matching oracle.py)
const imm12Signed = ref<number>(-5)

const presets12 = [
  { label: '+5 (0x005)', val: 5 },
  { label: '-5 (0xFFB)', val: -5 },
  { label: '-1 (0xFFF)', val: -1 },
  { label: '+2047 (Max 12b)', val: 2047 },
  { label: '-2048 (Min 12b)', val: -2048 },
]

const raw12 = computed(() => imm12Signed.value & 0xfff)
const signBit12 = computed(() => (raw12.value >> 11) & 1)
const xorStep = computed(() => raw12.value ^ 0x800)
const subStep = computed(() => xorStep.value - 0x800)
const u32Extended = computed(() => (subStep.value >>> 0))

const shiftAmount = ref<number>(1)
const srlResult = computed(() => (u32Extended.value >>> shiftAmount.value) >>> 0)
const sraResult = computed(() => ((subStep.value >> shiftAmount.value) >>> 0))
const sraSigned = computed(() => subStep.value >> shiftAmount.value)

function hex32(n: number): string {
  const h = (n >>> 0).toString(16).toUpperCase().padStart(8, '0')
  return `0x${h.slice(0, 4)}_${h.slice(4)}`
}

function hex12(n: number): string {
  return `0x${(n & 0xfff).toString(16).toUpperCase().padStart(3, '0')}`
}
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">
        <span class="hw-badge">Interactive Workbench</span>
        <span>Two's Complement Number Ring, Sign Extension &amp; Right Shifts</span>
      </div>
      <div style="display: flex; gap: 6px; flex-wrap: wrap">
        <button
          type="button"
          class="hw-btn"
          :class="{ active: activeTab === 'ring' }"
          @click="activeTab = 'ring'"
        >
          1. 4-Bit Modular Ring &amp; Adder
        </button>
        <button
          type="button"
          class="hw-btn"
          :class="{ active: activeTab === 'signext' }"
          @click="activeTab = 'signext'"
        >
          2. 12-to-32-Bit Sign Extension &amp; Shifts
        </button>
      </div>
    </div>

    <!-- TAB 1: 4-BIT RING -->
    <div v-if="activeTab === 'ring'">
      <p style="margin: 0 0 12px 0; color: var(--vp-c-text-2); font-size: 13.5px">
        Click any bit below to toggle it. Notice that <strong>Bit 3</strong> carries weight
        <code>+8</code> in unsigned representation (<code>u4</code>) and <code>-8</code> in
        two's complement (<code>s4</code>), yet the identical 4-bit binary adder computes the
        correct modular sum for both.
      </p>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; align-items: center">
        <div style="display: flex; flex-direction: column; gap: 10px">
          <!-- Input A -->
          <div class="hw-card">
            <div class="hw-label">Input A (Click bits 3..0 to toggle)</div>
            <div style="display: flex; gap: 6px; margin: 6px 0">
              <button
                v-for="bit in [3, 2, 1, 0]"
                :key="`a-${bit}`"
                type="button"
                class="hw-btn hw-mono"
                :class="{ active: ((aU4 >> bit) & 1) === 1 }"
                style="flex: 1; padding: 6px 4px"
                @click="toggleBit4('a', bit)"
              >
                <div style="font-size: 10px; opacity: 0.8">
                  Bit {{ bit }} ({{ bit === 3 ? '-8/+8' : `+${1 << bit}` }})
                </div>
                <div style="font-size: 15px; font-weight: 700">{{ (aU4 >> bit) & 1 }}</div>
              </button>
            </div>
            <div class="hw-mono" style="font-size: 12.5px; color: var(--vp-c-text-2)">
              Unsigned <code>u4</code> = <strong>{{ aU4 }}</strong> · Signed <code>s4</code> =
              <strong>{{ aS4 >= 0 ? `+${aS4}` : aS4 }}</strong>
            </div>
          </div>

          <!-- Input B -->
          <div class="hw-card">
            <div class="hw-label">Input B (Click bits 3..0 to toggle)</div>
            <div style="display: flex; gap: 6px; margin: 6px 0">
              <button
                v-for="bit in [3, 2, 1, 0]"
                :key="`b-${bit}`"
                type="button"
                class="hw-btn hw-mono"
                :class="{ active: ((bU4 >> bit) & 1) === 1 }"
                style="flex: 1; padding: 6px 4px"
                @click="toggleBit4('b', bit)"
              >
                <div style="font-size: 10px; opacity: 0.8">
                  Bit {{ bit }} ({{ bit === 3 ? '-8/+8' : `+${1 << bit}` }})
                </div>
                <div style="font-size: 15px; font-weight: 700">{{ (bU4 >> bit) & 1 }}</div>
              </button>
            </div>
            <div class="hw-mono" style="font-size: 12.5px; color: var(--vp-c-text-2)">
              Unsigned <code>u4</code> = <strong>{{ bU4 }}</strong> · Signed <code>s4</code> =
              <strong>{{ bS4 >= 0 ? `+${bS4}` : bS4 }}</strong>
            </div>
          </div>

          <!-- Sum Output -->
          <div class="hw-card" style="border-color: var(--vp-c-brand-1)">
            <div class="hw-label">Hardware 4-Bit Sum: (A + B) mod 16</div>
            <div class="hw-mono" style="font-size: 16px; font-weight: 700; margin: 4px 0">
              {{ bin4(aU4) }} + {{ bin4(bU4) }} =
              <span style="color: var(--vp-c-brand-1)">{{ bin4(sumBits4) }}</span>
            </div>
            <div style="font-size: 12.5px; display: flex; flex-direction: column; gap: 3px">
              <div>
                <strong>Unsigned view:</strong> {{ aU4 }} + {{ bU4 }} →
                <code class="hw-mono">{{ sumU4 }}</code>
                <span v-if="unsignedOverflow" style="color: #d97706; font-weight: 600">
                  (wrapped modulo 16 from {{ rawSumU }})
                </span>
              </div>
              <div>
                <strong>Signed view:</strong> ({{ aS4 }}) + ({{ bS4 }}) →
                <code class="hw-mono">{{ sumS4 >= 0 ? `+${sumS4}` : sumS4 }}</code>
                <span v-if="signedOverflow" style="color: #dc2626; font-weight: 600">
                  (signed 4-bit overflow: true sum {{ aS4 + bS4 }} outside [-8..+7])
                </span>
                <span v-else style="color: #10b981; font-weight: 600"> (exact) </span>
              </div>
            </div>
          </div>
        </div>

        <!-- SVG Number Wheel -->
        <div style="display: flex; flex-direction: column; align-items: center">
          <svg viewBox="0 0 230 230" style="width: 225px; height: 225px">
            <circle
              cx="115"
              cy="115"
              r="86"
              fill="none"
              stroke="currentColor"
              stroke-opacity="0.16"
              stroke-width="1.5"
            />
            <g v-for="slot in wheelSlots" :key="slot.u">
              <circle
                :cx="slot.x"
                :cy="slot.y"
                :r="slot.u === sumBits4 ? 15 : slot.u === aU4 || slot.u === bU4 ? 13 : 11"
                :fill="
                  slot.u === sumBits4
                    ? 'var(--vp-c-brand-1)'
                    : slot.u === aU4
                      ? '#10b981'
                      : slot.u === bU4
                        ? '#f59e0b'
                        : 'var(--vp-c-bg)'
                "
                stroke="currentColor"
                stroke-opacity="0.25"
              />
              <text
                :x="slot.x"
                :y="slot.y + 3.5"
                text-anchor="middle"
                font-size="9.5"
                font-weight="700"
                :fill="
                  slot.u === sumBits4 || slot.u === aU4 || slot.u === bU4
                    ? '#ffffff'
                    : 'currentColor'
                "
              >
                {{ slot.s >= 0 ? `+${slot.s}` : slot.s }}
              </text>
            </g>
            <text
              x="115"
              y="108"
              text-anchor="middle"
              font-size="10"
              fill="currentColor"
              opacity="0.7"
            >
              Green = A · Amber = B
            </text>
            <text
              x="115"
              y="123"
              text-anchor="middle"
              font-size="10.5"
              font-weight="700"
              fill="var(--vp-c-brand-1)"
            >
              Blue = Sum ({{ bin4(sumBits4) }})
            </text>
          </svg>
        </div>
      </div>
    </div>

    <!-- TAB 2: 12-TO-32 SIGN EXTENSION & SHIFTS -->
    <div v-else>
      <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 12px">
        <span style="font-size: 12.5px; font-weight: 600; color: var(--vp-c-text-2)">Presets:</span>
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

      <div class="hw-card" style="margin-bottom: 12px">
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap">
          <label style="font-size: 13px; font-weight: 600">
            12-Bit Signed Constant (<code>imm[11:0]</code>):
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

        <div style="margin-top: 10px; overflow-x: auto">
          <div class="hw-label">Widening 12 Bits → 32 Bits (Copying Bit 11 into Bits 31..12)</div>
          <div class="hw-mono" style="display: flex; align-items: center; gap: 6px; font-size: 13px; margin-top: 4px">
            <span
              style="
                padding: 4px 8px;
                border-radius: 6px;
                background: rgba(37, 99, 235, 0.14);
                border: 1px solid var(--vp-c-brand-1);
                font-weight: 700;
              "
              title="20 copies of Bit 11"
            >
              Bits 31..12: {{ String(signBit12).repeat(20) }}
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
            <span>= <strong>{{ hex32(u32Extended) }}</strong></span>
          </div>
        </div>
      </div>

      <div class="hw-grid-2">
        <div class="hw-card">
          <div class="hw-label">Branchless Formula in oracle.py: sign_extend(val, 12)</div>
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
            <div class="hw-label">Right Shift Comparison (Shift by {{ shiftAmount }})</div>
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
              <strong>Shift Right Logical Immediate (<code>SRLI</code> — fills left with <code>0</code>):</strong><br />
              <code class="hw-mono">{{ hex32(srlResult) }}</code> (unsigned {{ srlResult }})
            </div>
            <div>
              <strong>Shift Right Arithmetic Immediate (<code>SRAI</code> — copies sign bit <code>{{ signBit12 }}</code>):</strong><br />
              <code class="hw-mono">{{ hex32(sraResult) }}</code> (signed
              <strong>{{ sraSigned }}</strong>)
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
