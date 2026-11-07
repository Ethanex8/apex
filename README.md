# Apex: Robotics & Computer Engineering

**Apex** is an open-source, full-stack curriculum and engineering blueprint bridging first-principles theory and real-world autonomous hardware. It unifies foundational mathematics, theoretical physics, computer science, electrical engineering, and mechanical engineering into a cohesive 5-tier academic sequence paired with 8 physically realizable hardware capstone systems.

---

## Repository Structure

- [`CURRICULUM.md`](./CURRICULUM.md) — The comprehensive 5-tier course syllabus (58 courses), textbook reading scopes, core topic breakdowns, 8 capstone engineering specifications, phased home-lab tooling blueprints, and residential safety protocols.
- [`PROGRESS.md`](./PROGRESS.md) — Live section-level study progress dashboard, velocity analytics, and chapter-weighted completion forecasts across all 5 tiers.
- [`curriculum.yaml`](./curriculum.yaml) — The declarative single source of truth defining all courses, prerequisite DAG edges, textbook chapter partitions, capstones, and home-lab specifications.
- [`progress.yaml`](./progress.yaml) — Incremental textbook section Table of Contents and dated completion records.
- [`scripts/build.py`](./scripts/build.py) & [`scripts/track.py`](./scripts/track.py) — Automated invariant validator, Markdown generator, and CLI progress tracker.

---

## Core Pillars

1. **First-Principles Rigor**: Full coverage of vector calculus, analytical & variational mechanics, electromagnetism, linear algebra, dynamical systems, Lie groups ( $\mathrm{SO}(3)$ and $\mathrm{SE}(3)$ ), convex optimization, and optimal control.
2. **Silicon-to-Software Stack**: Spanning transistor physics and CMOS VLSI design up through custom RISC-V CPU pipelining, low-level C systems programming, bare-metal RTOS development, POSIX OS kernels, compiler construction, and distributed robotic middleware (ROS 2 / DDS).
3. **Physical System Realization**: Hands-on hardware execution across all engineering domains—from 4/6-layer high-speed controlled-impedance PCB design, switched-mode power converters, and Field-Oriented Control (FOC) inverter drives to precision cycloidal gearboxes, carbon-fiber composite airframes, and multi-sensor spatial SLAM pods.
4. **Apex Synthesis**: System-level convergence into an 8–10 kg, 12-DOF torque-controlled quadruped / wheeled-biped dynamic robot integrating all previous subsystems.

---

## Curriculum at a Glance

| Tier | Level | Focus Areas |
| :--- | :--- | :--- |
| **Tier 1** | **100-Level** | Single & Multivariable Calculus, Mechanics, Electromagnetism, Modern Physics, Scientific Python, Discrete Math, Materials Science & Lab, Engineering Statics, Parametric CAD & GD&T |
| **Tier 2** | **200-Level** | Linear Algebra, ODEs & Transforms, Probability & Random Processes, Numerical Methods, PDEs & Complex Analysis, Data Structures & Algorithms, Systems Programming & Low-Level C, Linear Circuits & KiCad EDA, Signals & Systems, SystemVerilog RTL, Mechanics of Materials, 3D Analytical & Variational Dynamics, Engineering Thermodynamics |
| **Tier 3** | **300-Level** | Specialized Tracks:<br>• **Track A**: Processor Microarchitecture, CMOS VLSI, Embedded RTOS, OS Kernels, Compilers, Networking & ROS 2<br>• **Track B**: Analog Devices, Sensors & Metrology, DSP, Applied Electromagnetics, RF & Microwave Engineering, Power Electronics<br>• **Track C**: Machine Component Design, Mechanical Vibrations, Finite Element Analysis (FEA), Fluid Mechanics, Heat Transfer, Rotorcraft Aerodynamics<br>• **Track D**: Lie Groups & Spatial Dynamics, Feedback Control, 3D Computer Vision, Factor-Graph SLAM, Digital Control & System ID |
| **Tier 4** | **400-Level** | Systems Engineering & HIL, High-Speed PCB & EMC, Antenna & Phased Arrays, Digital Wireless & SDR, Battery Management Systems (BMS), Field-Oriented Servo Drives, Nonlinear & Geometric Control, Algorithmic Motion Planning, Optimal Control & MPC |
| **Tier 5** | **500-Level** | Underactuated Robotics & Trajectory Optimization, Deep Learning for Robotics, Reinforcement Learning & Sim-to-Real Control |

---

## Curriculum Progress

Currently studying **MATH 101 (Single Variable Calculus)**: **13 / 84 sections** (`15.5%`, ETA `2026-12-21` at **1.62 sections/day**).

| Tier | Courses Done | Assigned Units | Sections (Done / Est.) | Progress | Cumulative ETA |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (100-Level)** | 0 / 10 | 5.50 / 122 | 13 / ~779 | `█░░░░░░░░░` `1.7%` | `2028-02-22` |
| **Tier 2 (200-Level)** | 0 / 13 | 0.00 / 166 | 0 / ~1,195 | `░░░░░░░░░░` `0.0%` | `2030-02-26` |
| **Tier 3 (300-Level)** | 0 / 23 | 0.00 / 280 | 0 / ~2,013 | `░░░░░░░░░░` `0.0%` | `2033-07-19` |
| **Tier 4 (400-Level)** | 0 / 9 | 0.00 / 95 | 0 / ~665 | `░░░░░░░░░░` `0.0%` | `2034-09-01` |
| **Tier 5 (500-Level)** | 0 / 3 | 0.00 / 50 | 0 / ~359 | `░░░░░░░░░░` `0.0%` | `2035-04-10` |

For section-by-section checklists, velocity trends, and pace scenarios, see [**PROGRESS.md**](./PROGRESS.md).

---

## Capstones Matrix

All capstone hardware designs target residential home-lab execution within Safe Extra-Low Voltage ( $< 25.2\text{ V}$ SELV) boundaries and budget-conscious procurement:

- **Capstone 1**: Custom 32-Bit RISC-V SoC, 6-Layer PCB, Compiler & Preemptive RTOS
- **Capstone 2**: Custom 915 MHz / 2.4 GHz ISM SDR Transceiver & Patch Array Link
- **Capstone 3**: Smart 6S LiFePO4 BMS & Multi-Rail Power Distribution Unit
- **Capstone 4**: High-Torque Quasi-Direct-Drive (QDD) Actuator & 20 kHz FOC Drive
- **Capstone 5**: Desktop 6-DOF Precision Robot Arm & 6-Axis Force/Torque Wrist
- **Capstone 6**: Synchronized Visual-Inertial-LiDAR SLAM & Spatial AI Pod
- **Capstone 7**: Sub-250g Ducted Carbon-Fiber Quadrotor with Custom Flight Computer
- **Capstone 8 (Apex Thesis)**: Desktop-Scale 12-DOF Torque-Controlled Quadruped / Wheeled-Biped

For complete details, textbook scopes, BOMs, and lab safety protocols, see [**CURRICULUM.md**](./CURRICULUM.md).
