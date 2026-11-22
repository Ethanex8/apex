# Editorial Pacing, Logic & Math Editor Rubric

Audit every heading, subsection bridge, equation intro, aligned proof block, numeric example, and Exercise/Problem solution inside your primary shard (cross-checking the **Prior-Section Ledger** and **overlap windows**):

## 1. Mathematical & Logical Soundness
1. **Strict Lemma Dependency Order**: Flag any step citing an unproved property, forward corollary, or identity derived later in the shard (checking Prior-Section Ledger boundaries explicitly).
2. **Prerequisite Refreshers & Operational Intuition**: Flag non-trivial discrete, modular, bit-slice, or physics rules used without an intuitive refresher, usage boundaries (what substitutions hold vs. break), and a concrete example.
3. **Simple-to-Derived Theorem Ordering**: Flag lists or derivations that place circuit-implementation tricks ahead of simpler direct consequences they rely upon.
4. **Strict Causal Entailment**: Test every causal connective (*because*, *consequently*, *therefore*, *thus*, *so*); flag any link where premise $P$ leaves conclusion $Q$'s mechanism unproved.
5. **Exact Arithmetic & Boundary Proofs**: Verify every signed/unsigned bound, congruence, power-of-two identity, rounding direction (floor vs. truncating), empty-sum or $N = 1$ corner case, and Exercise/Problem calculation.

## 2. Equations & Dual-Interpretation Derivations
6. **Prose-to-Equation Action Alignment**: Flag intro sentences before `$$` that describe operations absent from the displayed symbols below, or dense >40-word prose walls preceding an equation.
7. **Post-Equation Sub-Term Remarks**: Flag prose commenting on unseen equation sub-terms, indices, or exponents before `$$` appears, or stating integrality/parity preconditions without naming the theorem step needing them.
8. **Step-by-Step Display Algebra**: Flag in-paragraph multi-substitution algebra or collapsed `=` chains skipping non-trivial splits, bound substitutions, or factoring steps (keep display width `<= 624 px`).
9. **Justified Output-to-Target Bridges**: Flag shared-hardware proofs argued in prose instead of an aligned `target(output)` derivation down through circuit semantics with concise right-hand reasons; ensure shared bridges appear once before parallel lists.
10. **Parenthetical Sub-Proofs & Redundant Proofs**: Flag hidden sub-proofs or unexplained examples inside parentheses, motivating sentences overloaded with secondary boundary caveats, or full parallel re-derivations duplicating established congruence.

## 3. Editorial Discipline & Exercise Conciseness
11. **Pacing, Style & Proportional Lead-Ins**: Verify calm 2–4 sentence bridges matching `<= 8`-word headings, proportional lead-ins across all groups in multi-category tables, Markdown tables over `3+` item prose catalogs, one-sentence-per-line formatting, and zero stiff `"Next we prove..."` announcements.
12. **Per-Question Terse Solutions & Clean Notation**: Verify every `#### Exercise` question or sub-part has its own adjacent collapsible terse algebraic reveal using strictly functions and notation already defined in the chapter (never undefined symbols in an answer key).
