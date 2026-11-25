---
name: code-author
description: Author and refactor clean, modular software, scripts, firmware, and hardware code using a 4-pass Staff-Engineer pipeline (Architecture & Failure-Mode Blueprint, Self-Documenting Contracts, 2-Specialist Clean-Room Audit, and Automated Static Analysis & Coverage Verification). Applies across any repository; defer to project-specific orchestration skills when present.
file_names:
    - references/rubric_code_arch.md
    - references/rubric_code_clarity.md
---
# 4-Pass Engineering Code Authoring Skill

Use this skill for **every** production module, test suite, automation script, firmware unit, simulator, or hardware description written or refactored—especially before writing accompanying documentation.

## Core Quality Standard

Write code as both **reliable engineering** and **primary source prose**: modular (`<= 80` LOC/unit), fail-fast, CWD-independent, free of magic literals or positional tuple puzzles, statically typed where supported, and verified with high-coverage tests (`>= 95%` target).

---

## Mandatory 4-Pass Authoring Pipeline

### Pass 1: Architecture, Naming & Failure-Mode Blueprint
1. **Path-Stutter-Free Naming**: Name files for their role relative to their parent directory (`sim/oracle.py`, never `sim/rv32_oracle.py`; `rtl/core.sv`, never `rtl/cpu_core.sv`).
2. **Single-Responsibility Decomposition (`<= 80` LOC/unit)**: Split functions, methods, and hardware blocks into focused helpers of `<= 80` lines (explicitly annotated flat dispatchers excepted).
3. **Failure-Mode Matrix**: Enumerate invalid inputs, boundary alignments, permission/bus faults, concurrency/reset hazards, and missing prerequisites up front; fail fast with actionable errors and zero dead fallback branches.

### Pass 2: Self-Documenting Contract & Literary Readability
1. **Top Contract Header**: Include `Purpose:`, `Usage:`, and `Invariants:`/`Outputs:` on source files (plus `Ports:`/`Clock Domain:` on RTL modules with ports, `# Bump policy:` on pinned tags, and include guards on C headers).
2. **Named Constants & Uniform Contracts**: Group named constants (zero magic hex/numeric literals), keep sibling helpers on one uniform return/error contract (`@dataclass`/`NamedTuple`/struct, no `> 2`-item positional tuples), and document bit widths/signs on interface fields.
3. **100% Docstrings, Clean Tests & Why-Comments**: Keep imports at module top, document every class/method/function/`test_*` test, enforce one non-tautological invariant per `assert`, explain non-obvious math/hardware traps inline, and resolve paths from `Path(__file__).resolve()` or `BASH_SOURCE[0]`.

### Pass 3: 2-Specialist Clean-Room Audit (`research` Subagents) & Convergence
If the repository provides a deterministic review planner (e.g. `scripts/build_review_plan.py --code`), run it and execute every emitted task verbatim; otherwise launch **2 parallel isolated `research` subagents**:
1. **`Architecture & Spec-Correctness Auditor`**: Read `references/rubric_code_arch.md` and audit spec fidelity, edge/width traps, fail-fast invariants, domain hazards, and independent adversarial tests.
2. **`Code Readability & Literary Clarity Critic`**: Read `references/rubric_code_clarity.md` and audit naming, modularity, named constants, uniform contracts, docstrings, inline why-comments, and single-invariant assertions.
- **Convergence Loop**: Resolve all P0/P1/P2 findings, re-run verification, and re-audit modified scopes with fresh clean-room reviewers (plus a diff-regression check) until zero defects remain.

### Pass 4: Automated Static Analysis, Tests & Coverage Gate
Run every repository static gate and test suite (e.g. `ruff`, `mypy`, `shellcheck`, `eslint`/`tsc`, `gcc -fsyntax-only`, `verilator --lint-only`, or repo `check_*` scripts) plus unit/simulation tests targeting `--cov-fail-under=95` where applicable.