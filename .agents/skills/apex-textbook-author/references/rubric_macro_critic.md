# Global Macro & Dependency Critic Rubric

Audit whole-chapter macro architecture, section line-share balance, and consumer-driven placement using `docs/CHAPTER_INDEX.md` alongside subsection opening bridges:

## 1. Macro Layering & Core-vs-Application Scoping
1. **Consumer-Driven Placement & Foundational Coherence**: Using `docs/CHAPTER_INDEX.md`, flag specialized variants taught far ahead of consumers, small sets of elementary operators/primitives scattered piecemeal downstream instead of receiving a brief cohesive overview in core theory, and simpler stateless/carry-free primitives placed after coupled multi-bit mechanisms or wrap-around abstractions.
2. **Unintroduced Opening Motivations**: Flag any subsection whose opening paragraph justifies itself using hardware tasks, data structures, or system mechanisms not yet introduced at that point in the chapter.
3. **Base-Before-Custom Progression**: Verify core standard architectures complete end-to-end before custom domain extensions or project-specific accelerators.

## 2. Rigor Balance & Assessment Coverage
4. **End-to-End Quantitative Balance**: Check `docs/CHAPTER_INDEX.md` to confirm later system, peripheral, trap, and verification sections derive explicit bounds or invariants rather than flattening into API narration.
5. **Selective Inline `#### Example` Scoping (No Problem Sets)**: Flag any homework drill (`#### Exercise`), closing `Problems` section, or `<details>` toggle, and verify inline `#### Example` blocks focus strictly on genuinely non-trivial algebra, boundary traps, or counterexamples rather than duplicating derivations or verification tables.
6. **Heading Conciseness & Alignment**: Check every H1 (`<= 6` words) and `##`/`###` (`<= 8` words, no colons/`&`/backticks) aligns strictly with its subsection contents.
