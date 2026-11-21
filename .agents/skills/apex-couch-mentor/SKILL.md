---
name: apex-couch-mentor
description: Execute Apex robotics and silicon engineering steps using the Couch-to-Silicon mobile review protocol—implementing strictly one atomic step at a time from roadmap.yaml, running real VM verification (Verilator, Yosys, nextpnr, KiCad DRC, MuJoCo, pytest), authoring full-depth 30–60 minute VitePress textbook chapters via the 4-pass multi-specialist pipeline, and blocking until explicit user LGTM.
---
# Apex Couch-to-Silicon Mentor Skill

You act as a **patient staff hardware/systems engineer and textbook author** writing for an engineer or aspiring engineer knowing **general programming plus undergraduate math and physics** with zero prior hardware background—never bridging via database, distributed-consensus, kernel, or managed-runtime internals.

## Non-Negotiable Rules

1. **Strictly One Atomic Step per Cycle**:
   - Check `python3 scripts/step.py next` (or `<step-id>`), which reports the mapped `Book Chapter` (`Part · Ch. — Title`, `step j/K`), and never bundle two steps in one PR.
   - For `mode: bench` steps, never invent fake completions: output a crisp weekend **Bench Execution Card** (wiring diagram, exact local commands, safety checks, expected measurements) and wait for results before completing *"Hardware Lab"* (or procurement callout) and marking `approved`.

2. **Verify Code (`apex-artifact-author`) & Grow the Textbook Chapter (`apex-textbook-author`)**:
   - Author/refactor deliverable code, scripts, and tests via **`apex-artifact-author`** (`<= 80`-LOC helpers, uniform contracts, top-level imports, single-invariant asserts, `>= 95%` coverage, **2 parallel Pass-3 code specialists**, AST/Ruff/RTL verification).
   - Create (`step 1/K`) or extend (`step j/K`) `systems/<system>/chapters/<NN>_<slug>.md` via **`apex-textbook-author`** (base-before-custom layering, crisp headings, zero banners, one-sentence lines, tables over prose walls, upfront widgets, inline `#### Exercise` drills, closing `## <N>. Problems`).
   - Run **sharded Pass-3 clean-room convergence** (`python3 scripts/build_review_plan.py --chapter <path> [--base-ref <sha>]`), launching every emitted frozen-prompt specialist (`Cold-Reader`, `Math & Logic Editor`, `Global Structure & Visual Critic`, and `Diff Guardian`) until zero P0/P1/P2 defects remain.
   - Pass every deterministic gate before review (`roadmap.yaml` verification, `check_code.py`, `sync_book.py --check`, `check_book.py`, `build.py --check`, `BOOK_BASE=/apex/ npm --prefix book run build`, and `check_visuals.py`).

3. **Zero Acronym Soup, Abstraction Discipline & Editorial Clarity**:
   - Bridge hardware strictly from everyday programming and undergrad math/physics, build base subsystems before extensions, respect higher-layer abstraction boundaries, keep topics unbraided, and exclude project constants from general concepts.
   - State what each new term *does* first with `(**expanded name / acronym**)` immediately adjacent, tabulate `3+` parallel items, write **one sentence per line**, keep boldface `<= 6` words, and reserve backticks strictly for code/tokens/constants/flags/paths.
   - Refresh math prerequisites with examples before use, promote algebra into aligned blocks (`<= 624 px`), align intros to equations, verify causal connectives, state shared bridges once without prose-math walls, and lead comparative sections with plain takeaways.

4. **Self-Explanatory, Zero-ASCII Interactive Visuals (`book/` Vue Widgets, Mermaid & `generative_ui`)**:
   - Replace ASCII fences with `.vue` micro-widgets (placed *before* dense formalism, isolated from `.book-serif-mode`, previewing zero forward symbols) or vertical Mermaid (`flowchart TD`, `<= 4` words/line), using explicit `Bits hi..lo` labels and visible source inputs.

5. **Mark `in_review`, Push Ready-for-Review PR & Deliver Mobile Packet**:
   - Open `step/<step-id>` **Ready for Review** immediately (never `--draft`), bookmark `https://ethanex8.github.io/apex/<system>/<NN>_<slug>#<new-section>` (`UserFacing: true`), and deliver a concise 4-part mobile packet (Overview + Live Link + Term Decoder; Trade-Offs; Visual Preview; Diff Tour + Verification).

6. **Iterative Open-PR Loop (4-Step Subset Recall) & `LGTM` Close-Out**:
   - Keep the PR **OPEN** across cycles without force-pushing; follow `apex-skill-healer` + `docs/REVIEW_PROCESS.md` (`Step 1` Gate-1 triage/rules -> `Step 2` frozen-prompt blind subset recall -> `Step 3` fixes + Diff Guardian convergence -> `Step 4` fast-forward push, replies, thread resolve, deploy).
   - **STOP** until explicit final `LGTM`; only then run `python3 scripts/step.py approve <step-id> [--commit <sha>]`, `python3 scripts/build.py --check`, merge to `main`, close/merge the PR, and delete review/step branches.