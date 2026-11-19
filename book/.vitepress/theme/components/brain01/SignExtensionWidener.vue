<script setup lang="ts">
import { computed, ref } from 'vue'

type NarrowWidth = 8 | 12 | 16

const width = ref<NarrowWidth>(12)
const signedVal = ref<number>(-5)

const minVal = computed(() => -(1 << (width.value - 1)))
const maxVal = computed(() => (1 << (width.value - 1)) - 1)
const mask = computed(() => (1 << width.value) - 1)
const signMask = computed(() => 1 << (width.value - 1))

const presets = computed(() => [
  { label: '+5', val: 5 },
  { label: '-5', val: -5 },
  { label: '-1', val: -1 },
  { label: `+${maxVal.value} (Max)`, val: maxVal.value },
  { label: `${minVal.value} (Min)`, val: minVal.value },
])

function selectWidth(w: NarrowWidth): void {
  width.value = w
  const lo = -(1 << (w - 1))
  const hi = (1 << (w - 1)) - 1
  if (signedVal.value < lo) signedVal.value = lo
  if (signedVal.value > hi) signedVal.value = hi
}

const rawNarrow = computed(() => signedVal.value & mask.value)
const signBit = computed(() => (rawNarrow.value >> (width.value - 1)) & 1)
const xorStep = computed(() => rawNarrow.value ^ signMask.value)
const signExtendedS32 = computed(() => xorStep.value - signMask.value)
const signExtendedU32 = computed(() => signExtendedS32.value >>> 0)
const zeroExtendedU32 = computed(() => rawNarrow.value >>> 0)

function hex32(n: number): string {
  const h = (n >>> 0).toString(16).toUpperCase().padStart(8, '0')
  return `0x${h.slice(0, 4)}_${h.slice(4)}`
}

function hexNarrow(n: number, bits: number): string {
  const digits = Math.ceil(bits / 4)
  return `0x${(n & ((1 << bits) - 1)).toString(16).toUpperCase().padStart(digits, '0')}`
}

function groupNibbles(bitStr: string): string[] {
  const parts: string[] = []
  for (let i = 0; i < bitStr.length; i += 4) {
    parts.push(bitStr.slice(i, i + 4))
  }
  return parts
}

const upperZeroNibbles = computed(() => groupNibbles('0'.repeat(32 - width.value)))
const upperSignNibbles = computed(() => groupNibbles(String(signBit.value).repeat(32 - width.value)))
const lowerNibbles = computed(() => groupNibbles(rawNarrow.value.toString(2).padStart(width.value, '0')))
const lowerBits = computed(() => lowerNibbles.value.join('_'))
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">
        <span class="hw-badge">Wire Fan-Out</span>
        <span>Widening Narrow Integers to 32-Bit Wires</span>
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px">
        <button
          v-for="w in ([8, 12, 16] as NarrowWidth[])"
          :key="w"
          type="button"
          class="hw-btn hw-mono"
          :class="{ active: width === w }"
          @click="selectWidth(w)"
        >
          {{ w }}-bit
        </button>
      </div>
    </div>

    <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px">
      <button
        v-for="p in presets"
        :key="p.label"
        type="button"
        class="hw-btn hw-mono"
        :class="{ active: signedVal === p.val }"
        @click="signedVal = p.val"
      >
        {{ p.label }}
      </button>
    </div>

    <div class="hw-card" style="margin-bottom: 12px">
      <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap">
        <label style="font-size: 13px; font-weight: 600">
          {{ width }}-Bit Input (<code>Bits {{ width - 1 }}..0</code>):
          <span class="hw-mono" style="color: var(--vp-c-brand-1); display: inline-flex; flex-wrap: wrap; gap: 0 6px">
            <span style="white-space: nowrap">S<sub>{{ width }}</sub> = {{ signedVal }},</span>
            <span style="white-space: nowrap">U<sub>{{ width }}</sub> = {{ rawNarrow.toLocaleString() }} ({{ hexNarrow(rawNarrow, width) }})</span>
          </span>
        </label>
        <input
          v-model.number="signedVal"
          type="range"
          :min="minVal"
          :max="maxVal"
          style="width: 220px; max-width: 100%; accent-color: var(--vp-c-brand-1)"
        />
      </div>

      <div class="hw-mono" style="font-size: 12px; margin-top: 8px; color: var(--vp-c-text-2)">
        Low {{ width }} wires (<code>Bits {{ width - 1 }}..0</code>):
        <strong style="color: var(--vp-c-brand-1)">{{ lowerBits.slice(0, 1) }}</strong>{{ lowerBits.slice(1) }}
        (Sign wire <code>Bit {{ width - 1 }}</code> = <strong>{{ signBit }}</strong>)
      </div>
    </div>

    <div class="hw-grid-2" style="margin-bottom: 12px">
      <div class="hw-card">
        <div class="hw-label">Zero Extension (<code>Bits 31..{{ width }} = 0</code>)</div>
        <div class="hw-mono" style="font-size: 11px; display: flex; flex-wrap: wrap; margin: 6px 0">
          <span
            v-for="(nib, idx) in upperZeroNibbles"
            :key="`z-hi-${idx}`"
            style="white-space: nowrap; color: var(--vp-c-text-2)"
          >{{ nib }}_</span>
          <span
            v-for="(nib, idx) in lowerNibbles"
            :key="`z-lo-${idx}`"
            style="white-space: nowrap; color: var(--vp-c-text-1)"
          >{{ nib }}<template v-if="idx < lowerNibbles.length - 1">_</template></span>
        </div>
        <div style="font-size: 12.5px; line-height: 1.55">
          <div>Result: <code class="hw-mono">{{ hex32(zeroExtendedU32) }}</code></div>
          <div>
            Preserves U<sub>{{ width }}</sub> = <strong>{{ zeroExtendedU32.toLocaleString() }}</strong>
            <span v-if="signBit === 1" style="color: var(--hw-red)">
              (shifts negative S<sub>{{ width }}</sub> by +2<sup>{{ width }}</sup>)
            </span>
          </div>
        </div>
      </div>

      <div class="hw-card">
        <div class="hw-label">Sign Extension (<code>Bits 31..{{ width }} = Bit {{ width - 1 }}</code>)</div>
        <div class="hw-mono" style="font-size: 11px; display: flex; flex-wrap: wrap; margin: 6px 0">
          <span
            v-for="(nib, idx) in upperSignNibbles"
            :key="`s-hi-${idx}`"
            style="white-space: nowrap; color: var(--vp-c-brand-1); font-weight: 700"
          >{{ nib }}_</span>
          <span
            v-for="(nib, idx) in lowerNibbles"
            :key="`s-lo-${idx}`"
            style="white-space: nowrap; color: var(--vp-c-text-1)"
          >{{ nib }}<template v-if="idx < lowerNibbles.length - 1">_</template></span>
        </div>
        <div style="font-size: 12.5px; line-height: 1.55">
          <div>Result: <code class="hw-mono">{{ hex32(signExtendedU32) }}</code></div>
          <div>
            Preserves S<sub>32</sub> = <strong style="color: var(--hw-green)">{{ signExtendedS32 }}</strong>
            (U<sub>32</sub> = {{ signExtendedU32.toLocaleString() }})
          </div>
        </div>
      </div>
    </div>

    <div class="hw-card">
      <div class="hw-label">Branchless Software Check: <code>sign_extend(val, {{ width }})</code> (^ = bitwise XOR)</div>
      <ol class="hw-mono" style="margin: 6px 0 0 18px; padding: 0; font-size: 12px; line-height: 1.7">
        <li>masked = val &amp; {{ hexNarrow(mask, width) }} = {{ rawNarrow }} ({{ hexNarrow(rawNarrow, width) }})</li>
        <li>sign_bit = 1 &lt;&lt; {{ width - 1 }} = {{ signMask }} ({{ hexNarrow(signMask, width) }})</li>
        <li>masked ^ sign_bit = {{ rawNarrow }} ^ {{ signMask }} = <strong>{{ xorStep }}</strong></li>
        <li>
          (masked ^ sign_bit) - sign_bit = {{ xorStep }} - {{ signMask }} =
          <strong style="color: var(--vp-c-brand-1)">{{ signExtendedS32 }}</strong>
        </li>
      </ol>
    </div>
  </div>
</template>
