# Apex Engineering & Couch-to-Silicon Platform Invariants

## 1. Zero-Throwaway Hardware Convergence
- **One Cohesive Machine**: Every subsystem (`brain`, `drive`, `power`, `limb`, `walker`, `sight`) must function as a verifiable standalone desktop build *and* bolt directly into the final `~2.5 kg` autonomous quadruped without hardware respins or throwaway subsystems.
- **Locked Interface Contracts**: All electrical rails (`21.9V` max `6S LiFePO4` SELV bus, regulated `5V`/`3.3V` logic rails), communication frames (dual `5 Mbps` CAN-FD actuator protocol, `sight <-> brain` framed velocity link, sub-microsecond FPGA camera sync pulse), and mechanical mounting patterns are canonically specified in `VISION.md` and `systems/*/README.md`.
- **Home-Safe by Design**: Physical hardware targets `~2.5 kg` total mass, `< 22V` touch-safe `LiFePO4` power, `< 2.5 N·m` hand-backdrivable joints, current-limited PSU-first bring-up, physical E-stop cutoffs, and turnkey PCBA/MJF/CNC manufacturing to avoid indoor solder-paste or high-temp polymer fumes.

## 2. Zero Academic Jargon & Plain-English First Principles
- **Engineering Naming Only**: Use plain-English subsystem IDs (`brain`, `drive`, `power`, `limb`, `walker`, `sight`) and sequential step IDs (`<system>-NN`). Never introduce academic course codes, credit tiers, or opaque capstone numbers.
- **Self-Contained Derivations**: Every step explains the exact math, physics, timing, or CS mechanics needed right there in plain language, paired with optional deeper book pointers (`reference_reading`) for curious readers.

## 3. Declarative Single Source of Truth (`roadmap.yaml` & `scripts/build.py`)
- **Canonical Roadmap**: `roadmap.yaml` is the single source of truth for all 6 systems, phases, atomic `couch` and `bench` steps, verification commands, first-principles concepts, home-workbench procurement gates, and step completion state (`pending`, `in_review`, `approved`).
- **Automated Compilation & Validation**: Never hand-edit `ROADMAP.md` or `README.md` directly. After modifying `roadmap.yaml` (directly or via `scripts/step.py`), always run `python3 scripts/build.py` to validate all schema, DAG acyclicity, and step-completeness invariants and regenerate `ROADMAP.md` and `README.md`, then confirm zero drift with `python3 scripts/build.py --check`.

## 4. Couch-to-Silicon Atomic Review Contract
- **Strictly One Step at a Time**: Agents execute at most one atomic step from `roadmap.yaml` per turn (`~50–150 LOC` for software/RTL steps or one bounded PCB/CAD milestone). Never bundle multiple steps together.
- **Verify Before Requesting Review**: Every `couch` step must pass its automated verification suite (`Verilator`, `Yosys`/`nextpnr`, KiCad ERC/DRC, impedance/PDN solver, MuJoCo simulation, or `pytest`) inside the workspace before entering `in_review`.
- **Mobile Review Packet + Hard Approval Gate**: Present each completed step with (1) a 5-minute First-Principles Concept Brief, (2) interactive visual diagrams/waveforms/layer renders, (3) a guided diff tour backed by a clean GitHub PR/commit, and (4) 2–3 intuition-check questions. Wait for explicit user `LGTM` before marking the step `approved` (`python3 scripts/step.py approve <step-id>`) and advancing to the next step.
