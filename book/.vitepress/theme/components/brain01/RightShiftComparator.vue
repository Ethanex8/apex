<script setup lang="ts">
import { computed, ref } from 'vue'

interface ShiftPreset {
  label: string
  u32: number
}

const presets: ShiftPreset[] = [
  { label: '+5 (0x0000_0005)', u32: 5 },
  { label: '-5 (0xFFFF_FFFB)', u32: 0xfffffffb },
  { label: '-1 (0xFFFF_FFFF)', u32: 0xffffffff },
  { label: 'INT32_MIN (0x8000_0000)', u32: 0x80000000 },
]

const inputU32 = ref<number>(0xfffffffb)
const shiftK = ref<number>(1)

const inputS32 = computed(() => inputU32.value | 0)
const signBit = computed(() => (inputU32.value >>> 31) & 1)
const divisor = computed(() => 1 << shiftK.value)
const remainder = computed(() => (shiftK.value === 0 ? 0 : inputU32.value & (divisor.value - 1)))

const srlU32 = computed(() => (inputU32.value >>> shiftK.value) >>> 0)
const srlS32 = computed(() => srlU32.value | 0)
const sraS32 = computed(() => inputS32.value >> shiftK.value)
const sraU32 = computed(() => sraS32.value >>> 0)

function hex32(n: number): string {
  const h = (n >>> 0).toString(16).toUpperCase().padStart(8, '0')
  return `0x${h.slice(0, 4)}_${h.slice(4)}`
}

function bitsToNibbles(bitStr: string): string[] {
  const parts: string[] = []
  for (let i = 0; i < bitStr.length; i += 4) {
    parts.push(bitStr.slice(i, i + 4))
  }
  return parts
}

function bits32Nibbles(n: number): string[] {
  return bitsToNibbles((n >>> 0).toString(2).padStart(32, '0'))
}

const rawBits = computed(() => (inputU32.value >>> 0).toString(2).padStart(32, '0'))
const keptNibbles = computed(() => bitsToNibbles(rawBits.value.slice(0, 32 - shiftK.value)))
const droppedNibbles = computed(() => (shiftK.value === 0 ? [] : bitsToNibbles(rawBits.value.slice(32 - shiftK.value))))
const vacatedRange = computed(() => (shiftK.value === 1 ? 'Bit 31' : `Bits 31..${32 - shiftK.value}`))
const droppedRange = computed(() => (shiftK.value === 1 ? 'Bit 0' : `Bits ${shiftK.value - 1}..0`))
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">
        <span class="hw-badge">Floor Division</span>
        <span>32-Bit Logical vs. Arithmetic Right Shifts</span>
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px">
        <button
          v-for="p in presets"
          :key="p.label"
          type="button"
          class="hw-btn hw-mono"
          :class="{ active: inputU32 === p.u32 }"
          @click="inputU32 = p.u32"
        >
          {{ p.label }}
        </button>
      </div>
    </div>

    <div class="hw-card" style="margin-bottom: 12px">
      <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap">
        <div style="font-size: 13px; font-weight: 600">
          Shift Distance <code>k = {{ shiftK }}</code> (divide by 2<sup>{{ shiftK }}</sup> = {{ divisor }}):
        </div>
        <input
          v-model.number="shiftK"
          type="range"
          min="0"
          max="8"
          style="width: 190px; max-width: 100%; accent-color: var(--vp-c-brand-1)"
        />
      </div>

      <div class="hw-mono" style="font-size: 11.5px; margin-top: 8px; line-height: 1.65">
        <div style="display: flex; flex-wrap: wrap; gap: 2px 6px; align-items: baseline">
          <span>Input <code class="hw-mono">{{ hex32(inputU32) }}</code>:</span>
          <span style="white-space: nowrap">U<sub>32</sub> = <strong>{{ inputU32.toLocaleString() }}</strong>,</span>
          <span style="white-space: nowrap">S<sub>32</sub> = <strong>{{ inputS32.toLocaleString() }}</strong></span>
          <span style="white-space: nowrap">(<code>Bit 31</code> = {{ signBit }})</span>
        </div>
        <div style="margin-top: 4px; display: flex; flex-wrap: wrap; align-items: center; gap: 4px">
          <span>Kept (<code>Bits 31..{{ shiftK }}</code>):</span>
          <span style="display: inline-flex; flex-wrap: wrap; padding: 1px 5px; border-radius: 4px; background: var(--vp-c-brand-soft); color: var(--vp-c-brand-1); font-weight: 700">
            <span v-for="(nib, idx) in keptNibbles" :key="`k-${idx}`" style="white-space: nowrap">{{ nib }}<template v-if="idx < keptNibbles.length - 1">_</template></span>
          </span>
        </div>
        <div style="margin-top: 4px; display: flex; flex-wrap: wrap; align-items: center; gap: 4px">
          <template v-if="shiftK > 0">
            <span>Dropped (<code>{{ droppedRange }}</code>):</span>
            <span style="display: inline-flex; flex-wrap: wrap; padding: 1px 5px; border-radius: 4px; border: 1px solid var(--vp-c-divider); color: var(--hw-amber); font-weight: 700">
              <span v-for="(nib, idx) in droppedNibbles" :key="`d-${idx}`" style="white-space: nowrap">{{ nib }}<template v-if="idx < droppedNibbles.length - 1">_</template></span>
            </span>
            <span style="white-space: nowrap">(Remainder R = {{ remainder }})</span>
          </template>
          <span v-else style="white-space: nowrap">Dropped: none (Remainder R = 0)</span>
        </div>
      </div>
    </div>

    <div class="hw-grid-2">
      <div class="hw-card">
        <div class="hw-label">
          Logical Right Shift (<code>b &gt;&gt;<sub>log</sub> {{ shiftK }}</code>)
        </div>
        <div class="hw-mono" style="font-size: 11px; display: flex; flex-wrap: wrap; color: var(--vp-c-text-2); margin: 4px 0">
          <span v-for="(nib, idx) in bits32Nibbles(srlU32)" :key="`srl-${idx}`" style="white-space: nowrap">{{ nib }}<template v-if="idx < 7">_</template></span>
        </div>
        <div style="font-size: 12.5px; line-height: 1.6">
          <div>
            Vacated <span v-if="shiftK > 0"><code>{{ vacatedRange }}</code> = <code>0</code></span>
            <span v-else>wires: none</span>
          </div>
          <div>Output: <code class="hw-mono">{{ hex32(srlU32) }}</code></div>
          <div class="hw-mono" style="font-size: 12px">
            <span style="white-space: nowrap">U<sub>32</sub> = <strong>{{ srlU32.toLocaleString() }}</strong></span>{{ ' ' }}<span style="white-space: nowrap">(= &lfloor;{{ inputU32.toLocaleString() }} / {{ divisor }}&rfloor;)</span>
          </div>
          <div style="font-size: 11.5px; color: var(--vp-c-text-2)">
            U<sub>32</sub> / {{ divisor }} = {{ srlU32.toLocaleString() }} + {{ remainder }}/{{ divisor }}
            <span v-if="signBit === 1 && shiftK > 0" style="color: var(--hw-red); display: block">
              Signed S<sub>32</sub> flips positive ({{ srlS32.toLocaleString() }}) because Bit 31 became 0.
            </span>
          </div>
        </div>
      </div>

      <div class="hw-card">
        <div class="hw-label">
          Arithmetic Right Shift (<code>b &gt;&gt;<sub>arith</sub> {{ shiftK }}</code>)
        </div>
        <div class="hw-mono" style="font-size: 11px; display: flex; flex-wrap: wrap; color: var(--vp-c-text-2); margin: 4px 0">
          <span v-for="(nib, idx) in bits32Nibbles(sraU32)" :key="`sra-${idx}`" style="white-space: nowrap">{{ nib }}<template v-if="idx < 7">_</template></span>
        </div>
        <div style="font-size: 12.5px; line-height: 1.6">
          <div>
            Vacated <span v-if="shiftK > 0"><code>{{ vacatedRange }}</code> = <code>{{ signBit }}</code> (Bit 31 copy)</span>
            <span v-else>wires: none</span>
          </div>
          <div>Output: <code class="hw-mono">{{ hex32(sraU32) }}</code></div>
          <div class="hw-mono" style="font-size: 12px">
            <span style="white-space: nowrap">S<sub>32</sub> = <strong style="color: var(--hw-green)">{{ sraS32.toLocaleString() }}</strong></span>{{ ' ' }}<span style="white-space: nowrap">(= &lfloor;{{ inputS32.toLocaleString() }} / {{ divisor }}&rfloor;)</span>
          </div>
          <div style="font-size: 11.5px; color: var(--vp-c-text-2)">
            S<sub>32</sub> / {{ divisor }} = {{ sraS32.toLocaleString() }} + {{ remainder }}/{{ divisor }}
            <span v-if="inputS32 < 0 && remainder > 0" style="display: block; color: var(--vp-c-brand-1)">
              Non-negative remainder {{ remainder }}/{{ divisor }} &isin; [0, 1) floors toward -&infin; (not {{ Math.trunc(inputS32 / divisor) }}).
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
