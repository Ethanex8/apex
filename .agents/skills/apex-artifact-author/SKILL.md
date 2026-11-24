---
name: apex-artifact-author
description: Author and refactor Apex Python, Shell, SystemVerilog, C, Assembly, and simulator artifacts using a mandatory 4-pass Staff-Engineer pipeline (Architecture & Modularity Blueprint, Self-Documenting Contract Implementation, Sharded Frozen-Prompt 2-Specialist Audit with Convergence, and Automated AST/Ruff/mypy/ShellCheck/RTL/C/Coverage Verification).
file_names:
    - references/rubric_code_arch.md
    - references/rubric_code_clarity.md
---
# Apex 4-Pass Technical Artifact Authoring Skill

Use this skill for **every** code, testbench, hardware-description, firmware, widget simulator, and automation script (`*.py`, `*.sh`, `*.sv`, `*.svh`, `*.c`, `*.h`, `*.S`, `*.vue`) written or refactored across `scripts/`, `systems/`, and `book/` **before** textbook chapter drafting.

## Core Quality Standard

Every line of code in Apex is both **working engineering hardware/software** and **primary textbook source code**: modular (`<= 80` LOC/unit), fail-fast, self-documenting, CWD-independent, free of magic literals or positional tuple puzzles, statically typed (`mypy`), and protected by `>= 95%` test coverage.

---

## Mandatory 4-Pass Authoring Pipeline

### Pass 1: Architecture, Naming & Failure-Mode Blueprint
1. **Path-Stutter-Free Naming**: Name files for their role relative to their directory (`systems/brain/sim/oracle.py`, never `sim/rv32_oracle.py`; `systems/brain/rtl/core.sv`, never `rtl/brain_core.sv`).
2. **Single-Responsibility Decomposition (`<= 80` LOC/unit)**: Split every Python/C function and SystemVerilog `always` block into focused helpers of `<= 80` lines (flat opcode dispatchers may use `#` / `// code-gate: allow-long-dispatch (<reason>)`).
3. **Failure-Mode Matrix**: Enumerate illegal encodings, alignment errors, access faults, clock/reset hazards, and missing prerequisites up front; fail fast with actionable errors and zero dead branches.

### Pass 2: Self-Documenting Contract & Literary Readability Implementation
1. **Top Contract Header**: Include `Purpose:`, `Usage:`, and `Invariants:`/`Outputs:` on all code files, `Ports:`/`Clock Domain` on `.sv` modules with ports, `# Bump policy:` on pinned tags, and `#pragma once`/`#ifndef` guards on `.h` headers.
2. **Named Constants & Uniform Contracts**: Group named constants (zero magic hex literals), keep sibling helpers on one uniform return/error contract (`@dataclass`/`NamedTuple`, no `> 2`-item positional tuples), and document bit widths/signs on interface structs.
3. **100% Docstrings, Clean Tests & Why-Comments**: Keep imports at module top, document every class/method/function/`test_*` test, enforce one non-tautological invariant per `assert`, explain non-obvious hardware/math traps inline, and resolve paths from `BASH_SOURCE[0]` or `Path(__file__).resolve()`.

### Pass 3: Frozen-Prompt Sharded Audit (`research` Subagents) & Convergence
Generate the deterministic sharded manifest before spawning reviewers:
```bash
python3 scripts/build_review_plan.py --code <file1> [<file2> ...] [--base-ref <pre_fix_sha>]
```
- **Execute Emitted Tasks Verbatim**: Run `Architecture & Spec-Correctness Auditor` (`rubric_code_arch.md`) and `Code Readability & Literary Clarity Critic` (`rubric_code_clarity.md`) across every code shard (plus `Diff & Flow Regression Guardian` when `--base-ref` is set) with zero custom steering.
- **Convergence Loop**: After Round $r$ edits, re-run verification and converge fresh clean-room reviewers via `--base-ref <pre_fix_sha> --changed-since <round_r_sha>` until zero P0/P1/P2 defects remain.

### Pass 4: Automated Static Analysis, Coverage & Calibration Gate
Run and pass **all** checks cleanly:
```bash
python3 scripts/check_code.py
python3 scripts/sync_book.py --check
python3 scripts/check_book.py
uv run --with pyyaml python3 scripts/build.py --check
```
Plus the unit/simulation test suite with `--cov-fail-under=95` (or `Verilator`/`Yosys`/`nextpnr`/`kicad-cli`). Record substantive lessons in `docs/calibration/apex-artifact-author.md`.