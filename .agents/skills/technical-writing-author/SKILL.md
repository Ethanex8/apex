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

Write **publication-grade, reader-respecting prose** (*Feynman Lectures*, *The Art of Electronics*, *Harris & Harris*, *Crafting Interpreters*, *OSTEP*) alongside working, verified code.

- **Guiding North Star (Rule of Four)**: Treat **Words** (causal mechanism), **Visuals** (spatial structure), **Numbers** (concrete grounding/boundaries), and **Algebra** (concise general rules) as four equal representations, each with pros and cons—pick whichever mode(s) maximize clarity per unit complexity.
- **Universal First-Principles Reader**: Write for anyone with **general programming (`if`/`else`, loops, arrays, functions, structs, byte buffers) and foundational STEM literacy**—zero assumed domain specialization, zero niche software internals (databases, consensus, kernels, runtimes), and zero assumed instant theorem recall.
- **Scoped Applicability**: Core Rule-of-Four clarity, layering, mechanism-first terminology, and diff-regression rules apply to **all** technical docs; quantitative/math rules activate on equations, bounds, or derivations, and visual rules activate on diagrams, Mermaid, or interactive components.

---

## Mandatory 4-Pass Authoring Pipeline

### Pass 1: Pedagogical Blueprint & Strict Layering
1. **Source Inventory**: Inventory every constant, public interface, normal path, and error path across paired code and tests before drafting.
2. **Layering & Abstraction Boundaries**:
   - Order elementary stateless primitives before coupled multi-part mechanisms, establish intrinsic representation properties early, complete base architectures before custom extensions, and exclude repo-specific constants or unbuilt tools from general theory.
   - Describe higher layers strictly at their observable contract without leaking unintroduced lower-layer ports, pins, internal signals, or implementation cycle counts.
   - Open comparative sections with a plain-English takeaway, keep introductory overviews free of premature formal bounds, align `###` subsections strictly to headings, and unbraid distinct mechanisms.
3. **Concise Headings & Calm Bridges**:
   - Keep H1 (`<= 6` words) and `##`/`###` (`<= 8` words) crisp without `:`, `&`, parentheticals, backticks, or redundant `---` dividers above `## `, give each distinct conceptual layer its own `###` subsection, and open sections with calm 2–4 sentence bridges.
4. **Contiguous Visuals & Motivated Code Slices**:
   - Pair schematic `<svg>` or Mermaid diagrams (never equation cards, one title) contiguously with the mechanism they clarify—never buried after proof walls—with zero premature symbols.
   - Explain each mechanism clearly using the right Rule-of-Four mix **before** quoting code, keep embedded slices focused (`<= 25` lines), and anchor file/symbol links cleanly.

### Pass 2: First-Principles Rule-of-Four Drafting
1. **Feynman Openings & Semantic Line Breaks**: Open sections directly with plain mechanistic intuition (showing why naive models break when relevant)—never negative foils or cold, unmotivated theorem/set-notation walls—write **one sentence per Markdown line** (no `<br>`), and break paragraphs cleanly around visuals and equations.
2. **Mechanism First & Code-Only Backticks**:
   - State what each new term does before placing `(**expanded name / acronym**)` immediately adjacent (never after an em-dash or `3+` stacked acronyms); tabulate `3+` structured items with proportional lead-in prose across every table category.
   - Reserve backticks strictly for literal code, tokens, constants, CLI flags, and paths—never acronyms, proper nouns, prose numbers/units, or raw TeX; keep boldface `<= 6` words.
3. **Rule-of-Four Fit, Refreshers & Zero Logic Leaps**:
   - Refresh foundational math/physics with brief 1–2 sentence intuitive anchors right before use, choose whichever of Words, Visuals, Numbers, or Algebra is cleanest (e.g. `\begin{cases}` over tangled prose; concrete traces over proof theater), and state every domain and boundary explicitly.
   - Reserve multi-step formal proofs strictly for genuinely non-obvious invariants or surprising hardware collapses; when writing an explicit proof, show key steps cleanly without `"Next we prove..."` boilerplate or prose-telescoping shortcuts.
4. **Woven Examples & Visual Hygiene**: Weave concrete examples naturally inside section explanations—never standalone `### Example`/`#### Example` headings, homework drills, or `<details>` toggles—keep inline math unclipped, label bit ranges `Bits hi..lo`, escape `\$`, and avoid prose `~` or bare line numbers.

### Pass 3: Clean-Room Audit & Diff-Regression Convergence
If the repository provides a deterministic review planner (e.g. `scripts/build_review_plan.py`), run it and execute every emitted task verbatim.
Otherwise, isolate `research` subagents with the bundled `references/` rubrics: `rubric_cold_reader.md` and `rubric_macro_critic.md` on all docs, `rubric_math_editor.md` on math/proofs, `rubric_visual_critic.md` on visuals/widgets, and `rubric_diff_guardian.md` against the pre-edit diff.
- **Convergence Loop**: Fix all P0/P1/P2 findings, rebuild docs/visuals, and re-audit touched scopes with fresh clean-room reviewers until zero defects remain.

### Pass 4: Build, Link & Visual Verification Gate
Run all repository doc/book/link checks (and headless visual light/dark checks if the repo renders web pages or interactive widgets) and confirm clean passes.