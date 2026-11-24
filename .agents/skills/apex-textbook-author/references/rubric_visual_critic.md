# Visual Pedagogy & Surface Critic Rubric

Audit interactive widgets, MathJax rendering, `book/.vitepress/theme/custom.css`, and Playwright screenshots in `.cache/visual-audit/<slug>/`:

## 1. Visual Pedagogy & Playwright Surface Audit
1. **SVG-First Visual Substance & Single Unambiguous Title**: Flag any widget rendering text/equation cards or calculator boxes instead of genuine spatial, geometric, or schematic `<svg>` diagrams (rings, number lines, wire/signal-flow diagrams, aligned lane schematics), and flag redundant dual titles such as a separate pill/category title stacked beside a main title.
2. **Exact Insertion-Line Alignment**: Inspect each `.vue` widget at its Markdown insertion point to confirm zero unintroduced symbols, formulas, presets, or code idioms appear prematurely.
3. **MathJax & Typography Hygiene**: Inspect `prose_math_desktop.png`, `display_math_desktop.png`, and `custom.css` to confirm zero inline math scrollbars/baseline clipping, display math fitting column bounds, and `.hw-widget` immunity from `.book-serif-mode`.
4. **SVG Legibility, Light/Dark Contrast & Bit Labels**: Verify desktop (`1280px`), dark-mode (`widget_*_dark.png`, `mermaid_*_dark.png`), and mobile (`390px`) PNGs show crisp SVG viewBox scaling, clean arrow/wire alignment, zero label overlap, explicit `Bits hi..lo` labels, high light/dark contrast, and zero clipped Mermaid `<foreignObject>` nodes.
