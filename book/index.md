# Apex: Integrated Systems Engineering

> **An Eight-Part, 34-Chapter Textbook on Custom Silicon, Compilers, Power Electronics, and Legged Robotics**  
> Written for software and systems engineers approaching processor architecture (`RISC-V`), hardware description (`SystemVerilog`), circuit-board electromagnetics, motor control, and dynamic locomotion for the first time.

<div class="book-hero-banner">
  <div class="book-hero-stat">
    <span class="stat-num">8</span>
    <span class="stat-label">Chronological Parts</span>
  </div>
  <div class="book-hero-stat">
    <span class="stat-num">34</span>
    <span class="stat-label">Cohesive Chapters</span>
  </div>
  <div class="book-hero-stat">
    <span class="stat-num">186</span>
    <span class="stat-label">Verified Steps &amp; Labs</span>
  </div>
  <div class="book-hero-stat">
    <span class="stat-num">100%</span>
    <span class="stat-label">Live-Synced Code</span>
  </div>
</div>

---

## Preface

**Apex** integrates processor architecture, printed-circuit physics, compiler construction, power electronics, and dynamic robotic control around a single cohesive machine: an indoor-safe (about `2.5 kg`, `< 22V`) autonomous quadruped built from first principles. Across eight chronological parts, we design a custom 32-bit processor on a **Field-Programmable Gate Array (`FPGA`)**, route a 6-layer controlled-impedance carrier board, build a C compiler and preemptive **Real-Time Operating System (`RTOS`)**, implement `20 kHz` brushless torque control, engineer a solid-state power distribution spine, and deploy stereo visual-inertial navigation.

Every chapter develops one natural arc—combining mathematical derivations, interactive visualizers, verified implementations in `systems/`, and closing hardware bench experiments—growing section by section as each underlying implementation milestone lands.

---

## Start Reading

- **[Prologue: System Architecture & Hardware Contracts](/vision)** — How the six physical subsystems integrate into a unified quadruped without throwaway prototypes or board revisions.
- **[Chapter 1: Instruction Set Architecture & Fixed-Width Binary Arithmetic](/brain/01_isa_and_binary_arithmetic)** *(about 55 minutes)* — Golden reference modeling, modular binary rings (`u32`/`s32`), `RV32IM` + `Zicsr` + `Xapex mac` encoding, memory-mapped I/O, and traps.

---

## Complete Syllabus (Parts I–VIII)

### Part I: Digital Logic and Processor Architecture

Fixed-width binary algebra, instruction set contracts, combinational and sequential logic, single-cycle and 5-stage pipelined `RISC-V` + `SIMD` silicon, and `FPGA` timing closure ([`brain` Reference](/brain/)).

| Ch. | Title & Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **1** | **[Instruction Set Architecture & Fixed-Width Binary Arithmetic](/brain/01_isa_and_binary_arithmetic)**<br/>Golden reference modeling, modular rings and two's complement, `RV32IM` + `Zicsr` + `Xapex mac` encoding, memory-mapped I/O, and traps. | `brain-01` | <span class="book-status-live">Published</span> |
| **2** | **Combinational Logic, Sequential Storage & Timing Constraints**<br/>Carry-chain adders, single-cycle barrel shifters, signed/unsigned comparators, clocked flip-flops, setup/hold windows, `32×32` register files, and sign extension. | `brain-02`–`03` | <span class="book-status-upcoming">Upcoming</span> |
| **3** | **Clock-Domain Synchronization & Asynchronous Serial Framing**<br/>Flip-flop metastability, two-stage synchronizers, `16×`-oversampled `UART` framing with `FIFO`s, and physical `FPGA` logic-analyzer capture. | `brain-04`–`05` | <span class="book-status-upcoming">Upcoming</span> |
| **4** | **Single-Cycle Processor Composition & Memory Alignment**<br/>Control-table decoding, conditional branches, little-endian byte/halfword alignment, Block `RAM`, and `10k`-instruction lockstep verification. | `brain-06`–`08` | <span class="book-status-upcoming">Upcoming</span> |
| **5** | **Multi-Cycle Arithmetic, Custom Neural Silicon & Machine Traps**<br/>Valid/ready backpressure, shift-add multiply and restoring divide, dual-`INT16` `DSP` dot-product silicon, atomic `CSR`s, and `64`-bit `CLINT` timers. | `brain-09`–`11` | <span class="book-status-upcoming">Upcoming</span> |
| **6** | **Pipelined Execution, Hazard Resolution & Timing Closure**<br/>Five-stage throughput vs. latency, `RAW` bypass networks, load-use stalls, precise trap flushes, `100k`-instruction stress testing, and `50 MHz` `LUT4` timing closure. | `brain-12`–`16` | <span class="book-status-upcoming">Upcoming</span> |

### Part II: High-Speed Board Physics and System-on-Chip Interconnects

Switching power supplies, transmission-line electromagnetics, `6`-layer controlled-impedance `PCB` routing, and external `Flash`/`SDRAM` and real-time `SoC` controllers ([`brain` Reference](/brain/)).

| Ch. | Title & Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **7** | **Power Conversion, Transmission Lines & Power-Delivery Networks**<br/>Synchronous buck switching physics, `USB-C` negotiation, copper traces as waveguides, impedance reflections, and multi-decade `MLCC` charge caches. | `brain-17`–`18` | <span class="book-status-upcoming">Upcoming</span> |
| **8** | **Controlled-Impedance Six-Layer Circuit Board Design**<br/>Unbroken ground return planes, Kelvin sensing, series damping, `120 Ω` differential `CAN` termination, ground-slot test coupons, length matching, and `DFM`/`DRC` sign-off. | `brain-19`–`23` | <span class="book-status-upcoming">Upcoming</span> |
| **9** | **Bus Crossbars, Persistent Flash & Dynamic RAM Controllers**<br/>Address-decoded `MMIO` crossbars, bidirectional `4`-lane `QSPI` Flash `XIP` engines, and `SDRAM` capacitor refresh, row/column timing, and burst scheduling. | `brain-24`–`26` | <span class="book-status-upcoming">Upcoming</span> |
| **10** | **Real-Time Peripherals, PLL Clocking & SoC Bring-Up**<br/>Motion-sensor `SPI` bursts, sub-microsecond camera shutter latching, `CAN-FD` bit-stuffing and `CRC`s, `PLL` phase-shifted `SDRAM` capture, and dock `FPGA` boot. | `brain-27`–`29` | <span class="book-status-upcoming">Upcoming</span> |

### Part III: Compilers, Real-Time Operating Systems and Silicon Validation

Two-pass machine assembly, C compilation from lexing to register allocation, preemptive real-time scheduling, quantized neural inference, and custom-board `TDR` bring-up ([`brain` Reference](/brain/)).

| Ch. | Title & Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **11** | **Machine Assembly, Relocation & C Front-End Parsing**<br/>Two-pass label resolution, `%hi/%lo` relocations, Flash-to-RAM linker maps, `DFA` lexing, recursive-descent parsing, pointer typing, and `SSA`-lite `IR` lowering. | `brain-30`–`32` | <span class="book-status-upcoming">Upcoming</span> |
| **12** | **Data-Flow Optimization, Register Allocation & Code Generation**<br/>Fixed-point optimization with `volatile` `MMIO` barriers, backward liveness, linear-scan register allocation, `ABI` stack frames, `mac` emission, and translation validation. | `brain-33`–`35` | <span class="book-status-upcoming">Upcoming</span> |
| **13** | **Preemptive Real-Time Kernels & Lock-Free Synchronization**<br/>Bare-metal startup, `QSPI`-to-`SDRAM` bootloading, `31`-register `mscratch` trap switching, priority-inheritance mutexes, and lock-free `SPSC` ring buffers. | `brain-36`–`37` | <span class="book-status-upcoming">Upcoming</span> |
| **14** | **Fixed-Point Control, Quantized Inference & Hardware Bring-Up**<br/>`Q16.16` attitude filtering, `1 kHz` `PID` jitter histograms, interactive `ash` shell, `< 0.6 ms` `INT16` neural inference, `LiteVNA` `TDR` sweeps, and custom-board graduation. | `brain-38`–`42` | <span class="book-status-upcoming">Upcoming</span> |

### Part IV: Brushless Electromechanics, Power Inverters and Force Actuation

Permanent-magnet motor physics, Field-Oriented Control, `24V` `3`-phase inverter hardware, `20 kHz` embedded firmware, `8:1` planetary gearing, and haptic bench validation ([`drive` Reference](/drive/)).

| Ch. | Title & Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **15** | **Brushless Electromechanics & Field-Oriented Control**<br/>Three-phase motor back-EMF and Lorentz torque, Clarke/Park rotating coordinates, hexagonal `SVPWM` headroom, and nested `20 kHz` current + `1 kHz` impedance loops. | `drive-01`–`04` | <span class="book-status-upcoming">Upcoming</span> |
| **16** | **Three-Phase Power Inverters, Current Sensing & Switching Transients**<br/>Low-side shunt valley sampling, `Q`-format `CAN-FD` packets, `MOSFET` losses and bootstrap pumps, `SPICE` switch-ringing damping, and `4`-layer circular `PCB` layout. | `drive-05`–`12`, `14` | <span class="book-status-upcoming">Upcoming</span> |
| **17** | **Hard Real-Time Motor Firmware, Sensor Observers & Calibration**<br/>Fixed-point `CORDIC` trig, timer-triggered `ADC` valleys, `14`-bit magnetic `PLL` speed tracking, coil `R/L` and eccentricity auto-ID, anticogging `ISR`, `CAN-FD`, and `CCM-SRAM` linking. | `drive-13`, `15`–`21` | <span class="book-status-upcoming">Upcoming</span> |
| **18** | **Quasi-Direct-Drive Transmissions, Structural FEA & Actuator Bring-Up**<br/>Reflected inertia, `8:1` tooth geometry, parametric `CAD`, `CalculiX` tooth stress `FEA`, `RSS` tolerance stack-ups, oscilloscope switching checks, backdrive tests, and haptic wheel graduation. | `drive-22`–`30` | <span class="book-status-upcoming">Upcoming</span> |

### Part V: Electrochemical Energy and Solid-State Power Protection

`LiFePO4` battery modeling, capacitive surge physics, Extended Kalman State-of-Charge estimation, microsecond solid-state circuit breakers, and fault-injection testing ([`power` Reference](/power/)).

| Ch. | Title & Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **19** | **Battery Electrochemistry, Surge Physics & Kalman State Estimation**<br/>`6S LiFePO4` Randles impedance and flat `OCV` plateaus, `2,400 µF` capacitive inrush and regenerative energy, and nonlinear `EKF` fuel-gauge estimation. | `power-01`–`03` | <span class="book-status-upcoming">Upcoming</span> |
| **20** | **Solid-State Circuit Breakers, Loop Stability & High-Current Layout**<br/>Back-to-back `N-MOSFET` blocking, `TVS`-clamped inductive turn-off, `5V` buck Bode stability, hardware `E-stop` latching, and `2 oz` thick-copper thermal layout. | `power-04`–`11`, `14` | <span class="book-status-upcoming">Upcoming</span> |
| **21** | **Power Supervision Firmware, Black-Box Telemetry & Fault Validation**<br/>Positive-definite C `EKF` covariance updates, pre-trigger black-box fault logs, soft pre-charge short guards, Steinhart-Hart `ADC` calibration, and `< 5 µs` hard-short scope graduation. | `power-12`–`13`, `15`–`24` | <span class="book-status-upcoming">Upcoming</span> |

### Part VI: Spatial Kinematics, Dynamics and Compliant Limbs

`3D` rigid-body transformations, Product-of-Exponentials kinematics, recursive dynamics, Cartesian impedance, hopping control, low-inertia leg mechanics, and rail bring-up ([`limb` Reference](/limb/)).

| Ch. | Title & Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **22** | **Rigid-Body Transformations, Screw Kinematics & Force-Torque Duality**<br/>`SO(3)` rotations and `SE(3)` twists, Product-of-Exponentials forward kinematics, closed-form geometric `IK` with singularity clamping, and virtual-work Jacobian duality. | `limb-01`–`04` | <span class="book-status-upcoming">Upcoming</span> |
| **23** | **Articulated-Body Inverse Dynamics & Cartesian Virtual-Spring Control**<br/>`O(N)` Recursive Newton-Euler gravity and inertia sweeps, `3D` Cartesian impedance stiffness/damping, and `MuJoCo` verification with `64×` reflected rotor inertia. | `limb-05`–`07` | <span class="book-status-upcoming">Upcoming</span> |
| **24** | **Momentum Contact Estimation, Hopping Control & Silicon Co-Simulation**<br/>Sensorless generalized-momentum impact observers, `C^2` Bézier swing paths, `SLIP` pogo energy control, `Q16.16` `SysC` kinematics, and `Verilator`-to-`MuJoCo` co-simulation. | `limb-08`–`12` | <span class="book-status-upcoming">Upcoming</span> |
| **25** | **Low-Inertia Limb Mechanics, Impact Buckling & Structural CAD**<br/>Hip-mounted belt transmissions, impact impulse and Euler column buckling, neutral-axis cable routing, `4g` landing `FEA`, `2020` rail stand `CAD`, and software torque walls. | `limb-13`–`21` | <span class="book-status-upcoming">Upcoming</span> |
| **26** | **Embedded Limb Control, Joint Calibration & Experimental Rail Hopping**<br/>`1 kHz` `SysC` leg loop, right-hand zero-offset calibration, telemetry identification, weightless gravity float, soft drop landings, and `30`-hop rail graduation. | `limb-22`–`28` | <span class="book-status-upcoming">Upcoming</span> |

### Part VII: Whole-Body Optimal Control and Learned Locomotion

Floating-base state estimation, constrained `QP` balance, receding-horizon Centroidal `MPC`, `GPU`-parallel `PPO` reinforcement learning, `INT16` quantization, and untethered walking ([`walker` Reference](/walker/)).

| Ch. | Title & Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **27** | **Floating-Base State Estimation, Friction Cones & Quadratic Balance**<br/>Unanchored `18-DOF` modeling, stance-constrained `ESKF` speed/height estimation, friction-cone balance `QP`, Raibert capture-point footholds, back-EMF realism, and fall reflexes. | `walker-01`–`07` | <span class="book-status-upcoming">Upcoming</span> |
| **28** | **Centroidal Dynamics & Receding-Horizon Model Predictive Control**<br/>Single-rigid-body linearization, `200 ms` Convex `MPC` via `OSQP`, integrated `MPC` + Bézier trotting, slip reflexes, and cost-of-transport comparisons against kinematic playback. | `walker-08`–`14` | <span class="book-status-upcoming">Upcoming</span> |
| **29** | **Deep Reinforcement Learning & Quantized Sim-to-Real Deployment**<br/>Partially observable locomotion `MDP`, from-scratch `PPO` and `GAE`, domain randomization in `GPU`-parallel `MJX`, symmetric `INT16` `mac` export, `12`-joint `CAN-FD` scheduling, and `Verilator` walking. | `walker-15`–`22` | <span class="book-status-upcoming">Upcoming</span> |
| **30** | **Quadruped Chassis Mechanics, EMI Harnessing & Untethered Locomotion**<br/>Carbon sandwich torso `CAD`, diagonal-trot torsional `FEA`, twisted-pair `CAN-FD` harnesses, slack-bungee safety gantry, telemetry system ID, and untethered `LiFePO4` walking graduation. | `walker-23`–`34` | <span class="book-status-upcoming">Upcoming</span> |

### Part VIII: Stereo Vision, State Estimation and Autonomous Navigation

Camera projection and stereo depth, inertial pre-integration, Lie-algebra `VIO` and factor-graph `SLAM`, `3D` occupancy grids, motion planning, and full-stack autonomous navigation ([`sight` Reference](/sight/)).

| Ch. | Title & Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **31** | **Projective Camera Geometry, Stereo Depth & Inertial Pre-Integration**<br/>Pinhole optics and Brown-Conrady distortion, epipolar rectification and quadratic depth error, `KLT` optical flow with `5`-point `RANSAC`, `IMU` pre-integration, and `< 50 µs` shutter sync. | `sight-01`–`06` | <span class="book-status-upcoming">Upcoming</span> |
| **32** | **Visual-Inertial Odometry, Factor-Graph SLAM & Occupancy Mapping**<br/>Manifold `ESKF` `VIO`, Schur-complement bundle adjustment, loop closure, Bayesian log-odds `2.5D`/`3D` obstacle grids, metric scale observability, and the `2 Mbps` `brain`-`sight` bridge. | `sight-07`–`13` | <span class="book-status-upcoming">Upcoming</span> |
| **33** | **Configuration-Space Planning, Dynamic Windows & Semantic Safety**<br/>Minkowski obstacle inflation with `A*`/`RRT*`, Dynamic-Window velocity tracking, `INT8` neural safety bubbles, `150 ms` watchdog safe-stop `FSM`s, and full `MuJoCo` autonomy simulation. | `sight-14`–`18` | <span class="book-status-upcoming">Upcoming</span> |
| **34** | **Synchronized Stereo Hardware, Calibration & Full-Stack Autonomy**<br/>Global-shutter stereo baseline sizing, rigid head pod `CAD`, `FSYNC` harness `ICD`, asymmetric `AprilGrid` calibration, handheld `SLAM`, and untethered obstacle-avoiding quadruped graduation. | `sight-19`–`28` | <span class="book-status-upcoming">Upcoming</span> |
