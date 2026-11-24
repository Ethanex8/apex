# Apex Technical Artifact Authoring Calibration Log

Persistent ledger of code/testbench review lessons and audit blind spots graduated into [SKILL.md](../../.agents/skills/apex-artifact-author/SKILL.md) and [scripts/check_code.py](../../scripts/check_code.py).

## Entry 001 — `brain-01` Oracle & Testbench Audit (2026-11-16)

- **Trigger**: Inline code review and Staff-Engineer audit of `systems/brain/sim/oracle.py` and `systems/brain/tb/test_oracle.py`.
- **Lessons & Upstream Fixes**:
  1. **Pedagogical Inline `#` Why-Comments**: Removing large code dumps from chapters requires architectural state fields, hardware register masks, `WARL` rules, host-language sign/mask nuances (e.g., unsigned `MASK32 ^` instead of negative `~` complements), and MMIO width guards to live clearly right next to the Python/SV/C lines they govern.
     - *Healed By*: Added Pass 2 & Pass 3 inline commentary grading criterion in `SKILL.md`.
  2. **Hardware Spec Bit-Alignment Precision**: `_take_trap` must enforce `IALIGN=32` (`pc & 0xFFFF_FFFC`) on `mepc`, and test cases triggering trap handlers sequentially must account for cumulative interrupt-enable side effects (`MIE + MEIE + MEIP`) so tests do not accidentally fire unintended traps before `EBREAK`.
     - *Healed By*: Updated `oracle.py` (`100%` line coverage across `684/684` statements in `test_oracle.py`) and encoded adversarial edge-case coverage rules in Pass 3.

## Entry 002 — Textbook-Grade Python Readability & Literary Code Audit (`U7`, 2026-11-16)

- **Trigger**: User critique asking to scrutinize Python code readability across `systems/brain/sim/oracle.py`, `systems/brain/tb/test_oracle.py`, and `scripts/` with the same rigor applied to prose.
- **What Was Missed Upstream**:
  1. Single code auditor focused on functional correctness and missed **literary readability**: raw hex opcodes (`0x37`, `0x13`, `0x33`, `0x73`) in dispatchers/tests, opaque 3/4-element positional return tuples (`tuple[int, int, int, bool]`, `tuple[int, int, int]`), inconsistent `_exec_*` fault signaling (`None` vs. `StepTrace`), duplicated truncation division / MMIO guard logic, local imports, and cramped `assert a and b and c` lines.
- **Healed By**:
  1. Hardened `scripts/check_code.py` to reject `> 2`-item positional tuple return annotations, nested local imports (`# code-gate: allow-local-import`), and compound `assert ... and ...` statements in `test_*.py` (+ regression tests in `scripts/tests/test_self_healing_gates.py`).
  2. Split Pass 3 into **2 parallel specialist `research` subagents** (*Architecture & Spec Auditor* + *Code Readability & Literary Clarity Critic*) with post-refactor re-review convergence.
  3. Refactored `scripts/check_book.py` (`FenceBlock`, `ChapterValidationResult`), `scripts/step.py` (`BookChapterMatch`), `oracle.py` (`OPCODE_*`, `F3_*`, `F7_*`, `ExecOutcome`, `trunc_div_s32`, `_check_clint_access`, `_check_uart_access`), and `test_oracle.py` (readable destination-first instruction builders, zero dead reads/resets, single-invariant asserts).
