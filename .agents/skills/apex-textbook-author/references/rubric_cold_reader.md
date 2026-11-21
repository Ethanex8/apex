# Sequential Novice Cold-Reader Rubric

Read primary shard lines strictly from top to bottom assuming only general programming (`if`/`else`, loops, arrays, functions, structs, byte buffers) and undergraduate math/physics. Check every bullet below against the **Prior-Section Ledger**, **previous overlap lines**, and exact widget/slice insertion points:

## 1. Layering & Forward References
1. **Zero Forward References**: Flag any symbol, operator (`&`, `|`, `^`, `<<`, `>>`), mnemonic, helper function, or theorem used before it is defined in the Prior-Section Ledger, overlap lines, or earlier in this shard.
2. **Widget & Slice Insertion Audit**: Inspect every `.vue` widget (`<Tag />`) and `<<<` code slice *at its exact Markdown insertion line* and flag any preset, formula, label, helper, or idiom not yet introduced above that line.
3. **Foundational Property Placement**: Flag foundational representation properties (range, uniqueness, wrap rules) wedged mid-stream inside downstream hardware or algorithm sections instead of right where that representation is defined.
4. **Abstraction Boundaries**: Flag pre-hardware architectural descriptions that leak unbuilt lower-layer hardware ports, control pins, internal signals, or physical implementation tricks.
5. **No Specialist Analogies or Premature Constants**: Flag analogies from niche software specialties (databases, distributed consensus, kernel paging, managed runtimes) or project-specific clock/sizing constants inside general conceptual explanations.

## 2. Intuition, Flow & Reader Empathy
6. **Plain Intuition Before Mechanics**: Flag proofs, boundary cases, or formal blocks that open cold into symbolic manipulation without 1–2 plain, low-symbol sentences stating what is shown and why it matters here.
7. **Unbraided Topic Flow**: Flag non sequiturs, unintroduced mechanism leaps, missing paragraph breaks between concrete examples and formal proofs, or separate mechanisms braided inside one bullet or paragraph.
8. **Upfront Takeaways & Honest Rationales**: Flag comparative sections that bury the main takeaway after examples, or claims boasting about avoiding language constructs (`if`/`else`) without genuine cost or correctness motivation.
9. **Zero Prose-Math Walls or Boilerplate**: Flag consecutive prose sentences crammed with dense symbolic clauses, forward section catalogs, or repetitive cross-section boilerplate (`Section X's ... corollary`, repeated per-item uniqueness restatements).
10. **Mechanism-First Acronyms & Code-Only Backticks**: Flag detached term definitions (`— ... (**Acronym**)`), 3+ stacked new acronyms in one sentence, backticks on English acronyms/proper nouns/prose numbers, and boldface over 6 words.

## 3. Inline Drill Scoping
11. **Math/Encoding/Bound Drills Only**: Flag mathematical, encoding, or bound-derivation subsections missing a `6–8` part inline `#### Exercise <S.K>: <Title>` drill, while leaving pure hardware-interface subsections clean.
12. **Hardware Polymorphism Callouts**: Flag dual-interpretation proofs that pass silently over why shared algebra eliminates duplicate hardware, mode bits, or extra multiplexers.
