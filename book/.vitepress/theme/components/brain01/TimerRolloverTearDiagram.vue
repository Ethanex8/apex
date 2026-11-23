<template>
  <div class="hw-widget">
    <div class="hw-widget-header">
      <div class="hw-widget-title">64-Bit Timer Rollover Tear Hazard vs. 3-Read Retry Loop</div>
    </div>

    <div class="hw-mobile-scroll-hint">↔ Swipe horizontally to inspect the 64-bit rollover timeline</div>
    <div style="overflow-x: auto; padding-bottom: 4px">
    <svg
      viewBox="0 0 680 242"
      class="hw-svg-diagram"
      style="min-width: 550px"
      role="img"
      aria-label="Timeline diagram contrasting a torn 2-read 64-bit timer access across a 32-bit carry boundary against a tear-free 3-read hi1, lo, hi2 retry loop"
    >
      <!-- Vertical Carry Tick Boundary -->
      <line x1="340" y1="26" x2="340" y2="210" stroke="var(--hw-red)" stroke-width="2" stroke-dasharray="5 3" />
      <rect x="266" y="6" width="148" height="20" rx="4" fill="rgba(220, 38, 38, 0.1)" stroke="var(--hw-red)" stroke-width="1" />
      <text x="340" y="20" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--hw-red)">
        32-Bit Carry Tick (+1)
      </text>

      <!-- Hardware mtime state before vs after tick -->
      <rect x="12" y="34" width="314" height="36" rx="6" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.2" />
      <text x="169" y="48" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--vp-c-text-2)">Before Tick: mtime</text>
      <text x="169" y="63" text-anchor="middle" font-size="11.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        HI = 0x0000_0000 | LO = 0xFFFF_FFFF
      </text>

      <rect x="354" y="34" width="314" height="36" rx="6" fill="var(--vp-c-bg)" stroke="var(--vp-c-divider)" stroke-width="1.2" />
      <text x="511" y="48" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--vp-c-text-2)">After Tick: mtime</text>
      <text x="511" y="63" text-anchor="middle" font-size="11.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        HI = 0x0000_0001 | LO = 0x0000_0000
      </text>

      <!-- ROW 1: BUGGY 2-READ SEQUENCE -->
      <rect x="12" y="84" width="656" height="54" rx="8" fill="rgba(220, 38, 38, 0.05)" stroke="var(--hw-red)" stroke-width="1.3" />
      <text x="24" y="101" font-size="10.5" font-weight="700" fill="var(--hw-red)">Buggy 2-Read Sequence (Torn Timestamp):</text>

      <rect x="150" y="108" width="174" height="24" rx="5" fill="var(--vp-c-bg)" stroke="var(--hw-red)" stroke-width="1.2" />
      <text x="237" y="124" text-anchor="middle" font-size="9.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        1. Read LO → 0xFFFF_FFFF
      </text>

      <rect x="352" y="108" width="166" height="24" rx="5" fill="var(--vp-c-bg)" stroke="var(--hw-red)" stroke-width="1.2" />
      <text x="435" y="124" text-anchor="middle" font-size="9.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        2. Read HI → 0x0000_0001
      </text>

      <text x="594" y="118" text-anchor="middle" font-size="9.5" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--hw-red)">
        0x0000_0001_FFFF_FFFF
      </text>
      <text x="594" y="131" text-anchor="middle" font-size="9" font-weight="700" fill="var(--hw-red)">
        (+85.9 s overshoot!)
      </text>

      <!-- ROW 2: TEAR-FREE 3-READ RETRY LOOP -->
      <rect x="12" y="150" width="656" height="58" rx="8" fill="rgba(5, 150, 105, 0.06)" stroke="var(--hw-green)" stroke-width="1.4" />
      <text x="24" y="167" font-size="10.5" font-weight="700" fill="var(--hw-green)">Tear-Free 3-Read Loop (hi1, lo, hi2 while hi1 != hi2):</text>

      <rect x="64" y="176" width="116" height="24" rx="5" fill="var(--vp-c-bg)" stroke="var(--hw-green)" stroke-width="1.2" />
      <text x="122" y="192" text-anchor="middle" font-size="10" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        1. hi1 → 0x0
      </text>

      <rect x="192" y="176" width="134" height="24" rx="5" fill="var(--vp-c-bg)" stroke="var(--hw-green)" stroke-width="1.2" />
      <text x="259" y="192" text-anchor="middle" font-size="10" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        2. lo → 0xFFFF_FFFF
      </text>

      <rect x="358" y="176" width="116" height="24" rx="5" fill="var(--vp-c-bg)" stroke="var(--hw-green)" stroke-width="1.2" />
      <text x="416" y="192" text-anchor="middle" font-size="10" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--vp-c-text-1)">
        3. hi2 → 0x1
      </text>

      <text x="572" y="186" text-anchor="middle" font-size="10" font-weight="700" font-family="var(--vp-font-family-mono)" fill="var(--hw-green)">
        hi1 ≠ hi2 → Retry!
      </text>
      <text x="572" y="199" text-anchor="middle" font-size="9.5" fill="var(--vp-c-text-2)">
        Pass 2 captures consistent (1, lo)
      </text>

      <!-- Bottom takeaway -->
      <text x="340" y="229" text-anchor="middle" font-size="10.5" fill="var(--vp-c-text-2)">
        Because carries occur only every 2^32 ticks (about 85.9 s at 50 MHz), the retry loop finishes in at most one extra pass.
      </text>
    </svg>
    </div>
  </div>
</template>
