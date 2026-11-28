# Global Macro & Dependency Critic Rubric

Audit whole-document macro architecture, section balance, and consumer-driven placement using the repo's outline/chapter index (if present) alongside every subsection's opening bridge:

## 1. Macro Layering & Core-vs-Application Scoping
1. **Consumer-Driven Placement & Foundational Coherence**: Flag specialized variants taught far ahead of consumers, small sets of elementary primitives scattered piecemeal downstream instead of receiving a brief cohesive overview in core theory, and simpler stateless primitives placed after coupled multi-part mechanisms.
2. **Unintroduced Opening Motivations**: Flag any subsection whose opening paragraph justifies itself using downstream tasks, data structures, or system mechanisms not yet introduced at that point in the document.
3. **Base-Before-Custom Progression**: Verify core standard architectures complete end-to-end before custom domain extensions or project-specific optimizations.
4. **One Core Topic per Subsection**: Flag oversized `###` subsections—especially with compound "A, B, and C" headings—that pack distinct conceptual layers (such as representation, operational mechanics, and formal theory) into one block; keep small cohesive primitive sets unified in one overview.

## 2. Rule-of-Four Balance & Woven Examples
5. **End-to-End Rule-of-Four & Quantitative Balance**: Check the full document outline to confirm every section balances Words, Visuals, Numbers, and Algebra cleanly—preserving concrete invariants and quantitative contracts in later sections without either proof-wall overload or superficial API narration.
6. **Woven Examples Only (Zero Standalone Example Headings or Drills)**: Flag any standalone `### Example` / `#### Example` heading, homework drill (`#### Exercise`), closing `Problems` section, or `<details>` toggle, verifying concrete examples live woven naturally inside section prose.
7. **Heading Conciseness & Alignment**: Check every H1 (`<= 6` words) and `##`/`###` (`<= 8` words, no colons/`&`/backticks) aligns strictly with its subsection contents.
