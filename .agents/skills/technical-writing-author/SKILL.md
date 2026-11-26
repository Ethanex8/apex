---
name: technical-writing-author
description: Author and revise clear, first-principles technical documentation, design guides, RFCs, and engineering textbook chapters using a 4-pass pipeline (Layering Blueprint, Mechanism-First Draft, Cold-Reader + Diff-Regression Audit, and Visual/Build Verification). Applies across any repository; defer to project-specific authoring skills when present.
file_names:
    - references/rubric_cold_reader.md
    - references/rubric_math_editor.md
    - references/rubric_macro_critic.md
    - references/rubric_visual_critic.md
    - references/rubric_diff_guardian.md
---
# Multi-Pass Technical Writing & Textbook Authoring Skill

Use this skill whenever drafting or revising engineering textbook chapters, architecture guides, design specs, or reference documentation.

## Core Philosophy

Write **publication-grade, reader-respecting prose** (*Harris & Harris*, *Crafting Interpreters*, *OSTEP*) alongside working, verified code.

- **Target Reader**: Write for an engineer or student knowing **general programming (`if`/`else`, loops, arrays, functions, structs, byte buffers) plus undergraduate math/physics** with zero niche domain background—never bridge via niche database, distributed-consensus, kernel, or runtime internals unless that is the topic.
- **Scoped Applicability**: Core clarity, layering, mechanism-first terminology, and diff-regression rules apply to **all** technical docs; math/proof rules activate on derivations/bounds, and visual rules activate on diagrams, Mermaid, or interactive components.

---

## Mandatory 4-Pass Authoring Pipeline

### Pass 1: Pedagogical Blueprint & Strict Layering
1. **Source Inventory**: Inventory every constant, public interface, normal path, and error path across paired code and tests before drafting.
2. **Layering & Abstraction Boundaries**:
   - Order elementary stateless primitives before coupled multi-part mechanisms, establish intrinsic representation properties early, complete base architectures before custom extensions, and exclude repo-specific constants or unbuilt tools from general theory.
   - Describe higher layers strictly at their observable contract without leaking unintroduced lower-layer ports, pins, internal signals, or implementation cycle counts.
   - Open comparative sections with a plain-English takeaway, keep introductory operator overviews free of premature formal bounds, align `###` subsections strictly to headings, and unbraid distinct mechanisms.
3. **Concise Headings & Calm Bridges**:
   - Keep H1 (`<= 6` words) and `##`/`###` (`<= 8` words) crisp without `:`, `&`, parentheticals, backticks, or redundant `---` dividers above `## `, give each distinct conceptual layer its own `###` subsection, and open sections with calm 2–4 sentence bridges.
4. **Diagram-First Visuals & Clean Code Slices**:
   - Place schematic `<svg>` or Mermaid diagrams (never equation cards, one title) right after plain intuition, a concrete trace, and minimal labels—before set notation, dense formal rules, or proofs rather than last—auditing insertion lines for zero premature symbols.
   - Derive non-obvious formulas **before** quoting code, keep embedded slices focused (`<= 25` lines), and anchor file/symbol links cleanly.

### Pass 2: Uncompressed First-Principles Drafting
1. **Direct Openings & Semantic Line Breaks**: Open sections with plain intuition and concrete examples—never negative foils or cold set-notation, quantifier, or general-theorem walls—write **one sentence per Markdown line** (no `<br>`), and break paragraphs before formal derivations.
2. **Mechanism First & Code-Only Backticks**:
   - State what each new term does before placing `(**expanded name / acronym**)` immediately adjacent (never after an em-dash or `3+` stacked acronyms); tabulate `3+` structured items with proportional lead-in prose across every table category.
   - Reserve backticks strictly for literal code, tokens, constants, CLI flags, and paths—never acronyms, proper nouns, prose numbers/units, or raw TeX; keep boldface `<= 6` words.
3. **Proof Economy & Scannable Examples** *(when derivations or bounds appear)*:
   - Refresh prerequisite identities with examples first, open proofs plainly, and display step-by-step aligned `$$` summations (showing index shifts and cancellation rather than prose telescoping shortcuts) while avoiding multi-block bloat or `"Next we prove..."` boilerplate.
   - Place visible inline `#### Example <S.K>: <Title>` blocks **selectively** for non-trivial algebra, boundary traps, or counterexamples—never homework problem sets or `<details>` toggles.
4. **Math & Visual Hygiene**: Keep inline math unclipped without scrollbars, label bit ranges explicitly (`Bits hi..lo`), escape `\$`, and avoid prose `~` or bare line numbers.

### Pass 3: Clean-Room Audit & Diff-Regression Convergence
If the repository provides a deterministic review planner (e.g. `scripts/build_review_plan.py`), run it and execute every emitted task verbatim.
Otherwise, isolate `research` subagents with the bundled `references/` rubrics: `rubric_cold_reader.md` and `rubric_macro_critic.md` on all docs, `rubric_math_editor.md` on math/proofs, `rubric_visual_critic.md` on visuals/widgets, and `rubric_diff_guardian.md` against the pre-edit diff.
- **Convergence Loop**: Fix all P0/P1/P2 findings, rebuild docs/visuals, and re-audit touched scopes with fresh clean-room reviewers until zero defects remain.

### Pass 4: Build, Link & Visual Verification Gate
Run all repository doc/book/link checks (and headless visual light/dark checks if the repo renders web pages or interactive widgets) and confirm clean passes.