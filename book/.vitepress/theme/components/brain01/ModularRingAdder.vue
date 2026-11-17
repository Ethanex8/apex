<script setup lang="ts">
import { computed, ref } from 'vue'

const aBits = ref<number>(0b1011) // 11 unsigned, -5 signed
const bBits = ref<number>(0b0011) // 3 unsigned, +3 signed

const presets = [
  { label: '-5 + (+3) = -2', a: 0b1011, b: 0b0011 },
  { label: '+7 + (+2) wraps to -7', a: 0b0111, b: 0b0010 },
  { label: '-1 + (+1) wraps to 0', a: 0b1111, b: 0b0001 },
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
    const r = 90
    return {
      u,
      s: toSigned4(u),
      bits: bin4(u),
      x: 125 + r * Math.cos(angle),
      y: 125 + r * Math.sin(angle),
    }
  })
})
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">
        <span class="hw-badge">Intuition Builder</span>
        <span>4-Bit Modular Ring (Clock-Face Addition)</span>
      </div>
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
      Think of a 4-bit register like a 16-hour clock face (<code>0000</code> at 12 o'clock). Notice that
      <strong>Bit 3</strong> carries weight <code>+8</code> in unsigned view (<code>u4</code>) and
      <code>-8</code> in two's complement view (<code>s4</code>), yet stepping clockwise around the ring computes
      both sums with the exact same hardware adder.
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
              style="flex: 1; padding: 5px 4px"
              @click="toggleBit4('a', bit)"
            >
              <div style="font-size: 10px; opacity: 0.8">
                b{{ bit }} ({{ bit === 3 ? '-8/+8' : `+${1 << bit}` }})
              </div>
              <div style="font-size: 15px; font-weight: 700">{{ (aU4 >> bit) & 1 }}</div>
            </button>
          </div>
          <div class="hw-mono" style="font-size: 12px; color: var(--vp-c-text-2); white-space: nowrap">
            Unsigned <code>u4</code> = <strong>{{ aU4 }}</strong> · Signed <code>s4</code> = <strong>{{ fmtS4(aS4) }}</strong>
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
              style="flex: 1; padding: 5px 4px"
              @click="toggleBit4('b', bit)"
            >
              <div style="font-size: 10px; opacity: 0.8">
                b{{ bit }} ({{ bit === 3 ? '-8/+8' : `+${1 << bit}` }})
              </div>
              <div style="font-size: 15px; font-weight: 700">{{ (bU4 >> bit) & 1 }}</div>
            </button>
          </div>
          <div class="hw-mono" style="font-size: 12px; color: var(--vp-c-text-2); white-space: nowrap">
            Unsigned <code>u4</code> = <strong>{{ bU4 }}</strong> · Signed <code>s4</code> = <strong>{{ fmtS4(bS4) }}</strong>
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

      <!-- SVG Clock Wheel with concentric role halos -->
      <div style="display: flex; flex-direction: column; align-items: center; gap: 6px">
        <svg viewBox="0 0 250 250" style="width: 240px; height: 240px; max-width: 100%">
          <circle
            cx="125"
            cy="125"
            r="90"
            fill="none"
            stroke="currentColor"
            stroke-opacity="0.16"
            stroke-width="1.5"
          />
          <g v-for="slot in wheelSlots" :key="slot.u">
            <!-- Outer Green Halo when A hits this slot -->
            <circle
              v-if="slot.u === aU4"
              :cx="slot.x"
              :cy="slot.y"
              r="18.5"
              fill="none"
              stroke="var(--hw-green)"
              stroke-width="2.5"
            />
            <!-- Middle Amber Halo when B hits this slot -->
            <circle
              v-if="slot.u === bU4"
              :cx="slot.x"
              :cy="slot.y"
              r="15.5"
              fill="none"
              stroke="var(--hw-amber)"
              stroke-width="2.5"
            />
            <!-- Inner Slot Disc (Blue if Sum) -->
            <circle
              :cx="slot.x"
              :cy="slot.y"
              r="12"
              :fill="
                slot.u === sumBits4
                  ? 'var(--vp-c-brand-1)'
                  : 'var(--vp-c-bg)'
              "
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
          <text x="125" y="109" text-anchor="middle" font-size="10" fill="var(--hw-green)" font-weight="700">
            Green halo = A ({{ fmtS4(aS4) }})
          </text>
          <text x="125" y="124" text-anchor="middle" font-size="10" fill="var(--hw-amber)" font-weight="700">
            Amber halo = B ({{ fmtS4(bS4) }})
          </text>
          <text x="125" y="141" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--vp-c-brand-1)">
            Blue fill = Sum {{ fmtS4(sumS4) }} ({{ bin4(sumBits4) }})
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
