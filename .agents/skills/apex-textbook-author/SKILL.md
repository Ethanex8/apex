---
name: apex-textbook-author
description: Author and revise full-depth (30–60 minute) interactive engineering textbook chapters in systems/<system>/chapters/<NN>_<slug>.md alongside repo code using a mandatory 4-pass pipeline (Blueprint, Multi-Chunk First-Principles Draft, 3-Specialist Parallel Cold-Reader Audit with Re-Review Convergence, and Interactive Vue Widgets + Code-Sync Verification).
---

# Apex Multi-Pass Textbook Authoring Skill

Use this skill whenever writing, extending, or upgrading a chapter in `systems/<system>/chapters/<NN>_<slug>.md` mapped from `roadmap.yaml` (`book.parts`).

## Core Philosophy

We are writing an **8-part, 34-chapter publication-grade systems engineering textbook** (*Harris & Harris*, *Crafting Interpreters*, *xv6*, *OSTEP*) alongside tested silicon, firmware, circuit-board, and robotics code rendered via VitePress (`book/`).

- **Target Reader**: An engineer or aspiring engineer who knows **general programming (`if`/`else`, loops, arrays, functions, structs, byte buffers) plus undergraduate math and physics**, does not instantly recall every specialist topic, and has **zero prior background** in computer architecture (RISC-V), RTL/FPGA toolchains, electrical circuits, or mechanical shop jargon. **Never** anchor explanations in specialist software domains (lock-free database engines, write-ahead logs, distributed consensus, OS-kernel demand paging, JVM internals).
- **M:1 Step-to-Chapter Growth (`3–6` steps -> 1 cohesive `~45–60 min` chapter)**:
  - **`step 1/K` (Chapter Launch)**: Creates `01_...md` with a concise primary-topic H1 (`<= 6` words), opening prose (zero front-matter metadata/TOC/figure-inventory blockquotes), foundational sections (`~10–20 min`), and `## Graded Engineering Exercises`.
  - **`step j/K` (Growth)**: Appends `1–2` focused sections (`~10–20 min`) **before** `## Graded Engineering Exercises`, adds anchored exercises, reuses prior notation, and adds widgets only where a new physical/algorithmic model helps.
  - **`bench` Steps**: Close the chapter with *"From Simulation to Silicon / Hardware Lab"* (pure order steps add a concise fabrication callout only).

---

## Mandatory 4-Pass Authoring Pipeline

### Pass 1: Pedagogical Blueprint & Zero-Forward-Reference Graph
1. Read every line of the step's source file(s) and test file(s); list every constant, helper, hardware register, normal path, and corner/fault path.
2. **Base-Before-Custom Layering, Just-in-Time Concepts & Even Rigor Budget**:
   - Build standard/base subsystems end-to-end (core arithmetic, memory, control flow, traps) *before* custom hardware accelerators (`Xapex`), co-locate specialized helpers (`sat32`, custom encoders) inside the section that motivates them, and preview global step outcomes (e.g., normal retirement vs. precise atomic trap) in Section 1 so later fault rules never forward-reference.
   - Never dump upfront glossaries, system maps, front-matter banners (`Reading Time`, `Primary Modules`, `Interactive Figures`), or unbuilt toolchain terms (`assembler`, `linker`), and never inject project-specific constants (`50 MHz`) into rate-independent general principles.
   - Topologically sort sections without braiding separate topics across interleaved intuition/widget/proof blocks, and assign *every* section at least one concrete quantitative or formal invariant (reach/mux fan-in, prefix decoding, counter-tearing, divider drift, state transitions, inductive lockstep) so rigor never concentrates early and drops off later.
3. **Concise Primary-Topic Headings, Top-Down Taxonomy & Calm Section Bridges**:
   - Keep chapter H1 (`<= 6` words) and `##`/`###` headings (`<= 8` words) focused on the primary topic without `&`, `Hook: Subtitle` colons, parentheticals, or backticks.
   - Present functional groups (what operations exist and what programmer problem each solves) *before* binary bit layouts or corner cases, without dumping unexpanded mnemonic walls.
   - Open every `##` and `###` section (outside Exercise prompts) with a calm **2–4 sentence conceptual bridge**—never jump straight into widgets, tables, lists, code blocks, or abrupt imperatives (`Trace...`, `Inspect...`), and never use conversational crutches (`Wait: why...`).
4. **Code-vs.-Prose Division of Labor**:
   - Keep `<!-- book-sync: <spec> -->` + `<<< @/systems/...#L<start>-L<end>` transclusions to **tight, focused excerpts (`<= 25` lines)**; push line-by-line mechanics into source comments (`apex-artifact-author`) and anchor **every** code/test symbol link with `#L<start>-L<end>` via `sync_book.py`.
5. **Upfront Micro-Widgets & Zero-ASCII Cohesive Visuals**:
   - **Zero ASCII Art**: Never use raw ASCII-art/`text` fences (`check_book.py` rejects them); build interactive Vue micro-widgets or compact vertical Mermaid figures (`flowchart TD`).
   - **Single-Concept Upfront Micro-Widgets**: Any multi-width arithmetic, signedness divergence, truncating division, or multi-lane datapath **must** open with its own dedicated single-concept Vue widget **before** dense math (never bundle two separate mechanisms into one widget that forces braided prose), using only concepts already defined.

### Pass 2: Uncompressed Multi-Chunk Drafting
1. Draft across **2–4 sequential writes/appends** (`write_to_file`) with **one sentence per Markdown line** (single newlines, zero trailing two-space `<br>` breaks) so PR reviewers can comment on any individual sentence cleanly.
2. **Mechanism First, Tables Over Coordinate/Catalog Prose & Immediate Adjacency**: State what every term, mnemonic, register, or peripheral *does* in everyday words and place `(**expanded name / acronym**)` **immediately adjacent** to the noun phrase it defines—never separated by an em-dash clause, and never stacking `3+` new acronyms in one sentence. Never recite bit-slice coordinate lists (`Bit A at Bit B, Bits C..D in Bits E..F...`), opcode catalogs, MMIO register maps, or trap matrices inside running prose; present `3+` structured items in scannable Markdown tables or lists and reserve prose for physical motivation, trade-offs, and invariants.
3. **Code-Only Backticks & Restrained Boldface**: Reserve backticks strictly for literal code tokens, machine instructions/registers (`x0`, `add`, `self.pc`), hex/binary literals, CLI flags, and file paths—never wrap English acronyms (HDL, ISA, ALU, FPGA, MMIO, CSR), proper nouns (SystemVerilog, RISC-V, RV32I, Verilator, Python), prose numbers/units (`32-bit`, `50 MHz`, `32 wires`), or raw TeX (`Z_{2^N}`) in backticks. Reserve `**bold**` (`<= 6` words) for newly defined terms and bullet lead-ins, never rhetorical phrases.
4. **Gentle Math Refreshers, Proof Economy & Strict Dependency Order**: Refresh specialized or easily forgotten undergrad identities (*modular congruence addition/subtraction/multiplication* via $x = x' + km$ right after residue classes, *finite geometric series*, *modular inverses*, *Euclidean division*) with a concise derivation/example before use, define operation formulas (e.g., truncating quotient $q$) before proving overflow bounds, walk through concrete numbers before general proofs, prefer 1-step induction or centered Euclidean division over pedantic empty-sum index casework, keep desktop `\begin{aligned}` blocks `<= 624 px`, justify $U_N$ vs. $S_N$, avoid redundant double-proofs once congruence transfers the result, and explicitly prove exceptions and rounding directions.
5. **Responsive Widgets, Clean Inline Math & Sync Hygiene**: Protect `.hw-widget` typography from `.book-serif-mode`, keep inline `mjx-container:not([display='true'])` strictly `display: inline; overflow: visible` (never `inline-block` or `overflow-x: auto`), use explicit `Bits 31..25` labels, run `sync_book.py`, escape `\$`, avoid prose `~...~`, and **never write bare prose line numbers**.

### Pass 3: 3-Specialist Parallel Cold-Reader Critique & Re-Review Convergence
Invoke **3 parallel isolated `research` subagents** (`Model: 'inherit'`, `Workspace: 'inherit'`) on the chapter, code, `.vue` widgets, `custom.css`, and `.cache/visual-audit/<slug>/*.png` screenshots (including `prose_math_desktop.png`):
1. **`Sequential Novice Cold-Reader`**: Reads strictly Line 1 → EOF as a general programmer with undergrad math/physics; flags *any* forward reference (in prose, tables, widgets, or transcluded docstrings), front-loaded widths/helpers orphaned from first use, custom accelerators placed before base memory/control flow, braided multi-topic sections, **specialist software analogies** (`lock-free DB`, `WAL`, `consensus`, `OS paging`, `JVM`), **premature project constants** (`50 MHz`), detached term definitions, `3+` stacked acronyms, or unexpanded mnemonics/registers.
2. **`Editorial Pacing, Narrative Bridge & Math Editor`**: Audits H1/`##`/`###` conciseness, calm 2–4 sentence section bridges, **prose coordinate/catalog walls that belong in tables or lists**, **uneven rigor across early vs. late sections** (flagging early pedantic empty-sum detours and late datasheet/code-narration cliffs), one-sentence-per-line formatting, code-only backticks, bold restraint, concrete examples before proofs, unrefreshed discrete/modular/series identities, redundant parallel proofs, strict lemma dependency order, explicit $U_N$/$S_N$ justification, rounding/exception proofs, and compact desktop display equations.
3. **`Visual Pedagogy & Diagram Coverage Critic`**: Audits `prose_math_desktop.png`, `custom.css`, `.hw-widget`, and Mermaid PNGs for inline math baseline misalignment/scrollbars, clipped/scrolling desktop display equations, ASCII art, `.book-serif-mode` leaks, missing or multi-topic bundled micro-widgets, mobile legibility, and contrast flaws.

- **Mandatory Post-Edit Re-Review Convergence**: After *any* prose or widget edit addressing Round $r$ tickets, rebuild, re-capture `.cache/visual-audit/`, and spawn **fresh clean-room Round $r+1$ specialist subagents** until a full round returns **zero P0/P1/P2 defects**.

### Pass 4: Verification & Final Sync Gate
Conclude with `4–6` **Graded Engineering Exercises** (`<details><summary>Worked Solution</summary>`), then pass every gate before entering review:
```bash
python3 scripts/sync_book.py && python3 scripts/sync_book.py --check
python3 scripts/check_book.py && uv run --with pyyaml python3 scripts/build.py --check
BOOK_BASE=/apex/ npm --prefix book run build
uv run --with playwright python3 scripts/check_visuals.py --screenshot-dir .cache/visual-audit
```
Keep `SKILL.md <= 120` lines; record new patterns in `references/calibration_log.md` and sync updated skills via `save_skill`.
