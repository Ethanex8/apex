<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">32-Bit Constant Split Carry Bias (+0x800 across Bit 11 to Bit 12)</div>
    </div>

    <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect both Bit 11 cases</div>
    <div style="overflow-x: auto; padding-bottom: 4px">
    <svg
      viewBox="0 0 680 388"
      class="hw-svg-diagram"
      style="min-width: 560px"
      role="img"
      aria-label="Dual-case bit-boundary diagram showing how compiler/assembler bias +0x800 leaves Bit 11 = 0 untouched (lui x5, 0x12345; addi x5, x5, 291) while carrying +1 into Bit 12 when Bit 11 = 1 (lui x5, 0x12346; addi x5, x5, -1348)"
    >
      <defs>
        <marker id="lui-arr-brand" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--vp-c-brand-1)" />
        </marker>
      </defs>

      <!-- Top seam header (above Case 1 title so zero overlap) -->
      <text x="410" y="14" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--hw-red)">
        Bit 12 | Bit 11 Seam
      </text>

      <!-- CASE 1: Bit 11 = 0 (No Carry) -->
      <text x="12" y="34" font-size="10.5" font-weight="700" fill="var(--hw-green)">
        Case 1 (Bit 11 = 0): 0x1234_5123 — +0x800 Does Not Carry Into Bit 12
      </text>
      <line x1="410" y1="40" x2="410" y2="126" stroke="var(--vp-c-divider)" stroke-width="1.5" stroke-dasharray="4 3" />

      <text x="12" y="59" font-size="10.5" font-weight="700" fill="var(--vp-c-text-1)">Target</text>
      <text x="12" y="73" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">0x1234_5123</text>

      <rect x="124" y="44" width="278" height="36" rx="6" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.3" />
      <text x="263" y="59" text-anchor="middle" font-size="9.2" font-weight="700" fill="var(--vp-c-text-2)">Bits 31..12 (Upper 20 Bits)</text>
      <text x="263" y="74" text-anchor="middle" font-size="11.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">0x12345</text>

      <rect x="418" y="44" width="250" height="36" rx="6" fill="rgba(5, 150, 105, 0.08)" stroke="var(--hw-green)" stroke-width="1.4" />
      <text x="543" y="59" text-anchor="middle" font-size="9.2" font-weight="700" fill="var(--hw-green)">Bits 11..0 (Bit 11 = 0 → Positive)</text>
      <text x="543" y="74" text-anchor="middle" font-size="11" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">0x123 (+291)</text>

      <text x="12" y="103" font-size="10.5" font-weight="700" fill="var(--vp-c-brand-1)">+ 0x800</text>
      <text x="12" y="117" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">0x1234_5923</text>

      <rect x="124" y="88" width="278" height="36" rx="6" fill="var(--vp-c-bg)" stroke="var(--vp-c-brand-1)" stroke-width="1.3" />
      <text x="263" y="103" text-anchor="middle" font-size="9.2" font-weight="700" fill="var(--vp-c-brand-1)">Upper 20 Bits Unchanged (Carry 0)</text>
      <text x="263" y="118" text-anchor="middle" font-size="11.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-brand-1)">hi_lui = 0x12345</text>

      <rect x="418" y="88" width="250" height="36" rx="6" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.2" stroke-dasharray="4 2" />
      <text x="543" y="103" text-anchor="middle" font-size="9.2" font-weight="700" fill="var(--vp-c-text-2)">0x123 + 0x800 = 0x923 &lt; 0x1000</text>
      <text x="543" y="118" text-anchor="middle" font-size="9.2" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">No carry out; addi adds +291</text>

      <rect x="12" y="132" width="656" height="36" rx="7" fill="rgba(5, 150, 105, 0.08)" stroke="var(--hw-green)" stroke-width="1.5" />
      <text x="340" y="154" text-anchor="middle" font-size="10.3" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        Assembler emits: lui x5, 0x12345  ;  addi x5, x5, 291   →   0x1234_5000 + 0x123 = 0x1234_5123
      </text>

      <!-- Divider -->
      <line x1="12" y1="180" x2="668" y2="180" stroke="var(--vp-c-divider)" stroke-width="1" />

      <!-- CASE 2: Bit 11 = 1 (Carries +1) -->
      <text x="12" y="200" font-size="10.5" font-weight="700" fill="var(--vp-c-brand-1)">
        Case 2 (Bit 11 = 1): 0x1234_5ABC — +0x800 Carries +1 Across Bit 11 Into Bit 12
      </text>
      <line x1="410" y1="208" x2="410" y2="320" stroke="var(--hw-red)" stroke-width="1.6" stroke-dasharray="4 3" />

      <text x="12" y="224" font-size="10.5" font-weight="700" fill="var(--vp-c-text-1)">Target</text>
      <text x="12" y="238" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">0x1234_5ABC</text>

      <rect x="124" y="209" width="278" height="36" rx="6" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.3" />
      <text x="263" y="224" text-anchor="middle" font-size="9.2" font-weight="700" fill="var(--vp-c-text-2)">Bits 31..12 (Upper 20 Bits)</text>
      <text x="263" y="239" text-anchor="middle" font-size="11.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">0x12345</text>

      <rect x="418" y="209" width="250" height="36" rx="6" fill="rgba(220, 38, 38, 0.08)" stroke="var(--hw-red)" stroke-width="1.5" />
      <text x="543" y="224" text-anchor="middle" font-size="9.2" font-weight="700" fill="var(--hw-red)">Bits 11..0 (Bit 11 = 1 → Negative)</text>
      <text x="543" y="239" text-anchor="middle" font-size="10.8" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">0xABC (-1,348 = -0x544)</text>

      <!-- Carry corridor (y=245..284) -->
      <rect x="374" y="247" width="72" height="17" rx="4" fill="var(--vp-c-bg)" stroke="var(--vp-c-brand-1)" stroke-width="1.1" />
      <text x="410" y="259" text-anchor="middle" font-size="9.2" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-brand-1)">
        carry +1
      </text>
      <path
        d="M 466 282 C 450 264, 370 264, 354 280"
        fill="none"
        stroke="var(--vp-c-brand-1)"
        stroke-width="2.2"
        marker-end="url(#lui-arr-brand)"
      />

      <text x="12" y="299" font-size="10.5" font-weight="700" fill="var(--vp-c-brand-1)">+ 0x800</text>
      <text x="12" y="313" font-size="9.5" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">0x1234_62BC</text>

      <rect x="124" y="284" width="278" height="36" rx="6" fill="var(--vp-c-brand-soft)" stroke="var(--vp-c-brand-1)" stroke-width="1.5" />
      <text x="263" y="299" text-anchor="middle" font-size="9.2" font-weight="700" fill="var(--vp-c-brand-1)">Upper 20 Bits Promoted (+1)</text>
      <text x="263" y="314" text-anchor="middle" font-size="11.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-brand-1)">hi_lui = 0x12346</text>

      <rect x="418" y="284" width="250" height="36" rx="6" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.2" stroke-dasharray="4 2" />
      <text x="543" y="299" text-anchor="middle" font-size="9.2" font-weight="700" fill="var(--vp-c-text-2)">0xABC + 0x800 = 0x12BC ≥ 0x1000</text>
      <text x="543" y="314" text-anchor="middle" font-size="9.2" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-2)">Low 12 bits dropped; lui zeroes Bits 11..0</text>

      <!-- Naive vs Biased execution cards (y=330..378) -->
      <rect x="12" y="330" width="320" height="48" rx="7" fill="rgba(220, 38, 38, 0.06)" stroke="var(--hw-red)" stroke-width="1.3" />
      <text x="172" y="347" text-anchor="middle" font-size="9.8" font-weight="700" fill="var(--hw-red)">
        Without +0x800 (Undershoots by 0x1000)
      </text>
      <text x="172" y="366" text-anchor="middle" font-size="9.4" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        lui x5,0x12345; addi x5,x5,-1348 → 0x1234_4ABC
      </text>

      <rect x="348" y="330" width="320" height="48" rx="7" fill="rgba(5, 150, 105, 0.08)" stroke="var(--hw-green)" stroke-width="1.6" />
      <text x="508" y="347" text-anchor="middle" font-size="9.8" font-weight="700" fill="var(--hw-green)">
        With +0x800 (Exact Reconstruction)
      </text>
      <text x="508" y="366" text-anchor="middle" font-size="9.4" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        lui x5,0x12346; addi x5,x5,-1348 → 0x1234_5ABC
      </text>
    </svg>
    </div>
  </div>
</template>
