# Apex Technical Artifact Authoring Calibration Log

Persistent ledger of code/testbench review lessons and audit blind spots graduated into [SKILL.md](../SKILL.md) and [scripts/check_code.py](../../../../scripts/check_code.py).

## Entry 001 — `brain-01` Oracle & Testbench Audit (2026-11-16)

- **Trigger**: Inline code review and Staff-Engineer audit of `systems/brain/sim/oracle.py` and `systems/brain/tb/test_oracle.py`.
- **Lessons & Upstream Fixes**:
  1. **Pedagogical Inline `#` Why-Comments**: Removing large code dumps from chapters requires architectural state fields, hardware register masks, `WARL` rules, host-language sign/mask nuances (e.g., unsigned `MASK32 ^` instead of negative `~` complements), and MMIO width guards to live clearly right next to the Python/SV/C lines they govern.
     - *Healed By*: Added Pass 2 & Pass 3 inline commentary grading criterion in `SKILL.md`.
  2. **Hardware Spec Bit-Alignment Precision**: `_take_trap` must enforce `IALIGN=32` (`pc & 0xFFFF_FFFC`) on `mepc`, and test cases triggering trap handlers sequentially must account for cumulative interrupt-enable side effects (`MIE + MEIE + MEIP`) so tests do not accidentally fire unintended traps before `EBREAK`.
     - *Healed By*: Updated `oracle.py` (`100%` line coverage across `684/684` statements in `test_oracle.py`) and encoded adversarial edge-case coverage rules in Pass 3.
