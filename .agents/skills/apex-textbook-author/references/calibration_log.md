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

## Entry 004 — PR #5 Pass 2: Mathematical Proof Completeness, Lemma Order & Representation Choices (2026-11-18)

- **Trigger**: 4 inline PR #5 review comments (`U1..U4`, `systems/brain/chapters/01_isa_and_binary_arithmetic.md`) plus Step 2 blind calibration audit:
  - `U1` (`L134`): Negation proof started from $U_N(\bar{b}) + 1$ without explaining why $U_N$ was chosen instead of $S_N$ or whether either interpretation works equally ($S_N(\bar{b}) + 1 = -S_N(b)$ holds directly before $N$-bit truncation).
  - `U2` (`L146`): Item 1 cited $U_N(b) \equiv S_N(b) \pmod{2^N}$ inside its negation derivation *before* Item 2 deduced that congruence from $S_N(b) = U_N(b) - b_{N-1} \cdot 2^N$.
  - `U3` (`L147`): Asserted sign-agnostic addition, subtraction, and left-shifting without explicit modular congruence proofs, and claimed `<`, widening, and right-shifts break congruence without proving why.
  - `U4` (`L161`): Wrote floor quotients $\lfloor x / 2 \rfloor$ for right shifts without proving why discarding low bits leaves a non-negative Euclidean remainder $0 \le r < 2^k$ forcing floor division toward $-\infty$ rather than truncation toward zero.
  - Step 2 blind bonus catches: `(2^32 - 1)^2 < 2^64` bound slip at `L355`, negative `(rs1_s * rs2_s) >> 32` needing `u32(...)` + `mulhsu` proof (`L368–379`), and incomplete `+0x800` floor step (`L345–347`).
- **Why Missed Upstream**:
  1. Earlier math/editorial passes checked *existence* of aligned proofs and numerical examples before formulas, without enforcing strict intra-section **lemma dependency order** (`U2`), **explicit proofs for every equivalence claim and exception** (`U3`), **justified choice of representation ($U_N$ vs. $S_N$)** (`U1`), or **explicit proofs of non-obvious rounding directions** (`U4`).
- **Healed By**:
  1. Updated `GEMINI.md` (Section 2 *Proof Rigor, Lemma Order & Representation Choices*) and `SKILL.md` (Pass 2 #4 + Pass 3 #2 *Editorial Pacing, Narrative Bridge & Math Editor*) with all four proof-rigor mandates, then synced via `save_skill` and verified 100% recall in Step 4 Blind Convergence Replay.

## Entry 005 — PR #5 Pass 3: Desktop MathJax Rendering Gate, Proof Non-Redundancy & Math Refreshers (2026-11-18)

- **Trigger**: 3 inline PR #5 review comments (`N1..N3`, review `5964111381`) plus Step 2 blind calibration audit on `67fd2bf`:
  - `N1` (`L92`, `custom.css:110-123`): Pervasive inline math horizontal scrollbars and baseline bouncing on desktop because `custom.css` set `overflow-x: auto; overflow-y: hidden` on all `mjx-container` and `display: inline-block; vertical-align: middle` on inline `mjx-container:not([display='true'])`, plus `11/19` display equations exceeding the desktop `624 px` column width.
  - `N2` (`L152`): Over-explicit redundant double derivation re-expanding $S_N(\bar{b}) + 1 = -S_N(b)$ in full after $U_N(b) \equiv S_N(b) \pmod{2^N}$ and $U_N(\bar{b}) + 1 \equiv -S_N(b) \pmod{2^N}$ had already proved the exact same $N$-bit pattern.
  - `N3` (`L135`): Elementary modular arithmetic congruence rules ($x \pm y$, $c \cdot x$, $x \cdot y$) stated without a quick algebraic refresher and concrete example (plus unrefreshed geometric-series and modular-inverse claims in Section 2).
- **Why Missed Upstream**:
  1. `scripts/check_visuals.py` audited only `.hw-widget` and `.mermaid-book-figure` containers, omitting `mjx-container` CSS/overflow assertions and prose+math desktop screenshots (`prose_math_desktop.png`).
  2. Our prior proof-rigor heal emphasized showing alternative representations so strongly that it invited full redundant parallel expansions even after congruence already established equivalence, while treating basic modular congruence identities as instant recall.
- **Healed By**:
  1. Upgraded `scripts/check_visuals.py` (`MATH_AUDIT_JS` + `prose_math_desktop.png` capture) and `scripts/tests/test_self_healing_gates.py` to deterministically fail on non-`inline`/non-`visible` inline math, clipped display math, or desktop display-math column overflow (`N1`).
  2. Updated `GEMINI.md` and `SKILL.md` (Pass 2 #4–5, Pass 3 #2–3) to require elementary discrete/modular/series refreshers with examples, transfer results cleanly via congruence without redundant double proofs (`N2`, `N3`), and keep desktop display equations within column width, synced via `save_skill`.

## Entry 006 — Holistic Pedagogical Flow, Reference Tables Over Prose Walls & Balanced End-to-End Rigor (2026-11-18)

- **Trigger**: Deep first-principles pedagogical evaluation of Chapter 1 (`01_isa_and_binary_arithmetic.md`, `HEAD = ccb765d`) identifying three structural weaknesses despite local proof accuracy:
  1. **Macro/Micro Ordering & Front-Loading**: 216 lines of abstract $N$-bit theory (including unused gate-level MSB-XOR `<` and orphaned `sat32`) preceded registers/instructions; S/B/U/J scrambled bitfields preceded the instructions using them; custom `Xapex` appeared before Memory and Loops (forcing forward references to BRAM, loads, branches, and `StepTrace`); congruence preservation appeared 45 lines after `-5 + 3 = -2`; Section 2.4 braided widening and right-shift floor division (because `SignExtensionShifter.vue` bundled both); and Section 5.3 bounded `INT32_MIN / -1` before defining truncating quotient $q$.
  2. **Enumerative Coordinate & Catalog Prose Walls**: 8 dense prose passages (signed encoding bullets, S/B/J bit-slice coordinates, 19-mnemonic ALU catalog, RV32M multiply bounds, load/store + CLINT/UART0 register maps, `mie`/`mip` bit alignments + Zicsr rules, and a 45-word 6-case `mtval` sentence) forced readers to parse structured reference specs out of prose.
  3. **End-to-End Rigor Imbalance**: Early sections spent 12–27 lines on degenerate empty-sum index edge cases and ad-hoc boolean rewrites while Memory, Control Flow, Traps, and Verification dropped into flat code/helper narration without deriving prefix decoding, 64-bit counter rollover tearing, UART baud drift, branch completeness, `mscratch` ISR stack swap, or $O(1)$ inductive `StepTrace` sufficiency.
- **Why Missed Upstream**:
  1. Checking local zero-forward-reference correctness alone encouraged front-loading Section 2 with premature abstract math instead of layering base machine $\to$ custom accelerator and co-locating helpers (`sat32`).
  2. `check_book.py` lacked a deterministic gate catching multi-coordinate prose walls (`>= 5` `Bits ...` citations per prose line), and `SKILL.md` lacked explicit rules requiring Markdown tables for structured catalogs/maps and balanced quantitative invariants in late sections.
- **Healed By**:
  1. Added `allow-enumerative-prose` gate + `COORDINATE_BIT_RE` prose-wall check in `scripts/check_book.py` with regression tests in `scripts/tests/test_self_healing_gates.py`.
  2. Updated `GEMINI.md`, `apex-textbook-author/SKILL.md`, and `apex-couch-mentor/SKILL.md` to enforce base-before-custom layering, unbraided single-concept widgets/subsections, tables over prose walls, proof economy, and uniform rigor across all sections, synced via `save_skill`.

## Entry 007 — PR #6: 4-Step Subset-Recall Protocol, Abstraction Boundaries & Step-by-Step Display Algebra (2026-11-19)

- **Trigger**: 15 inline PR #6 comments (`U1..U15`) plus review note (`U16`) and isolated clean-room Pass-3 panel findings on `48bc0b2` (`01_isa_and_binary_arithmetic.md`, `.vue` widgets, `custom.css`, `oracle.py`):
  - **Abstraction & Widget Insertion Audit (`U3`, `U6`, `U9`)**: Pre-hardware section leaked `"adder's bottom carry-in wire"`, upfront `SignExtensionWidener.vue` previewed unintroduced `sign_extend` Python code, and prose advertised `"without an if/else branch"` without real cost motivation.
  - **Prose-to-Equation Faithfulness, Causal Logic & Step-by-Step Algebra (`U1`, `U2`, `U4`, `U7`, `U8`, `U10`, `U11`, `U12`, `U13`)**: Prose claimed `"cancels every lower wire"` when the lower sum remained intact; `"Consequently"` asserted right-shift upper-wire fill from non-invertibility alone; parenthetical uniqueness sub-proofs, boundary caveats, and in-paragraph math cramped readability; and `U_N(a << k)` + `i = j + k` re-indexing skipped intermediate summation steps.
  - **Takeaways, Cohesion & Exercises Heading (`U5`, `U14`, `U15`)**: Buried sign-extension vs. zero-extension takeaway, ordered comparisons tacked onto Right Shifts, and `## 9. Graded Engineering Exercises` instead of `## 9. Exercises`.
  - **Panel Bonus Catches (`U16`)**: False `new_lo < old_lo` CLINT 2-store inequality, inaccurate `Side-Effect-Free Evaluation` wording vs. `_exec_store`/`_exec_zicsr` mutations, `mac.clr` loop reset wording, `5 x 64 KB` vs. power-of-two window wording, missing Section 8.1 opcode-partition table, incomplete Exercise 2 `divu`/`remu` solution, `XapexMacDatapath.vue` missing `mac.set`/`mac.get` presets, `RiscvFormatMatrix.vue` U-type `S` split and `6px`/`0.3` contrast, `RiscvBitfieldDecoder.vue` illegal SYSTEM/`fence` formatting, and `.hw-label code` CSS specificity.
- **Healed By**:
  1. Formalized the 4-Step Subset-Recall PR Review Protocol in `docs/REVIEW_PROCESS.md`, `apex-skill-healer/SKILL.md`, `apex-couch-mentor/SKILL.md`, and `GEMINI.md`, scrubbing Chapter-1-specific tokens/lemmas from `GEMINI.md` and sibling skills.
  2. Updated `apex-textbook-author/SKILL.md` (Pass 1–3) with abstraction-boundary checks, honest construct rationale, buried-takeaway detection, exact-insertion widget audits, chunked long-chapter Pass-3 audits, step-by-step display algebra, prose-to-equation action-verb checks, and premise-to-conclusion entailment checks.
  3. Added deterministic `## <N>. Exercises` check in `scripts/check_book.py` + tests in `scripts/tests/test_self_healing_gates.py`, and resolved all `U1..U15` + panel findings across Chapter 1, Vue widgets, `custom.css`, and `oracle.py`.


## Entry 008 — PR #6 Round 2: Unbraided List Items, Intuition Before Edge Cases & Post-Equation Preconditions (2026-11-19)

- **Trigger**: 3 inline PR #6 comments (`#4637597770`, `#4637622384`, `#4637677447`) plus review note (`#5986527983`) on `301f82a` / `a7c0db8`, plus Step 2 isolated panel catches:
  - **Braided Multi-Operation Items & Cold Boundary Openings (`U1`, `U2`)**: A single numbered item (`2.`) interleaved addition/subtraction concrete examples, a left-shift example before left shifts were defined, a `+`/`-` theorem, and then opened left shifts cold with the `k = 0` identity case before plain-English intuition.
  - **Forward Exponent Commentary Without Theorem Purpose (`U3`)**: A sentence asserted non-negativity of an equation's factored exponent (`i + k - N >= 0`) *before* the display equation appeared and without explaining why integrality matters (keeping the factored multiplier whole so the discarded upper tail vanishes modulo `2^N`).
  - **Step 2 Blind Panel Catches**: `TruncatingDivisionComparator.vue` inserted before divide-by-zero/overflow rules were introduced (`division-fault line` jargon, `"Euclidean identity"` at divisor 0), buried `Two's Complement` takeaway before the encoding comparison table, `Right Shifts` modular-inverse non-entailment, `N = 1` telescoping wording, and parenthetical scaling/examples.
- **Healed By**:
  1. Added content-agnostic rules in `GEMINI.md` and `apex-textbook-author/SKILL.md` forbidding braided multi-operation bullets/paragraphs, requiring plain-English operation intuition before boundary edge cases/equations, banning commentary on unseen equation sub-terms/exponents, and requiring explicit theorem-step motivation for every precondition.
  2. Proved isolated Step 2 blind subset recall (`U_agreed = {U1, U2, U3} \subseteq PanelFindings` on the first run without extra persona edits).
  3. Unbraided Addition/Subtraction vs. Left Shifts, moved exponent integrality explanation after the equation with explicit modular-multiplier motivation, rewrote Right Shifts around direct `b_{N-1} 2^{N-k}` congruence loss, surfaced the `Two's Complement` takeaway before the comparison table, and relocated `TruncatingDivisionComparator.vue` after the corner-case table.

## Entry 009 — PR #6 Round 3: Simple-to-Derived Ordering, Proof Paragraph Breaks & Two-Sided Hardware Equivalence (2026-11-20)

- **Trigger**: 2 inline PR #6 Round 3 comments (`#4641824975`, `#4641834300`) plus review note (`#5992031731`) on `c5315ec`, plus Step 2 isolated panel catches:
  - **Inverted Theorem Order (`U1`)**: `Negation via Invert Plus One` (including two-operand `a + ~b + 1` subtraction) appeared ahead of `Sign-Agnostic Addition and Subtraction`, placing a circuit-implementation trick before the simpler, direct congruence property it relies on.
  - **Missing Proof Paragraph Break & Incomplete Two-Sided Hardware Bridge (`U2`)**: The left-shift proof goal ran straight onto the concrete example paragraph without a blank line, and asserted identical signed/unsigned hardware from `U_N(a << k) === 2^k S_N(a) (mod 2^N)` without spelling out both sides (what the circuit outputs under `U_N` vs. why reading that *same* output wire pattern `w` under `S_N` returns the exact signed answer).
  - **Step 2 Blind Panel Catches**: Section 2 braided unary negation with two-operand subtraction and lacked the output-wire `w` bridge across all four items, six missing paragraph breaks before formal proofs, H1 colon, `N = 1` boundary/undefined-`S` phrasing, zero-extension intro-vs-equation mismatch, right-shift undefined `q` jump, stacked `RV32I`/`RV32M`/`RV32IM` acronyms, immediate vs. register `shamt` masking (`35 & 31`), deferred `auipc` load/jump forward references, and `mul` vs. `mulh*` paragraph braiding + `U_64(w)`/`S_64(w)` bridge.
- **Healed By**:
  1. Broke monolithic `GEMINI.md` Section 2 rules into atomic sub-bullets per user feedback on Gate 1 (`Proposed Diff A`) and added content-agnostic rules in `GEMINI.md` and `apex-textbook-author/SKILL.md` enforcing simple-to-derived ordering, paragraph breaks before formal proofs, and explicit two-sided shared-hardware equivalence bridges across data interpretations.
  2. Proved isolated Step 2 blind subset recall (`U_agreed = {U1, U2} <= PanelFindings` on the first run without extra persona edits).
  3. Applied all Step 2 and PR Round 3 fixes across Sections 1–4 of `systems/brain/chapters/01_isa_and_binary_arithmetic.md`.
