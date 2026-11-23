<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">32-Bit Constant Split Carry Bias (+0x800 across Bit 11 to Bit 12)</div>
    </div>

    <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect the 32-bit carry seam</div>
    <div style="overflow-x: auto; padding-bottom: 4px">
    <svg
      viewBox="0 0 680 270"
      class="hw-svg-diagram"
      style="min-width: 550px"
      role="img"
      aria-label="Bit-boundary diagram showing how adding 0x800 carries +1 from Bit 11 into Bit 12 so lui plus negative addi lands exactly on 0x1234_5ABC"
    >
      <defs>
        <marker id="lui-arr-brand" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--vp-c-brand-1)" />
        </marker>
        <marker id="lui-arr-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--hw-green)" />
        </marker>
      </defs>

      <!-- Bit-12 / Bit-11 vertical seam (ends cleanly above bottom comparison cards) -->
      <line x1="406" y1="16" x2="406" y2="174" stroke="var(--hw-red)" stroke-width="1.6" stroke-dasharray="4 3" />
      <text x="406" y="13" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--hw-red)">
        Bit 12 | Bit 11 Seam
      </text>

      <!-- ROW 1: Target Constant X (y=26..66) -->
      <text x="12" y="47" font-size="11" font-weight="700" fill="var(--vp-c-text-1)">Target X</text>
      <text x="12" y="61" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">0x1234_5ABC</text>

      <rect x="130" y="26" width="268" height="40" rx="6" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.4" />
      <text x="264" y="42" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--vp-c-text-2)">Bits 31..12 (Upper 20 Bits)</text>
      <text x="264" y="59" text-anchor="middle" font-size="12.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">0x12345</text>

      <rect x="414" y="26" width="254" height="40" rx="6" fill="rgba(220, 38, 38, 0.08)" stroke="var(--hw-red)" stroke-width="1.5" />
      <text x="541" y="42" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--hw-red)">Bits 11..0 (Bit 11 = 1 → Negative)</text>
      <text x="541" y="59" text-anchor="middle" font-size="12" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        0xABC (S12 = -1,348 = -0x544)
      </text>

      <!-- Open Carry Corridor (y=66..122): Pill at y=74..92, curved arrow cleanly below at y=98..120 -->
      <rect x="371" y="74" width="70" height="18" rx="4" fill="var(--vp-c-bg)" stroke="var(--vp-c-brand-1)" stroke-width="1.1" />
      <text x="406" y="86.5" text-anchor="middle" font-size="9.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-brand-1)">
        carry +1
      </text>
      <path
        d="M 460 120 C 446 96, 366 96, 352 118"
        fill="none"
        stroke="var(--vp-c-brand-1)"
        stroke-width="2.4"
        marker-end="url(#lui-arr-brand)"
      />

      <!-- ROW 2: Add Bias +0x800 (2^11) (y=122..162) -->
      <text x="12" y="143" font-size="11" font-weight="700" fill="var(--vp-c-brand-1)">Add +0x800</text>
      <text x="12" y="157" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">X + 2^11</text>

      <rect x="130" y="122" width="268" height="40" rx="6" fill="var(--vp-c-brand-soft)" stroke="var(--vp-c-brand-1)" stroke-width="1.6" />
      <text x="264" y="138" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--vp-c-brand-1)">Biased lui Payload (Upper 20 Bits + 1)</text>
      <text x="264" y="155" text-anchor="middle" font-size="12.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-brand-1)">0x12346</text>

      <rect x="414" y="122" width="254" height="40" rx="6" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.2" stroke-dasharray="4 2" />
      <text x="541" y="138" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--vp-c-text-2)">0xABC + 0x800 = 0x12BC</text>
      <text x="541" y="155" text-anchor="middle" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">Low 12 bits dropped; lui zeroes 11..0</text>

      <!-- ROW 3: Hardware Execution Comparison (Naive vs Biased) (y=184..232) -->
      <rect x="10" y="184" width="320" height="48" rx="7" fill="rgba(220, 38, 38, 0.06)" stroke="var(--hw-red)" stroke-width="1.3" />
      <text x="170" y="202" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--hw-red)">
        Without +0x800 (Undershoots by 0x1000)
      </text>
      <text x="170" y="221" text-anchor="middle" font-size="11" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        0x1234_5000 - 0x544 = 0x1234_4ABC
      </text>

      <rect x="348" y="184" width="322" height="48" rx="7" fill="rgba(5, 150, 105, 0.08)" stroke="var(--hw-green)" stroke-width="1.6" />
      <text x="509" y="202" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--hw-green)">
        With +0x800 (Exact Reconstruction)
      </text>
      <text x="509" y="221" text-anchor="middle" font-size="11" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        0x1234_6000 - 0x544 = 0x1234_5ABC
      </text>

      <!-- Bottom takeaway -->
      <text x="340" y="254" text-anchor="middle" font-size="10.5" fill="var(--vp-c-text-2)">
        When Bit 11 = 0 (Bits 11..0 ≤ 0x7FF), adding 0x800 stays below 0x1000 and never carries into Bit 12.
      </text>
    </svg>
    </div>
  </div>
</template>
