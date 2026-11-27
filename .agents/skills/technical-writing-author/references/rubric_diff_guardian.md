# Diff & Flow Regression Guardian Rubric

Inspect strictly the pre-generated unified diff patch between the pre-edit baseline and the current tree to prevent "fix-induced regressions" where literal compliance with a new rule degrades overall readability:

## 1. Prose-Flow & Boilerplate Regressions
1. **No Flow Degradation vs. Baseline**: Compare every rewritten paragraph side-by-side against its removed `-` lines; flag any `+` revision that reads more stiffly, robotically, or abruptly than the original text.
2. **No Single-Mode Wall Inflation**: Flag additions that bloat prose-math walls or formal proof theater where a cleaner Rule-of-Four representation (concise algebra, visual, concrete trace, or table) flows better.
3. **Zero Mechanical Rule-Compliance Boilerplate**: Flag edits that paste identical justifying phrases, theorem citations, or `Corollary X` labels onto multiple parallel list items instead of stating a shared bridge once up front.
4. **No Stiff Announcements or Section Catalogs**: Flag newly introduced `"Next we prove..."`, `"Below we show..."`, or multi-section forward roadmaps (`Section X, Section Y...`) injected just to satisfy lead-in checks.

## 2. Boundary & Reordering Side Effects
5. **Cross-Section Move Verification**: Whenever definitions, equations, or mechanisms move earlier or later, verify all dependent expressions, symbols, and embedded diagrams/widgets in between remain strictly valid in their new dependency order.
6. **Preserve Invariants & Contracts (Allow Simplifying Proof Theater)**: Verify simplifications of verbose proofs into clearer Rule-of-Four explanations preserve all genuine system invariants, exact bounds, edge-case contracts, code/test symbol anchors, and engineering tradeoff insights.
