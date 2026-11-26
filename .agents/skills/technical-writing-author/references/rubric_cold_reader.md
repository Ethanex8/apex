# Sequential Novice Cold-Reader Rubric

Read primary lines strictly from top to bottom assuming only general programming (`if`/`else`, loops, arrays, functions, structs, byte buffers) and undergraduate math/physics. Check every bullet below against prior sections and exact diagram/code insertion points:

## 1. Layering & Forward References
1. **Zero Forward References & Foundational Coherence**: Flag any symbol, operator (`&`, `|`, `^`, `<<`, `>>`), math function, mnemonic, or theorem used before definition, and flag small sets of elementary operators scattered piecemeal downstream without one brief cohesive foundational reference.
2. **Stateless-First Ordering & Defined Mechanics**: Flag coupled multi-bit or stateful mechanisms placed ahead of simpler stateless/carry-free primitives, and flag wrap-around or hardware arithmetic invoked before its bit-level mechanism is defined.
3. **Plain Introductory Operator Summaries**: Flag introductory overview prose or table cells that cram formal range inequalities, multi-environment caveats, or symbolic domain bounds ahead of the math section; state operational behavior via simple everyday analogues and defer formal bounds to derivations.
4. **Visual-First Placement & Code Audit**: Place schematic diagrams right after plain intuition, one concrete trace, and minimal visible labels—before set notation, dense formal rules, or proofs rather than last; audit widgets and code slices at insertion lines so no formulas or tricks precede derivations.
5. **Concept & Mechanic Placement**: Verify no subsection motivates itself with unintroduced downstream concepts, and verify specialized mechanics sit beside their first consuming subsystem rather than in an unrelated earlier section.
6. **Abstraction Boundaries**: Flag contract-level descriptions that leak unintroduced lower-layer ports, control pins, internal signals, or unmotivated microarchitectural implementations (specific datapath topologies, stage counts, or cycle counts) before implementation sections.
7. **No Specialist Analogies or Premature Constants**: Flag analogies from niche software specialties (databases, distributed consensus, kernel paging, managed runtimes) or project-specific clock/sizing constants inside general conceptual explanations.
8. **Actor & Phase Distinction**: When offline tooling (compiler, assembler, linker) and runtime execution both touch a mechanism, name the exact actor and phase rather than umbrella nouns ("software", "system"); skip redundant toolchain recaps where behavior is purely hardware-resident.

## 2. Intuition, Flow & Reader Empathy
9. **Intuition-First Lead-Ins (Before Theorems/Sets)**: Flag any section or subsection that introduces negative foils ("Before...", "Unlike..."), set notation (`∈ ℤ`, `∈ {0,1}`), domain quantifiers, or general theorems (`$$`) before establishing everyday plain-language intuition and a concrete numeric example.
10. **Exhaustive Branch Walkthrough Before Algebra**: When a mechanism splits across a threshold or condition (e.g. sign-extension carry or overflow trigger), trace every branch explicitly using concrete instructions, operands, and intermediate values before symbolic variables or proofs; avoid duplicating non-branching linear formulas.
11. **Unbraided & Proportional Topic Flow**: Flag non sequiturs, unintroduced mechanism leaps, missing paragraph breaks before formal proofs, separate mechanisms braided inside one item, or multi-category table lead-ins that disproportionately elaborate one narrow parameter while neglecting major table groups.
12. **Upfront Takeaways & Honest Rationales**: Flag comparative sections that bury the main takeaway after examples, or claims boasting about avoiding language constructs (`if`/`else`) without genuine cost or correctness motivation.
13. **Zero Prose-Math Walls, Bloated Proofs, or Dense Text Examples**: Flag multi-step numeric/hex examples crammed into prose blocks instead of aligned LaTeX/SVGs, exhausting multi-block symbolic detours obscuring simple mechanisms, forward section catalogs, or repetitive cross-section boilerplate.
14. **Mechanism-First Acronyms & Code-Only Backticks**: Flag detached term definitions (`— ... (**Acronym**)`), 3+ stacked new acronyms in one sentence, backticks on English acronyms/proper nouns/prose numbers, and boldface over 6 words.

## 3. Inline Example Scoping & Implementation Callouts
15. **Worked Examples Without Exercises or Problems**: Flag any exercise (`#### Exercise`), homework problem (`## <N>. Problems` / `### Problem`), or collapsible `<details>` toggle anywhere in the document, and flag missing or redundant visible inline `#### Example` blocks where non-trivial traps need step-by-step demonstration.
16. **Shared-Mechanism Elimination Callouts**: Flag dual-interpretation proofs that pass silently over why shared algebra eliminates duplicate hardware, mode bits, or extra multiplexers.
