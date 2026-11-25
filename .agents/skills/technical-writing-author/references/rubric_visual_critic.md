# Visual Pedagogy & Surface Critic Rubric

Activate whenever a document embeds `<svg>` diagrams, Mermaid flowcharts, interactive UI/widget components, custom theme CSS, or rendered visual audit screenshots:

## 1. Visual Pedagogy & Surface Audit
1. **SVG-First Visual Substance & Single Unambiguous Title**: Flag widgets or diagrams rendering text/equation cards or calculator boxes instead of genuine spatial, geometric, or schematic `<svg>` diagrams (rings, number lines, wire/signal-flow diagrams, aligned lanes), and flag duplicate dual titles (such as a separate pill stacked beside a main title).
2. **Exact Insertion-Line Alignment**: Inspect each diagram or interactive component at its Markdown insertion point to confirm zero unintroduced symbols, formulas, presets, or code idioms appear prematurely.
3. **Math & Typography Hygiene**: Inspect rendered prose/display math and stylesheets to confirm zero inline math scrollbars/baseline clipping, display math fitting column bounds, and interactive widgets staying isolated from serif prose overrides.
4. **SVG Legibility, Light/Dark Contrast & Bit Labels**: Verify desktop, dark-mode, and mobile renders show crisp SVG viewBox scaling, clean arrow/wire alignment, zero label overlap, explicit `Bits hi..lo` labels where bitfields appear, high light/dark contrast, and zero clipped Mermaid `<foreignObject>` nodes.
5. **No Duplicate Section Dividers**: Flag bare `---` horizontal rules immediately preceding `##` headings whenever the rendered theme already draws heading dividers.
