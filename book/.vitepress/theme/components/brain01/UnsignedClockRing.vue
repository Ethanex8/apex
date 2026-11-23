<script setup lang="ts">
import { computed, ref } from 'vue'

interface PresetCase {
  label: string
  x: number
  expr: string
}

const presets: PresetCase[] = [
  { label: 'x = 18', x: 18, expr: '11 + 7 = 18' },
  { label: 'x = 2', x: 2, expr: '2 (base slot)' },
  { label: 'x = -5', x: -5, expr: 'Step back 5 from 0' },
  { label: 'x = 34', x: 34, expr: '2 full laps + 2' },
]

const rawX = ref<number>(18)
const exprNote = ref<string>('11 + 7 = 18')

function mod16(val: number): number {
  return ((val % 16) + 16) % 16
}

const remainder = computed(() => mod16(rawX.value))
const quotient = computed(() => Math.floor(rawX.value / 16))
const remainderBits = computed(() => remainder.value.toString(2).padStart(4, '0'))

function selectPreset(p: PresetCase) {
  rawX.value = p.x
  exprNote.value = p.expr
}

function stepBy(delta: number) {
  rawX.value += delta
  exprNote.value = `Stepped to ${rawX.value}`
}

function pickSlot(slot: number) {
  rawX.value = slot
  exprNote.value = `Slot ${slot} (${slot.toString(2).padStart(4, '0')})`
}

const clockSlots = computed(() => {
  return Array.from({ length: 16 }, (_, r) => {
    const angle = (r / 16) * Math.PI * 2 - Math.PI / 2
    const radius = 92
    return {
      r,
      bits: r.toString(2).padStart(4, '0'),
      x: 130 + radius * Math.cos(angle),
      y: 130 + radius * Math.sin(angle),
    }
  })
})
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">16-Slot Unsigned Modular Clock (Modulo 16)</div>
      <div style="display: flex; gap: 6px; flex-wrap: wrap">
        <button
          v-for="p in presets"
          :key="p.label"
          type="button"
          class="hw-btn hw-mono"
          :class="{ active: rawX === p.x }"
          @click="selectPreset(p)"
        >
          {{ p.label }}
        </button>
      </div>
    </div>

    <p style="margin: 0 0 12px 0; color: var(--vp-c-text-2); font-size: 13.5px">
      Every multiple of 16 completes one full clockwise lap around the 16-slot ring and lands back on the
      <strong>same slot</strong>. Try stepping past slot <code>15</code> or backward below <code>0</code>, or click
      any slot directly.
    </p>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; align-items: center">
      <div style="display: flex; flex-direction: column; gap: 10px">
        <div class="hw-card">
          <div class="hw-label">Integer Input (x ∈ ℤ)</div>
          <div class="hw-mono" style="font-size: 18px; font-weight: 700; margin: 4px 0">
            x = {{ rawX }}
            <span style="font-size: 12px; font-weight: 400; color: var(--vp-c-text-2)">({{ exprNote }})</span>
          </div>
          <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px">
            <button type="button" class="hw-btn hw-mono" @click="stepBy(-16)">-16 (-1 lap)</button>
            <button type="button" class="hw-btn hw-mono" @click="stepBy(-1)">-1</button>
            <button type="button" class="hw-btn hw-mono" @click="stepBy(1)">+1</button>
            <button type="button" class="hw-btn hw-mono" @click="stepBy(16)">+16 (+1 lap)</button>
          </div>
        </div>

        <div class="hw-card" style="border-color: var(--vp-c-brand-1)">
          <div class="hw-label">Euclidean Division (m = 16)</div>
          <div class="hw-mono" style="font-size: 14px; font-weight: 600; margin: 4px 0">
            {{ rawX }} = ({{ quotient }}) × 16 +
            <span style="color: var(--vp-c-brand-1); font-weight: 700">{{ remainder }}</span>
          </div>
          <div style="font-size: 12.5px; color: var(--vp-c-text-2); display: flex; flex-direction: column; gap: 3px">
            <div>
              <strong>4-Bit Hardware Remainder (Bits 3..0):</strong>
              <code class="hw-mono" style="margin-left: 4px; color: var(--vp-c-text-1)">{{ remainderBits }}</code>
              <span> ({{ remainder }} unsigned)</span>
            </div>
            <div>
              <strong>Residue Class:</strong>
              <code class="hw-mono" style="margin-left: 4px">{{ rawX }} ≡ {{ remainder }} (mod 16)</code>
            </div>
          </div>
        </div>
      </div>

      <div style="display: flex; flex-direction: column; align-items: center; gap: 6px">
        <svg viewBox="0 0 260 260" style="width: 245px; height: 245px; max-width: 100%">
          <circle
            cx="130"
            cy="130"
            r="92"
            fill="none"
            stroke="currentColor"
            stroke-opacity="0.16"
            stroke-width="1.5"
          />
          <g
            v-for="slot in clockSlots"
            :key="slot.r"
            style="cursor: pointer"
            @click="pickSlot(slot.r)"
          >
            <circle
              :cx="slot.x"
              :cy="slot.y"
              :r="slot.r === remainder ? 16 : 12.5"
              :fill="slot.r === remainder ? 'var(--vp-c-brand-1)' : 'var(--vp-c-bg)'"
              :stroke="slot.r === remainder ? 'var(--vp-c-brand-1)' : 'currentColor'"
              :stroke-opacity="slot.r === remainder ? 1 : 0.25"
              stroke-width="1.5"
            />
            <text
              :x="slot.x"
              :y="slot.y + 3.5"
              text-anchor="middle"
              font-size="10.5"
              font-family="var(--vp-font-family-mono)"
              :font-weight="slot.r === remainder ? '700' : '500'"
              :fill="slot.r === remainder ? 'var(--vp-c-bg)' : 'currentColor'"
            >
              {{ slot.r }}
            </text>
          </g>
          <text
            x="130"
            y="123"
            text-anchor="middle"
            font-size="11"
            font-weight="700"
            fill="var(--vp-c-text-1)"
          >
            mod 16
          </text>
          <text
            x="130"
            y="141"
            text-anchor="middle"
            font-size="11.5"
            font-family="var(--vp-font-family-mono)"
            font-weight="700"
            fill="var(--vp-c-brand-1)"
          >
            slot {{ remainder }} ({{ remainderBits }})
          </text>
        </svg>
      </div>
    </div>
  </div>
</template>
