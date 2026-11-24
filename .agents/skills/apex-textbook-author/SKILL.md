---
name: apex-textbook-author
description: Author and revise full-depth (30–60 minute) interactive engineering textbook chapters in systems/<system>/chapters/<NN>_<slug>.md alongside repo code using a mandatory 4-pass pipeline (Blueprint, Multi-Chunk First-Principles Draft, Sharded Deterministic Cold-Reader Audit with Diff Regression Guard, and Interactive Vue Widgets + Code-Sync Verification).
file_names:
    - references/rubric_cold_reader.md
    - references/rubric_math_editor.md
    - references/rubric_macro_critic.md
    - references/rubric_visual_critic.md
    - references/rubric_diff_guardian.md
---
# Apex Multi-Pass Textbook Authoring Skill

Use this skill whenever writing, extending, or upgrading a chapter in `systems/<system>/chapters/<NN>_<slug>.md` mapped from `roadmap.yaml` (`book.parts`).

## Core Philosophy

We write a **publication-grade systems engineering textbook** (*Harris & Harris*, *Crafting Interpreters*, *OSTEP*) alongside tested hardware and robotics code rendered via VitePress (`book/`).

- **Target Reader**: An engineer or aspiring engineer knowing **general programming (`if`/`else`, loops, arrays, functions, structs, byte buffers) plus undergraduate math/physics** with zero hardware/architecture background—never bridge via niche database, distributed-consensus, kernel, or runtime internals.
- **M:1 Step-to-Chapter Growth (`3–6` steps -> 1 cohesive `~45–60 min` chapter)**:
  - **`step 1/K` (Launch)**: Creates `<NN>_<slug>.md` with a `<= 6`-word H1, opening prose (zero metadata banners), inline `#### Exercise` drills, and `## <N>. Problems`.
  - **`step j/K` (Growth)**: Inserts `1–2` focused sections (`~10–20 min`) before `## <N>. Problems` and adds synthesis problems without breaking prior notation.
  - **`bench` Steps**: Append a closing *"Hardware Lab"* verification section (pure procurement steps add a brief fabrication callout only).

---

## Mandatory 4-Pass Authoring Pipeline

### Pass 1: Pedagogical Blueprint & Strict Layering
1. Inventory every constant, helper, public state field, normal path, and error path across the step's source and test files.
2. **Layering, Intrinsic Properties & Abstraction Boundaries**:
   - Group elementary operators coherently in foundational theory, establish intrinsic representation properties early, complete base architectures before custom extensions, defer operation-specific derivations to consumers, and exclude project constants or unbuilt tools from general concepts.
   - Keep higher-layer descriptions strictly at their observable contract—never leak unintroduced lower-layer ports, pins, datapath topologies, or cycle counts.
   - Open comparative sections with a direct plain-English takeaway, keep `###` subsections aligned to headings, unbraid distinct mechanisms, order simplest direct properties before implementation tricks, and open new operations with plain intuition before corner cases.
3. **Concise Headings & Calm Bridges**:
   - Keep H1 (`<= 6` words) and `##`/`###` (`<= 8` words) crisp without `:`, `&`, parentheticals, or backticks, opening each section with a calm 2–4 sentence conceptual bridge.
4. **SVG-First Visuals, Exact Insertion Audits & Focused Transclusions**:
   - Build figures as static or interactive `<svg>` diagrams depicting geometry, wire/signal paths, or aligned lanes (never text-only calculator cards) with one unambiguous title (zero duplicate pill + title stacking), auditing each figure at its insertion line for zero forward symbols.
   - Derive non-obvious bit-manipulation or algorithmic formulas **before** transcluding their code snippet; keep `<!-- book-sync: <spec> -->` + `<<<` slices `<= 25` lines and anchor every code/test link (`#L<start>-L<end>`).

### Pass 2: Uncompressed Multi-Chunk Drafting
1. Draft sequentially with **one sentence per Markdown line** (no `<br>`), starting a fresh paragraph before pivoting from intuition/examples into formal proofs.
2. **Mechanism First & Code-Only Backticks**:
   - State what each new term does before placing `(**expanded name / acronym**)` immediately adjacent (never after an em-dash or `3+` stacked acronyms); tabulate `3+` structured items with proportional lead-in prose across every table category.
   - Reserve backticks strictly for literal code, tokens, constants, CLI flags, and paths—never acronyms, proper nouns, prose numbers/units, or raw TeX; keep boldface `<= 6` words.
3. **Step-by-Step Math, Proof Economy & Scannable Examples**:
   - Refresh prerequisite identities with examples before use, prove rounding directions cleanly, keep motivating sentences single-purpose, and state shared bridges once before parallel lists without prose-math walls, `"Next we prove..."` boilerplate, or forward catalogs.
   - Open proofs with 1–2 plain, low-symbol sentences giving intuitive meaning; pair reusable theorems with operational usage intuition (safe substitutions vs. broken preconditions/inverses).
   - Place inline `#### Exercise <S.K>: <Title>` drills **selectively** only for genuinely new, error-prone math or **symbolic algebraic manipulation** (using fresh inputs distinct from prose examples, widgets, and `Problems`), embedding a compact collapsible terse solution right below each question/sub-part using strictly introduced notation.
   - Pair step-by-step clarity with **proof economy**: choose the shortest transparent valid proof over multi-block symbolic detours, lift dense multi-step numeric worked examples out of prose paragraphs into aligned LaTeX (`<= 624 px`) or SVGs, enforce causal entailment, and spotlight hardware-polymorphism wins.
4. **Responsive Widgets & Math Hygiene**: Isolate `.hw-widget` from `.book-serif-mode`, keep inline MathJax `display: inline; overflow: visible`, label `Bits hi..lo`, escape `\$`, and avoid prose `~` or bare line numbers.

### Pass 3: Deterministic Sharded Clean-Room Audit & Convergence
Run `python3 scripts/build.py` so `docs/CHAPTER_INDEX.md` is fresh, then generate the non-biased sharded review manifest before spawning any `research` subagent (`Model: 'inherit'`, `Workspace: 'inherit'`):
```bash
python3 scripts/build_review_plan.py --chapter <chapter_path> [--base-ref <pre_fix_sha>] [--changed-since <round_r_sha>]
```
- **Execute Every Emitted Task Verbatim**: Never write ad-hoc custom steering prompts. Launch every emitted shard's `Cold-Reader`, `Math & Logic Editor`, `Global Macro & Dependency Critic`, `Visual Pedagogy Critic`, and `Diff & Flow Regression Guardian` using `build_review_plan.py`'s exact prompts.
- **Mandatory Convergence Loop**: Run a full sweep on Round 1 (`--base-ref <pre_fix_sha>`). After resolving Round $r$ tickets, rebuild book + light/dark PNGs and converge fresh clean-room reviewers (`--base-ref <pre_fix_sha> --changed-since <round_r_sha>`) until **zero P0/P1/P2 defects** remain.

### Pass 4: Synthesis Problems & Final Verification Gate
Close with `4–6` synthesis **Problems** (`## <N>. Problems`, `### Problem <K>: <Title>`, `<details><summary>Worked Solution</summary>`), then pass every gate:
```bash
python3 scripts/sync_book.py && python3 scripts/sync_book.py --check
python3 scripts/check_book.py && uv run --with pyyaml python3 scripts/build.py --check
BOOK_BASE=/apex/ npm --prefix book run build
uv run --with playwright python3 scripts/check_visuals.py --screenshot-dir .cache/visual-audit
```
Keep `SKILL.md <= 120` lines, record substantive lessons in `docs/calibration/apex-textbook-author.md`, and sync `.agents/skills/*` via `save_skill` whenever any skill or rubric file changes.