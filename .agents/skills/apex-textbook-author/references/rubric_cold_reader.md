# Sequential Novice Cold-Reader Rubric

Read primary shard lines strictly from top to bottom assuming only general programming (`if`/`else`, loops, arrays, functions, structs, byte buffers) and undergraduate math/physics. Check every bullet below against the **Prior-Section Ledger**, **previous overlap lines**, and exact widget/slice insertion points:

## 1. Layering & Forward References
1. **Zero Forward References & Foundational Coherence**: Flag any symbol, operator (`&`, `|`, `^`, `<<`, `>>`), math function, mnemonic, or theorem used before definition, and flag small sets of elementary operators scattered piecemeal downstream without one brief cohesive foundational reference.
2. **Widget, Metaphor & Code-Slice Insertion Audit**: Inspect every `.vue` widget and `<<<` code slice *at its exact insertion line*: flag premature symbols/formulas, non-obvious code tricks shown *before* prose derives them, and core visual metaphors left unillustrated until a much later figure.
3. **Concept & Mechanic Placement**: Using `docs/CHAPTER_INDEX.md`, verify no subsection motivates itself with unintroduced downstream concepts, and verify specialized mechanics sit beside their first consuming subsystem rather than in an unrelated earlier section.
4. **Abstraction Boundaries**: Flag contract-level descriptions that leak unintroduced lower-layer ports, control pins, internal signals, or unmotivated microarchitectural circuit implementations (specific datapath topologies, stage counts, or cycle counts) before hardware-implementation chapters.
5. **No Specialist Analogies or Premature Constants**: Flag analogies from niche software specialties (databases, distributed consensus, kernel paging, managed runtimes) or project-specific clock/sizing constants inside general conceptual explanations.

## 2. Intuition, Flow & Reader Empathy
6. **Plain Intuition Before Mechanics**: Flag proofs, boundary cases, or formal blocks that open cold into symbolic manipulation without 1–2 plain, low-symbol sentences stating what is shown and why it matters here.
7. **Unbraided & Proportional Topic Flow**: Flag non sequiturs, unintroduced mechanism leaps, missing paragraph breaks before formal proofs, separate mechanisms braided inside one item, or multi-category table lead-ins that disproportionately elaborate one narrow parameter while neglecting major table groups.
8. **Upfront Takeaways & Honest Rationales**: Flag comparative sections that bury the main takeaway after examples, or claims boasting about avoiding language constructs (`if`/`else`) without genuine cost or correctness motivation.
9. **Zero Prose-Math Walls, Bloated Proofs, or Dense Text Examples**: Flag multi-step numeric/hex examples crammed into prose blocks instead of aligned LaTeX/SVGs, exhausting multi-block symbolic detours obscuring simple mechanisms, forward section catalogs, or repetitive cross-section boilerplate.
10. **Mechanism-First Acronyms & Code-Only Backticks**: Flag detached term definitions (`— ... (**Acronym**)`), 3+ stacked new acronyms in one sentence, backticks on English acronyms/proper nouns/prose numbers, and boldface over 6 words.

## 3. Inline Drill Scoping & Interactive UX
11. **High-Signal Selective Drills & Per-Item Reveals**: Flag repetitive routine arithmetic drills for straightforward operations already shown in widgets/`## <N>. Problems`, missing symbolic algebraic manipulation practice where algebra underpins proofs, or monolithic bottom-only solution blocks instead of per-question/sub-part collapsible reveals.
12. **Hardware Polymorphism Callouts**: Flag dual-interpretation proofs that pass silently over why shared algebra eliminates duplicate hardware, mode bits, or extra multiplexers.
