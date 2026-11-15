# Apex: Integrated Systems Engineering

> **A Six-Volume Engineering Textbook on Custom Silicon, Embedded Systems, and Legged Robotics**  
> Written for software and systems engineers approaching processor architecture (`RISC-V`), hardware description (`SystemVerilog`), circuit-board physics, motor control, and dynamic locomotion for the first time.

<div class="book-hero-banner">
  <div class="book-hero-stat">
    <span class="stat-num">6</span>
    <span class="stat-label">Integrated Volumes</span>
  </div>
  <div class="book-hero-stat">
    <span class="stat-num">154</span>
    <span class="stat-label">Design Chapters</span>
  </div>
  <div class="book-hero-stat">
    <span class="stat-num">32</span>
    <span class="stat-label">Hardware Lab Sessions</span>
  </div>
  <div class="book-hero-stat">
    <span class="stat-num">100%</span>
    <span class="stat-label">Verified Source &amp; RTL</span>
  </div>
</div>

---

## Preface

Most engineering curricula isolate processor architecture, printed-circuit design, compiler construction, power electronics, and robotic control into separate disciplines, leaving the interfaces between them abstract.

**Apex** develops all six layers around a single cohesive machine: an indoor-safe (about `2.5 kg`, `< 22V`) autonomous quadruped built from first principles. Across six volumes, we design a custom 32-bit processor on a **Field-Programmable Gate Array (`FPGA`)**, route a 6-layer controlled-impedance carrier board, write a C compiler and preemptive **Real-Time Operating System (`RTOS`)**, implement `20 kHz` brushless torque control, engineer a solid-state power distribution spine, and deploy stereo visual-inertial navigation.

Each chapter derives the underlying mathematics, physics, and architecture from first principles, walks directly through the corresponding verified implementation in `systems/` (`Python`, `SystemVerilog`, `C`, and `KiCad` generators), and provides interactive workbenches and worked exercises to test comprehension before moving to physical hardware.

---

## Start Reading

- **[Prologue: System Architecture & Hardware Contracts](/vision)** — How the six volumes integrate into a unified quadruped without throwaway prototypes or board revisions.
- **[Volume I (`brain`) Overview](/brain/)** — Custom `RISC-V` CPU on `FPGA`, 6-layer carrier board, `SysC` compiler, and preemptive `RTOS`.
  - **[Chapter 1 (`brain-01`): The Golden ISA Contract, Fixed-Width Binary Math & Instruction Execution](/brain/01_golden_oracle_and_isa)** *(about 60 minutes)*

---

## The Six Volumes

| Volume | System ID | Scope & Technical Focus | Structure |
| :---: | :--- | :--- | :--- |
| **Vol. I** | **[`brain`](/brain/)** | Custom 5-stage pipelined `RV32IM` + `Xapex mac` processor on `FPGA`, 6-layer controlled-impedance Spine circuit board, `SysC` C compiler, and strict-deadline `RTOS` | 42 steps (36 chapters + 6 bench labs) |
| **Vol. II** | **[`drive`](/drive/)** | Force-controlled brushless pancake motor actuator (`20 kHz` Field-Oriented Control), 4-layer `24V` inverter board, and `8:1` backdrivable planetary gearbox | 30 steps (24 chapters + 6 bench labs) |
| **Vol. III** | **[`power`](/power/)** | Smart `6S LiFePO4` power distribution spine, soft pre-charge surge limiter, `< 5 µs` electronic circuit breaker, and Extended Kalman battery fuel gauge | 24 steps (19 chapters + 5 bench labs) |
| **Vol. IV** | **[`limb`](/limb/)** | 3-joint spatial leg kinematics (`SO(3)` / `SE(3)`), Jacobian virtual-spring impedance control, carbon-fiber leg CAD, and tabletop rail hopping | 28 steps (23 chapters + 5 bench labs) |
| **Vol. V** | **[`walker`](/walker/)** | Full 12-joint (`about 2.5 kg`) quadruped dynamics, error-state estimator, predictive balance control, GPU-parallel reinforcement learning, and quantized sim-to-real deployment on `brain` | 34 steps (28 chapters + 6 bench labs) |
| **Vol. VI** | **[`sight`](/sight/)** | Sub-microsecond hardware-synced stereo cameras, semi-global depth matching, visual-inertial odometry, 3D occupancy grid mapping, and autonomous obstacle navigation | 28 steps (24 chapters + 4 bench labs) |
