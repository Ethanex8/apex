<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">64-Bit Product Split: Shared Low 32 Bits (mul) vs. Divergent High 32 Bits</div>
    </div>

    <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect all 64-bit product halves</div>
    <div style="overflow-x: auto; padding-bottom: 4px">
    <svg
      viewBox="0 0 680 250"
      class="hw-svg-diagram"
      style="min-width: 550px"
      role="img"
      aria-label="Aligned 64-bit product diagram showing identical lower 32 bits shared by mul and divergent upper 32 bits for mulh, mulhsu, and mulhu"
    >
      <!-- Input wire header -->
      <rect x="10" y="8" width="318" height="36" rx="7" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.2" />
      <text x="169" y="23" text-anchor="middle" font-size="10.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--hw-green)">
        rs1 = 0xFFFF_FFFF
      </text>
      <text x="169" y="38" text-anchor="middle" font-size="9.5" fill="var(--vp-c-text-2)">
        Signed S32 = -1 · Unsigned U32 = 2^32 - 1
      </text>

      <rect x="352" y="8" width="318" height="36" rx="7" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.2" />
      <text x="511" y="23" text-anchor="middle" font-size="10.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--hw-amber)">
        rs2 = 0x8000_0000
      </text>
      <text x="511" y="38" text-anchor="middle" font-size="9.5" fill="var(--vp-c-text-2)">
        Signed S32 = -2^31 · Unsigned U32 = +2^31
      </text>

      <!-- Column header + Shared Low-32 Highlight Column -->
      <rect x="406" y="54" width="264" height="164" rx="8" fill="rgba(5, 150, 105, 0.08)" stroke="var(--hw-green)" stroke-width="1.5" stroke-dasharray="5 3" />
      <text x="266" y="68" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--vp-c-text-1)">
        Upper Half (Bits 63..32) — 3 Distinct Sign Modes
      </text>
      <text x="538" y="68" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--hw-green)">
        Lower Half (Bits 31..0) — Single Shared mul
      </text>

      <!-- Bit-32 vertical split seam -->
      <line x1="396" y1="54" x2="396" y2="218" stroke="var(--vp-c-text-2)" stroke-width="1.5" stroke-dasharray="3 3" />

      <!-- Row 1: mulh (Signed x Signed) -->
      <text x="12" y="96" font-size="11" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-brand-1)">mulh</text>
      <text x="12" y="110" font-size="9.5" fill="var(--vp-c-text-2)">S32 × S32 = +2^31</text>
      <rect x="148" y="78" width="236" height="38" rx="6" fill="var(--vp-c-bg)" stroke="var(--vp-c-brand-1)" stroke-width="1.5" />
      <text x="266" y="102" text-anchor="middle" font-size="12" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-brand-1)">
        0x0000_0000
      </text>
      <rect x="416" y="78" width="244" height="38" rx="6" fill="var(--vp-c-bg)" stroke="var(--hw-green)" stroke-width="1.5" />
      <text x="538" y="102" text-anchor="middle" font-size="12" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--hw-green)">
        0x8000_0000
      </text>

      <!-- Row 2: mulhsu (Signed x Unsigned) -->
      <text x="12" y="144" font-size="11" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--hw-purple)">mulhsu</text>
      <text x="12" y="158" font-size="9.5" fill="var(--vp-c-text-2)">S32 × U32 = -2^31</text>
      <rect x="148" y="126" width="236" height="38" rx="6" fill="var(--vp-c-bg)" stroke="var(--hw-purple)" stroke-width="1.5" />
      <text x="266" y="150" text-anchor="middle" font-size="12" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--hw-purple)">
        0xFFFF_FFFF
      </text>
      <rect x="416" y="126" width="244" height="38" rx="6" fill="var(--vp-c-bg)" stroke="var(--hw-green)" stroke-width="1.5" />
      <text x="538" y="150" text-anchor="middle" font-size="12" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--hw-green)">
        0x8000_0000
      </text>

      <!-- Row 3: mulhu (Unsigned x Unsigned) -->
      <text x="12" y="192" font-size="11" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--hw-amber)">mulhu</text>
      <text x="12" y="206" font-size="9.5" fill="var(--vp-c-text-2)">U32 × U32 = 2^63 - 2^31</text>
      <rect x="148" y="174" width="236" height="38" rx="6" fill="var(--vp-c-bg)" stroke="var(--hw-amber)" stroke-width="1.5" />
      <text x="266" y="198" text-anchor="middle" font-size="12" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--hw-amber)">
        0x7FFF_FFFF
      </text>
      <rect x="416" y="174" width="244" height="38" rx="6" fill="var(--vp-c-bg)" stroke="var(--hw-green)" stroke-width="1.5" />
      <text x="538" y="198" text-anchor="middle" font-size="12" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--hw-green)">
        0x8000_0000
      </text>

      <!-- Bottom takeaway -->
      <text x="340" y="238" text-anchor="middle" font-size="10.5" fill="var(--vp-c-text-2)">
        All three 64-bit products share identical Bits 31..0 (mul) while diverging in Bits 63..32.
      </text>
    </svg>
    </div>
  </div>
</template>
