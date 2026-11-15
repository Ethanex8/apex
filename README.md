# Apex: Building a Walking Robot Dog From Scratch

Build every layer of a safe, living-room-sized (about 2.5 kg) autonomous robot dog from blank files—your own programmable-silicon CPU & 6-layer circuit board (`brain`), force-controlled electric muscles (`drive`), smart surge/breaker power board (`power`), single hopping leg (`limb`), simulator-trained 4-legged walker (`walker`), and stereo camera eyes (`sight`)—one small, phone-reviewable step at a time.

- **Target Machine**: About 2.5 kg Desktop Research Class (roughly 35 cm long, < 22V touch-safe power, < 2.5 N·m finger-safe joints)
- **Estimated Cost**: About \$1,495 for robot parts across roughly 12 months (about \$125/mo), plus about \$310–\$540 for reusable bench tools if needed
- **Workflow**: **154 / 186 steps (`83%`)** built by AI agents & verified in simulation or automated board checks for mobile **couch review**, paired with **32 batched weekend bench sessions**.

---

## Active Step Queue

**Current Focus**: **`brain-01`** (🛋️ Couch · 🔍 In Review) — **Hardware Simulator Toolchain & Golden RISC-V Reference Emulator**

- **First Principles**: Instruction bit-field decoding, architectural CPU state (Program Counter + 32 registers + Control/Status Registers), two's complement arithmetic & comparing real hardware against a golden software oracle
- **Verification Gate**: `uv run --with pytest --with pytest-cov pytest --cov=systems/brain/sim --cov-report=term-missing --cov-fail-under=95 systems/brain/tb/test_oracle.py && which verilator yosys nextpnr-himbaechel`

```bash
python3 scripts/step.py status          # Progress across all 6 systems
python3 scripts/step.py next            # Inspect next pending step & verification gate
python3 scripts/check_code.py           # Run AST docstring/modularity, Ruff, and ShellCheck gates
python3 scripts/build.py --check        # Validate roadmap invariants, book sync & zero doc drift
```

---

## The 6 Zero-Throwaway Systems

| # | System | What It Builds | Steps (Done / Total) | Couch / Bench | Timeline |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **1** | [**`brain`**](./systems/brain/) | Custom CPU on FPGA, 6-Layer Circuit Board, C Compiler & Real-Time OS | `░░░░░░░░` **0 / 42** | 36 / 6 | 10–12 weeks (8–12 hr/wk) |
| **2** | [**`drive`**](./systems/drive/) | Force-Controlled Brushless Motor Driver & 8:1 Gearbox (Electric Muscle) | `░░░░░░░░` **0 / 30** | 24 / 6 | 7–8 weeks |
| **3** | [**`power`**](./systems/power/) | Smart Power Distribution, Soft Startup & Electronic Breaker Spine | `░░░░░░░░` **0 / 24** | 19 / 5 | 5–6 weeks |
| **4** | [**`limb`**](./systems/limb/) | 3-Joint Force-Controlled Leg & Tabletop Hopping Stand | `░░░░░░░░` **0 / 28** | 23 / 5 | 6–7 weeks |
| **5** | [**`walker`**](./systems/walker/) | 4-Legged Walking Robot Dog (Physics Balance + Simulator-Trained AI) | `░░░░░░░░` **0 / 34** | 28 / 6 | 8–10 weeks |
| **6** | [**`sight`**](./systems/sight/) | Synchronized Stereo Camera Eyes, 3D Room Mapping & Navigation Head | `░░░░░░░░` **0 / 28** | 24 / 4 | 6–8 weeks |

---

## Repository Guide

- [**`Apex Interactive Textbook (GitHub Pages)`**](https://ethanex8.github.io/apex/) — 6-volume VitePress engineering textbook ([`book/`](./book/index.md)) publishing `systems/*/chapters/*.md` with auto-synced repo code transclusions & hardware widgets.
- [**`VISION.md`**](./VISION.md) — Two-Brain architecture, locked hardware/protocol interfaces, home safety & parts budget.
- [**`ROADMAP.md`**](./ROADMAP.md) — Full phase breakdowns, ordering schedule & all 186 step checklists.
- [**`roadmap.yaml`**](./roadmap.yaml) — Canonical declarative source of truth for systems, steps & review state.
- [**`systems/`**](./systems/brain/README.md) — Subsystem workspaces (`brain`, `drive`, `power`, `limb`, `walker`, `sight`).
- [**`scripts/`**](./scripts/step.py) — [`step.py`](./scripts/step.py), [`build.py`](./scripts/build.py), [`sync_book.py`](./scripts/sync_book.py), [`check_book.py`](./scripts/check_book.py), and [`check_code.py`](./scripts/check_code.py) lifecycle, anchor-sync, and quality gates.

---

## How Couch-to-Silicon Works

1. **Agent Implements & Verifies One Atomic Step (roughly 50–150 LOC)**: Runs real `Verilator` digital simulations, `Yosys`/`nextpnr` FPGA builds, KiCad circuit-board checks (`ERC`/`DRC`), trace-impedance solvers, `MuJoCo` physics, or `pytest` inside the VM.
2. **Multi-Pass Interactive Textbook Chapter (`30–60 min`)**: Alongside each step, a 4-pass authoring pipeline produces an unhurried textbook chapter in `systems/<system>/chapters/` published to GitHub Pages with auto-synced repo code and interactive explorers.
3. **Ask Why, Then `LGTM`**: Review a calm mobile summary + full rendered chapter; interrogate any derivation or trade-off before approving Step `N`.
