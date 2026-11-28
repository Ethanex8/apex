# Editorial Pacing, Logic & Math Editor Rubric

Activate whenever a document includes headings, equations, derivations, quantitative bounds, or worked numeric traces. Audit every bridge, formula, bound, and inline numeric check inside the primary shard:

## 1. Mathematical & Logical Soundness
1. **Strict Dependency Order**: Flag any step citing an unestablished property, convention, forward corollary, or identity introduced later in the document (checking prior-section boundaries explicitly).
2. **Just-in-Time Prerequisite Refreshers**: Flag non-trivial discrete, modular, algebraic, calculus, linear-algebra, or physics rules used without a brief 1–2 sentence intuitive refresher, operational boundaries (what holds vs. breaks), and a concrete check.
3. **Simple-to-Derived Ordering**: Flag lists or explanations that place implementation tricks ahead of simpler direct consequences they rely upon.
4. **Strict Causal Entailment & Zero Logic Leaps**: Test every causal connective (*because*, *therefore*, *thus*, *so*), inequality step, and concluding claim on examples or derivations; flag any unstated domain, omitted discreteness condition, or leap from one concrete calculation to an unproven general property.
5. **Exact Arithmetic & Boundary Verification**: Verify every domain bound, equivalence, identity, rounding convention, and worked numeric calculation for complete accuracy.

## 2. Rule-of-Four Representation Fit & Proof Economy
6. **Symmetric Rule-of-Four Fit**: Flag **mode mismatches** in any direction—tangled verbal `if`/`else` cases where concise `\begin{cases}` fits, algebraic walls where words/numbers/visuals clarify better, or parallel labeled numeric comparisons forced into two-column `\begin{aligned}` blocks that zig-zag on the left margin or clip narrow screens (tabulate cleanly instead).
7. **Proof Economy (Zero Proof Theater)**: Reserve multi-step formal derivations strictly for genuinely non-obvious invariants or surprising structural equivalences; flag auxiliary lemmas, forced proof ceremonies, or multi-block proofs where an intuitive, visual, numeric, or 2-line algebraic check suffices.
8. **Prose-Equation Alignment & Interleaving**: When derivations combine two or more substitutions or multi-equality steps, interleave one concise sentence per move ahead of each equation rather than front-loading dense prose summaries before multi-step or aligned `$$` blocks (keep single-move identities compact); flag unseen sub-terms or skipped steps.
9. **Zero Parenthetical Sub-Proofs or Redundant Re-Derivations**: Flag hidden sub-proofs inside parentheses, motivating sentences overloaded with secondary boundary caveats, full parallel re-derivations duplicating an established rule, or separate near-identical symmetric cases that collapse cleanly.

## 3. Editorial Discipline & Clean Notation
10. **Pacing, Proportional Lead-Ins & Formatting**: Verify calm 2–4 sentence bridges matching `<= 8`-word headings, proportional lead-ins across all groups in multi-category tables, Markdown tables over `3+` item prose catalogs, one-sentence-per-line formatting, and zero stiff `"Next we prove..."` announcements.
11. **Clean Notation & Zero Standalone Example Headings**: Verify every symbol is defined before use and flag any standalone `### Example` / `#### Example` heading, exercise, problem set, or `<details>` toggle anywhere in the shard.
