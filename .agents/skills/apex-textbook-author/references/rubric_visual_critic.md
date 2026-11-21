# Global Structure & Visual Pedagogy Critic Rubric

Audit whole-chapter macro architecture plus visual rendering across `custom.css`, `.vue` widgets, Mermaid figures, and desktop/mobile screenshots in `.cache/visual-audit/<slug>/`:

## 1. Whole-Chapter Macro Structure
1. **Base-Before-Custom Progression**: Verify core standard architectures (arithmetic, base instructions, memory, control flow, traps) complete cleanly before custom hardware extensions and project-specific accelerators.
2. **End-to-End Rigor Balance**: Verify quantitative invariants, error bounds, and formal models stay evenly rigorous from opening sections through late peripheral, trap, and verification sections.
3. **Exercise vs. Problem Scoping**: Verify inline `#### Exercise <S.K>` `6–8` part drills appear cleanly on mathematical/encoding/bound subsections, while closing `## <N>. Problems` synthesizes multi-section engineering tasks across the whole chapter.
4. **Heading Consistency & Zero Drift**: Check that every `##`/`###` heading stays concise (`<= 8` words, zero `&`/colons/backticks) and subsection content matches its title cleanly.

## 2. Visual Pedagogy & Playwright Surface Audit
5. **Upfront Single-Concept Widgets**: Confirm complex multi-mode or multi-stage mechanisms receive a dedicated interactive `.vue` widget *before* dense formalism, without bundling unrelated concepts.
6. **MathJax & Typography Hygiene**: Inspect `prose_math_desktop.png` and `custom.css` to confirm zero inline math horizontal scrollbars/baseline clipping, zero display equations overflowing desktop width, and `.hw-widget` immunity from `.book-serif-mode`.
7. **Widget Legibility, Contrast & Bit Labels**: Verify mobile (`390px`) and desktop (`1280px`) widget PNGs show explicit `Bits hi..lo` labels, high text/badge contrast in light and dark mode, clean number/text wrapping, and zero clipped Mermaid `<foreignObject>` nodes.
