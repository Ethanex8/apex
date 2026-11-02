# Apex: Robotics & Computer Engineering

**Apex** is an open-source, full-stack curriculum and engineering blueprint bridging first-principles theory and real-world autonomous hardware. It unifies foundational mathematics, theoretical physics, computer science, electrical engineering, and mechanical engineering into a cohesive 5-tier academic sequence paired with 8 physically realizable hardware capstone systems.

---

## Repository Structure

- [`CURRICULUM.md`](./CURRICULUM.md) — The comprehensive 5-tier course syllabus (51 courses), textbook reading scopes, core topic breakdowns, 8 capstone engineering specifications, phased home-lab tooling blueprints, and residential safety protocols.

---

## Core Pillars

1. **First-Principles Rigor**: Full coverage of vector calculus, analytical & variational mechanics, electromagnetism, linear algebra, dynamical systems, Lie groups ($\mathrm{SO}(3)$ and $\mathrm{SE}(3)$), convex optimization, and optimal control.
2. **Silicon-to-Software Stack**: Spanning transistor physics and CMOS VLSI design up through custom RISC-V CPU pipelining, low-level C systems programming, bare-metal RTOS development, POSIX OS kernels, compiler construction, and distributed robotic middleware (ROS 2 / DDS).
3. **Physical System Realization**: Hands-on hardware execution across all engineering domains—from 4/6-layer high-speed controlled-impedance PCB design, switched-mode power converters, and Field-Oriented Control (FOC) inverter drives to precision cycloidal gearboxes, carbon-fiber composite airframes, and multi-sensor spatial SLAM pods.
4. **Apex Synthesis**: System-level convergence into an 8–10 kg, 12-DOF torque-controlled quadruped / wheeled-biped dynamic robot integrating all previous subsystems.

---

## Curriculum at a Glance

| Tier | Level | Focus Areas |
| :--- | :--- | :--- |
| **Tier 1** | **100-Level** | Single & Multivariable Calculus, Mechanics, Electromagnetism, Modern Physics, Scientific Python, Discrete Math, Materials Science & Lab, Engineering Statics, Parametric CAD & GD&T |
| **Tier 2** | **200-Level** | Linear Algebra, ODEs & Transforms, Probability & Random Processes, Numerical Methods, PDEs & Complex Analysis, Data Structures & Algorithms, Systems Programming & Low-Level C, Linear Circuits & KiCad EDA, Signals & Systems, SystemVerilog RTL, Mechanics of Materials, 3D Analytical & Variational Dynamics, Engineering Thermodynamics |
| **Tier 3** | **300-Level** | Specialized Tracks:<br>• **Track A**: Processor Microarchitecture, CMOS VLSI, Embedded RTOS, OS Kernels, Compilers, Networking & ROS 2<br>• **Track B**: Analog Devices, Sensors & Metrology, DSP, Applied Electromagnetics & RF, Power Electronics<br>• **Track C**: Machine Component Design, FEA & Vibrations, Heat Transfer, Fluid Mechanics & Aerodynamics<br>• **Track D**: Lie Groups & Spatial Dynamics, Feedback Control, 3D Computer Vision, Factor-Graph SLAM, Digital Control & System ID |
| **Tier 4** | **400-Level** | Systems Engineering & HIL, High-Speed PCB & EMC, Antenna Design & SDR Comms, Battery Management Systems (BMS), Field-Oriented Servo Drives, Nonlinear & Geometric Control, Motion Planning & MPC |
| **Tier 5** | **500-Level** | Underactuated Robotics & Trajectory Optimization, Deep Learning & Reinforcement Learning for Robotics |

---

## Capstones Matrix

All capstone hardware designs target residential home-lab execution within Safe Extra-Low Voltage ($< 25.2\text{ V}$ SELV) boundaries and budget-conscious procurement:

- **Capstone 1**: Custom 32-Bit RISC-V SoC, 6-Layer PCB, Compiler & Preemptive RTOS
- **Capstone 2**: Custom 915 MHz / 2.4 GHz ISM SDR Transceiver & Patch Array Link
- **Capstone 3**: Smart 6S LiFePO4 BMS & Multi-Rail Power Distribution Unit
- **Capstone 4**: High-Torque Quasi-Direct-Drive (QDD) Actuator & 20 kHz FOC Drive
- **Capstone 5**: Desktop 6-DOF Precision Robot Arm & 6-Axis Force/Torque Wrist
- **Capstone 6**: Synchronized Visual-Inertial-LiDAR SLAM & Spatial AI Pod
- **Capstone 7**: Sub-250g Ducted Carbon-Fiber Quadrotor with Custom Flight Computer
- **Capstone 8 (Apex Thesis)**: Desktop-Scale 12-DOF Torque-Controlled Quadruped / Wheeled-Biped

For complete details, textbook scopes, BOMs, and lab safety protocols, see [**CURRICULUM.md**](./CURRICULUM.md).
