# Visual Pedagogy & Surface Critic Rubric

Activate whenever a document embeds `<svg>` diagrams, Mermaid flowcharts, interactive UI/widget components, custom theme CSS, or rendered visual audit screenshots:

## 1. Visual Pedagogy & Surface Audit
1. **SVG-First Visual Substance & Single Unambiguous Title**: Flag widgets or diagrams rendering text/equation cards or calculator boxes instead of genuine spatial, geometric, or schematic `<svg>` diagrams (rings, number lines, wire/signal-flow diagrams, aligned lanes), and flag duplicate dual titles (such as a separate pill stacked beside a main title).
2. **Contiguous Placement & Symbol Alignment**: Read every line from each enclosing `###` heading down to the widget line: flag premature widget symbols or schematics buried after multi-step proofs or cold set-notation walls (concise 1-line definitions or piecewise `\begin{cases}` alongside plain intuition are welcome).
3. **Math & Typography Hygiene**: Inspect rendered prose/display math and stylesheets to confirm zero inline math scrollbars/baseline clipping, zero sawtooth/zig-zag left margins or clipped right-hand terms in aligned display equations on desktop or mobile viewports, and interactive widgets staying isolated from serif prose overrides.
4. **SVG Legibility, Light/Dark Contrast & Bit Labels**: Verify desktop, dark-mode, and mobile renders show crisp SVG viewBox scaling, clean arrow/wire alignment, zero label overlap, explicit `Bits hi..lo` labels where bitfields appear, high light/dark contrast, and zero clipped Mermaid `<foreignObject>` nodes.
5. **No Duplicate Section Dividers**: Flag bare `---` horizontal rules immediately preceding `##` headings whenever the rendered theme already draws heading dividers.
