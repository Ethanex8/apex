# Diff & Flow Regression Guardian Rubric

Inspect strictly the pre-generated unified diff patch between the pre-edit baseline and the current tree to prevent "fix-induced regressions" where literal compliance with a new rule degrades overall readability:

## 1. Prose-Flow & Boilerplate Regressions
1. **No Flow Degradation vs. Baseline**: Compare every rewritten paragraph side-by-side against its removed `-` lines; flag any `+` revision that reads more stiffly, robotically, or abruptly than the original text.
2. **No Prose-Math Wall Inflation**: Flag additions that pack multi-clause symbolic expressions, interval notation walls, or nested caveats into consecutive prose sentences where a crisp plain sentence or aligned display equation would flow cleanly.
3. **Zero Mechanical Rule-Compliance Boilerplate**: Flag edits that paste identical justifying phrases, theorem citations, or `Corollary X` labels onto multiple parallel list items instead of stating a shared bridge once up front.
4. **No Stiff Announcements or Section Catalogs**: Flag newly introduced `"Next we prove..."`, `"Below we show..."`, or multi-section forward roadmaps (`Section X, Section Y...`) injected just to satisfy proof-lead-in checks.

## 2. Boundary & Reordering Side Effects
5. **Cross-Section Move Verification**: Whenever theorems, lemmas, or definitions move earlier or later, verify all dependent expressions, symbols, `#### Example` blocks, and embedded diagrams/widgets in between remain strictly valid in their new dependency order.
6. **No Silent Content Deletion**: Verify style/flow tightenings preserve all genuine quantitative invariants, corner-case proofs, code/test symbol anchors, and engineering tradeoff insights.
