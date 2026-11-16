---
name: apex-textbook-author
description: Author and revise full-depth (30–60 minute) interactive engineering textbook chapters in systems/<system>/chapters/<NN>_<slug>.md alongside repo code using a mandatory 4-pass pipeline (Blueprint, Multi-Chunk First-Principles Draft, Cold-Reader Subagent Audit, and Vue Interactive Widgets + Code-Sync Verification).
---

# Apex Multi-Pass Textbook Authoring Skill

Use this skill whenever writing or upgrading a chapter in `systems/<system>/chapters/<NN>_<slug>.md` for an Apex `couch` step.

## Core Philosophy

We are writing a **6-volume, publication-grade systems engineering textbook** (*Harris & Harris*, *Crafting Interpreters*, *xv6*, *OSTEP*) embedded directly alongside tested silicon, firmware, circuit-board, and robotics code, rendered via VitePress (`book/`).

- **Target Reader**: Experienced, mathematically strong software/systems engineer with **zero prior background** in computer architecture (`RISC-V`), RTL/FPGA toolchains, electrical circuits, or mechanical shop jargon.
- **Adaptive Reading Pace (Never Rushed)**:
  - **Foundational / Architectural Pillar Steps** (e.g., `brain-01` Golden ISA & Oracle, pipelining/hazards, 6-layer EM/PDN, SDRAM, FOC motor physics): **45–60 minutes** (`roughly 8,500–12,000 words` across `7–9` sections + `2–3` interactive Vue widgets).
  - **Focused Module Steps** (e.g., combinational ALU, register file, shift-add muldiv, buck regulator): **30–45 minutes** (`roughly 5,000–8,000 words` across `5–7` sections + `1–2` interactive Vue widgets).
  - **Integration / Torture Steps**: **25–35 minutes** (`roughly 3,500–5,500 words` + `1` interactive explorer).

---

## Mandatory 4-Pass Authoring Pipeline

Never write a chapter in a single hurried pass. Execute all four passes in order:

### Pass 1: Pedagogical Blueprint & Zero-Forward-Reference Graph
1. Read every line of the step's source file(s) and test file(s).
2. List every constant, helper function, hardware register/signal, normal path, and corner/fault path.
3. **Just-in-Time Concept Dripping (Zero Front-Loaded Vocabulary Walls)**:
   - Never open a chapter with an upfront glossary, "Architectural Vocabulary" list, or multi-peripheral system map that dumps 10+ unfamiliar extensions, memory regions, and peripherals (`RV32IM`, `Zicsr`, `BRAM`, `QSPI`, `SDRAM`, `CLINT`, `UART`, etc.) before the reader understands the fundamentals.
   - Give at most a brief 2-sentence plain-English chapter arc in Section 1, then **drip** each extension, memory region, and peripheral *only* in the section where it is first needed and derived.
   - Topologically sort sections so every concept is built before it is used. If a small transcluded snippet must reference a field initialized for a later section, give a 1-sentence inline pointer rather than explaining the whole subsystem prematurely.
4. **Top-Down Functional Taxonomy Before Deep Dives**:
   - Whenever introducing an instruction set (`ISA`), compiler IR, bus protocol, or subsystem API, include a crisp high-level map of the **functional categories** (what groups of operations exist and what problem each group solves for a programmer) **before** diving into binary bit layouts or corner-case semantics. Never introduce the operations themselves as scattered afterthoughts inside bitfield or edge-case discussions.
5. **Code-vs.-Prose Division of Labor (No Large Code Dumps)**:
   - Never embed large multi-dozen-line code blocks (`> ~20` lines) in the chapter followed by line-by-line prose recaps of what the code does. Code-level mechanics belong directly inside the source file's inline comments (`apex-artifact-author`).
   - Keep `<!-- book-sync: <spec> -->` + `<<< @/systems/...#L<start>-L<end>` transclusions to **tight, focused excerpts (`roughly 5–20` lines)** highlighting one mathematical identity, interface contract, or subtle guard, and link to full implementations via anchored `[`symbol`](...)` links (never adding `#region` comments into source code).
   - Dedicate chapter prose to what **cannot** live comfortably in code comments: mental models, physical constraints, intuition-building visuals, contiguous math derivations, diagrams, and design trade-offs.
6. **Plan Upfront Micro-Widgets & Each Section's Structure**:
   - **Intuition-First Micro-Widgets**: Design small, single-concept interactive Vue figures placed **upfront when a concept is introduced—*before* dense equations or formal proofs**—so the reader builds visual/hands-on intuition first and the math then formalizes what they observed. Never bundle unrelated concepts into multi-tab mega-widgets parked at the end of a section.
   - **Direct Definition & Software-Systems Anchor**: State what the hardware mechanism **is** and **does** directly, then bridge from a familiar CS primitive (hash map, ring buffer, state machine, mutex, try/catch).
   - **Design Trade-Off & Physical Constraint**: Show the physical or silicon constraint that motivates the design.
   - **Mathematical / Bit-Level Derivation**: Follow deductive flow (**Intuition & Gentle Math Refresher → Generalized Definition → Contiguous Aligned Derivation → Corollaries & Code → Numerical Check**).

### Pass 2: Uncompressed Multi-Chunk Drafting
1. Write the chapter across **2–4 sequential file writes/appends** (`write_to_file` with `Overwrite: true` for Part 1, followed by `Append: true` for subsequent section batches) so each section gets full narrative breathing room instead of bullet-wall compression.
2. Follow strict **Mechanism First, Expanded Name + Acronym Second** hygiene for every domain term, mnemonic, and register name, dripping new terms only when first needed.
3. **Gentle Refreshers for Specialized Undergrad Math**:
   - Assume undergrad engineering math and strong programming fluency, *not* instant recall of specialized terminology (e.g., *modular ring* $\mathbb{Z}_{2^{32}}$, *residue class*, *Euclidean division*, *SO(3)/SE(3)*, *convex QP*, *Laplace/pole-zero*).
   - Pair an upfront visual/intuitive analogy with a brief 1–2 sentence plain-English definition before introducing formal mathematical terminology or set notation.
4. **Self-Contained, Top-to-Bottom Aligned Derivations (Zero Paragraph-Hopping)**:
   - Never split a single algebraic derivation across scattered prose paragraphs or ask the reader to jump back several paragraphs to connect formulas (*"from the summations above... Adding 1 yields..."*).
   - Present each multi-step proof inside a **single contiguous `$$\begin{aligned} ... \end{aligned}$$` block** where every step sits directly below the previous one with short right-hand justifications (`\quad\text{(split top bit } i=N-1\text{)}`), briefly restating any earlier identity inline if reused from a previous section.
   - Define symbolic variables with explicit domains and asymmetric bounds (e.g., $1 \le k < 32$, $[-2^{15}, 2^{15}-1]$) before deriving formulas and specializing to code.
5. **Browser-Legible Diagrams & Responsive Widgets**:
   - In VitePress's `~688px` content column (`~646px` inner `.hw-widget` width), wide horizontal `flowchart LR` chains (`>= 4` stages or long labels), wide ASCII tables (`> 76` columns), or fixed multi-column grids (`> 640px` min width) shrink text to unreadable sizes, force horizontal scrollbars, or clip node labels.
   - Prefer **top-down (`flowchart TD`)** or compact 2–3-node diagrams with short, intentionally wrapped labels (`<br/>`, `<= 4` words per line) and concise `sequenceDiagram` participant/message labels. In Mermaid theme configuration (`MermaidDiagram.vue`), pass an explicit resolved font stack rather than CSS `var(...)` strings so SVG bounding-box calculation never mis-measures or clips node labels.
6. **Zero-Clutter Anchored References**:
   - Guard every `<<<` transclusion with `<!-- book-sync: <spec> -->` (supporting `sym`, `symA..symB`, and `Scope['pat1'..'pat2']`).
   - Anchor every `#L...` link via either a backticked symbol label (e.g., `` [`sign_extend`](../sim/oracle.py#L138-L143) ``) or a `"anchor: <spec>"` link title, and keep file line counts synced via `([`file.py`](...) (\`1,027\` lines))`.
   - **Never write unanchored bare prose line numbers** (`line 142` or `lines 50–60`); name the function/branch/constant or use an anchored `#L` link.
7. **Directness, Zero Meta-Commentary & Host-Language Traps**:
   - Introduce every subsystem, section, and mechanism directly by what it **is** and **does**—never open with meta-commentary about curricula, reader transitions, or negative foils about unrelated technologies.
   - Explicitly call out host-language vs. hardware semantic traps (`//` floor division vs. truncating `DIV`, `>>` sign replication, unsigned vs. signed comparison).

### Pass 3: Two-Lens Adversarial "Cold-Reader" Subagent Critique
Invoke an isolated `research` subagent (`invoke_subagent`, `Model: 'inherit'`, `Workspace: 'inherit'`) role-playing a senior software engineer with **zero prior RISC-V, RTL, EDA, or EE background**. Instruct it to read the chapter, source code, VitePress diagram/CSS helpers (`MermaidDiagram.vue`, `custom.css`), and chapter Vue widgets cold, and structure its report as **Part 1: High-Impact Macro & Structural Findings (Lens A)** first—so structural pedagogy and browser rendering issues are never buried under micro-nits—followed by **Part 2: Section-by-Section Line Audit (Lens B)**:

**Lens A — Macro Pedagogy, Structure & Visual Experience Audit:**
1. **Front-Loaded Vocabulary Walls**: Does Section 1 (or any intro) dump lists of extensions, memory regions, or peripherals instead of dripping them just-in-time where needed?
2. **Missing Top-Down Taxonomy**: Are high-level instruction/API groups introduced clearly before diving into binary bit layouts or corner cases?
3. **Code-vs.-Prose Anti-Pattern**: Are there large (`> ~20`-line) code dumps followed by prose paraphrases instead of pushing code-level explanation into source comments and focusing chapter prose on math, intuition, and diagrams?
4. **Widget Granularity & Upfront Placement**: Is every interactive widget focused on a single concept and placed **before** dense math to build intuition, rather than bundled into multi-tab widgets at the end of a section?
5. **Browser Diagram & Widget Readability**: Does any Mermaid (`flowchart LR`, crowded labels), ASCII block (`> 76` cols), `MermaidDiagram.vue` CSS/font config, or Vue widget grid risk shrinking below readable size, overflowing `~646px`, or clipping text at normal `100%` zoom?

**Lens B — Line-by-Line Clarity, Math Rigor & Hygiene Audit:**
6. **Unexplained Jargon & Undergrad Math Refreshers**: Any hardware acronym/mnemonic used before plain-English mechanism + expansion, or any specialized math term (*modular ring*, *residue class*, *SO(3)*) dropped without a gentle refresher.
7. **Derivation Flow & Arithmetic Accuracy**: Any proof forcing readers to jump across paragraphs instead of flowing in a contiguous `\begin{aligned}` chain, missing parameter domains, or hex/decimal/binary arithmetic errors (cross-check every worked number).
8. **Unmotivated Bit Layouts, Rushed Pacing, Uncovered Corner Cases & Sync Hygiene**: Arbitrary constants without physical trade-offs, missing fault/edge-case notes, unescaped `$`, prose `~...~` tildes, bare prose line numbers, unanchored `#L` links, or meta-commentary/negative-foil openers.

### Pass 4: Interactive Vue Widgets, Graded Exercises & Verification Gate
1. Resolve **100%** of Lens A and Lens B tickets raised by the Cold-Reader subagent.
2. Build focused, single-concept Vue components under `book/.vitepress/theme/components/<step>/`, register them in `book/.vitepress/theme/index.ts`, and place each widget **upfront before the dense formal math it illuminates** (following strict bit-position labeling `Bits 31..25` and zero hidden state jumps).
3. Conclude the chapter with `4–6` **Graded Engineering Exercises** anchored to the step's test suite, each paired with a collapsible `<details><summary>Worked Solution</summary>...</details>` derivation.
4. Sync, build, and verify **every** gate—and when headless `chromium` is installed in the VM, render the built HTML chapter at desktop `1280px` (`100%` zoom) to check SVG `viewBox` scale and screenshot diagram/widget legibility—before presenting for review:
   ```bash
   python3 scripts/sync_book.py
   python3 scripts/sync_book.py --check
   python3 scripts/check_book.py
   uv run --with pyyaml python3 scripts/build.py --check
   BOOK_BASE=/apex/ npm --prefix book run build
   ```
   When updating source files under an existing chapter, run `python3 scripts/sync_book.py --prose-impact main` to check whether any transcluded behavior changed and requires prose updates.
