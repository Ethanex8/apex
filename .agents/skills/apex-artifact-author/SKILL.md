---
name: apex-artifact-author
description: Author and refactor Apex Python, Shell, SystemVerilog, and C artifacts using a mandatory 4-pass Staff-Engineer pipeline (Architecture & Modularity Blueprint, Self-Documenting Contract Implementation, 2-Specialist Parallel Audit with Convergence, and Automated AST/Ruff/ShellCheck/Coverage Verification).
---
# Apex 4-Pass Technical Artifact Authoring Skill

Use this skill for **every** code, testbench, hardware-description, firmware, and automation script (`*.py`, `*.sh`, `*.sv`, `*.c`, `*.h`) written or refactored across `scripts/` and `systems/` **before** beginning textbook chapter drafting.

## Core Quality Standard

Every line of code in Apex is both **working engineering hardware/software** and **primary textbook source code**. It must read as though reviewed by a principal hardware/systems engineer: modular, fail-fast, self-documenting, CWD-independent, free of magic literals or opaque tuple puzzles, and protected by `>= 95%` test coverage.

---

## Mandatory 4-Pass Authoring Pipeline

### Pass 1: Architecture, Naming & Failure-Mode Blueprint
Before writing code:
1. **Path-Stutter-Free Naming**: Name files for their role relative to their directory (`systems/brain/sim/oracle.py`, never `sim/rv32_oracle.py`; `systems/brain/rtl/core.sv`, never `rtl/brain_core.sv`).
2. **Single-Responsibility Modular Decomposition (`<= 80` LOC/unit)**:
   - Decompose every Python/C function and SystemVerilog `always` block into focused, cleanly named helpers of `<= 80` lines so each unit verifies one clear invariant and transcludes cleanly into the textbook.
   - Only flat, single-level opcode dispatchers may exceed 80 lines, with an explicit `# code-gate: allow-long-dispatch (<reason>)` annotation.
3. **Failure-Mode & Precondition Matrix**:
   - Enumerate all illegal encodings, alignment errors, access faults, OS/CPU mismatches, and missing prerequisites up front.
   - **Fail fast with actionable errors** naming the exact missing dependency, platform, or offending address—never leave dead/untested fallback branches.

### Pass 2: Self-Documenting Contract & Literary Readability Implementation
1. **Top-of-File Contract Header** on every `.py`, `.sh`, `.sv`, `.c`, and `.h` file (`Purpose:`, `Usage:`, `Invariants:`/`Outputs:`, plus `# Bump policy:` above pinned tool tags in shell scripts and `Ports & Clock Domain` in SV).
2. **Named Constants & Uniform Self-Documenting Contracts**:
   - Define grouped named constants for opcodes, masks, addresses, and error codes—never dispatch or build test inputs from raw magic hex/integer literals.
   - Keep sibling helpers on **one uniform return/error contract** (such as a single outcome/trace record), replace `>= 3`-item positional return tuples with `@dataclass` or `NamedTuple` (`check_code.py` rejects `> 2`-item tuple returns unless exempted), and deduplicate shared boundary/validation guard helpers.
   - Trace/interface dataclasses must document field-level width/sign semantics, and helpers should decode narrow bitfields locally.
3. **100% Docstrings, Clean Tests & Rich Inline Commentary**:
   - Keep all imports at module top (`check_code.py` flags local imports inside functions unless exempted for optional runtime dependencies).
   - Every Python class, method, and function—**including every `test_*` function**—must have a concise docstring. Build readable test stimuli in natural operand order, avoid dead setup statements, and enforce **one invariant per `assert`** in `test_*.py` (`check_code.py` rejects `assert a and b`).
   - Explain non-obvious mechanics, architectural state fields, domain register bitfield masks, fixed-width hardware vs. host-language arithmetic traps (sign replication, overflow wrapping, floor vs. truncating division), and linter pragmas inline right beside the code.
4. **CWD-Safe Paths**: Always resolve paths relative to `BASH_SOURCE[0]` (Bash) or `Path(__file__).resolve()` (Python).

### Pass 3: 2-Specialist Parallel Audit (`research` Subagents) & Convergence
Invoke **2 parallel isolated `research` subagents** (`Model: 'inherit'`, `Workspace: 'inherit'`) across all created/modified code and tests:
1. **`Architecture & Spec-Correctness Auditor`**: Audits spec/hardware edge cases, fail-fast invariants, CWD independence, hardware safety (no inferred RTL latches, reset polarity), zero dead branches, and `>= 95%` adversarial coverage.
2. **`Code Readability & Literary Clarity Critic`**: Reads code and test files cold as textbook source prose; flags magic hex literals, positional tuple returns, inconsistent sibling helper contracts, duplicated bit/guard logic, local imports, dead assertions, and cramped tests.

- **Mandatory Post-Refactor Convergence Loop**: After any edit resolving Round $r$ tickets, re-run verification and spawn **fresh clean-room Round $r+1$ specialist subagents** until zero P0/P1/P2 defects remain.

### Pass 4: Automated Static Analysis, Coverage & Book Sync Gate
Run and pass **all** checks cleanly:
```bash
python3 scripts/check_code.py
python3 scripts/sync_book.py --check
python3 scripts/check_book.py
uv run --with pyyaml python3 scripts/build.py --check
```
Plus the unit/simulation test suite with `--cov-fail-under=95` (or `Verilator`/`Yosys`/`nextpnr`). Record new lessons in `references/calibration_log.md`.