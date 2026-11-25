# Apex Textbook Authoring Calibration Log

Persistent ledger of real user review findings, blind-audit gaps, and upstream fixes graduated into [SKILL.md](../../.agents/skills/apex-textbook-author/SKILL.md) or automated repo gates (`check_book.py`, `check_visuals.py`).

## Entry 001 — `brain-01` Inline Review & Cold-Reader Audit Convergence (2026-11-16)

- **Trigger**: 7 inline PR #3 review comments + Pass 3 Cold-Reader audit (`16` tickets) on `systems/brain/chapters/01_golden_oracle_and_isa.md` (renamed to `01_isa_and_binary_arithmetic.md`).
- **What Was Missed Upstream**:
  1. **Mermaid SVG/CSS Clipping & Sizing**: VitePress `.vp-doc p` line-height (`1.78`) and margins leaked into Mermaid `<foreignObject>` nodes, clipping box text and shrinking horizontal flowcharts (`flowchart LR`) at normal browser zoom.
     - *Healed By*: Fixed [MermaidDiagram.vue](../../book/.vitepress/theme/MermaidDiagram.vue) + [custom.css](../../book/.vitepress/theme/custom.css); graduated static topology/semicolon checks into `scripts/check_book.py` and DOM `<foreignObject>` clipping + SVG scale assertions into `scripts/check_visuals.py`.
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

## Entry 010 — PR #6 Round 4: Justified Output-to-Target Algebra, Hardware-Polymorphism Spotlights & Inline Exercises vs. Closing Problems (2026-11-20)

- **Trigger**: 4 inline PR #6 Round 4 comments (`#4643142055`, `#4643156207`, `#4643240796`, `#4643249800`) on `238e167` / `a427029`, plus Step 2 gate/panel catches:
  - **Prose Chains vs. Justified Output-to-Target Algebra (`U1`)**: Section 2.2 dual-interpretation circuit proofs explained multi-hop residue chains inside prose paragraphs instead of justified aligned derivations starting from `S_N(w)` down through `U_N(w)` and the circuit formula to the signed target modulo `2^N`.
  - **Under-Highlighted Hardware-Polymorphism Breakthrough (`U2`)**: Section 2.2 and `mul` proved shared unsigned/signed circuits matter-of-factly without spotlighting why pure algebra eliminates mode bits, separate adders/subtractors, and signedness muxes in silicon (and contrasting where broken invariance forces hardware splits).
  - **Reusable Algebra Intuition, Failure Boundaries & Inline Exercises (`U3`)**: Modular congruence preservation lacked operational intuition (free term-wise substitution across `+`, `-`, `*` under matching modulus `m` vs. breaking on incongruent terms, mixed moduli, or non-coprime integer division) and lacked immediate inline fluency checks.
  - **Exercises vs. Closing Problems Separation (`U4`)**: Multi-section synthesis tasks were labeled `## 9. Exercises` / `### Exercise K:` rather than pairing lightweight inline `#### Exercise S.K:` checks after key theorems with closing `## <N>. Problems` (`### Problem K:`).
  - **Step 2 Blind Panel Catches**: Missing `modulus-scaling lemma` (`c*x === c*x' mod c*m`) invoked in Sections 4.2/4.3, unproved `U_{N-k}(H) - S_{N-k}(H)` formula in the Summary Table, missing `S_N` bijection statement, `0x` hex gloss, `strictly inside [0, 2^32 - 1]` endpoint bug, `M > k` negative MSB zeroing step in zero extension, pre-equation index substitution preview in Right Shifts, collapsed multi-step algebra lines, and `RTL` Mermaid node ID.
- **Healed By**:
  1. Updated `GEMINI.md`, `apex-textbook-author/SKILL.md`, `apex-couch-mentor/SKILL.md`, `scripts/check_book.py`, and `scripts/tests/test_self_healing_gates.py` (enforcing `## <N>. Problems` + `#### Exercise <S.K>` checks, operational algebra intuition/failure boundaries, justified output-to-target circuit derivations, and hardware-reuse spotlights).
  2. Proved isolated Step 2 blind subset recall (`U_agreed = {U1, U2, U3, U4} <= PanelFindings U GateFindings` on the first run without extra persona edits).
  3. Applied all Step 2 and PR Round 4 fixes across `systems/brain/chapters/01_isa_and_binary_arithmetic.md`, adding inline Exercises 2.1–2.4 and 4.1–4.2 and promoting closing Section 9 to `## 9. Problems` (`Problem 1..6`).

## Entry 011 — PR #6 Round 5: Inline Drill Density (6–8 Parts), Terse Algebraic Solutions & Math-vs-Hardware Exercise Scoping (2026-11-20)

- **Trigger**: 5 inline PR #6 Round 5 comments (`#4645516681`, `#4645527323`, `#4645564812`, `#4645582472`, `#4645595695`) plus review note (`#58`) on `39630a7`, plus Step 2 isolated panel catches:
  - **Under-Populated Drills & Wordy Prose Solutions (`U1`, `U3`)**: Inline `#### Exercise` blocks (`2.1`–`2.4`, `4.1`–`4.2`) carried only 2 parts instead of `6–8` crisp mental-practice parts and explained answers in multi-sentence prose essays rather than terse step-by-step algebraic equalities.
  - **Missing Math/Encoding/Bound-Derivation Drills & Scoping Rule (`U2`, `U4`, `U5`)**: Mathematical, encoding, and bound-derivation subsections (`Two's Complement Signed Integers`, `Full 64-Bit Integer Multiplication`, `First-Step Accumulator Overflow Proof`, plus panel-caught `Equality and Ordered Comparisons` and `Bitfield Layouts and Offset Reach`) lacked inline mental-practice drills, whereas pure hardware-interface/contract subsections (`Section 1`, `3.1`–`3.2`, `4.1`, `5`, `6`, `7.1`, `8`) belong under end-of-chapter `## <N>. Problems`.
  - **Step 2 Blind Panel Catches**: Missing paragraph break, same-sign vs. opposite-sign lane-min entailment step, and forward `$S_{\min}, S_{\max}$` reference in `First-Step Accumulator Overflow Proof`; late `<TruncatingDivisionComparator />` placement after dense division math; dense trap-entry symbol intro; non-definition boldface in Section 2.3; exclamation marks and minor state-continuity wording in `Problems 3–5`.
- **Healed By**:
  1. Updated `GEMINI.md` and `apex-textbook-author/SKILL.md` (Pass 2, Pass 3 `Cold-Reader` / `Math Editor`, Pass 4) with `6–8` part drill density, terse algebraic `<details><summary>Solution</summary>` formatting, and the explicit math/encoding/bound vs. hardware-interface scoping boundary.
  2. Proved isolated Step 2 blind subset recall (`U_agreed = {U1, U2, U3, U4, U5} <= PanelFindings` on the first run without extra persona edits).
  3. Rewrote and added inline 6–8 part drills (`Exercise 2.1`–`2.6`, `3.1`, `4.1`–`4.3`, `7.1`) with terse algebraic solutions across all math, encoding, and bound-derivation subsections of `systems/brain/chapters/01_isa_and_binary_arithmetic.md` while fixing all panel P1/P2 proof-flow, widget-placement, and formatting findings.

## Entry 012 — PR #6 Round 6: Lemma Claim-and-Payoff Lead-Ins & Explicit Interval-Uniqueness Handoffs (2026-11-20)

- **Trigger**: 1 inline PR #6 Round 6 comment (`#4650212274` at `01_isa_and_binary_arithmetic.md:231`), plus Step 2 isolated panel catches:
  - **Cold Lemma Mechanics Without Stated Claim or Downstream Payoff (`U1`)**: The `Shared Adder, Negation, and Shift Circuits` subsection plunged straight into comparing two bit vectors at highest differing wire `k` without stating up front **what** was being proved ($U_N$ and $S_N$ are collision-free bijections) or **why** modular arithmetic and the downstream circuit proofs rely on it (locking modular congruences to unique bit patterns with no aliases and yielding exact numerical equality inside any $2^K$-element interval).
  - **Step 2 Blind Panel Catches**: Missing interval-uniqueness corollary in Section 2.3 and implicit handoffs in Section 2.3 Items 1–5 and Sections 4.2/4.3; braided `modulus-scaling lemma` in Section 2.1 lacking a separate paragraph, $c > 0$ motivation, display proof, and usage intuition; cold lead-ins on `S = 2^N - 1`, zero/sign extension, `sign_extend`, and truncating remainder proofs; Section 2.5/2.6 entailment gaps; undefined $p_i$ and Section 5.3 $T_1/T_2$/`|` clarity; Section 5.1 paragraph break; and Section 1/3.3/6.1 polish.
- **Healed By**:
  1. Added universal claim-and-payoff lead-in and downstream-handoff rules in `GEMINI.md` and `apex-textbook-author/SKILL.md` (Pass 2 and Pass 3).
  2. Proved isolated Step 2 blind subset recall (`U_agreed = {U1} <= PanelFindings` on the first run without extra persona edits).
  3. Rewrote Section 2.3's encoding-uniqueness & interval-uniqueness lemma with an explicit claim-and-payoff lead-in and downstream tie-backs, unbraided the modulus-scaling lemma with display proof and usage intuition, added claim-and-payoff lead-ins across Sections 2.1, 2.4, 4.2–4.4, and 7.2, closed Section 2.5/2.6 entailment gaps, and polished Sections 1, 2.2, 3.3, 5.1, 5.3, and 6.1.

## Entry 013 — PR #6 Round 7: Intuitive Clock-Slot Framing, Foundational Placement & Stripping Boilerplate (2026-11-21)

- **Trigger**: 2 inline PR #6 Round 7 comments (`#4652286823` at `01_isa_and_binary_arithmetic.md:243`, `#4652300885` at `257`) plus review note (`#6004998896`, *"Disappointed in last revision"*):
  - **Dense Prose-Math Wall & Misplaced Lemmas (`U1`)**: Round 6's rule (*"state ... how later proofs or hardware rely on it, and explicitly cite that connection..."*) caused a dense prose-math wall at `lines 243–250` wedging foundational $U_N$/$S_N$ bijection and interval-uniqueness proofs mid-stream into `Section 2.3` (*Shared Adder, Negation, and Shift Circuits*) with forward section catalogs.
  - **Repetitive Bijection Boilerplate & Legalisms (`U2`)**: `Section 2.3` Items 1–5 (`lines 257, 269, 296, 309, 329`) and `Section 4` (`lines 781–816`, `895–909`) repeated per-item bijection/corollary boilerplate and stiff `"Next we prove..."` / `"Section X.Y's ... corollary"` legalisms instead of establishing uniqueness once intuitively where each representation is introduced (`Sections 2.1` and `2.2`) and framing clock-slot equivalence naturally up front.
- **Healed By**:
  1. Replaced the faulty Round 6 wording in `GEMINI.md` and `apex-textbook-author/SKILL.md` with rules enforcing plain low-symbol proof lead-ins, placing intrinsic representation properties right where each representation is introduced, stating shared bridges once before parallel lists, and banning dense prose-math walls, stiff `"Next we prove..."` announcements, forward section catalogs, and repetitive cross-section legalisms.
  2. Proved isolated Step 2 blind subset recall (`U_agreed = {U1, U2} <= PanelFindings` on the first run across both blind auditors without hints or extra persona edits).
  3. Moved $U_N$ uniqueness and one-lap clock interval uniqueness cleanly into `Section 2.1`, moved $S_N$ uniqueness into `Section 2.2`, simplified `Section 2.3` to one crisp intuitive clock-slot bridge before Items 1–5 (reordering Left Shifts after Subtraction via Invert Plus One), stripped all five per-item bijection boilerplate remarks, and cleaned up stiff announcements/legalisms/dense walls across Sections 2.4–2.6, 4.2–4.4, 6.1, and 7.2.

## Entry 014 — PR #6 Round 8: Consumer-Driven Section Placement, Committed Chapter Index & Split Macro Critic (2026-11-21)

- **Trigger (`PR #6`, Round 8 — Comment `#4653038685`)**: User questioned whether Section 2 (*Binary Arithmetic Foundations*) tried to cover too much upfront theory before hardware consumers appeared, asking which pieces belonged in core binary theory versus dedicated downstream sections.
- **Root Cause**: `rubric_cold_reader.md` lacked a structural principle checking consumer-driven concept placement against a whole-chapter map, and `rubric_visual_critic.md` mixed whole-chapter macro pacing checks with figure layout audits.
- **Systemic Rule & Tooling Changes (Non-Cheating)**:
  1. Built `scripts/chapter_index.py` and wired automated compilation/drift validation of `docs/CHAPTER_INDEX.md` into `scripts/build.py` and `scripts/build_review_plan.py` so cold-reader and macro auditors can verify whole-chapter section placement deterministically.
  2. Split whole-chapter macro architecture checks into `.agents/skills/apex-textbook-author/references/rubric_macro_critic.md` (`Global Macro & Dependency Critic`), updated `GEMINI.md`, `apex-textbook-author/SKILL.md`, `rubric_cold_reader.md`, and `rubric_visual_critic.md` to enforce consumer-driven placement and plain-language figure contracts, and removed any instance-specific threshold hints.
  3. Proved isolated Step 2 blind subset recall (`Cold-Reader Shard 2/5` and `Global Macro Critic`) on untouched `8b3574f`, catching both bloated Section 2 placement and `<RightShiftComparator />` forward symbol preview without hints.
  4. Relocated `Widening` (`<SignExtensionWidener />`, `sign_extend`, `s32`) into `Section 3.4` alongside instruction immediate unpacking, relocated `Right Shifts`, `Comparisons`, and `Hardware Equivalence Summary` into `Section 4.2–4.3` (moving `<RightShiftComparator />` after the floor-division proof), kept `Modulus Scaling` in core `Section 2.1`, added 7-part `Exercise 5.1`, and expanded `Section 9` problems.

## Entry 015 — PR #6 Round 9: Inline Per-Question Reveals, Analogy-Aligned Clock Widget & Selective Symbolic Drills (2026-11-22)

- **Trigger (`PR #6`, Round 9 — 8 inline comments `#4658225845`, `#4658227171`, `#4658232645`, `#4658234666`, `#4658264735`, `#4658276920`, `#4658290578`, `#4658293030`)**:
  - **Monolithic Bottom-Only Exercise Reveals & Undefined Answer Notation (`U1`, `U2`)**: Every `#### Exercise` dumped all answers into one shared bottom `<details>` block instead of per-question/sub-part toggles, and `Exercise 2.1` Solution 6 introduced `\gcd()` without defining it in prose.
  - **Delayed Visual Metaphor & Meta-Pedagogical Widget Badge (`U3`, `U4`)**: Modular clock-face wraparound debuted 85 lines before `<ModularRingAdder />`, and `ModularRingAdder.vue` displayed an unnecessary `"Intuition Builder"` badge.
  - **Low-Value Arithmetic Drill Inflation & Missing Symbolic Algebra (`U5`, `U7`)**: Round 5's blanket drill quota inflated Chapter 1 to 12 routine numeric drills (`87` questions, `0` symbolic algebraic manipulation items, several verbatim-repeating prose/widget examples).
  - **Code-Before-Derivation Inversion & Premature Microarchitecture Leak (`U6`, `U8`)**: `sign_extend` (`L529`) appeared ahead of the XOR-and-subtract derivation, and `Section 4.1` (`L586`) leaked a 5-stage `barrel shifter` cascade inside an ISA contract chapter.
- **Root Cause & Systemic Healing (Non-Cheating)**:
  1. Replaced blanket exercise quotas with selective high-signal/symbolic-algebra drill rules in `GEMINI.md`, `apex-textbook-author/SKILL.md`, and `rubric_{cold_reader,math_editor,macro_critic,visual_critic}.md`; added explicit anti-pendulum guidance in `apex-skill-healer/SKILL.md`, a novel-input Pass-2 rule, `<= 50`-word bullet caps plus per-question `<details>` enforcement in `scripts/check_book.py`, and `<system>__<slug>` freshness checks in `scripts/build_review_plan.py`.
  2. Proved `8 / 8` (`100%`) first-run blind recall across `check_book.py` and the isolated frozen-prompt Step 2 panel on untouched `99a2427`, surfacing bonus catches (heading alignment, `div`/`divu` zero sentinels before code slices, floor notation ordering, `u32` negative-masking entailment, and exponent-vs-power precision).
  3. Added `<UnsignedClockRing />` right below the clock-face introduction (with WCAG dark-mode active-slot label contrast via `var(--vp-c-bg)`), removed the filler badge and clarified presets in `ModularRingAdder.vue`, removed cycle copy from `XapexMacDatapath.vue`, styled nested `<details>` toggles in `custom.css`, reordered `sign_extend`, `trunc_div_s32`, and split `sat32`/`s16` code slices after their derivations, eliminated `barrel shifter`/`single-cycle`/clock-cycle abstraction leaks and stacked Section 5/6 acronyms, pruned repetitive drills (`12` $\to$ `5`), upgraded `Exercise 2.2` to **Modular Algebra Manipulations**, added symbolic algebra parts to `Exercises 4.1–4.3`, and converged the sharded clean-room panel (`ZERO P0/P1/P2 DEFECTS FOUND`).

## Entry 016 — PR #6 Round 10: 3-Tier Triage, Cohesive Bitwise Primitives & Proportional Table Lead-Ins (2026-11-22)

- **Trigger (`PR #6`, Round 10 — 4 inline comments `#4659256461`, `#4659261158`, `#4659332628`, `#4659373995`)**:
  - **Hyper-Specific Rule Risk (`U1` `op2_u`, `U4` `neg` container vs. value)**: Local naming and table-cell phrasing tweaks (`op2` vs. `op2_s`, `u32(0 - rs1_u)` vs. signed `-1`) risked forcing chapter-specific overfitting into global rubrics if forced through mandatory Step 2 recall.
  - **Disproportionate Table Lead-In (`U2`)**: Section 4.1 devoted three full sentences ahead of a 7-row multi-category ALU table strictly to `shamt` packing while skipping integer comparisons and bitwise gates.
  - **Scattered Foundational Bitwise Primitives (`U3`)**: Elementary operators (`&`, `~`, `|`, `^`, `<<`, `>>`) appeared piecemeal across Sections 2.2–3.4 without a concise foundational reference table, and `1 << 31` appeared before `<<` was introduced.
- **Root Cause & Systemic Healing (Option A — Zero Overfitting)**:
  1. Upgraded `apex-skill-healer/SKILL.md` and `GEMINI.md` to 3-tier triage (**Tier 0** mechanical typos, **Tier 1** local editorial polish $\to$ Step 3 directly without per-chapter rule files, **Tier 2** universal cross-discipline rules $\to$ Steps 1–4 + Step 2 blind recall).
  2. Classified `U1`/`U4` as Tier 1 and `U2`/`U3` as Tier 2; added domain-agnostic proportional table-lead-in and cohesive elementary-primitive rules across `GEMINI.md`, `apex-textbook-author/SKILL.md`, `rubric_cold_reader.md`, `rubric_math_editor.md`, and `rubric_macro_critic.md`.
  3. Proved `100%` Step 2 blind recall on untouched `4f047b1` (`Cold-Reader 3/5` caught `U2` as P1 + `rs2_u == 0` bonus; `Global Macro Critic` caught `U3` as P1 + forward `<<`; `Cold-Reader 1/5` flagged Python's infinite-width two's-complement premise on `u32`).
  4. Added Section 2.2 (`### Bitwise Wire Gates and Bit Shifts`), removed redundant downstream operator re-definitions, rebalanced Section 4.1 around `op2_u`/`op2_s` and all four operation categories, clarified raw `u32` storage vs. `s32` interpretation (`neg`), fixed `rs2_u == 0`, and converged cleanly (`ZERO P0/P1/P2 DEFECTS FOUND`).

## Entry 017 — PR #6 Round 11: SVG-First Visuals, Single-Title Figures, Proof Economy & Full-Chapter Tier 2 Sweeps (2026-11-23)

- **Trigger (`PR #6`, Round 11 — 2 inline comments `#4659858767`, `#4659862365` + holistic review feedback)**:
  - **Text-Card Calculator Widgets (`U1`)**: Five `.vue` widgets (`RightShiftComparator`, `SignExtensionWidener`, `RiscvFormatMatrix`, `Product64Inspector`, `XapexMacDatapath`, plus `RiscvBitfieldDecoder`) used HTML text-box arithmetic cards instead of genuine visual `<svg>` wire/lane/geometry schematics.
  - **Duplicate Widget Titles (`U2`)**: Every widget rendered a header pill badge (`.hw-badge`) directly beside its main title, creating two competing titles on every figure.
  - **Bloated Proofs, Dense Prose Worked Examples & Partial-Shard Blind Spots (`U3`)**: One-sided *"don't skip steps"* rubric wording encouraged multi-block symbolic ceremony in Sections 4.2/4.5/4.6/7.2, worked numeric/hex traces stayed crammed inside prose walls (Sections 5.3, 4.2, 4.6), and earlier Tier 2 rounds only ran partial-shard sweeps instead of sweeping all shards across the full chapter.
- **Root Cause & Systemic Healing (Non-Cheating, No Brittle Class Bans)**:
  1. Updated `GEMINI.md`, `apex-textbook-author/SKILL.md`, `rubric_visual_critic.md`, `rubric_math_editor.md`, `rubric_cold_reader.md`, and `apex-skill-healer/SKILL.md` to mandate **SVG-first** visual diagrams (banning text-only calculator cards), **one unambiguous title** per figure (avoiding brittle CSS-class bans), **proof economy** paired with step-by-step clarity, **scannable worked examples** (aligned LaTeX/tables/SVGs rather than prose walls), and **mandatory full-chapter sweeps** across all emitted shards whenever any Tier 2 rule changes.
  2. Proved `100%` first-run full-chapter blind recall across all 12 subagents (`Shards 1–5` + `Global Macro` + `Visual Critic`) on untouched `7926663` (zero extra prompt tweaks), catching every dual-title badge, every text-card calculator, bloated derivations in Sections 4.2/4.5, dense Section 5.3 hex/alarm prose walls, and numerous latent defects across Sections 2–9.
  3. Rebuilt all interactive Chapter 1 diagrams as vector `<svg>` schematics (`UnsignedClockRing`, `ModularRingAdder`, `RiscvFormatMatrix`, `SignExtensionWidener`, `RightShiftComparator`, `TruncatingDivisionComparator`, `XapexMacDatapath`, `RiscvBitfieldDecoder`, `OracleStepTracer`), replaced `Product64Inspector` with static `<Product64SplitDiagram />` plus added static `<LuiBiasCarryDiagram />` and `<TimerRolloverTearDiagram />`, stripped all `.hw-badge` dual titles and uppercase `.hw-label` corruption, simplified Sections 4.2/4.5/4.6/7.2 proofs, lifted Section 5.3/4.x worked traces into aligned LaTeX/SVGs, and fixed all Step 2 + Step 3 clean-room findings.

## Entry 018 — PR #10 Round 1: Visible Examples, Stateless-First Carry Visuals, and Unified ± Proofs (2026-11-24)

- **Trigger (`PR #10`, Round 1 — 3 preview-anchored issue comments `#7151050552`, `#7151050878`, `#7151051235`)**:
  - **Mid-Chapter Quiz Toggles (`U1`)**: Chapter 1 used mid-chapter `#### Exercise` drill sections with `<details>` solution toggles in Sections 2 and 4 instead of visible inline `#### Example` worked examples, duplicating end-of-chapter self-test practice in `## 9. Problems`.
  - **Carry-Free Ordering & Unillustrated Wrap-Around (`U2`)**: Section 2.1 introduced carry-coupled binary addition and abstract Euclidean remainder wrap-around before stateless `Bitwise Wire Gates and Bit Shifts`, omitted an explicit column-carry definition and diagram showing dropped `c_4` carry-out before modulo wrap-around, and defined **modulus scaling** early before its first Section 4 (`lui`/`mulh*`) consumers.
  - **Symmetric Congruence Duplication (`U3`)**: `Shared Adder, Negation, and Left-Shift Circuits` proved `Sign-Agnostic Addition Congruence` (`+`) and `Sign-Agnostic Subtraction Congruence` (`-`) as two nearly identical consecutive derivations instead of one unified `±` item.
- **Root Cause & Systemic Healing (Tier 2 — Zero Overfitting)**:
  1. Updated `GEMINI.md`, `apex-textbook-author/SKILL.md`, `apex-couch-mentor/SKILL.md`, `rubric_cold_reader.md`, `rubric_math_editor.md`, `rubric_macro_critic.md`, and `rubric_diff_guardian.md` to replace mid-chapter `#### Exercise` + `<details>` drills with selective visible `#### Example` worked examples (keeping self-test practice in `## <N>. Problems`), mandate stateless/carry-free-first ordering with upfront bit-level mechanism visuals before wrap-around abstractions, and collapse identical symmetric-operator (`+`/`-`) derivations into unified `±` proofs.
  2. Tightened deterministic gates (`scripts/check_book.py`, `scripts/chapter_index.py`, `scripts/build_review_plan.py`, `scripts/tests/test_self_healing_gates.py`) to reject mid-chapter `#### Exercise` headings and mid-chapter `<details>` toggles outside `## <N>. Problems`.
  3. Verified `100%` Step 2 blind subset recall across 14 untouched `163ab0f` subagents (`U1`–`U3` all flagged without hints) plus zero false regressions (`check_book.py`, `pytest`, `ruff`, `mypy`, and `check_visuals.py` all green).
  4. Reordered `Bitwise Wire Gates and Bit Shifts` ahead of `Unsigned Integers, Binary Addition, and Modular Congruence`, added column-carry conservation plus interactive `<BinaryAdditionCarryDiagram />` before Euclidean division, deferred **modulus scaling** to `Full 32-Bit Constant Construction`, merged `Sign-Agnostic Addition and Subtraction` via `±`, converted `Exercise 2.1`–`4.3` into visible `Example 2.1`–`4.3` (moving the general $k$-bit carry-bias proof into `Problem 1` item 3), fixed `Product64SplitDiagram.vue`, `XapexMacDatapath.vue`, and `MermaidDiagram.vue` dark-mode rendering, and converged Round 1 -> Round 2 -> Round 3 to `ZERO P0/P1/P2 DEFECTS FOUND` across all emitted review tasks.
