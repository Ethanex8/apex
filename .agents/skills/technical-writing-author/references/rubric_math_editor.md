# Editorial Pacing, Logic & Math Editor Rubric

Activate whenever a document includes headings, equations, derivations, quantitative bounds, or worked numeric traces. Audit every bridge, formula, bound, and inline numeric check inside the primary shard:

## 1. Mathematical & Logical Soundness
1. **Strict Dependency Order**: Flag any step citing an unestablished property, convention, forward corollary, or identity introduced later in the document (checking prior-section boundaries explicitly).
2. **Just-in-Time Prerequisite Refreshers**: Flag non-trivial discrete, modular, bit-slice, calculus, linear-algebra, or physics rules used without a brief 1–2 sentence intuitive refresher, operational boundaries (what holds vs. breaks), and a concrete check.
3. **Simple-to-Derived Ordering**: Flag lists or explanations that place implementation tricks ahead of simpler direct consequences they rely upon.
4. **Strict Causal Entailment & Zero Logic Leaps**: Test every causal connective (*because*, *consequently*, *therefore*, *thus*, *so*) and inequality step; flag any unstated domain (e.g. signed range bounds), omitted integer discreteness, or premise $P$ that leaves conclusion $Q$ unexplained.
5. **Exact Arithmetic & Boundary Verification**: Verify every signed/unsigned bound, congruence, power-of-two identity, rounding direction (floor vs. truncating), and worked numeric calculation for complete accuracy.

## 2. Rule-of-Four Representation Fit & Proof Economy
6. **Symmetric Rule-of-Four Fit**: Flag **mode mismatches** in any direction—tangled verbal `if`/`else` or parenthetical case definitions where concise piecewise `\begin{cases}` or a 1-line equation is cleaner, OR symbolic/algebraic walls where words, concrete numbers, or a visual explain the mechanism more simply.
7. **Proof Economy (Zero Proof Theater)**: Reserve multi-step formal derivations strictly for genuinely non-obvious invariants or surprising hardware equivalences; flag auxiliary lemmas, forced `target(output)` proof ceremonies, or multi-block proofs where an intuitive, visual, numeric, or 2-line algebraic check suffices.
8. **Prose-Equation Alignment & Step Integrity**: When a display equation or derivation *is* warranted, flag intro prose describing operations absent from `$$`, remarks on unseen sub-terms before `$$`, or skipped algebraic steps (such as unexpanded telescoping claims) inside an explicit proof.
9. **Zero Parenthetical Sub-Proofs or Redundant Re-Derivations**: Flag hidden sub-proofs inside parentheses, motivating sentences overloaded with secondary boundary caveats, full parallel re-derivations duplicating an established rule, or separate near-identical symmetric cases that collapse cleanly.

## 3. Editorial Discipline & Clean Notation
10. **Pacing, Proportional Lead-Ins & Formatting**: Verify calm 2–4 sentence bridges matching `<= 8`-word headings, proportional lead-ins across all groups in multi-category tables, Markdown tables over `3+` item prose catalogs, one-sentence-per-line formatting, and zero stiff `"Next we prove..."` announcements.
11. **Clean Notation & Zero Standalone Example Headings**: Verify every symbol is defined before use and flag any standalone `### Example` / `#### Example` heading, exercise, problem set, or `<details>` toggle anywhere in the shard.
