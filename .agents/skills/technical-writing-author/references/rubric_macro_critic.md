# Global Macro & Dependency Critic Rubric

Audit whole-document macro architecture, section balance, and consumer-driven placement using the repo's outline/chapter index (if present) alongside every subsection's opening bridge:

## 1. Macro Layering & Core-vs-Application Scoping
1. **Consumer-Driven Placement & Foundational Coherence**: Flag specialized variants taught far ahead of consumers, small sets of elementary operators/primitives scattered piecemeal downstream instead of receiving a brief cohesive overview in core theory, and simpler stateless/carry-free primitives placed after coupled multi-bit mechanisms or wrap-around abstractions.
2. **Unintroduced Opening Motivations**: Flag any subsection whose opening paragraph justifies itself using downstream tasks, data structures, or system mechanisms not yet introduced at that point in the document.
3. **Base-Before-Custom Progression**: Verify core standard architectures complete end-to-end before custom domain extensions or project-specific optimizations.
4. **One Core Topic per Subsection**: Flag oversized `###` subsections—especially with compound "A, B, and C" headings—that pack distinct conceptual layers (such as representation, bit-level mechanics, and algebraic theory) into one block; keep small cohesive primitive sets unified in one overview.

## 2. Rigor Balance & Example Coverage
5. **End-to-End Quantitative Balance**: Check the full document outline to confirm later system, integration, and verification sections derive explicit bounds or invariants rather than flattening into superficial API narration.
6. **Selective Inline `#### Example` Scoping (No Problem Sets)**: Flag any homework drill (`#### Exercise`), closing `Problems` section, or `<details>` toggle, and verify inline `#### Example` blocks focus strictly on genuinely non-trivial algebra, boundary traps, or counterexamples rather than duplicating derivations or verification tables.
7. **Heading Conciseness & Alignment**: Check every H1 (`<= 6` words) and `##`/`###` (`<= 8` words, no colons/`&`/backticks) aligns strictly with its subsection contents.
