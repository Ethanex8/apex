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
   - Group related elementary operators coherently in foundational theory before downstream sections scatter them, establish intrinsic representation properties early, complete core architectures before custom extensions, defer operation-specific derivations to consumers, and keep project constants or unbuilt tools out of general principles.
   - Keep higher-layer descriptions strictly at their observable contract—never leak unintroduced lower-layer ports, control pins, or unmotivated microarchitectural circuit topologies/cycle counts.
   - Open comparative sections with a direct plain-English takeaway and justify choices honestly without unmotivated claims about avoiding standard constructs (`if`/`else`).
   - Keep `###` subsections aligned to headings, unbraid distinct mechanisms into separate items/subsections, order simplest direct consequences before implementation tricks, and open new operations with plain-English intuition before corner cases.
3. **Concise Headings & Calm Bridges**:
   - Keep H1 (`<= 6` words) and `##`/`###` (`<= 8` words) crisp without `:`, `&`, parentheticals, or backticks, opening each section with a calm 2–4 sentence conceptual bridge.
4. **Upfront Visuals, Exact Insertion Audits & Focused Transclusions**:
   - Replace raw ASCII fences with single-concept `.vue` widgets right where geometric metaphors first appear (zero meta-pedagogical filler badges) or compact vertical Mermaid (`flowchart TD`), auditing each widget at its exact insertion line for zero forward symbols.
   - Derive non-obvious bit-manipulation or algorithmic formulas **before** transcluding their code snippet; keep `<!-- book-sync: <spec> -->` + `<<<` slices `<= 25` lines and anchor every code/test link (`#L<start>-L<end>`).

### Pass 2: Uncompressed Multi-Chunk Drafting
1. Draft sequentially with **one sentence per Markdown line** (no `<br>`), starting a fresh paragraph before pivoting from intuition/examples into formal proofs.
2. **Mechanism First & Code-Only Backticks**:
   - State what each new term does before placing `(**expanded name / acronym**)` immediately adjacent (never after an em-dash clause, and never stacking `3+` acronyms); tabulate `3+` structured coordinates, opcodes, or maps, balancing lead-in prose proportionally across all table groups.
   - Reserve backticks strictly for literal code, tokens, constants, CLI flags, and paths—never acronyms, proper nouns, prose numbers/units, or raw TeX; keep boldface `<= 6` words.
3. **Step-by-Step Math, Sound Logic & Prose Hygiene**:
   - Refresh prerequisite identities with examples before use, prove rounding directions cleanly, keep motivating sentences single-purpose, and state shared bridges once before parallel lists without prose-math walls, `"Next we prove..."` boilerplate, or forward catalogs.
   - Open proofs with 1–2 plain, low-symbol sentences giving intuitive meaning; pair reusable theorems with operational usage intuition (safe substitutions vs. broken preconditions/inverses).
   - Place inline `#### Exercise <S.K>: <Title>` drills **selectively** only for genuinely new, error-prone math or **symbolic algebraic manipulation** (using fresh inputs distinct from prose examples, widgets, and `Problems`), embedding a compact collapsible terse solution right below each question/sub-part using strictly introduced notation.
   - Promote multi-step or in-paragraph algebra into compact aligned blocks (`<= 624 px`), keep equation intros faithful to displayed symbols below, enforce strict causal entailment, spotlight hardware-polymorphism wins, and state theorem purposes before preconditions without commenting on unseen sub-terms.
4. **Responsive Widgets & Math Hygiene**: Isolate `.hw-widget` from `.book-serif-mode`, keep inline MathJax `display: inline; overflow: visible`, label `Bits hi..lo`, escape `\$`, and avoid prose `~` or bare line numbers.

### Pass 3: Deterministic Sharded Clean-Room Audit & Convergence
Generate the exact non-biased sharded review manifest before spawning any `research` subagent (`Model: 'inherit'`, `Workspace: 'inherit'`):
```bash
python3 scripts/build_review_plan.py --chapter <chapter_path> [--base-ref <pre_fix_sha>]
```
- **Execute Every Emitted Task Verbatim**: Never write ad-hoc custom steering prompts. Launch each shard's `Cold-Reader` (`rubric_cold_reader.md`) and `Math & Logic Editor` (`rubric_math_editor.md`), the chapter's `Global Macro & Dependency Critic` (`rubric_macro_critic.md`) and `Visual Pedagogy Critic` (`rubric_visual_critic.md`), plus the `Diff & Flow Regression Guardian` (`rubric_diff_guardian.md`) using `build_review_plan.py`'s exact prompts.
- **Mandatory Convergence Loop**: After any edit resolving Round $r$ tickets, rebuild screenshots, re-run `build_review_plan.py --base-ref <pre_fix_sha>`, and iterate fresh clean-room rounds until all shards, global checks, and the Diff Guardian report **zero P0/P1/P2 defects**.

### Pass 4: Synthesis Problems & Final Verification Gate
Close with `4–6` synthesis **Problems** (`## <N>. Problems`, `### Problem <K>: <Title>`, `<details><summary>Worked Solution</summary>`), then pass every gate:
```bash
python3 scripts/sync_book.py && python3 scripts/sync_book.py --check
python3 scripts/check_book.py && uv run --with pyyaml python3 scripts/build.py --check
BOOK_BASE=/apex/ npm --prefix book run build
uv run --with playwright python3 scripts/check_visuals.py --screenshot-dir .cache/visual-audit
```
Keep `SKILL.md <= 120` lines, record retrospective patterns in `references/calibration_log.md`, and sync skills via `save_skill`.