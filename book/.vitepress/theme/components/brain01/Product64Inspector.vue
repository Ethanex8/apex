<script setup lang="ts">
import { computed, ref } from 'vue'

interface MulPreset {
  label: string
  rs1U: number
  rs2U: number
  note: string
}

const presets: MulPreset[] = [
  {
    label: '-1 × -2^31 (Classic Divergence)',
    rs1U: 0xffffffff,
    rs2U: 0x80000000,
    note: 'Bits 31..0 match across all four operations, while Signed/Mixed/Unsigned interpretations push Bits 63..32 to 0, -1, and 0x7FFF_FFFF.',
  },
  {
    label: '-7 × +3 (Negative × Positive)',
    rs1U: 0xfffffff9,
    rs2U: 3,
    note: "Signed product -21 needs two's-complement sign bits (0xFFFF_FFFF) in Bits 63..32, whereas unsigned interpretation treats 0xFFFF_FFF9 as +4,294,967,289.",
  },
  {
    label: '65536 × 65536 (32-Bit Carry)',
    rs1U: 0x00010000,
    rs2U: 0x00010000,
    note: 'Two positive 16-bit-shifted numbers multiply to 2^32: mul returns 0 (the lower 32 bits), while mulh/mulhsu/mulhu return 1.',
  },
  {
    label: '-3 × -4 (Negative × Negative)',
    rs1U: 0xfffffffd,
    rs2U: 0xfffffffc,
    note: 'Signed (-3) × (-4) = +12 fits inside Bits 31..0 (mulh = 0), whereas unsigned 4.29B × 4.29B generates huge upper carry bits.',
  },
]

const selectedIdx = ref(0)
const current = computed(() => presets[selectedIdx.value])

function toS32(u: number): bigint {
  const val = BigInt(u >>> 0)
  return val >= 0x80000000n ? val - 0x100000000n : val
}

function toU32(u: number): bigint {
  return BigInt(u >>> 0)
}

function fmtHex32(val: bigint): string {
  const masked = ((val % 0x100000000n) + 0x100000000n) % 0x100000000n
  const hex = masked.toString(16).toUpperCase().padStart(8, '0')
  return `0x${hex.slice(0, 4)}_${hex.slice(4)}`
}

const rows = computed(() => {
  const r1s = toS32(current.value.rs1U)
  const r2s = toS32(current.value.rs2U)
  const r1u = toU32(current.value.rs1U)
  const r2u = toU32(current.value.rs2U)

  const prodSS = r1s * r2s
  const prodSU = r1s * r2u
  const prodUU = r1u * r2u

  const split = (insn: string, mode: string, left: bigint, right: bigint, prod: bigint, accent: string) => {
    const prodU64 = ((prod % (1n << 64n)) + (1n << 64n)) % (1n << 64n)
    const hi32 = prodU64 >> 32n
    const lo32 = prodU64 & 0xffffffffn
    return {
      insn,
      mode,
      leftDec: left.toLocaleString(),
      rightDec: right.toLocaleString(),
      prodDec: prod.toLocaleString(),
      hiHex: fmtHex32(hi32),
      loHex: fmtHex32(lo32),
      accent,
    }
  }

  return [
    split('mulh', 'Signed × Signed', r1s, r2s, prodSS, 'var(--vp-c-brand-1)'),
    split('mulhsu', 'Signed × Unsigned', r1s, r2u, prodSU, 'var(--hw-purple)'),
    split('mulhu', 'Unsigned × Unsigned', r1u, r2u, prodUU, 'var(--hw-amber)'),
  ]
})

const sharedLowHex = computed(() => rows.value[0].loHex)
</script>

<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">
        <span class="hw-badge">RV32M 64-Bit Multiplier</span>
        <span>Same Input Wires, Shared Lower 32 Bits, Divergent Upper 32 Bits</span>
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

    <div class="hw-grid-2" style="margin-bottom: 10px">
      <div class="hw-card">
        <div class="hw-label">Raw Input Wire <code>rs1</code></div>
        <div class="hw-mono" style="font-size: 14px; font-weight: 700; color: var(--hw-green)">
          {{ fmtHex32(toU32(current.rs1U)) }}
        </div>
        <div style="font-size: 12px; color: var(--vp-c-text-2)">
          Signed: {{ toS32(current.rs1U).toLocaleString() }} | Unsigned: {{ toU32(current.rs1U).toLocaleString() }}
        </div>
      </div>
      <div class="hw-card">
        <div class="hw-label">Raw Input Wire <code>rs2</code></div>
        <div class="hw-mono" style="font-size: 14px; font-weight: 700; color: var(--hw-amber)">
          {{ fmtHex32(toU32(current.rs2U)) }}
        </div>
        <div style="font-size: 12px; color: var(--vp-c-text-2)">
          Signed: {{ toS32(current.rs2U).toLocaleString() }} | Unsigned: {{ toU32(current.rs2U).toLocaleString() }}
        </div>
      </div>
    </div>

    <div style="display: flex; flex-direction: column; gap: 8px">
      <div
        v-for="r in rows"
        :key="r.insn"
        class="hw-card"
        style="padding: 10px"
      >
        <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 6px; margin-bottom: 6px">
          <div>
            <span class="hw-mono" style="font-weight: 800; font-size: 13px" :style="{ color: r.accent }">{{ r.insn }}</span>
            <span style="font-size: 12px; color: var(--vp-c-text-2); margin-left: 6px">({{ r.mode }})</span>
          </div>
          <div class="hw-mono" style="font-size: 11.5px; color: var(--vp-c-text-2)">
            {{ r.leftDec }} × {{ r.rightDec }} = {{ r.prodDec }}
          </div>
        </div>

        <div class="hw-grid-2" style="gap: 6px">
          <div
            style="padding: 6px 8px; border-radius: 6px; border: 1.5px solid"
            :style="{ borderColor: r.accent, background: 'var(--vp-c-bg)' }"
          >
            <div style="font-size: 10px; font-weight: 700" :style="{ color: r.accent }">
              Upper 32 Bits (Bits 63..32) — {{ r.insn }} returns:
            </div>
            <div class="hw-mono" style="font-size: 13.5px; font-weight: 800">{{ r.hiHex }}</div>
          </div>

          <div
            style="
              padding: 6px 8px;
              border-radius: 6px;
              border: 1.5px solid var(--hw-green);
              background: var(--vp-c-bg);
            "
          >
            <div style="font-size: 10px; font-weight: 700; color: var(--hw-green)">
              Lower 32 Bits (Bits 31..0) — Shared by mul:
            </div>
            <div class="hw-mono" style="font-size: 13.5px; font-weight: 800">{{ r.loHex }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="hw-card" style="margin-top: 10px; font-size: 13px">
      <strong style="color: var(--hw-green)">Invariant Check (mul = {{ sharedLowHex }}): </strong>
      <span>{{ current.note }}</span>
    </div>
  </div>
</template>
