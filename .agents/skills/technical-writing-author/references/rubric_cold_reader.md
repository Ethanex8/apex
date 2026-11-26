# Sequential Novice Cold-Reader Rubric

Read primary lines strictly from top to bottom assuming only general programming (`if`/`else`, loops, arrays, functions, structs, byte buffers) and undergraduate math/physics. Check every bullet below against prior sections and exact diagram/code insertion points:

## 1. Layering & Forward References
1. **Zero Forward References & Foundational Coherence**: Flag any symbol, operator (`&`, `|`, `^`, `<<`, `>>`), math function, mnemonic, or theorem used before definition, and flag small sets of elementary operators scattered piecemeal downstream without one brief cohesive foundational reference.
2. **Stateless-First Ordering & Defined Mechanics**: Flag coupled multi-bit or stateful mechanisms placed ahead of simpler stateless/carry-free primitives, and flag wrap-around or hardware arithmetic invoked before its bit-level mechanism is defined.
3. **Plain Introductory Operator Summaries**: Flag introductory overview prose or table cells that cram formal range inequalities, multi-environment caveats, or symbolic domain bounds ahead of the math section; state operational behavior via simple everyday analogues and defer formal bounds to derivations.
4. **Visual, Metaphor & Code-Slice Insertion Audit**: Inspect every diagram, interactive widget, and code slice *at its exact insertion line*: flag premature symbols/formulas, non-obvious code tricks shown *before* prose derives them, wrap-around abstractions lacking an upfront mechanism visual, and core metaphors left unillustrated until later.
5. **Concept & Mechanic Placement**: Verify no subsection motivates itself with unintroduced downstream concepts, and verify specialized mechanics sit beside their first consuming subsystem rather than in an unrelated earlier section.
6. **Abstraction Boundaries**: Flag contract-level descriptions that leak unintroduced lower-layer ports, control pins, internal signals, or unmotivated microarchitectural implementations (specific datapath topologies, stage counts, or cycle counts) before implementation sections.
7. **No Specialist Analogies or Premature Constants**: Flag analogies from niche software specialties (databases, distributed consensus, kernel paging, managed runtimes) or project-specific clock/sizing constants inside general conceptual explanations.

## 2. Intuition, Flow & Reader Empathy
8. **Direct Positive Openings & Intuition**: Flag sections, paragraphs, or concept intros that introduce a mechanism by contrasting what it does *not* do, lacks, or precedes ("Before [other topic]...", "Unlike...", "Without..."), or open cold; state what it *is* and *does* directly (same-operation pipeline steps remain fine).
9. **Unbraided & Proportional Topic Flow**: Flag non sequiturs, unintroduced mechanism leaps, missing paragraph breaks before formal proofs, separate mechanisms braided inside one item, or multi-category table lead-ins that disproportionately elaborate one narrow parameter while neglecting major table groups.
10. **Upfront Takeaways & Honest Rationales**: Flag comparative sections that bury the main takeaway after examples, or claims boasting about avoiding language constructs (`if`/`else`) without genuine cost or correctness motivation.
11. **Zero Prose-Math Walls, Bloated Proofs, or Dense Text Examples**: Flag multi-step numeric/hex examples crammed into prose blocks instead of aligned LaTeX/SVGs, exhausting multi-block symbolic detours obscuring simple mechanisms, forward section catalogs, or repetitive cross-section boilerplate.
12. **Mechanism-First Acronyms & Code-Only Backticks**: Flag detached term definitions (`— ... (**Acronym**)`), 3+ stacked new acronyms in one sentence, backticks on English acronyms/proper nouns/prose numbers, and boldface over 6 words.

## 3. Inline Example Scoping & Implementation Callouts
13. **Worked Examples Without Exercises or Problems**: Flag any exercise (`#### Exercise`), homework problem (`## <N>. Problems` / `### Problem`), or collapsible `<details>` toggle anywhere in the document, and flag missing or redundant visible inline `#### Example` blocks where non-trivial traps need step-by-step demonstration.
14. **Shared-Mechanism Elimination Callouts**: Flag dual-interpretation proofs that pass silently over why shared algebra eliminates duplicate hardware, mode bits, or extra multiplexers.
