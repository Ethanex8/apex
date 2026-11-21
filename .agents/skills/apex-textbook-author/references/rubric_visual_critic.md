# Visual Pedagogy & Surface Critic Rubric

Audit interactive widgets, MathJax rendering, `book/.vitepress/theme/custom.css`, and Playwright screenshots in `.cache/visual-audit/<slug>/`:

## 1. Visual Pedagogy & Playwright Surface Audit
1. **Upfront Single-Concept Widgets**: Confirm complex multi-mode or multi-stage mechanisms receive a dedicated `.vue` widget *before* dense formalism, without bundling unrelated concepts.
2. **Exact Insertion-Line Alignment**: Inspect each `.vue` widget at its Markdown insertion point to confirm zero unintroduced symbols, formulas, presets, or code idioms appear prematurely.
3. **MathJax & Typography Hygiene**: Inspect `prose_math_desktop.png` and `custom.css` to confirm zero inline math scrollbars/baseline clipping, display math fitting column bounds, and `.hw-widget` immunity from `.book-serif-mode`.
4. **Widget Legibility, Contrast & Bit Labels**: Verify desktop (`1280px`) and mobile (`390px`) PNGs show explicit `Bits hi..lo` labels, high light/dark contrast, clean wrapping, and zero clipped Mermaid `<foreignObject>` nodes.
