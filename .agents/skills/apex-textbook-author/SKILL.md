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
3. Topologically sort sections so **every concept is derived from first principles before any code line uses it** (zero forward references). When an early initialization block (`__init__`, `reset()`, or module port list) sets state governed by a later section, give a 1-sentence plain-English summary and section cross-reference inline so no constant or flag sits unexplained.
4. For each planned section, define:
   - **Direct Definition & Software-Systems Anchor**: State what the hardware mechanism **is** and **does** directly, then bridge from a familiar CS primitive (hash map, ring buffer, state machine, mutex, try/catch).
   - **Design Trade-Off & Physical Constraint**: After defining the mechanism, show the physical or silicon constraint that motivates it (e.g., why a naive alternative stalls, overflows, or wastes area).
   - **Mathematical / Bit-Level Derivation**: Follow deductive textbook flow (**Generalized Definition → Algebraic Derivation → Corollaries & Code → Numerical Check**). Define symbolic $N$-bit or physical variables with explicit domains and asymmetric bounds (e.g., $1 \le k < 32$, $[-2^{15}, 2^{15}-1]$), and derive formulas by equating or expanding definitions (summations, geometric series, Euclidean division, product expansions) before specializing to code (`s32`, `s16`, `hi20`)—never assert a formula in prose and jump straight to plugging in numbers.
   - **Live Code Transclusion**: Plan `<!-- book-sync: <spec> -->` + `<<< @/systems/...#L<start>-L<end>` slices using zero-clutter symbol/pattern anchors (`scripts/code_anchors.py`), never adding `#region` comments into source code.

### Pass 2: Uncompressed Multi-Chunk Drafting
1. Write the chapter across **2–4 sequential file writes/appends** (`write_to_file` with `Overwrite: true` for Part 1, followed by `Append: true` for subsequent section batches) so each section gets full narrative breathing room instead of bullet-wall compression.
2. Follow strict **Mechanism First, Expanded Name + Acronym Second** hygiene for every domain term, mnemonic, and register name. When introducing a multi-peripheral chip or multi-module architecture in Section 1, group the system map by role (e.g., Instruction Set / Memory / Peripherals) with section pointers instead of a flat glossary wall.
3. **Zero-Clutter Anchored References**:
   - Guard every `<<<` transclusion with `<!-- book-sync: <spec> -->` (supporting `sym`, `symA..symB`, and `Scope['pat1'..'pat2']`).
   - Anchor every `#L...` link via either a backticked symbol label (e.g., `` [`sign_extend`](../sim/oracle.py#L138-L143) ``) or a `"anchor: <spec>"` link title, and keep file line counts synced via `([`file.py`](...) (\`1,027\` lines))`.
   - **Never write unanchored bare prose line numbers** (`line 142` or `lines 50–60`); name the function/branch/constant visible in the transcluded block or use an anchored `#L` link.
4. **Directness & Zero Meta-Commentary**: Introduce every subsystem, section, and mechanism directly by what it **is** and **does**. Never open with meta-commentary about engineering curricula, reader transitions, or what the reader doesn't need to know yet (silently defer out-of-scope future stages to their own chapters), and never introduce a system by listing what unrelated technologies fail to do.
5. **Algebraic Continuity & Host-Language Traps**: Carry proven identities forward into later sections (e.g., reusing the derived two's complement conversion identity to prove instruction-split carry rules, upper-half multiplication, and alignment masks) rather than re-arguing from informal prose or case-splitting where one algebraic chain suffices. Explicitly highlight any host-language vs. hardware semantic traps right where the code relies on them (e.g., Python floor division `//` vs. truncating `DIV`, Python `>>` sign-bit replication on negative ints, and trace-field width conventions).

### Pass 3: Adversarial "Cold-Reader" Subagent Critique
Invoke an isolated `research` subagent (`invoke_subagent`, `Model: 'inherit'`, `Workspace: 'inherit'`) role-playing a senior software engineer with **zero prior RISC-V, RTL, EDA, or EE background**. Instruct it to read the drafted chapter and source file cold and audit against 7 defect categories:
1. **Unexplained Jargon / Acronym Soup**: Any hardware acronym, mnemonic, or register name used before plain-English mechanism + spelled-out expansion.
2. **Hand-Waved Derivations & Arithmetic Slips**: Any equation, bitwise identity, or corner case stated without an explicit algebraic bridge, missing parameter domain/asymmetric bound, or any hex/decimal/binary conversion error (cross-check every worked number independently).
3. **Unmotivated Bit Layouts / Magic Numbers**: Any constant, address, or bit scramble presented as an arbitrary rule without explaining the physical trade-off.
4. **Rushed Pacing**: Any section reading like terse reference notes rather than patient textbook prose.
5. **Uncovered Deliverable Logic & Silent Traps**: Any function, early init/reset field, parameter bit-slice origin (e.g., `shamt`), fault branch, or host-language semantic trap left unexplained where transcluded.
6. **Formatting & Sync Hygiene Bugs**: Unescaped `$` currency, prose `~...~` tildes, broken links, bare prose line numbers, or unanchored `#L` links.
7. **Meta-Commentary & Negative-Foil Openers**: Any section, subsystem, or concept introduced by what it does not do, what an unrelated technology fails at, or meta-commentary about curricula, reader transitions, or deferred topics—every opening must state directly what the component **is** and **does**.

### Pass 4: Interactive Vue Widgets, Graded Exercises & Verification Gate
1. Resolve **every** ticket raised by the Cold-Reader subagent.
2. Build `1–3` self-contained Vue components under `book/.vitepress/theme/components/<step>/`, register them in `book/.vitepress/theme/index.ts`, and embed them inline at the exact conceptual friction points in the chapter (following strict bit-position labeling `Bits 31..25` and zero hidden state jumps).
3. Conclude the chapter with `4–6` **Graded Engineering Exercises** anchored to the step's test suite, each paired with a collapsible `<details><summary>Worked Solution</summary>...</details>` derivation.
4. Sync and run all verification gates before presenting for review:
   ```bash
   python3 scripts/sync_book.py
   python3 scripts/sync_book.py --check
   python3 scripts/check_book.py
   uv run --with pyyaml python3 scripts/build.py --check
   BOOK_BASE=/apex/ npm --prefix book run build
   ```
   When updating source files under an existing chapter, run `python3 scripts/sync_book.py --prose-impact main` to check whether any transcluded behavior changed and requires prose updates.
