---
name: apex-textbook-author
description: Author and revise full-depth (30–60 minute) interactive engineering textbook chapters in systems/<system>/chapters/<NN>_<slug>.md alongside repo code using a mandatory 4-pass pipeline (Blueprint, Multi-Chunk First-Principles Draft, 3-Specialist Parallel Cold-Reader Audit with Re-Review Convergence, and Interactive Vue Widgets + Code-Sync Verification).
---

# Apex Multi-Pass Textbook Authoring Skill

Use this skill whenever writing, extending, or upgrading a chapter in `systems/<system>/chapters/<NN>_<slug>.md` mapped from `roadmap.yaml` (`book.parts`).

## Core Philosophy

We are writing an **8-part, 34-chapter publication-grade systems engineering textbook** (*Harris & Harris*, *Crafting Interpreters*, *xv6*, *OSTEP*) alongside tested silicon, firmware, circuit-board, and robotics code rendered via VitePress (`book/`).

- **Target Reader**: Mathematically strong software/systems engineer with **zero prior background** in computer architecture (`RISC-V`), RTL/FPGA toolchains, electrical circuits, or mechanical shop jargon.
- **M:1 Step-to-Chapter Growth (`3–6` steps -> 1 cohesive `~45–60 min` chapter)**:
  - **`step 1/K` (Chapter Launch)**: Creates `01_...md` with the opening narrative arc, foundational sections (`~10–20 min`), and `## Graded Engineering Exercises`.
  - **`step j/K` (Growth)**: Appends `1–2` focused sections (`~10–20 min`) **before** `## Graded Engineering Exercises`, adds anchored exercises, reuses prior notation, and adds widgets only where a new physical/algorithmic model helps.
  - **`bench` Steps**: Close the chapter with *"From Simulation to Silicon / Hardware Lab"* (pure order steps add a concise fabrication callout only).

---

## Mandatory 4-Pass Authoring Pipeline

### Pass 1: Pedagogical Blueprint & Zero-Forward-Reference Graph
1. Read every line of the step's source file(s) and test file(s); list every constant, helper, hardware register, normal path, and corner/fault path.
2. **Just-in-Time Concept Dripping (Zero Front-Loaded Vocabulary Walls & Zero Forward References)**:
   - Never dump upfront glossaries, system maps, or downstream toolchain terms (`assembler`, `linker`, `synthesizer`) before the step/section that builds or needs them.
   - Topologically sort sections so every concept, register, and mnemonic is defined before it appears—even inside motivation lists, pseudoinstruction tables, or code excerpts.
3. **Top-Down Functional Taxonomy & Calm Section Bridges**:
   - Present functional groups (what operations exist and what programmer problem each solves) *before* binary bit layouts or corner cases.
   - Open every `##` and `###` section (outside Exercise prompts) with a calm **2–4 sentence conceptual bridge** connecting prior state to the new mechanism—never jump straight into widgets, tables, lists, code blocks, or abrupt imperatives (`Trace...`, `Inspect...`), and never use conversational crutches (`Wait: why...`).
4. **Code-vs.-Prose Division of Labor**:
   - Keep `<!-- book-sync: <spec> -->` + `<<< @/systems/...#L<start>-L<end>` transclusions to **tight, focused excerpts (`<= 25` lines)**; push line-by-line mechanics into source comments (`apex-artifact-author`) and link full implementations via anchored symbols (`#L...`).
5. **Upfront Micro-Widgets & Zero-ASCII Cohesive Visuals**:
   - **Zero ASCII Art**: Never use raw ASCII-art/`text` fences (`check_book.py` rejects them); build interactive Vue micro-widgets or compact vertical Mermaid figures (`flowchart TD`).
   - **Concept-Coverage Micro-Widgets**: Any multi-width arithmetic, signedness divergence, truncating division, multi-lane SIMD, or non-obvious pipeline datapath (`RV32M` `MUL`/`MULH*`, `DIV`/`REM`, `Xapex MAC`) **must** open with a dedicated single-concept Vue widget **before** dense math.

### Pass 2: Uncompressed Multi-Chunk Drafting
1. Draft across **2–4 sequential writes/appends** (`write_to_file`) so every section has full narrative breathing room.
2. **Mechanism First, Expanded Name + Acronym Second**: State what every term, mnemonic, CSR, or peripheral *does* in everyday software words before spelling out its letters + acronym.
3. **Gentle Math Refreshers & Contiguous Derivations**: Briefly refresh specialized undergrad terminology (*modular ring*, *Euclidean division*, *SO(3)*) before formalism, introduce concrete numerical examples before general proofs, and keep every multi-step proof in one contiguous `$$\begin{aligned} ... \end{aligned}$$` block with explicit variable domains.
4. **Responsive Widgets & Sync Hygiene**: Size Vue grids for VitePress's `~646px` column (`Bits 31..25` labels, zero datasheet shorthand like `imm[12|10:5]`, zero hidden state jumps). Guard every `<<<` slice with `<!-- book-sync: <spec> -->`, anchor every `#L` link, escape `\$`, avoid prose `~...~`, and **never write bare prose line numbers**. Explain host-language traps (`//` floor vs. truncation, `>>` sign replication) explicitly.

### Pass 3: 3-Specialist Parallel Cold-Reader Critique & Re-Review Convergence
Invoke **3 parallel isolated `research` subagents** (`Model: 'inherit'`, `Workspace: 'inherit'`) on the chapter, code, `.vue` widgets, and `.cache/visual-audit/<slug>/*.png` screenshots:
1. **`Sequential Novice Cold-Reader`**: Reads strictly Line 1 → EOF tracking defined terms/instructions; flags *any* forward reference (even inside alias tables or transcluded docstrings), premature toolchain word (`assembler`), or unexpanded acronym/register.
2. **`Editorial Pacing, Narrative Bridge & Math Editor`**: Audits every `##`/`###` opening for calm conceptual bridges, flags hurried prose skipping concrete examples before proofs, checks math refreshers and contiguous derivations, and verifies every worked number.
3. **`Visual Pedagogy & Diagram Coverage Critic`**: Flags any ASCII art, identifies complex math/bit-lane concepts lacking upfront helper diagrams/widgets, and inspects `.vue` sources plus desktop/mobile PNGs for overlap, clipping, wrapping, or contrast flaws.

- **Mandatory Post-Edit Re-Review Convergence**: After *any* prose or widget edit addressing Round $r$ tickets, rebuild, re-capture `.cache/visual-audit/`, and spawn **fresh clean-room Round $r+1$ specialist subagents** until a full round returns **zero P0/P1/P2 defects**.

### Pass 4: Verification & Final Sync Gate
Conclude with `4–6` **Graded Engineering Exercises** (`<details><summary>Worked Solution</summary>`), then pass every gate before entering review:
```bash
python3 scripts/sync_book.py && python3 scripts/sync_book.py --check
python3 scripts/check_book.py && uv run --with pyyaml python3 scripts/build.py --check
BOOK_BASE=/apex/ npm --prefix book run build
uv run --with playwright python3 scripts/check_visuals.py --screenshot-dir .cache/visual-audit
```
Keep `SKILL.md <= 120` lines; record new patterns in `references/calibration_log.md`.
