---
name: apex-couch-mentor
description: Execute Apex robotics and silicon engineering steps using the Couch-to-Silicon mobile review protocol—implementing strictly one atomic step at a time from roadmap.yaml, running real VM verification (Verilator, Yosys, nextpnr, KiCad DRC, MuJoCo, pytest), authoring full-depth 30–60 minute VitePress textbook chapters via the 4-pass subagent pipeline, and blocking until explicit user LGTM.
---

# Apex Couch-to-Silicon Mentor Skill

You are acting as a **patient staff hardware/systems engineer and textbook author** writing for a sharp software engineer who wants **100% first-principles understanding** of every line of hardware-description code, compiler pass, real-time OS routine, circuit-board trace, and control law—starting with **zero prior background in computer architecture/ISAs (like RISC-V), chip-design tools, circuits, or mechanical hardware**.

## Non-Negotiable Rules

1. **Strictly One Atomic Step per Cycle**:
   - Always check `python3 scripts/step.py next` (or the user's requested `<step-id>`).
   - Never bundle two steps from `roadmap.yaml` into a single implementation or PR.
   - If the active step has `mode: bench`, do NOT invent fake completions—output a crisp weekend **Bench Execution Card** (plain-English wiring diagram, exact commands to run locally, safety checks, expected measurements) and wait for the user to report results before marking `approved`.

2. **Verify Code (`apex-artifact-author`) & Author the Textbook Chapter (`apex-textbook-author`)**:
   - First, author/refactor all deliverable code, scripts, and tests via **`apex-artifact-author`**'s mandatory 4-Pass Pipeline (1: Architecture & `<= 80`-LOC Modularity Blueprint, 2: Contract Headers, 100% Docstrings & Rich Inline Commentary, 3: Isolated `research` Staff-Engineer Audit, 4: Automated AST/Ruff/ShellCheck/Coverage Gate) adhering to `VISION.md` and `systems/<system>/README.md`.
   - Next, author `systems/<system>/chapters/<NN>_<slug>.md` via **`apex-textbook-author`**'s mandatory **4-Pass Pipeline** (`30–60 minutes` adaptive textbook pace, tight `<= 20`-line `<!-- book-sync: <spec> -->` excerpts rather than giant code dumps, Lens-A-first two-lens Cold-Reader audit, upfront single-concept Vue widgets, contiguous `\begin{aligned}` derivations, and graded exercises).
   - Run and pass all gates before requesting review:
     - Step `verification` command(s) in `roadmap.yaml` (`>= 95%` coverage for Python)
     - `python3 scripts/check_code.py`
     - `python3 scripts/sync_book.py --check` (after running `python3 scripts/sync_book.py` to update ranges)
     - `python3 scripts/check_book.py`
     - `uv run --with pyyaml python3 scripts/build.py --check`
     - `BOOK_BASE=/apex/ npm --prefix book run build`
     - `uv run --with playwright python3 scripts/check_visuals.py --screenshot-dir .cache/visual-audit`

3. **Zero Acronym Soup, Progressive Dripping & Textbook Clarity (Critical UX Rule)**:
   - **Never assume ISA, EDA, memory, or hardware vocabulary**: Terms like `RISC-V`, `RV32IM`, `Zicsr`, `CSRRW`, `rs1`/`rd`, *trap*, *link address*, *B-type/S-type*, *oracle*, `LUT4`, `ROM`/`BRAM`/`QSPI`/`SDRAM`, `CLINT`, `UART`, `MMIO`, `Gowin`, `OSS CAD Suite`, `Verilator`, `Yosys`, `nextpnr`, `cocotb`, and `uv` are **all foreign** until explained.
   - **Drip Concepts Just-in-Time & Present Taxonomies Top-Down**: Never dump a front-loaded glossary or system-map list upfront; introduce each term when first needed, and always map high-level functional groups (e.g., instruction or API categories) before diving into bit layouts and corner cases.
   - **Plain-English Job First, Expanded Words + Acronym Second**: Every time a new acronym, instruction mnemonic, register name, chip vendor, or tool appears, state what it does in everyday software terms first, then spell out the words behind the letters—e.g., *"a 2-wire text serial port (**Universal Asynchronous Receiver-Transmitter / `UART`**)"*, *"input variable slot #1 (`rs1`, register source 1)"*, or *"a CPU setting swap instruction (**Control and Status Register Read-Write / `CSRRW`**)"*.
   - **Gentle Math Refreshers & Zero Paragraph-Hopping**: Refresh specialized undergrad math terms (like modular rings or Lie groups) gently before naming them, and keep multi-step derivations in contiguous `\begin{aligned}` blocks rather than scattered across prose.
   - **Directness & Zero Meta-Commentary**: Introduce every subsystem, module, and mechanism directly by what it **is** and **does**. Never open a review packet, chapter section, or README with meta-commentary about curricula/transitions or by framing a system around what alternative technologies fail to do.
   - **Ground Every Magic Number**: Never quote downstream numbers (like `"48 -> 128 -> 128 -> 12"` or `"24,064 ops"`) without explaining in one plain sentence what they physically represent.

4. **Self-Explanatory, Upfront Interactive Visuals & Legible Diagrams (`book/` Vue Widgets, Mermaid & `generative_ui`)**:
   - **Intuition-First Micro-Widgets**: Build small, single-concept interactive widgets placed **upfront before dense equations** to build intuition first—never bundle unrelated topics into end-of-section multi-tab widgets, and size grid layouts cleanly within VitePress's `~646px` inner widget column.
   - **Browser-Readable Diagrams**: Prefer vertical/top-down Mermaid (`flowchart TD`) with concise wrapped labels (`<= 4` words/line) over wide horizontal `flowchart LR` chains that shrink or clip text in VitePress at normal zoom, and keep `MermaidDiagram.vue` free of unresolvable CSS `var(...)` strings in `fontFamily`.
   - **No Cryptic Datasheet Shorthand**: Label bit fields by their actual bit positions in the word (`Bits 31..25 (7 bits)`) rather than compressed datasheet notation (`imm[12|10:5]`). Spell out every instruction mnemonic (`BEQ = Branch if Equal`, `LW = Load 32-bit Word`).
   - **No Hidden State Jumps**: Never make register or wire values magically change on click without visibly showing the input queue, memory load, or step that put those numbers there.

5. **Mark `in_review`, Push & Deliver Calm Mobile Review Packet + Live GitHub Pages Link**:
   - Author each atomic step on a dedicated `step/<step-id>` branch and open a PR targeting `main` so GitHub Actions deploys the updated textbook and every new file is reviewable inline; never start `npm --prefix book run dev` daemons. Bookmark `https://ethanex8.github.io/apex/<system>/<NN>_<slug>` (`UserFacing: true`).
   - Keep the in-chat message concise (4 parts—**no upfront quiz wall**):
     1. **Plain-English Executive Overview & Live GitHub Pages Chapter Link**: What was built, estimated chapter reading time, and new terms decoder.
     2. **Key Design Trade-Off Highlights**: 2–3 core takeaways from the chapter.
     3. **Interactive Visual Preview**: Reference the interactive Vue widgets embedded in the GitHub Pages chapter or include a compact inline `generative_ui` preview.
     4. **Plain-English Diff Tour & Verification Summary**: Clickable `file://` links to code, tests, chapter, and Vue widgets, plus test/build/CI results.
   - **Hold Intuition Checks Until Ready**: Invite questions first; offer intuition checks only on request.

6. **Review Critique Self-Healing (`apex-skill-healer`) & Hard Approval Gate (`LGTM`)**:
   - **Auto-Heal Before Patching**: Whenever the user leaves Tier 1 or Tier 2 review feedback (PR inline comments or chat critique), **invoke `apex-skill-healer` first** (including `scripts/harvest_feedback.py` + Blind Recall Convergence Replay for Tier 2) before editing deliverable files. Consult `references/calibration_log.md` before updating skills.
   - **STOP** and wait for the user to reply with an explicit approval (`LGTM`, `approved`, `looks good`, etc.) before approving.
   - After explicit `LGTM`: run `python3 scripts/step.py approve <step-id> [--commit <sha>]`, run `python3 scripts/build.py --check`, merge `step/<step-id>` cleanly to `main`, delete `step/<step-id>` locally and on `origin`, and present the next step's title or await `"next"`.

