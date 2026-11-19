# Apex: Autonomous Quadruped from Custom Silicon to Locomotion

A full-stack robotics platform engineered from first principles—comprising a custom RISC-V processor and 6-layer carrier board (`brain`), force-controlled brushless actuators (`drive`), solid-state power protection (`power`), a 3-DOF hopping leg (`limb`), simulator-trained locomotion (`walker`), and synchronized stereo navigation (`sight`).

- **Target Platform**: About 2.5 kg Desktop Research Class (about 35 cm long, < 22V touch-safe power, < 2.5 N·m finger-safe joints)
- **Estimated BOM**: About \$1,495 for robot parts across roughly 12 months (about \$125/mo), plus about \$310–\$540 for reusable bench instruments if needed
- **Scope**: **154 / 186 design & simulation steps (`83%`)** paired with **32 hardware assembly and laboratory bring-up sessions**.

---

## Active Milestone

**Current Focus**: **`brain-01`** (🛋️ Couch · 🔍 In Review) — **Hardware Simulator Toolchain & Golden RISC-V Reference Emulator**

- **First Principles**: Instruction bit-field decoding, architectural CPU state (Program Counter + 32 registers + Control/Status Registers), two's complement arithmetic & comparing real hardware against a golden software oracle
- **Verification Gate**: `uv run --with pytest --with pytest-cov pytest --cov=systems/brain/sim --cov-report=term-missing --cov-fail-under=95 systems/brain/tb/test_oracle.py && which verilator yosys nextpnr-himbaechel`

```bash
python3 scripts/step.py status          # Progress across all 6 subsystems
python3 scripts/step.py next            # Inspect next pending step & verification gate
python3 scripts/check_code.py           # Run AST docstring/modularity, Ruff, and ShellCheck gates
python3 scripts/build.py --check        # Validate roadmap invariants, book sync & doc consistency
```

---

## Subsystems

| # | Subsystem | Scope | Progress | Design / Bench | Timeline |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **1** | [**`brain`**](./systems/brain/) | Custom CPU on FPGA, 6-Layer Circuit Board, C Compiler & Real-Time OS | `░░░░░░░░` **0 / 42** | 36 / 6 | 10–12 weeks (8–12 hr/wk) |
| **2** | [**`drive`**](./systems/drive/) | Force-Controlled Brushless Motor Driver & 8:1 Gearbox | `░░░░░░░░` **0 / 30** | 24 / 6 | 7–8 weeks |
| **3** | [**`power`**](./systems/power/) | Smart Power Distribution, Soft Startup & Electronic Breaker Spine | `░░░░░░░░` **0 / 24** | 19 / 5 | 5–6 weeks |
| **4** | [**`limb`**](./systems/limb/) | 3-Joint Force-Controlled Leg & Tabletop Hopping Stand | `░░░░░░░░` **0 / 28** | 23 / 5 | 6–7 weeks |
| **5** | [**`walker`**](./systems/walker/) | 4-Legged Autonomous Quadruped (Dynamics, Balance & Learned Locomotion) | `░░░░░░░░` **0 / 34** | 28 / 6 | 8–10 weeks |
| **6** | [**`sight`**](./systems/sight/) | Synchronized Stereo Vision, 3D Mapping & Autonomous Navigation | `░░░░░░░░` **0 / 28** | 24 / 4 | 6–8 weeks |

---

## Repository Guide

- [**`Apex Interactive Textbook`**](https://ethanex8.github.io/apex/) — 8-part, 34-chapter VitePress textbook ([`book/`](./book/index.md)) compiling `systems/*/chapters/*.md` with synchronized source excerpts and interactive hardware figures.
- [**`VISION.md`**](./VISION.md) — Dual-processor architecture, electrical and protocol interface contracts, safety limits, and bill of materials.
- [**`docs/REVIEW_PROCESS.md`**](./docs/REVIEW_PROCESS.md) — 4-step isolated subset-recall PR review protocol, anti-cheating calibration gates, and workflow flowchart.
- [**`ROADMAP.md`**](./ROADMAP.md) — Phase breakdowns, procurement schedule, and all 186 step checklists.
- [**`roadmap.yaml`**](./roadmap.yaml) — Declarative manifest of subsystems, milestones, textbook outline, and verification state.
- [**`systems/`**](./systems/brain/README.md) — Subsystem workspaces (`brain`, `drive`, `power`, `limb`, `walker`, `sight`).
- [**`scripts/`**](./scripts/step.py) — [`step.py`](./scripts/step.py), [`build.py`](./scripts/build.py), [`sync_book.py`](./scripts/sync_book.py), [`check_book.py`](./scripts/check_book.py), and [`check_code.py`](./scripts/check_code.py) milestone tracking, documentation synchronization, and static checks.

---

## Engineering Methodology

1. **Incremental Specification & Simulation**: Each design milestone implements a bounded module verified in `Verilator` digital simulation, `Yosys`/`nextpnr` FPGA synthesis, KiCad electrical/layout checks (`ERC`/`DRC`), transmission-line solvers, `MuJoCo` rigid-body dynamics, or `pytest`.
2. **First-Principles Textbook Documentation**: Design milestones pair verified source code and hardware descriptions with chapters in `systems/<system>/chapters/`, linking code anchors directly to the analytical derivations.
3. **Staged Hardware Bring-Up**: Subsystems pass automated simulation and board-level verification gates before physical assembly, current-limited power-on testing, and system integration.
