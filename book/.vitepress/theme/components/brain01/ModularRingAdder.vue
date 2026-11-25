<!--
  Purpose: Interactive 4-bit unsigned and two's-complement modular addition clock visualizer.
  Usage: Embedded in Chapter 1 Section 2.4 to demonstrate shared adder equivalence on a mod-16 ring.
  Invariants: Operands A and B mask to 4-bit integers [0, 15]; inner circle shows S_4 [-8, +7], outer shows U_4 [0, 15].
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

/** 4-bit register mask (0..15) and modulus constants. */
const NIBBLE_MASK = 0xf
const MODULUS_4BIT = 16
const BIT_WIDTH_4 = 4
const SIGN_BIT_4 = 0x8
const UNSIGNED4_MAX = 15
const SIGNED4_MIN = -8
const SIGNED4_MAX = 7
const MIN_BIT_INDEX = 0
const MAX_BIT_INDEX = 3
const BIT_INDICES = [3, 2, 1, 0] as const

/** Clock SVG center, viewBox span, and concentric ring radii. */
const SVG_CENTER = 155
const SVG_SIZE = SVG_CENTER * 2
const INNER_RING_RADIUS = 104
const OUTER_RING_RADIUS = 132

/** Preset pair contrasting signed and unsigned wrap behavior. */
interface Preset {
  /** Human-readable preset caption shown on selector button. */
  label: string
  /** 4-bit unsigned pattern (`0..15`) for operand A. */
  a: number
  /** 4-bit unsigned pattern (`0..15`) for operand B. */
  b: number
}

/** Positioned modulo-16 wheel slot on the concentric signed/unsigned SVG rings. */
interface WheelSlot {
  /** Unsigned 4-bit residue (`0..15`). */
  u: number
  /** Signed two's-complement interpretation (`-8..+7`). */
  s: number
  /** Inner signed-ring SVG x-coordinate (pixels). */
  innerX: number
  /** Inner signed-ring SVG y-coordinate (pixels). */
  innerY: number
  /** Outer unsigned-ring SVG x-coordinate (pixels). */
  outerX: number
  /** Outer unsigned-ring SVG y-coordinate (pixels). */
  outerY: number
}

/** Descriptor for rendering one interactive 4-bit operand card. */
interface OperandControl {
  /** Target operand identifier (`'a'` or `'b'`). */
  which: 'a' | 'b'
  /** Card header text with ring color cue. */
  title: string
  /** Current 4-bit unsigned operand value (`0..15`). */
  valU4: number
  /** Current signed two's-complement interpretation (`-8..+7`). */
  valS4: number
}

const aBits = ref<number>(0b1011) // 11 unsigned, -5 signed
const bBits = ref<number>(0b0011) // 3 unsigned, +3 signed

const presets: Preset[] = [
  { label: '-5 + (+3) = -2', a: 0b1011, b: 0b0011 },
  { label: '+7 + (+2) wraps to -7', a: 0b0111, b: 0b0010 },
  { label: '-1 + (+1) = 0 (unsigned wrap)', a: 0b1111, b: 0b0001 },
  { label: '-4 + (-4) = -8', a: 0b1100, b: 0b1100 },
]

/** Mask any integer down to its low 4 bits (`0..15`). */
function mask4(u: number): number {
  return u & NIBBLE_MASK
}

/** Flip bit `bit` (`0..3`) of operand `'a'` or `'b'`, failing fast on out-of-range bit indices. */
function toggleBit4(which: 'a' | 'b', bit: number): void {
  if (!Number.isInteger(bit) || bit < MIN_BIT_INDEX || bit > MAX_BIT_INDEX) {
    throw new RangeError(`ModularRingAdder bit index must be in 0..3, got ${bit}`)
  }
  if (which === 'a') {
    aBits.value = mask4(aBits.value ^ (1 << bit))
  } else {
    bBits.value = mask4(bBits.value ^ (1 << bit))
  }
}

/** Reinterpret 4-bit pattern `u` (`0..15`) as two's-complement signed integer `-8..+7`. */
function toSigned4(u: number): number {
  const v = mask4(u)
  // Bit 3 carries weight -8 in S_4 vs. +8 in U_4, shifting U_4 downward by 16 when set.
  return v & SIGN_BIT_4 ? v - MODULUS_4BIT : v
}

/** Format a signed 4-bit integer with an explicit `+` sign when positive. */
function fmtS4(s: number): string {
  return s > 0 ? `+${s}` : `${s}`
}

/** Format the low 4 bits of `u` as a zero-padded 4-character binary string. */
function bin4(u: number): string {
  return mask4(u).toString(2).padStart(BIT_WIDTH_4, '0')
}

const aU4 = computed(() => mask4(aBits.value))
const bU4 = computed(() => mask4(bBits.value))
const aS4 = computed(() => toSigned4(aU4.value))
const bS4 = computed(() => toSigned4(bU4.value))

const rawSumU = computed(() => aU4.value + bU4.value)
const rawSumS = computed(() => aS4.value + bS4.value)
const sumBits4 = computed(() => mask4(rawSumU.value))
const sumS4 = computed(() => toSigned4(sumBits4.value))
const unsignedOverflow = computed(() => rawSumU.value > UNSIGNED4_MAX)
// Signed overflow tests the exact mathematical sum against [-8, +7], independent of unsigned carry-out.
const signedOverflow = computed(() => rawSumS.value < SIGNED4_MIN || rawSumS.value > SIGNED4_MAX)

const operandControls = computed<OperandControl[]>(() => [
  { which: 'a', title: 'Input A (Green Ring — Click Bits 3..0)', valU4: aU4.value, valS4: aS4.value },
  { which: 'b', title: 'Input B (Amber Ring — Click Bits 3..0)', valU4: bU4.value, valS4: bS4.value },
])

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

const wheelSlots = computed<WheelSlot[]>(() => {
  return Array.from({ length: MODULUS_4BIT }, (_, u) => {
    // Rotate by -pi/2 so unsigned 0 (0000) sits at 12 o'clock instead of 3 o'clock.
    const angle = (u / MODULUS_4BIT) * Math.PI * 2 - Math.PI / 2
    return {
      u,
      s: toSigned4(u),
      innerX: SVG_CENTER + INNER_RING_RADIUS * Math.cos(angle),
      innerY: SVG_CENTER + INNER_RING_RADIUS * Math.sin(angle),
      outerX: SVG_CENTER + OUTER_RING_RADIUS * Math.cos(angle),
      outerY: SVG_CENTER + OUTER_RING_RADIUS * Math.sin(angle),
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
        <div v-for="op in operandControls" :key="op.which" class="hw-card">
          <div class="hw-label">{{ op.title }}</div>
          <div style="display: flex; gap: 6px; margin: 6px 0">
            <button
              v-for="bit in BIT_INDICES"
              :key="`${op.which}-${bit}`"
              type="button"
              class="hw-btn hw-mono"
              :class="{ active: ((op.valU4 >> bit) & 1) === 1 }"
              style="flex: 1; padding: 5px 4px; display: flex; flex-direction: column; justify-content: space-between; align-items: center"
              @click="toggleBit4(op.which, bit)"
            >
              <div style="font-size: 10px; opacity: 0.8; min-height: 24px; display: flex; align-items: center">
                b{{ bit }} ({{ bit === MAX_BIT_INDEX ? '-8/+8' : `+${1 << bit}` }})
              </div>
              <div style="font-size: 15px; font-weight: 700">{{ (op.valU4 >> bit) & 1 }}</div>
            </button>
          </div>
          <div
            class="hw-mono"
            style="font-size: 12px; color: var(--vp-c-text-2); display: flex; flex-wrap: wrap; gap: 2px 10px"
          >
            <span style="white-space: nowrap">Unsigned (0..15) = <strong>{{ op.valU4 }}</strong></span>
            <span style="white-space: nowrap">Signed (-8..+7) = <strong>{{ fmtS4(op.valS4) }}</strong></span>
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
                (signed overflow: true sum {{ rawSumS }} outside {{ SIGNED4_MIN }}..+{{ SIGNED4_MAX }})
              </span>
              <span v-else style="color: var(--hw-green); font-weight: 600"> (exact)</span>
            </div>
          </div>
        </div>
      </div>

      <!-- SVG Clock Wheel with concentric signed/unsigned rings and role halos -->
      <div style="display: flex; flex-direction: column; align-items: center; gap: 6px">
        <svg :viewBox="`0 0 ${SVG_SIZE} ${SVG_SIZE}`" style="width: 280px; height: 280px; max-width: 100%">
          <circle
            :cx="SVG_CENTER"
            :cy="SVG_CENTER"
            :r="INNER_RING_RADIUS"
            fill="none"
            stroke="currentColor"
            stroke-opacity="0.16"
            stroke-width="1.5"
          />
          <g v-for="slot in wheelSlots" :key="slot.u">
            <!-- Outer Unsigned Label (0..15) -->
            <text
              :x="slot.outerX"
              :y="slot.outerY + 3.5"
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
              :cx="slot.innerX"
              :cy="slot.innerY"
              r="18"
              fill="none"
              stroke="var(--hw-green)"
              stroke-width="2.5"
            />
            <!-- Middle Amber Halo when B hits this slot -->
            <circle
              v-if="slot.u === bU4"
              :cx="slot.innerX"
              :cy="slot.innerY"
              r="15"
              fill="none"
              stroke="var(--hw-amber)"
              stroke-width="2.5"
            />
            <!-- Inner Slot Disc (Blue if Sum) -->
            <circle
              :cx="slot.innerX"
              :cy="slot.innerY"
              r="12"
              :fill="slot.u === sumBits4 ? 'var(--vp-c-brand-1)' : 'var(--vp-c-bg)'"
              stroke="currentColor"
              :stroke-opacity="slot.u === sumBits4 ? 0.6 : 0.25"
            />
            <text
              :x="slot.innerX"
              :y="slot.innerY + 3.5"
              text-anchor="middle"
              font-size="9.5"
              font-weight="700"
              :fill="slot.u === sumBits4 ? 'var(--vp-c-bg)' : 'currentColor'"
            >
              {{ fmtS4(slot.s) }}
            </text>
          </g>
          <text :x="SVG_CENTER" y="144" text-anchor="middle" font-size="10.5" fill="var(--hw-green)" font-weight="700">
            Green halo = A ({{ fmtS4(aS4) }} / {{ aU4 }})
          </text>
          <text :x="SVG_CENTER" y="161" text-anchor="middle" font-size="10.5" fill="var(--hw-amber)" font-weight="700">
            Amber halo = B ({{ fmtS4(bS4) }} / {{ bU4 }})
          </text>
          <text :x="SVG_CENTER" y="178" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--vp-c-brand-1)">
            Blue fill = {{ fmtS4(sumS4) }} / {{ sumBits4 }} ({{ bin4(sumBits4) }})
          </text>
        </svg>
        <div
          class="hw-mono"
          style="font-size: 11px; color: var(--vp-c-text-2); text-align: center"
        >
          Inner ring: Signed · Outer ring: Unsigned
        </div>
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
