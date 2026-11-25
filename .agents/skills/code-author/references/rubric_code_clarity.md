# Code Readability & Literary Clarity Critic Rubric

Read every code and test shard cold as clean engineering source prose alongside `SKILL.md`:

## 1. Modularity, Naming & Uniform Contracts
1. **Path-Stutter-Free Naming & `<= 80`-LOC Decomposition**: Flag redundant directory prefixes in filenames (`sim/rv32_oracle.py`), monolithic functions or logic blocks exceeding `80` lines without an explicit exemption, and mixed responsibilities.
2. **Named Constants & Zero Magic Literals**: Flag raw hex opcodes, bitmasks, register offsets, protocol magic numbers, or unexplained numeric literals inside dispatchers, state machines, or test cases instead of grouped named constants.
3. **Uniform Sibling Contracts & Zero Positional Tuple Puzzles**: Flag sibling helpers with inconsistent return/error conventions, `>= 3`-element positional tuple returns instead of `@dataclass`/`NamedTuple`/structs, and duplicated guard/decode logic.

## 2. Inline Documentation, Imports & Clean Tests
4. **Top-of-File Contract & Inline Why-Comments**: Verify `Purpose:`/`Usage:`/`Invariants:` (plus `Ports:`/`Clock Domain:` on RTL and `# Bump policy:` on pinned tags), field-level width/sign docs, explained lint pragmas, and inline comments explaining non-obvious math or edge-case traps.
5. **100% Docstrings & Clean Module Imports**: Flag missing docstrings on modules, classes, functions, methods, or `test_*` functions, and flag local imports inside functions unless explicitly exempted.
6. **Natural-Order, Single-Invariant Tests**: Flag dead setup statements, cryptic operand ordering in test builders, and compound `assert a and b` or tautological assertions instead of one crisp invariant per `assert`.
