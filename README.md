# Apex: Autonomous Walking Robot — From Blank Silicon to Full Autonomy

A Couch-to-Silicon, zero-throwaway engineering platform: build a custom RISC-V+MAC SoC, 6-layer PCB, scratch C compiler, preemptive RTOS, brushless FOC actuators, smart power spine, and Sim-to-Real stereo-navigated quadruped—one small, mobile-reviewable step at a time.

- **Target Machine**: ~2.5 kg Desktop Research Class (~35 cm body length, < 22V SELV, < 2.5 N·m backdrivable joints)
- **Estimated Cost**: ~$1,495 robot BOM across ~12 months (~$125/mo), plus ~$310–$540 reusable bench tools if needed
- **Workflow**: **154 / 186 steps (`83%`)** executed by AI agents & verified in simulation/DRC for mobile **couch review**, paired with **32 batched weekend bench gates**.

---

## Active Step Queue

**Current Focus**: **`brain-01`** (🛋️ Couch · ⬜ Pending) — **RTL/FPGA User-Space Toolchain & Golden RV32IM+Zicsr+MAC Reference Oracle**

- **First Principles**: Instruction bit-field encoding, architectural state (PC + 32 GPRs + CSRs), two's complement arithmetic & differential verification
- **Verification Gate**: `uv run --with pytest pytest systems/brain/tb/test_oracle.py && which verilator yosys nextpnr-himbaechel`

```bash
python3 scripts/step.py status          # Progress across all 6 systems
python3 scripts/step.py next            # Inspect next pending step & verification gate
python3 scripts/build.py --check        # Validate roadmap invariants & zero doc drift
```

---

## The 6 Zero-Throwaway Systems

| # | System | What It Builds | Steps (Done / Total) | Couch / Bench | Timeline |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **1** | [**`brain`**](./systems/brain/) | Custom RISC-V+MAC SoC, 6-Layer Spine PCB, Compiler & Real-Time OS | `░░░░░░░░` **0 / 42** | 36 / 6 | 10–12 weeks (8–12 hr/wk) |
| **2** | [**`drive`**](./systems/drive/) | 24V Brushless FOC Servo PCB & Quasi-Direct-Drive Actuator | `░░░░░░░░` **0 / 30** | 24 / 6 | 7–8 weeks |
| **3** | [**`power`**](./systems/power/) | 24V Smart Power Distribution, Pre-Charge & Solid-State E-Stop | `░░░░░░░░` **0 / 24** | 19 / 5 | 5–6 weeks |
| **4** | [**`limb`**](./systems/limb/) | 3-DOF Torque-Controlled Leg & Vertical Jumping Hopper | `░░░░░░░░` **0 / 28** | 23 / 5 | 6–7 weeks |
| **5** | [**`walker`**](./systems/walker/) | 12-DOF Dynamic Quadruped with Convex MPC & Sim-to-Real RL | `░░░░░░░░` **0 / 34** | 28 / 6 | 8–10 weeks |
| **6** | [**`sight`**](./systems/sight/) | Hardware-Synced Stereo-Inertial SLAM & Navigation Head | `░░░░░░░░` **0 / 28** | 24 / 4 | 6–8 weeks |

---

## Repository Guide

- [**`VISION.md`**](./VISION.md) — Two-Brain architecture, locked hardware/protocol interfaces, home safety & budget.
- [**`ROADMAP.md`**](./ROADMAP.md) — Full phase breakdowns, procurement schedule & all 186 step checklists.
- [**`roadmap.yaml`**](./roadmap.yaml) — Canonical declarative source of truth for systems, steps & review state.
- [**`systems/`**](./systems/brain/README.md) — Subsystem workspaces (`brain`, `drive`, `power`, `limb`, `walker`, `sight`).
- [**`scripts/step.py`**](./scripts/step.py) & [**`scripts/build.py`**](./scripts/build.py) — Step lifecycle CLI, invariant validator & Markdown generator.

---

## How Couch-to-Silicon Works

1. **Agent Implements & Verifies One Atomic Step (`~50–150 LOC`)**: Runs real `Verilator`, `Yosys`/`nextpnr`, KiCad ERC/DRC, impedance solvers, MuJoCo physics, or `pytest` inside the VM.
2. **You Review From Your Phone**: Inspect a 5-minute First-Principles Brief, interactive visual diagrams/waveforms/PCB renders, a guided PR diff, and 2–3 intuition checks.
3. **Ask Why, Then `LGTM`**: Interrogate any derivation or trade-off; the agent is blocked from starting Step $N+1$ until you approve Step $N$.
