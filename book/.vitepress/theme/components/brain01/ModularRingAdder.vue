<script setup lang="ts">
import { computed, ref } from 'vue'

const aBits = ref<number>(0b1011) // 11 unsigned, -5 signed
const bBits = ref<number>(0b0011) // 3 unsigned, +3 signed

const presets = [
  { label: '-5 + (+3) = -2', a: 0b1011, b: 0b0011 },
  { label: '+7 + (+2) wraps to -7', a: 0b0111, b: 0b0010 },
  { label: '-1 + (+1) = 0 (unsigned wrap)', a: 0b1111, b: 0b0001 },
  { label: '-4 + (-4) = -8', a: 0b1100, b: 0b1100 },
]

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

function fmtS4(s: number): string {
  return s > 0 ? `+${s}` : `${s}`
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
const sumS4 = computed(() => toSigned4(sumBits4.value))
const unsignedOverflow = computed(() => rawSumU.value > 15)
const signedOverflow = computed(() => aS4.value + bS4.value < -8 || aS4.value + bS4.value > 7)

const overlapNote = computed(() => {
  const hits: string[] = []
  if (aU4.value === bU4.value && aU4.value === sumBits4.value) {
    hits.push(`A, B, and Sum all share slot ${bin4(sumBits4.value)}`)
  } else {
    if (aU4.value === bU4.value) hits.push(`A & B share slot ${bin4(aU4.value)}`)
    if (aU4.value === sumBits4.value) hits.push(`A & Sum share slot ${bin4(sumBits4.value)}`)
    if (bU4.value === sumBits4.value) hits.push(`B & Sum share slot ${bin4(sumBits4.value)}`)
  }
  return hits.join(' · ')
})

const wheelSlots = computed(() => {
  return Array.from({ length: 16 }, (_, u) => {
    const angle = (u / 16) * Math.PI * 2 - Math.PI / 2
    const r = 104
    const rOuter = 132
    return {
      u,
      s: toSigned4(u),
      bits: bin4(u),
      x: 155 + r * Math.cos(angle),
      y: 155 + r * Math.sin(angle),
      ux: 155 + rOuter * Math.cos(angle),
      uy: 155 + rOuter * Math.sin(angle),
    }
  })
})
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">4-Bit Two's-Complement Shared Addition Clock</div>
      <div style="display: flex; gap: 6px; flex-wrap: wrap">
        <button
          v-for="p in presets"
          :key="p.label"
          type="button"
          class="hw-btn hw-mono"
          :class="{ active: aU4 === p.a && bU4 === p.b }"
          @click="aBits = p.a; bBits = p.b"
        >
          {{ p.label }}
        </button>
      </div>
    </div>

    <p style="margin: 0 0 12px 0; color: var(--vp-c-text-2); font-size: 13.5px">
      Think of a 4-bit register like a 16-slot clock face (<code>0000</code> at 12 o'clock): outer numbers show
      unsigned values (<code>0..15</code>) and inner circles show two's-complement signed values (<code>-8..+7</code>),
      yet stepping clockwise by Input B's unsigned count computes both sums on the exact same binary adder.
    </p>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; align-items: center">
      <div style="display: flex; flex-direction: column; gap: 10px">
        <div class="hw-card">
          <div class="hw-label">Input A (Green Ring — Click Bits 3..0)</div>
          <div style="display: flex; gap: 6px; margin: 6px 0">
            <button
              v-for="bit in [3, 2, 1, 0]"
              :key="`a-${bit}`"
              type="button"
              class="hw-btn hw-mono"
              :class="{ active: ((aU4 >> bit) & 1) === 1 }"
              style="flex: 1; padding: 5px 4px; display: flex; flex-direction: column; justify-content: space-between; align-items: center"
              @click="toggleBit4('a', bit)"
            >
              <div style="font-size: 10px; opacity: 0.8; min-height: 24px; display: flex; align-items: center">
                b{{ bit }} ({{ bit === 3 ? '-8/+8' : `+${1 << bit}` }})
              </div>
              <div style="font-size: 15px; font-weight: 700">{{ (aU4 >> bit) & 1 }}</div>
            </button>
          </div>
          <div
            class="hw-mono"
            style="font-size: 12px; color: var(--vp-c-text-2); display: flex; flex-wrap: wrap; gap: 2px 10px"
          >
            <span style="white-space: nowrap">Unsigned (0..15) = <strong>{{ aU4 }}</strong></span>
            <span style="white-space: nowrap">Signed (-8..+7) = <strong>{{ fmtS4(aS4) }}</strong></span>
          </div>
        </div>

        <div class="hw-card">
          <div class="hw-label">Input B (Amber Ring — Click Bits 3..0)</div>
          <div style="display: flex; gap: 6px; margin: 6px 0">
            <button
              v-for="bit in [3, 2, 1, 0]"
              :key="`b-${bit}`"
              type="button"
              class="hw-btn hw-mono"
              :class="{ active: ((bU4 >> bit) & 1) === 1 }"
              style="flex: 1; padding: 5px 4px; display: flex; flex-direction: column; justify-content: space-between; align-items: center"
              @click="toggleBit4('b', bit)"
            >
              <div style="font-size: 10px; opacity: 0.8; min-height: 24px; display: flex; align-items: center">
                b{{ bit }} ({{ bit === 3 ? '-8/+8' : `+${1 << bit}` }})
              </div>
              <div style="font-size: 15px; font-weight: 700">{{ (bU4 >> bit) & 1 }}</div>
            </button>
          </div>
          <div
            class="hw-mono"
            style="font-size: 12px; color: var(--vp-c-text-2); display: flex; flex-wrap: wrap; gap: 2px 10px"
          >
            <span style="white-space: nowrap">Unsigned (0..15) = <strong>{{ bU4 }}</strong></span>
            <span style="white-space: nowrap">Signed (-8..+7) = <strong>{{ fmtS4(bS4) }}</strong></span>
          </div>
        </div>

        <div class="hw-card" style="border-color: var(--vp-c-brand-1)">
          <div class="hw-label">Hardware 4-Bit Sum: (A + B) mod 16</div>
          <div class="hw-mono" style="font-size: 15.5px; font-weight: 700; margin: 4px 0">
            {{ bin4(aU4) }} + {{ bin4(bU4) }} =
            <span style="color: var(--vp-c-brand-1)">{{ bin4(sumBits4) }}</span>
          </div>
          <div style="font-size: 12.5px; display: flex; flex-direction: column; gap: 3px">
            <div>
              <strong>Unsigned:</strong> {{ aU4 }} + {{ bU4 }} →
              <code class="hw-mono">{{ sumBits4 }}</code>
              <span v-if="unsignedOverflow" style="color: var(--hw-amber); font-weight: 600">
                (wrapped from {{ rawSumU }})
              </span>
            </div>
            <div>
              <strong>Signed:</strong> ({{ fmtS4(aS4) }}) + ({{ fmtS4(bS4) }}) →
              <code class="hw-mono">{{ fmtS4(sumS4) }}</code>
              <span v-if="signedOverflow" style="color: var(--hw-red); font-weight: 600">
                (signed overflow: true sum {{ aS4 + bS4 }} outside -8..+7)
              </span>
              <span v-else style="color: var(--hw-green); font-weight: 600"> (exact)</span>
            </div>
          </div>
        </div>
      </div>

      <!-- SVG Clock Wheel with concentric signed/unsigned rings and role halos -->
      <div style="display: flex; flex-direction: column; align-items: center; gap: 6px">
        <svg viewBox="0 0 310 310" style="width: 280px; height: 280px; max-width: 100%">
          <circle
            cx="155"
            cy="155"
            r="104"
            fill="none"
            stroke="currentColor"
            stroke-opacity="0.16"
            stroke-width="1.5"
          />
          <g v-for="slot in wheelSlots" :key="slot.u">
            <!-- Outer Unsigned Label (0..15) -->
            <text
              :x="slot.ux"
              :y="slot.uy + 3.5"
              text-anchor="middle"
              font-size="9.5"
              font-family="var(--vp-font-family-mono)"
              :font-weight="slot.u === sumBits4 ? '800' : '600'"
              :fill="slot.u === sumBits4 ? 'var(--vp-c-brand-1)' : 'var(--vp-c-text-2)'"
            >
              {{ slot.u }}
            </text>
            <!-- Outer Green Halo when A hits this slot -->
            <circle
              v-if="slot.u === aU4"
              :cx="slot.x"
              :cy="slot.y"
              r="18"
              fill="none"
              stroke="var(--hw-green)"
              stroke-width="2.5"
            />
            <!-- Middle Amber Halo when B hits this slot -->
            <circle
              v-if="slot.u === bU4"
              :cx="slot.x"
              :cy="slot.y"
              r="15"
              fill="none"
              stroke="var(--hw-amber)"
              stroke-width="2.5"
            />
            <!-- Inner Slot Disc (Blue if Sum) -->
            <circle
              :cx="slot.x"
              :cy="slot.y"
              r="12"
              :fill="slot.u === sumBits4 ? 'var(--vp-c-brand-1)' : 'var(--vp-c-bg)'"
              stroke="currentColor"
              :stroke-opacity="slot.u === sumBits4 ? 0.6 : 0.25"
            />
            <text
              :x="slot.x"
              :y="slot.y + 3.5"
              text-anchor="middle"
              font-size="9.5"
              font-weight="700"
              :fill="slot.u === sumBits4 ? 'var(--vp-c-bg)' : 'currentColor'"
            >
              {{ fmtS4(slot.s) }}
            </text>
          </g>
          <text x="155" y="131" text-anchor="middle" font-size="9.5" fill="var(--vp-c-text-2)" font-weight="600">
            Inner: Signed · Outer: Unsigned
          </text>
          <text x="155" y="148" text-anchor="middle" font-size="10.5" fill="var(--hw-green)" font-weight="700">
            Green halo = A ({{ fmtS4(aS4) }} / {{ aU4 }})
          </text>
          <text x="155" y="164" text-anchor="middle" font-size="10.5" fill="var(--hw-amber)" font-weight="700">
            Amber halo = B ({{ fmtS4(bS4) }} / {{ bU4 }})
          </text>
          <text x="155" y="181" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--vp-c-brand-1)">
            Blue fill = {{ fmtS4(sumS4) }} / {{ sumBits4 }} ({{ bin4(sumBits4) }})
          </text>
        </svg>
        <div
          v-if="overlapNote"
          class="hw-mono"
          style="font-size: 11.5px; color: var(--vp-c-text-2); text-align: center"
        >
          {{ overlapNote }}
        </div>
      </div>
    </div>
  </div>
</template>
