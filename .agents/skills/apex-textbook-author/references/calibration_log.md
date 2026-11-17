# Apex Textbook Authoring Calibration Log

Persistent ledger of real user review findings, blind-audit gaps, and upstream fixes graduated into [SKILL.md](../SKILL.md) or automated repo gates (`check_book.py`, `check_visuals.py`).

## Entry 001 — `brain-01` Inline Review & Cold-Reader Audit Convergence (2026-11-16)

- **Trigger**: 7 inline PR #3 review comments + Pass 3 Cold-Reader audit (`16` tickets) on `systems/brain/chapters/01_golden_oracle_and_isa.md` (renamed to `01_isa_and_binary_arithmetic.md`).
- **What Was Missed Upstream**:
  1. **Mermaid SVG/CSS Clipping & Sizing**: VitePress `.vp-doc p` line-height (`1.78`) and margins leaked into Mermaid `<foreignObject>` nodes, clipping box text and shrinking horizontal flowcharts (`flowchart LR`) at normal browser zoom.
     - *Healed By*: Fixed [MermaidDiagram.vue](../../../../book/.vitepress/theme/MermaidDiagram.vue) + [custom.css](../../../../book/.vitepress/theme/custom.css); graduated static topology/semicolon checks into `scripts/check_book.py` and DOM `<foreignObject>` clipping + SVG scale assertions into `scripts/check_visuals.py`.
  2. **Front-Loaded Vocabulary Wall**: Opening Section 1 dumped unfamiliar architecture/memory/bus extensions before readers understood basic 32-bit state.
     - *Healed By*: Lens A Criterion #1 (Zero Front-Loaded Vocabulary Walls; drip extensions just-in-time) in `SKILL.md`.
  3. **Code-vs.-Prose Balance**: Embedding `30–50`-line Python slices followed by prose recaps felt repetitive and diluted prose focus on math, mental models, and hardware trade-offs.
     - *Healed By*: Enforced `MAX_TRANSCLUSION_LINES = 25` statically in `scripts/check_book.py` (`<!-- book-gate: allow-long-slice (<reason>) -->` escape hatch) paired with inline `#` code comments in `apex-artifact-author`.
  4. **Missing Top-Down Taxonomy & Upfront Micro-Widgets**: Jumping into binary bit layouts before showing instruction families, and bundling unrelated widgets at the end of sections.
     - *Healed By*: Split into single-concept widgets (`ModularRingAdder.vue`, `SignExtensionShifter.vue`) placed *before* dense derivations; added Lens A Criteria #2 & #4.
  5. **Gentle Math Refreshers & Contiguous Proofs**: Modular ring algebra and multi-step derivations skipped quick plain-English refreshers and forced paragraph-hopping across scattered equations.
     - *Healed By*: Added contiguous `\begin{aligned}` derivation rule + Lens B Criteria #6–7.
  6. **Mobile MathJax/Navbar Overflow & Active Button Hover Contrast**: Inline `<mjx-container>` inside list items overflowed `390px` viewports, mobile navbar toggle overflowed `12px`, and `.hw-btn:hover` overrode `.hw-btn.active` contrast.
     - *Healed By*: Fixed CSS in `custom.css` and promoted permanent desktop+mobile overflow and WCAG contrast (`>= 3.5:1`) checks into `scripts/check_visuals.py` + CI.

## Entry 002 — Chapter 1 Pedagogy, Visual Cohesion & Multi-Specialist Convergence (2026-11-16)

- **Trigger**: User critique (`U1..U6`) on `systems/brain/chapters/01_isa_and_binary_arithmetic.md`: forward references to `addi`/`sub`/`beq`/`jalr` inside Section 3 `x0` prose, hurried `LUI + ADDI` phrasing (`"Wait: why can..."` + unexplained/unnecessary `"assembler"`), raw ASCII art under format bitfield layout, missing helper visuals for `RV32M` multiply/divide and `Xapex MAC`, and abrupt section openings (e.g., Section 9 opening cold with a widget + `"Trace four..."`), missed by single-subagent Pass 3 and broken by un-re-reviewed Round 1 edits.
- **Why Missed Upstream**:
  1. Single omniscient Pass 3 subagent suffered 12-task attention dilution, overlooking global topological order, pacing, and missing widgets.
  2. No post-edit re-review convergence loop ran after addressing Round 1 edits, letting edit-induced regressions (like Section 9 losing its intro bridge and Section 3 gaining `x0` forward references) ship unchallenged.
  3. No deterministic gate checked raw ASCII-art fences, heading opening bridges, conversational crutches (`Wait: why`), or datasheet bit-slice shorthand (`imm[12|10:5]`).
- **Healed By**:
  1. Hardened `scripts/check_book.py` (ban ASCII fences, enforce calm prose intro after every `##`/`###` heading, ban `Wait: why`/`Hold on:`, scan `.md`/`.vue` for datasheet shorthand) + regression tests in `scripts/tests/test_self_healing_gates.py`.
  2. Split Pass 3 into **3 parallel specialized `research` subagents** (*Sequential Novice Cold-Reader*, *Editorial Pacing & Math Editor*, *Visual Pedagogy & Diagram Critic*) with mandatory fresh Round $r+1$ convergence until zero P0/P1/P2 tickets remain.
  3. Built dedicated upfront micro-widgets (`RiscvFormatMatrix.vue`, `Product64Inspector.vue`, `TruncatingDivisionComparator.vue`, `XapexMacDatapath.vue`) and fixed widget contrast/wrapping/precision issues.

## Entry 003 — PR #4 Pass 1: Concise Titles, Broad Engineer Persona, Code-Only Backticks & 1-Sentence Lines (2026-11-17)

- **Trigger**: 6 inline PR #4 review comments + review summary (`U1..U9`) on `systems/brain/chapters/01_isa_and_binary_arithmetic.md` (lines 1–13) plus blind baseline audit (`12` findings including `.book-serif-mode` leaking into `.hw-widget`, unanchored symbol links, and raw TeX inside backticks):
  - `U1`: Verbose multi-clause chapter titles (`Instruction Set Architecture & Fixed-Width Binary Arithmetic`) instead of concise primary-topic titles (`Instruction Set Architecture`).
  - `U2`: Noisy front-matter metadata/TOC/figure-inventory blockquotes (`Part I · Reading Time`, `Primary Modules`, `Interactive Figures`).
  - `U3`: Awkward `Hook: Subtitle` section headings (`## 1. Why Chip Design Starts in Software: The Golden Reference Model`).
  - `U4`: Narrow specialist software analogies (`lock-free database storage engines`, `distributed consensus`, `write-ahead logs`, `OS paging`, `JVM`) instead of targeting an engineer or aspiring engineer who knows general programming + undergrad math/physics without instant specialist recall.
  - `U5`: Overuse of inline backticks on English acronyms (`HDL`, `ISA`, `ALU`, `FPGA`), proper nouns (`SystemVerilog`, `RISC-V`), and prose numbers/units (`50 MHz`, `32-bit`, `32 wires`).
  - `U6`: Detached term definitions separated by em-dash clauses (`hardware selector switches—the circuit equivalent of ... (**multiplexers**)`).
  - `U7`: Injecting project-specific constants (`50 MHz`) into general conceptual explanations where the principle holds at any clock rate.
  - `U8`: Rhetorical bolding of multi-word clauses (`**simultaneously on every tick of a 50 MHz clock**`).
  - `U9`: Multi-sentence Markdown lines impeding line-level GitHub PR review comments (instead of one sentence per line).
- **Why Missed Upstream**:
  1. `GEMINI.md` and `SKILL.md` framed the reader as an *"experienced software/systems engineer"* and explicitly encouraged systems primitives like `xv6`/OS/DB concepts, causing authoring and auditing agents to reach for specialist DB/OS/consensus analogies (`U4`) and overlook premature hardware constants (`U7`).
  2. Neither `build.py` nor `check_book.py` checked chapter/section heading conciseness, front-matter banners, non-code backticks, term adjacency, rhetorical bolding, fragmentless code symbol links, or one-sentence-per-line Markdown (`U1, U2, U3, U5, U6, U8, U9`).
  3. `~/.gemini` skill registry had drifted behind `.agents/skills/*/SKILL.md`.
- **Healed By**:
  1. Graduated deterministic checks into `scripts/build.py` (`<= 6`-word primary-topic chapter titles without `&`, `:`, `,`), `scripts/sync_book.py` (auto-anchoring fragmentless code/test symbol links to `#Lstart-Lend`), and `scripts/check_book.py` (H1/`##`/`###` conciseness & colon/`&`/parenthetical/backtick bans, pre-`##` banner bans, `PROSE_NON_CODE_TERMS` + number/unit + TeX-in-backtick bans, `DETACHED_TERM_DEF_RE`, `<= 6`-word prose bold cap, and one-sentence-per-line enforcement) with unit tests in `scripts/tests/`.
  2. Updated `GEMINI.md` and `SKILL.md` (Pass 1–3) to anchor the broad general-programming + undergrad math/physics persona, ban premature project constants in general concepts, isolate `.hw-widget` fonts from `.book-serif-mode`, and sync skills via `save_skill`.
