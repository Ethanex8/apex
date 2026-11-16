---
name: apex-artifact-author
description: Author and refactor Apex Python, Shell, SystemVerilog, and C artifacts using a mandatory 4-pass Staff-Engineer pipeline (Architecture & Modularity Blueprint, Self-Documenting Contract Implementation, Isolated Adversarial Subagent Audit, and Automated AST/Ruff/ShellCheck/Coverage Verification).
---

# Apex 4-Pass Technical Artifact Authoring Skill

Use this skill for **every** code, testbench, hardware-description, firmware, and automation script (`*.py`, `*.sh`, `*.sv`, `*.c`, `*.h`) written or refactored across `scripts/` and `systems/` **before** beginning textbook chapter drafting.

## Core Quality Standard

Every line of code in Apex is both **working engineering hardware/software** and **primary textbook source code**. It must read as though reviewed by a principal hardware/systems engineer: modular, fail-fast, self-documenting, CWD-independent, free of path-stuttering or magic constants, and protected by `>= 95%` test coverage.

---

## Mandatory 4-Pass Authoring Pipeline

### Pass 1: Architecture, Naming & Failure-Mode Blueprint
Before writing code:
1. **Path-Stutter-Free Naming**: Name files for their role relative to their directory (`systems/brain/sim/oracle.py`, never `sim/rv32_oracle.py`; `systems/brain/rtl/core.sv`, never `rtl/brain_core.sv`).
2. **Single-Responsibility Modular Decomposition (`<= 80` LOC/unit)**:
   - Decompose every Python/C function and SystemVerilog `always` block into focused, cleanly named helpers of `<= 80` lines so each unit verifies one clear invariant and transcludes cleanly into the textbook.
   - Never hide multi-line logic inside nested closures or dump helper functions ungrouped at the bottom of a file.
   - Only flat, single-level opcode dispatchers (like `RV32Oracle.step`) may exceed 80 lines, and only with an explicit `# code-gate: allow-long-dispatch (<reason>)` annotation.
3. **Failure-Mode & Precondition Matrix**:
   - Enumerate all illegal encodings, alignment errors, access faults, OS/CPU mismatches, and missing prerequisites up front.
   - **Fail fast with actionable errors** naming the exact missing dependency, unsupported host platform, or offending address—never leave dead/untested fallback branches (e.g., silent `else python3 -m venv` fallbacks when `uv` is required).

### Pass 2: Self-Documenting Contract Implementation
1. **Top-of-File Contract Header** on every `.py`, `.sh`, `.sv`, `.c`, and `.h` file:
   - Python: module docstring with summary, `Purpose:`, `Usage:`, and `Invariants:`/`Outputs:`.
   - Shell: banner containing `Purpose:`, `Usage:`, `Optional Environment Variables:` (if any), `Outputs:`, and an explicit `# Bump policy:` comment above any pinned tool/package tag (deriving stamps dynamically, e.g., `${tag//-/}`, never duplicating strings).
   - SystemVerilog / C: block header documenting `Purpose:`, `Ports & Clock Domain` / `API`, `Parameters`, and reset/timing invariants.
2. **100% Docstrings & Function Comments**:
   - Every Python class, method, and function—**including every `test_*` function**—must have a concise docstring stating *what architectural invariant or failure mode* it enforces or proves.
   - Trace/interface dataclasses and structs must document field-level width/sign semantics (e.g., extended load value vs. width-masked store lane), and helper functions should decode narrow bitfields locally rather than hiding them across caller parameters.
   - Add concise 1-line inline comments on non-obvious host-language bit tricks (preferring explicit masks like `0xFFFF_FFFF_0000_0000` over negative-int `~MASK32`, and noting `>>` sign-bit replication) or spec-mandated dual guards (e.g., `& ~1` followed by `& 3`).
   - Every Bash function `<name>() {` must have an explanatory `#` comment directly above it.
   - Every `# shellcheck`, `# noqa`, `# type: ignore`, and `/* verilator lint_off */` suppression must carry a plain-English reason explaining *why* the rule cannot apply cleanly.
3. **CWD-Safe Paths**:
   - Always resolve paths relative to `BASH_SOURCE[0]` (Bash) or `Path(__file__).resolve()` (Python). Never print CWD-fragile hints like `source .tools/env.sh`; print the resolved path (`source ${ENV_FILE}`).

### Pass 3: Isolated Adversarial Staff-Engineer Audit (`research` Subagent)
Invoke an isolated `research` subagent (`invoke_subagent`, `Model: 'inherit'`, `Workspace: 'inherit'`, `Role: Adversarial Staff Code Reviewer`) on all created/modified code and tests, grading against:
1. Function modularity & size (`<= 80` lines, zero god-functions or nested closures).
2. Naming clarity & logical top-to-bottom file structure.
3. Complete headers, 100% docstrings, grounded constants, and explained linter pragmas.
4. CWD-independence, fail-fast errors, and zero dead fallback branches.
5. Hardware safety (for `.sv`: zero inferred latches, synchronous reset polarity consistency, clean clock boundaries).
6. Adversarial test thoroughness (negative paths, boundary overflow/underflow, misaligned/invalid inputs, `>= 95%` line coverage).

Resolve **100%** of tickets before moving to Pass 4.

### Pass 4: Automated Static Analysis, Coverage & Book Sync Gate
Run and pass **all** checks cleanly before considering the artifact complete:
```bash
python3 scripts/check_code.py
python3 scripts/sync_book.py --check   # or run scripts/sync_book.py when updating/creating chapters
uv run --with pyyaml python3 scripts/build.py --check
```
Plus the step's unit/simulation test suite with `--cov-fail-under=95` (for Python) or `Verilator`/`Yosys`/`nextpnr` verification.
