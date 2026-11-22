# Global Macro & Dependency Critic Rubric

Audit whole-chapter macro architecture, section line-share balance, and consumer-driven placement using `docs/CHAPTER_INDEX.md` alongside subsection opening bridges:

## 1. Macro Layering & Core-vs-Application Scoping
1. **Consumer-Driven Section Placement**: Across every section in `docs/CHAPTER_INDEX.md`, check section line shares and first-consumer columns; flag any subsection teaching specialized variants or implementation mechanics unused by adjacent sections and first exercised only much later instead of beside its motivating subsystem.
2. **Unintroduced Opening Motivations**: Flag any subsection whose opening paragraph justifies itself using hardware tasks, data structures, or system mechanisms not yet introduced at that point in the chapter.
3. **Base-Before-Custom Progression**: Verify core standard architectures complete end-to-end before custom domain extensions or project-specific accelerators.

## 2. Rigor Balance & Assessment Coverage
4. **End-to-End Quantitative Balance**: Check `docs/CHAPTER_INDEX.md` to confirm later system, peripheral, trap, and verification sections derive explicit bounds or invariants rather than flattening into API narration.
5. **High-Signal Drill vs. Problem Scoping**: Flag repetitive routine arithmetic `#### Exercise` drills on straightforward operations already explored by widgets/`## <N>. Problems`, check that algebra-heavy chapters include symbolic algebraic manipulation practice, and confirm `## <N>. Problems` covers every promised system section.
6. **Heading Conciseness & Alignment**: Check every H1 (`<= 6` words) and `##`/`###` (`<= 8` words, no colons/`&`/backticks outside `Exercise`/`Problem` labels) aligns strictly with its subsection contents.
