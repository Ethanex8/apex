# Apex: Couch-to-Silicon Systems Engineering

> **A 6-Volume Interactive Engineering Textbook Built Alongside Live Verified Hardware & Code**  
> Written for experienced software and systems engineers starting with **zero prior background** in processor architecture (`RISC-V`), hardware-description languages (`SystemVerilog`), electronic circuit-board physics, motor control, or legged robotics.

<div class="book-hero-banner">
  <div class="book-hero-stat">
    <span class="stat-num">6</span>
    <span class="stat-label">Integrated Volumes</span>
  </div>
  <div class="book-hero-stat">
    <span class="stat-num">154</span>
    <span class="stat-label">Couch Chapters</span>
  </div>
  <div class="book-hero-stat">
    <span class="stat-num">32</span>
    <span class="stat-label">Bench Lab Sessions</span>
  </div>
  <div class="book-hero-stat">
    <span class="stat-num">100%</span>
    <span class="stat-label">Live-Synced Repo Code</span>
  </div>
</div>

---

## Why This Book Is Different

Most engineering books force an uncomfortable choice: either read abstract academic theory disconnected from working silicon and copper, or follow hobbyist wiring tutorials that treat processors, compilers, power electronics, and neural control policies as black-box libraries.

**Apex** builds **one cohesive, living-room-safe (`about 2.5 kg`, `< 22V`) autonomous quadruped robot** from blank files—designing the custom 32-bit processor on a programmable logic chip (**Field-Programmable Gate Array / `FPGA`**), routing the 6-layer controlled-impedance circuit board, writing the C compiler and strict-deadline Real-Time Operating System (**`RTOS`**), winding the force-controlled electric muscle loops, and training the walking policy.

Every chapter in this book obeys four strict rules:

1. **Zero Unexplained Jargon (*Mechanism First, Term Second*)**: No domain acronym, instruction mnemonic, register name, or circuit component is ever dropped cold. Every concept is anchored first in familiar software/systems primitives, derived mathematically from first principles, and only then given its standard industry name.
2. **Unhurried Textbook Pacing (`30–60 Minutes` per Chapter)**: Foundational chapters take a full hour to unpack *why* naive designs fail in physical hardware before showing *how* real silicon solves them—complete with worked bit-level traces and edge-case autopsies.
3. **Zero Code Drift (Live Transclusion)**: Code listings in every chapter are transcluded directly from the verified source files in `systems/` (`Python`, `SystemVerilog`, `C`, and `KiCad` generators) and checked in continuous integration (`scripts/check_book.py`). When tests pass, the textbook code is guaranteed to run.
4. **Interactive Hardware Explorers**: Instead of static ASCII tables alone, chapters embed live interactive workbenches—toggle bits on a 32-bit number ring, inspect instruction wire slices, and step a live CPU state machine right inside the page.

---

## Start Reading

- **[Prologue: Two-Brain Architecture & Locked Hardware Contracts](/vision)** — How the six volumes bolt together into one zero-throwaway machine without circuit-board redesigns.
- **[Volume I (`brain`) Overview](/brain/)** — Custom `RISC-V` CPU on `FPGA`, 6-Layer Circuit Board, Scratch `SysC` Compiler & Preemptive `RTOS`.
  - **[Chapter 1 (`brain-01`): The Golden ISA Contract, Fixed-Width Binary Math & Instruction Execution](/brain/01_golden_oracle_and_isa)** *(about 60 minutes · 3 interactive explorers)*

---

## The Six Volumes

| Volume | System ID | What You Design & Build | Scope |
| :---: | :--- | :--- | :--- |
| **Vol. I** | **[`brain`](/brain/)** | Custom 5-stage pipelined `RV32IM` + `Xapex mac` processor on `FPGA`, 6-layer controlled-impedance Spine circuit board, scratch `SysC` C compiler, and strict-deadline `RTOS` | 42 steps (36 chapters + 6 bench labs) |
| **Vol. II** | **[`drive`](/drive/)** | Force-controlled brushless pancake motor actuator (`20 kHz` Field-Oriented Control), 4-layer `24V` inverter board, and `8:1` backdrivable planetary gearbox | 30 steps (24 chapters + 6 bench labs) |
| **Vol. III** | **[`power`](/power/)** | Smart `6S LiFePO4` power distribution spine, soft pre-charge surge limiter, `< 5 µs` electronic circuit breaker, and Extended Kalman battery fuel gauge | 24 steps (19 chapters + 5 bench labs) |
| **Vol. IV** | **[`limb`](/limb/)** | 3-joint spatial leg kinematics (`SO(3)` / `SE(3)`), Jacobian virtual-spring impedance control, carbon-fiber leg CAD, and tabletop rail hopping | 28 steps (23 chapters + 5 bench labs) |
| **Vol. V** | **[`walker`](/walker/)** | Full 12-joint (`about 2.5 kg`) quadruped dynamics, error-state Estimator, predictive balance control, GPU-parallel reinforcement learning, and quantized sim-to-real transfer onto `brain` | 34 steps (28 chapters + 6 bench labs) |
| **Vol. VI** | **[`sight`](/sight/)** | Sub-microsecond hardware-synced stereo cameras, semi-global depth matching, visual-inertial odometry, 3D occupancy grid mapping, and autonomous obstacle navigation | 28 steps (24 chapters + 4 bench labs) |
