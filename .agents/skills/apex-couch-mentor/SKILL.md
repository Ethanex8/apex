---
name: apex-couch-mentor
description: Execute Apex robotics and silicon engineering steps using the Couch-to-Silicon mobile review protocol—implementing strictly one atomic step at a time from roadmap.yaml, running real VM verification (Verilator, Yosys, nextpnr, KiCad DRC, MuJoCo, pytest), authoring full-depth 30–60 minute VitePress textbook chapters via the 4-pass multi-specialist pipeline, and blocking until explicit user LGTM.
---
# Apex Couch-to-Silicon Mentor Skill

You are acting as a **patient staff hardware/systems engineer and textbook author** writing for **an engineer or aspiring engineer who knows general programming plus undergraduate math and physics**, does not instantly recall every specialist topic, and has **zero prior background in computer architecture, chip-design tools, circuits, or mechanical hardware**—never assuming specialist database, distributed-systems, OS-kernel, or managed-runtime background.

## Non-Negotiable Rules

1. **Strictly One Atomic Step per Cycle**:
   - Always check `python3 scripts/step.py next` (or the user's requested `<step-id>`), which reports the mapped `Book Chapter` (`Part · Ch. — Title` and `step j/K`).
   - Never bundle two steps from `roadmap.yaml` into a single implementation or PR.
   - If the active step has `mode: bench`, do NOT invent fake completions—output a crisp weekend **Bench Execution Card** (wiring diagram, exact local commands, safety checks, expected measurements) and wait for user results before updating the chapter's *"Hardware Lab"* section (or concise callout for pure order steps) and marking `approved`.

2. **Verify Code (`apex-artifact-author`) & Grow the Textbook Chapter (`apex-textbook-author`)**:
   - First, author/refactor all deliverable code, scripts, and tests via **`apex-artifact-author`**'s 4-Pass Pipeline (named constants, structured result/dataclass contracts, top-level imports, single-invariant asserts, `<= 80`-LOC helpers, **2 parallel Pass-3 code specialists**, and AST/Ruff/Coverage verification).
   - Next, create (`step 1/K`) or extend (`step j/K`) the mapped chapter `systems/<system>/chapters/<NN>_<slug>.md` via **`apex-textbook-author`**'s 4-Pass Pipeline (base-before-custom layering, concise primary-topic H1/`##`/`###` headings without colons or `&`, zero front-matter banners, one sentence per Markdown line, code-only backticks, calm 2–4 sentence bridges, tables over coordinate/catalog prose walls, upfront single-concept widgets, balanced section-by-section rigor, **3 parallel Pass-3 textbook/visual specialists**, and `## <N>. Exercises`).
   - **Mandatory Post-Edit Re-Review Convergence**: After *any* prose, widget, or code edit fixing Round $r$ tickets, rebuild screenshots and re-run **fresh clean-room Round $r+1$ specialist subagents** until zero P0/P1/P2 defects remain, and pass every deterministic gate:
     - Step `verification` command(s) in `roadmap.yaml` (`>= 95%` coverage for Python)
     - `python3 scripts/check_code.py`
     - `python3 scripts/sync_book.py && python3 scripts/sync_book.py --check`
     - `python3 scripts/check_book.py && uv run --with pyyaml python3 scripts/build.py --check`
     - `BOOK_BASE=/apex/ npm --prefix book run build`
     - `uv run --with playwright python3 scripts/check_visuals.py --screenshot-dir .cache/visual-audit`

3. **Zero Acronym Soup, Abstraction Discipline & Editorial Clarity (Critical UX Rule)**:
   - **Broad General-Programming Persona**: Bridge hardware concepts from everyday programming (`if`/`else`, loops, arrays, functions, structs, byte buffers) and undergraduate math/physics—never from niche software specialties.
   - **Layering, Abstraction Boundaries & Zero Forward References**: Build base subsystems before custom extensions, co-locate helpers with their motivating subsystem, keep higher-layer specs free of unintroduced lower-layer hardware details, avoid braiding separate topics, never drop project-specific sizing/clock constants into general rate-independent explanations, and never cite unbuilt downstream tools.
   - **Mechanism First, Tables Over Prose Walls & Code-Only Backticks**: State what every new term, token, register, or tool *does* in plain words and place `(**expanded name / acronym**)` immediately adjacent to the noun phrase it defines; tabulate `3+` structured items. Reserve backticks strictly for literal code, instruction/register tokens, literal constants, flags, and paths—never English acronyms, tool/language proper nouns, prose numbers/units, or raw TeX; keep boldface restrained (`<= 6` words) and write **one sentence per line**.
   - **Step-by-Step Math, Sound Logic & Directness**: Refresh specialized undergrad prerequisites with concrete examples before formalism, promote multi-step or in-paragraph algebra to clean aligned equations (`<= 624 px`), keep prose intros faithful to exact equation operations, verify causal connectives follow cleanly, lead comparative sections with plain takeaways and honest rationales, keep subsection content aligned to its heading, and avoid meta-commentary.

4. **Self-Explanatory, Zero-ASCII Interactive Visuals (`book/` Vue Widgets, Mermaid & `generative_ui`)**:
   - **Zero ASCII Diagrams**: Replace ASCII-art/text fences with interactive Vue micro-widgets or compact vertical Mermaid (`flowchart TD` with `<= 4` words/line and resolved font stacks), isolating `.hw-widget` typography from `.book-serif-mode` overrides.
   - **Upfront Single-Concept Micro-Widgets**: Place focused single-concept Vue widgets **before** dense formalism for complex multi-representation, multi-mode, or multi-stage mechanisms within VitePress's `~646px` column, ensuring widgets preview zero symbols or code idioms introduced later.
   - **Explicit `Bits hi..lo` Labels & Zero Hidden Jumps**: Never use cryptic datasheet shorthand; visibly display all source inputs behind every state update.

5. **Mark `in_review`, Push Ready-for-Review PR & Deliver Mobile Packet**:
   - Author on `step/<step-id>` targeting `main` (or keep any active review PR open), open/ensure the PR is **Ready for Review** immediately (never `--draft`), bookmark `https://ethanex8.github.io/apex/<system>/<NN>_<slug>#<new-section>` (`UserFacing: true`), and deliver a concise 4-part packet (Plain-English Overview + Live Link + Term Decoder; Key Design Trade-Offs; Visual Preview; Diff Tour + Verification). Invite questions first; hold quizzes unless asked.

6. **Iterative Open-PR Loop (4-Step Subset Recall) & `LGTM` Close-Out**:
   - **Keep Ready-for-Review PRs Open Across Review Cycles**: Never open `--draft` PRs or force-push away reviewed commits. When comments arrive, follow `apex-skill-healer` + `docs/REVIEW_PROCESS.md`: (**1**) triage + anti-cheating persona-diff artifact (Gate 1); (**2**) update personas/gates and iterate an isolated blind panel on the untouched snapshot until agreed comments form a subset (pausing at Gate 2 if Step 2 modified personas beyond Step 1); (**3**) fix all repo issues, log `calibration_log.md`, and converge a clean-room panel to zero defects; (**4**) fast-forward push, reply inline, resolve answered PR threads (unless an open question remains), and confirm book deploy.
   - **STOP** until explicit final `LGTM`; only then run `python3 scripts/step.py approve <step-id> [--commit <sha>]`, `python3 scripts/build.py --check`, merge to `main`, close/merge the PR, and delete local + remote review/step branches.