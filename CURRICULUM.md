# Robotics & Computer Engineering (RCE) Curriculum

A comprehensive, mathematically rigorous, hands-on curriculum bridging first-principles theory and real-world physical systems engineering across 5 academic tiers, 8 hardware capstones, and residential laboratory safety protocols.

---

## Table of Contents

- [Curriculum Architecture & Overview](#curriculum-architecture--overview)
- [Tier 1: 100-Level Freshman Foundation](#tier-1-100-level-freshman-foundation)
- [Tier 2: 200-Level Sophomore Engineering Core](#tier-2-200-level-sophomore-engineering-core)
- [Tier 3: 300-Level Junior Specialization Tracks](#tier-3-300-level-junior-specialization-tracks)
  - [Track A: Silicon, Embedded Systems, Computer Architecture & Systems Software](#track-a-silicon-embedded-systems-computer-architecture--systems-software)
  - [Track B: Microelectronics, Optoelectronics, DSP & RF](#track-b-microelectronics-optoelectronics-dsp--rf)
  - [Track C: Mechanical Design, Thermo-Fluids & Structural Analysis](#track-c-mechanical-design-thermo-fluids--structural-analysis)
  - [Track D: Robotics Kinematics, Digital Control & Spatial Perception](#track-d-robotics-kinematics-digital-control--spatial-perception)
- [Tier 4: 400-Level Senior Advanced Systems](#tier-4-400-level-senior-advanced-systems)
- [Tier 5: 500-Level Graduate Synthesis & Autonomous Machines](#tier-5-500-level-graduate-synthesis--autonomous-machines)
- [Capstone Project Listing](#capstone-project-listing)
- [Phased Home-Lab Infrastructure & Safety Protocols](#phased-home-lab-infrastructure--safety-protocols)

---

## Curriculum Architecture & Overview

```mermaid
flowchart TD
    subgraph T1["Tier 1: 100-Level Freshman Foundation"]
        M101["MATH 101: Single Variable Calculus"]
        M102["MATH 102: Multivariable & Vector Calculus"]
        P101["PHYS 101: Mechanics"]
        P102["PHYS 102: Electromagnetism"]
        P103["PHYS 103: Waves, Optics & Modern Physics"]
        CS101["CS 101: Scientific Computing & Python"]
        CS102["CS 102: Discrete Mathematics"]
        MATS101["MATS 101: Materials Science"]
        ENGR101["ENGR 101: Parametric CAD & GD&T"]
    end

    subgraph T2["Tier 2: 200-Level Sophomore Core"]
        M201["MATH 201: Linear Algebra"]
        M202["MATH 202: Differential Equations"]
        M203["MATH 203: Probability & Random Processes"]
        M204["MATH 204: Numerical Methods"]
        M205["MATH 205: PDEs & Complex Analysis"]
        CS201["CS 201: Data Structures & Algorithms"]
        EE201["EE 201: Linear Circuit Theory & EDA"]
        EE202["EE 202: Signals & Systems"]
        ECE201["ECE 201: Digital Logic & SystemVerilog"]
        ME201["ME 201: Mechanics of Materials"]
        ME202["ME 202: 3D Analytical Dynamics"]
    end

    subgraph T3["Tier 3: 300-Level Junior Tracks"]
        direction TB
        subgraph TrackA["Track A: Silicon & Systems SW"]
            ECE301["ECE 301: Microarchitecture"]
            ECE302["ECE 302: CMOS VLSI"]
            ECE303["ECE 303: Embedded RTOS"]
            CS301["CS 301: Operating Systems"]
            CS302["CS 302: Compiler Engineering"]
            CS303["CS 303: Networking & ROS 2"]
        end
        subgraph TrackB["Track B: RF & Power"]
            EE301["EE 301: Analog Electronics"]
            EE302["EE 302: Sensors & Data Conversion"]
            EE303["EE 303: Digital Signal Processing"]
            EE304["EE 304: Applied Electromagnetics"]
            EE305["EE 305: Power Electronics"]
        end
        subgraph TrackC["Track C: Mechanical & Thermo-Fluids"]
            ME301["ME 301: Machine Component Design"]
            ME302["ME 302: FEA & Vibrations"]
            ME303["ME 303: Heat Transfer"]
            ME305["ME 305: Fluid Mechanics & Aerodynamics"]
        end
        subgraph TrackD["Track D: Robotics & Controls"]
            ROB301["ROB 301: Lie Groups & Spatial Dynamics"]
            ROB302["ROB 302: Feedback Control Systems"]
            ROB303["ROB 303: 3D Computer Vision"]
            ROB304["ROB 304: Lie-Group State Estimation"]
            ROB305["ROB 305: Digital Control & System ID"]
        end
    end

    subgraph T4["Tier 4: 400-Level Senior Systems"]
        ENGR401["ENGR 401: Systems Integration & HIL"]
        ECE401["ECE 401: High-Speed PCB & EMC"]
        EE401["EE 401: Antenna & SDR Comms"]
        EE402["EE 402: Battery Management Systems"]
        EE403["EE 403: Field-Oriented Servo Drives"]
        ROB401["ROB 401: Nonlinear Control"]
        ROB402["ROB 402: Motion Planning & MPC"]
    end

    subgraph T5["Tier 5: 500-Level Graduate Synthesis"]
        ROB501["ROB 501: Underactuated Robotics"]
        ROB502["ROB 502: Deep Learning & RL for Robotics"]
    end

    subgraph Capstones["Capstone Projects"]
        C1["Capstone 1: RISC-V SoC & RTOS"]
        C2["Capstone 2: SDR Transceiver Link"]
        C3["Capstone 3: Smart 6S BMS & PDU"]
        C4["Capstone 4: QDD Actuator & FOC Drive"]
        C5["Capstone 5: 6-DOF Robot Arm & F/T Wrist"]
        C6["Capstone 6: VIO-LiDAR SLAM Pod"]
        C7["Capstone 7: Sub-250g Ducted Quadrotor"]
        C8["Capstone 8: 12-DOF Quadruped / Biped (Apex)"]
    end

    M101 --> M102
    M101 --> P101
    M102 --> PHYS102
    M102 --> PHYS103
    P101 --> MATS101
    M102 --> M201
    M102 --> M202
    M201 --> M204
    M202 --> M204
    M202 --> M205
    CS101 --> CS201
    CS102 --> CS201
    PHYS102 --> EE201
    EE201 --> EE202
    P101 --> ME201
    ME201 --> ME202
    M201 --> ME202
    EE201 --> ECE201
    
    ECE201 --> ECE301
    ECE201 --> ECE303
    CS201 --> CS301
    CS201 --> CS302
    CS301 --> CS303
    EE201 --> EE301
    EE202 --> EE303
    EE201 --> EE304
    EE201 --> EE305
    ME201 --> ME301
    ME202 --> ME301
    ME201 --> ME302
    ME202 --> ME305
    ME202 --> ROB301
    EE202 --> ROB302
    M201 --> ROB303
    ROB301 --> ROB304
    ROB302 --> ROB305
    
    ECE301 --> ECE401
    EE304 --> ECE401
    EE303 --> EE401
    EE304 --> EE401
    EE305 --> EE402
    EE305 --> EE403
    ROB301 --> ROB401
    ROB302 --> ROB401
    ROB301 --> ROB402
    ROB305 --> ROB402
    
    ROB401 --> ROB501
    ROB402 --> ROB501
    ROB303 --> ROB502
    ROB304 --> ROB502

    ECE401 & CS301 & CS302 --> C1
    EE401 --> C2
    EE402 --> C3
    EE403 --> C4
    ROB401 & ROB402 & C4 --> C5
    ROB303 & ROB304 & ROB502 --> C6
    ME305 & ROB401 & ROB501 & C2 --> C7
    C1 & C2 & C3 & C4 & C6 & ROB501 & ROB502 & ENGR401 --> C8
```

---

## Tier 1: 100-Level Freshman Foundation

### MATH 101: Single Variable Calculus
- **Prerequisites**: None
- **Texts & Reading Scope**: James Stewart – *Calculus: Early Transcendentals* (Appendices A–E, Ch. 1–11 complete).
- **Core Topics**: Functions, limits, continuity, differentiation rules, optimization, definite and indefinite integrals, integration techniques, first-order separable/linear differential equations, parametric/polar curves, and infinite series.

### MATH 102: Multivariable & Vector Calculus
- **Prerequisites**: MATH 101
- **Texts & Reading Scope**: James Stewart – *Calculus: Early Transcendentals* (Appendices F–H, Ch. 12–16; skip Ch. 17 as second-order ODEs are covered in MATH 202); H.M. Schey – *Div, Grad, Curl, and All That* (read alongside Stewart Ch. 16).
- **Core Topics**: 3D coordinate geometry, dot and cross products, space curves, partial derivatives, gradients, Lagrange multipliers, double and triple integrals in cylindrical/spherical coordinates, line and surface integrals, Green’s theorem, Stokes’ theorem, and the Divergence theorem.

### PHYS 101: Mechanics
- **Prerequisites**: Co-requisite MATH 101
- **Texts & Reading Scope**: Randall Knight – *Physics for Scientists and Engineers* (Vol. 1: Ch. 1–15).
- **Core Topics**: 1D and 2D kinematics, Newtonian dynamics, impulse and linear momentum conservation, work and kinetic/potential energy, fixed-axis rigid-body rotation, static equilibrium, gravitation, and simple harmonic oscillations.

### PHYS 102: Electromagnetism
- **Prerequisites**: PHYS 101, MATH 102
- **Texts & Reading Scope**: Randall Knight – *Physics for Scientists and Engineers* (Vol. 3: Ch. 22–32; skip Ch. 28 and 31–32 as circuit analysis is covered in EE 201).
- **Core Topics**: Electric charge, Coulomb's law, electric fields, Gauss’s law, electric potential, capacitance, magnetic fields, Ampère's law, Faraday's law of electromagnetic induction, and Maxwell's equations.

### PHYS 103: Waves, Optics & Modern Physics
- **Prerequisites**: PHYS 101, MATH 102
- **Texts & Reading Scope**: Randall Knight – *Physics for Scientists and Engineers* (Vols. 2, 4–5; skim Ch. 33–35).
- **Core Topics**: Travelling mechanical and acoustic waves, superposition, standing waves, wave interference, diffraction limits, ray optics, thin lenses, photoelectric effect, and introductory quantum wave-particle duality.

### CS 101: Scientific Computing & Modular Programming
- **Prerequisites**: None
- **Texts & Reading Scope**: Mark Newman – *Computational Physics* (Ch. 1–5 only; later numerical methods chapters are covered in MATH 204).
- **Core Topics**: Python syntax, NumPy vectorization, SciPy/Matplotlib visualization, SymPy symbolic manipulation, object-oriented modeling, numerical integration basics, unit testing, and Git version control.

### CS 102: Discrete Mathematics for Engineering
- **Prerequisites**: None
- **Texts & Reading Scope**: Eric Lehman, F. Thomson Leighton, Albert R. Meyer – *Mathematics for Computer Science*.
- **Core Topics**: Propositional and predicate logic, mathematical induction, state machines and invariants, number theory, directed and undirected graph theory, recurrences, and combinatorics.

### MATS 101: Materials Science & Mechanical Selection
- **Prerequisites**: PHYS 101
- **Texts & Reading Scope**: William Callister & David Rethwisch – *Materials Science and Engineering: An Introduction*; Michael F. Ashby – *Materials Selection in Mechanical Design*.
- **Core Topics & Lab**: Crystal structures, elastic/plastic deformation, dislocation mechanics, failure modes, and Ashby material selection indices; home lab execution involves destructive stress-strain and creep tests on 3D-printed polymers (PLA, PETG-CF, PA-CF) and aluminum coupons using a 2020-extrusion lever rig, a 50 kg HX711 load cell, and a digital dial indicator.

### ENGR 101: Parametric CAD, GD&T & Tolerance Analysis
- **Prerequisites**: None
- **Texts & Reading Scope**: Randy Shih – *Parametric Modeling*; James Meadows – *GD&T (ASME Y14.5)*; Bryan Fischer – *Mechanical Tolerance Stackup*.
- **Core Topics**: Master-model parametric part and assembly CAD, technical engineering drawings, ASME Y14.5 geometric dimensioning and tolerancing (GD&T) datums and feature control frames, and 1D/3D worst-case and RSS statistical tolerance stack-ups.

---

## Tier 2: 200-Level Sophomore Engineering Core

### MATH 201: Linear Algebra & Matrix Theory
- **Prerequisites**: MATH 102
- **Texts & Reading Scope**: Gilbert Strang – *Introduction to Linear Algebra* (complete text).
- **Core Topics**: Vector spaces, four fundamental subspaces, inner products, orthogonality, projections, linear least squares, LU, QR, and SVD factorizations, eigenvalues/eigenvectors, and positive definite matrices.

### MATH 202: Ordinary Differential Equations & Transforms
- **Prerequisites**: MATH 102, MATH 201
- **Texts & Reading Scope**: Boyce & DiPrima – *Elementary Differential Equations* (Ch. 1–9 only; skip Ch. 10–11 as boundary-value PDEs and Fourier series are treated in MATH 205 and EE 202).
- **Core Topics**: First-order and higher-order linear ODEs, systems of coupled first-order linear equations, phase plane stability analysis, power series solutions, and unilateral Laplace transforms.

### MATH 203: Probability & Random Processes
- **Prerequisites**: MATH 102, CS 102
- **Texts & Reading Scope**: Dimitri Bertsekas & John Tsitsiklis – *Introduction to Probability* (Ch. 1–9 complete).
- **Core Topics**: Probability spaces, discrete and continuous random variables, joint and conditional PDFs, covariance matrices, conditional expectation, limit theorems, Bernoulli and Poisson processes, and finite-state Markov chains.

### MATH 204: Numerical Methods for Engineers
- **Prerequisites**: MATH 201, MATH 202, CS 101
- **Texts & Reading Scope**: Jaan Kiusalaas – *Numerical Methods in Engineering with Python 3*.
- **Core Topics**: Floating-point conditioning, direct and iterative linear system solvers, nonlinear root finding, cubic spline interpolation, Gauss quadrature, finite difference approximations, and adaptive Runge-Kutta ODE integration.

### MATH 205: Partial Differential Equations & Complex Analysis
- **Prerequisites**: MATH 202
- **Texts & Reading Scope**: Erwin Kreyszig – *Advanced Engineering Mathematics* (Ch. 11–18 only / Parts C & D; skip Parts A–B and E–G).
- **Core Topics**: Fourier series and integrals, canonical wave, heat, and Laplace PDEs, separation of variables, complex analytic functions, Cauchy-Riemann equations, Laurent series, contour integration, and Cauchy's residue theorem.

### CS 201: Data Structures & Algorithms
- **Prerequisites**: CS 101, CS 102
- **Texts & Reading Scope**: Michael Goodrich et al. – *Data Structures and Algorithms in Python*.
- **Core Topics**: Asymptotic complexity, self-balancing binary search trees, binary heaps and priority queues, hash tables, dynamic programming, shortest-path graph search algorithms (Dijkstra, A*), and spatial partitioning trees (k-d trees, octrees).

### EE 201: Linear Circuit Theory, Network Analysis & EDA
- **Prerequisites**: PHYS 102, MATH 202
- **Texts & Reading Scope**: Charles Alexander & Matthew Sadiku – *Fundamentals of Electric Circuits* (Ch. 1–16; skip introductory Laplace review); Peter Dalmaris – *KiCad Like a Pro*.
- **Core Topics & Lab**: Kirchhoff's laws, nodal and mesh analysis, Thévenin/Norton equivalents, ideal op-amp topologies, RLC transient responses, AC steady-state phasor analysis, schematic capture, and 2-layer/4-layer PCB layout in KiCad; home lab execution uses a 4-channel DSO, arbitrary waveform generator, and LTspice/Ngspice.

### EE 202: Continuous & Discrete Signals and Systems
- **Prerequisites**: EE 201, MATH 201, MATH 205
- **Texts & Reading Scope**: Alan Oppenheim & Alan Willsky – *Signals and Systems*.
- **Core Topics**: Continuous-time and discrete-time LTI systems, convolution integrals and sums, Fourier series, continuous-time and discrete-time Fourier transforms (CTFT, DTFT), bilateral Laplace transforms, Z-transforms, poles and zeros, transfer functions, and the Nyquist-Shannon sampling theorem.

### ECE 201: Digital Logic Design & SystemVerilog RTL
- **Prerequisites**: CS 102, EE 201
- **Texts & Reading Scope**: David Harris & Sarah Harris – *Digital Design and Computer Architecture (RISC-V Edition)* (Ch. 1–5 only); Stuart Sutherland – *RTL Modeling with SystemVerilog*.
- **Core Topics & Lab**: Combinational and sequential logic design, finite state machines (FSMs), timing analysis, metastability and clock-domain synchronizers, synthesizable SystemVerilog RTL coding standards, and testbench verification; home lab execution involves synthesis onto an FPGA board (Sipeed Tang Nano 20K / Artix-7) verified using Verilator, Cocotb, GTKWave, and an 8-channel USB logic analyzer.

### ME 201: Mechanics of Materials & Structural Statics
- **Prerequisites**: PHYS 101, MATH 102, MATS 101
- **Texts & Reading Scope**: James Gere & Barry Goodno – *Mechanics of Materials*.
- **Core Topics**: 3D static equilibrium, internal axial, torsional, shear-force, and bending-moment diagrams, 3D stress and strain tensors, Mohr's circle transformations, beam deflection, column buckling, and von Mises yield criteria.

### ME 202: 3D Analytical Dynamics
- **Prerequisites**: ME 201, MATH 201, MATH 202
- **Texts & Reading Scope**: Jerry Ginsberg – *Engineering Dynamics*.
- **Core Topics**: 3D kinematics in moving and rotating reference frames, transport theorem, Coriolis and centrifugal accelerations, 3D inertia tensors, Newton-Euler rigid-body equations of motion, gyroscopic precession, Hamilton's principle, and Lagrange's equations of motion with constraints.

---

## Tier 3: 300-Level Junior Specialization Tracks

### Track A: Silicon, Embedded Systems, Computer Architecture & Systems Software

#### ECE 301: Computer Organization & Processor Microarchitecture
- **Prerequisites**: ECE 201
- **Texts & Reading Scope**: David Harris & Sarah Harris – *Digital Design and Computer Architecture (RISC-V Edition)* (Ch. 6–8).
- **Core Topics**: Single-cycle, multi-cycle, and 5-stage pipelined RISC-V datapaths, structural/data/control hazards, forwarding units, branch prediction, multi-level cache hierarchies, virtual memory address translation (MMU/TLB), and Spike/QEMU ISA co-simulation.

#### ECE 302: CMOS VLSI Design
- **Prerequisites**: ECE 201, EE 201
- **Texts & Reading Scope**: Neil Weste & David Harris – *CMOS VLSI Design*.
- **Core Topics & Lab**: MOSFET current-voltage equations, CMOS inverter DC and switching characteristics, dynamic and leakage power dissipation, logical effort path optimization, standard-cell layout, clock-tree synthesis (CTS), static timing analysis (STA), and design rule checking (DRC); home lab execution uses the open-source OpenLane/LibreLane flow targeting the SkyWater 130 nm PDK, with optional tapeout through Tiny Tapeout.

#### ECE 303: Embedded Real-Time Firmware & RTOS
- **Prerequisites**: ECE 201, CS 201
- **Texts & Reading Scope**: Carmine Noviello – *Mastering STM32*; Richard Barry – *Mastering the FreeRTOS Real-Time Kernel*.
- **Core Topics**: Bare-metal startup code, linker scripts, nested vectored interrupt controllers (NVIC), multi-channel DMA pipelines, lock-free ring buffers, real-time preemptive scheduling (FreeRTOS), priority inversion protocols, memory protection units (MPU), and low-level peripheral drivers for CAN-FD, SPI, I2C, and UART.

#### CS 301: Operating Systems & Systems Programming
- **Prerequisites**: CS 201, ECE 301
- **Texts & Reading Scope**: Remzi Arpaci-Dusseau & Andrea Arpaci-Dusseau – *Operating Systems: Three Easy Pieces (OSTEP)*; Russ Cox, Frans Kaashoek & Robert Morris – *xv6: A Simple, Unix-Like Teaching Operating System (RISC-V)*.
- **Core Topics**: Virtual memory page table management, kernel traps and system calls, context switching, preemptive multi-threading, concurrency primitives (semaphores, mutexes, condition variables), deadlocks, I/O interrupt handlers, and POSIX file systems.

#### CS 302: Compiler Engineering
- **Prerequisites**: CS 201, ECE 301
- **Texts & Reading Scope**: Keith Cooper & Linda Torczon – *Engineering a Compiler*.
- **Core Topics**: Regular expressions, deterministic finite automata (DFA), lexical scanning, context-free grammars, LL/LR parsing, abstract syntax trees (AST), static single assignment (SSA) intermediate representation, control-flow graphs (CFG), data-flow optimization passes, graph-coloring register allocation, and RISC-V assembly code generation.

#### CS 303: Computer Networking & Robotic Middleware
- **Prerequisites**: CS 201, CS 301
- **Texts & Reading Scope**: James Kurose & Keith Ross – *Computer Networking: A Top-Down Approach* (Ch. 1–4 transport/network core); Francisco Martin Rico – *A Concise Introduction to Robot Programming with ROS2*.
- **Core Topics**: Layered network architecture, UDP and TCP socket programming, zero-copy inter-process communication (IPC), IEEE 1588 Precision Time Protocol (PTP) synchronization, Data Distribution Service (DDS) pub/sub topologies, and ROS 2 communication nodes, services, and actions.

---

### Track B: Microelectronics, Optoelectronics, DSP & RF

#### EE 301: Semiconductor Devices & Analog Electronics
- **Prerequisites**: EE 201
- **Texts & Reading Scope**: Paul Horowitz & Winfield Hill – *The Art of Electronics* (Ch. 1–8); Thomas Hayes – *Learning the Art of Electronics*.
- **Core Topics**: Small-signal and large-signal BJT/MOSFET modeling, current mirrors, differential pairs, high-gain output stages, operational amplifier frequency compensation and phase margin, active filters, precision voltage references, and low-noise analog signal conditioning.

#### EE 302: Sensors, Metrology & Data Conversion
- **Prerequisites**: EE 301, PHYS 103
- **Texts & Reading Scope**: Jacob Fraden – *Handbook of Modern Sensors*; Walt Kester – *Data Conversion Handbook* (selected SAR/Sigma-Delta ADC chapters).
- **Core Topics**: Wheatstone strain-gauge bridges, optical and magnetic shaft encoders, MEMS capacitive accelerometers and gyroscopes, photodiode transimpedance amplifiers (TIAs) for LiDAR/time-of-flight, Successive Approximation Register (SAR) and Sigma-Delta ADCs, and input-referred noise characterization.

#### EE 303: Digital Signal Processing (DSP)
- **Prerequisites**: EE 202
- **Texts & Reading Scope**: Richard Lyons – *Understanding Digital Signal Processing*.
- **Core Topics**: Discrete-time processing of continuous-time signals, decimation and interpolation, FIR linear-phase filter synthesis (Parks-McClellan), bilinear IIR filter synthesis, Fast Fourier Transform (FFT) algorithms, CORDIC math architectures, cascaded integrator-comb (CIC) decimators, and fixed-point finite word-length effects.

#### EE 304: Applied Electromagnetics & Microwave Engineering
- **Prerequisites**: EE 201, EE 202, MATH 205
- **Texts & Reading Scope**: David Pozar – *Microwave Engineering* (Ch. 1–5 and 11).
- **Core Topics & Lab**: Transmission line telegrapher equations, wave reflection coefficients, VSWR, Smith chart graphical matching, microstrip geometry synthesis, two-port S-parameter networks, low-noise amplifiers (LNAs), mixers, and phase-locked loop (PLL) local oscillators; home lab characterization uses a LiteVNA 64, tinySA Ultra, and openEMS 3D FDTD field simulations.

#### EE 305: Power Electronics & Switched-Mode Converters
- **Prerequisites**: EE 201, EE 202
- **Texts & Reading Scope**: Robert Erickson & Dragan Maksimovic – *Fundamentals of Power Electronics* (Ch. 1–9); Alex Lidow et al. – *GaN Transistors for Efficient Power Conversion* (selected layout/parasitics chapters).
- **Core Topics**: Non-isolated buck, boost, and buck-boost topologies, isolated flyback and forward converters, state-space averaging, small-signal control transfer functions, magnetic core selection and planar inductor design, high-side bootstrap and isolated gate drivers, and Gallium Nitride (GaN) switching transient management.

---

### Track C: Mechanical Design, Thermo-Fluids & Structural Analysis

#### ME 301: Machine Component Design & Tribology
- **Prerequisites**: ME 201, ME 202, ENGR 101
- **Texts & Reading Scope**: Richard Budynas & Keith Nisbett – *Shigley's Mechanical Engineering Design*; Alexander Slocum – *Precision Machine Design* (Ch. 1–3 structural loop stiffness and kinematic couplings).
- **Core Topics & Lab**: High-cycle fatigue life calculations (Goodman/Soderberg criteria), shaft and housing design, rolling-element bearing selection and preload, planetary and cycloidal gear reduction mechanics, fastener mechanics, and flexural/kinematic couplings; home lab uses CoreXY PA-CF 3D printing and SendCutSend cloud CNC manufacturing.

#### ME 302: Finite Element Analysis (FEA) & Structural Vibrations
- **Prerequisites**: ME 201, ME 202, MATH 204
- **Texts & Reading Scope**: Daryl Logan – *A First Course in the Finite Element Method*.
- **Core Topics & Lab**: Formulation of 1D truss/beam elements, 2D plane-stress/strain elements, and 3D isoparametric solid elements, global stiffness and mass matrix assembly, numerical quadrature, structural modal eigenfrequency extraction, and harmonic resonance analysis; home lab validation uses FreeCAD CalculiX/PrePoMax FEA confirmed via MEMS accelerometer physical tap tests and FFT analysis.

#### ME 303: Thermal Engineering & Heat Transfer
- **Prerequisites**: PHYS 101, MATH 202
- **Texts & Reading Scope**: Frank Incropera & David DeWitt – *Fundamentals of Heat and Mass Transfer*.
- **Core Topics & Lab**: Control-volume thermal energy balances, steady and transient multidimensional conduction, thermal contact resistance networks, laminar and turbulent forced/natural convective boundary layers, fin and heat-pipe heat sink design, and radiative surface exchange; home lab logging uses thermocouples and a USB-C thermal camera.

#### ME 305: Fluid Mechanics & Rotorcraft Aerodynamics
- **Prerequisites**: ME 202, MATH 205
- **Texts & Reading Scope**: Frank White – *Fluid Mechanics*; J. Gordon Leishman – *Principles of Helicopter Aerodynamics* (Ch. 2–6 and 12).
- **Core Topics & Lab**: Navier-Stokes equations, integral and differential momentum balances, boundary layer separation, Blade Element Momentum Theory (BEMT) for multirotor propellers, ducted fan aerodynamics, and ground effect; home lab testing uses an instrumented thrust/torque stand paired with OpenFOAM CFD simulations.

---

### Track D: Robotics Kinematics, Digital Control & Spatial Perception

#### ROB 301: Modern Robotics: Lie Groups, Spatial Dynamics & Simulation
- **Prerequisites**: MATH 201, ME 202
- **Texts & Reading Scope**: Kevin Lynch & Frank Park – *Modern Robotics: Mechanics, Planning, and Control* (Ch. 1–9 and 11); MuJoCo & Drake Official Documentation.
- **Core Topics**: Rotation matrices and matrix exponentials in $\mathrm{SO}(3)$, homogeneous transformations and twists in $\mathrm{SE}(3)$, Product of Exponentials (PoE) forward/inverse kinematics, geometric and analytical Jacobians, spatial inertia matrices, recursive Newton-Euler dynamics (RNEA), URDF modeling, and MuJoCo multibody simulation.

#### ROB 302: Feedback Control Systems
- **Prerequisites**: EE 202, MATH 202
- **Texts & Reading Scope**: Karl Johan Åström & Richard Murray – *Feedback Systems*.
- **Core Topics**: Linear state-space models, reachability and observability, state feedback pole placement, Linear Quadratic Regulator (LQR) optimal control, Luenberger state observers, frequency-domain transfer functions, Bode and Nyquist stability criteria, gain/phase margins, and PID loop shaping.

#### ROB 303: 3D Computer Vision & Multi-View Geometry
- **Prerequisites**: MATH 201, CS 201
- **Texts & Reading Scope**: Richard Szeliski – *Computer Vision: Algorithms and Applications*; Yi Ma, Stefano Soatto, Jana Kosecka & S. Shankar Sastry – *An Invitation to 3-D Vision*.
- **Core Topics**: Pinhole camera models, intrinsic/extrinsic calibration, radial/tangential distortion correction, epipolar geometry on $\mathrm{SE}(3)$, fundamental and essential matrices, calibrated stereo disparity algorithms, optical flow, sparse bundle adjustment, and Iterative Closest Point (ICP) point-cloud registration.

#### ROB 304: Lie-Group State Estimation & Factor-Graph SLAM
- **Prerequisites**: MATH 201, MATH 203, ROB 301
- **Texts & Reading Scope**: Timothy Barfoot – *State Estimation for Robotics*; Joan Solà – *A Micro Lie Theory for State Estimation in Robotics*.
- **Core Topics**: Recursive Bayesian filtering, Extended and Unscented Kalman Filters (EKF/UKF), manifold Error-State Kalman Filters (ESKF) on $\mathrm{SO}(3)$ and $\mathrm{SE}(3)$, maximum a posteriori (MAP) nonlinear least-squares smoothing, factor graphs using GTSAM/iSAM2, visual-inertial odometry (VIO), and LiDAR SLAM.

#### ROB 305: Digital Control & System Identification
- **Prerequisites**: ROB 302, EE 303
- **Texts & Reading Scope**: Gene Franklin, J. David Powell & Michael Workman – *Digital Control of Dynamic Systems*.
- **Core Topics**: Zero-Order Hold (ZOH) discretization, stability mapping from s-plane to z-plane, discrete-time state-space control, computational delay compensation, integrator anti-windup, quantization effects, and experimental frequency/time-domain parameter system identification.

---

## Tier 4: 400-Level Senior Advanced Systems

### ENGR 401: Systems Integration, Wire Harnessing & HIL Testing
- **Prerequisites**: ECE 303, EE 305, ME 301, ROB 305
- **Texts & Reading Scope**: NASA Systems Engineering Handbook; IPC/WHMA-A-620 Cable and Wire Harnessing Standards.
- **Core Topics**: Requirements decomposition, SWaP-C budgets, Failure Modes and Effects Analysis (FMEA), hardware watchdog architectures, high-flex robotic cable harnessing (Molex/JST crimping, shielding, strain relief), hardware-in-the-loop (HIL) automated test benches, and Kalibr multi-sensor spatial-temporal calibration.

### ECE 401: High-Speed Digital Design, Signal Integrity & EMC
- **Prerequisites**: ECE 301, EE 304
- **Texts & Reading Scope**: Eric Bogatin – *Signal and Power Integrity - Simplified*; Henry Ott – *Electromagnetic Compatibility Engineering*.
- **Core Topics**: Controlled-impedance multi-layer PCB stackups, ground return current paths, inductive/capacitive crosstalk, Power Distribution Network (PDN) target impedance optimization, decoupling capacitor placement, via inductance, RF shielding, and ground bounce mitigation.

### EE 401: Antenna Theory & SDR Digital Wireless Communications
- **Prerequisites**: EE 303, EE 304, MATH 203
- **Texts & Reading Scope**: Constantine Balanis – *Antenna Theory: Analysis and Design*; Michael Rice – *Digital Communications: A Discrete-Time Approach*.
- **Core Topics**: Microstrip patch antenna synthesis, planar phased arrays, link budget analysis, discrete-time QPSK/OFDM modulation, matched filtering, Gardner timing recovery, and Costas loop carrier phase synchronization.

### EE 402: Battery Management Systems & Pack Protection
- **Prerequisites**: EE 305, ME 303, MATH 203
- **Texts & Reading Scope**: Gregory Plett – *Battery Management Systems* (Vols. I & II); TI BQ769x2 Technical Reference Manual.
- **Core Topics**: Equivalent-circuit cell modeling (Randles models), online Extended Kalman Filter (EKF) State-of-Charge (SoC) and State-of-Health (SoH) estimation, active/passive cell balancing, pre-charge circuits, solid-state bidirectional e-fuses, and isolated CAN-FD telematics.

### EE 403: Electric Machinery & Field-Oriented Servo Drives
- **Prerequisites**: EE 305, ROB 305, ME 301
- **Texts & Reading Scope**: Paul Krause et al. – *Analysis of Electric Machinery and Drive Systems* (Ch. 1–6 only; skip utility grid generator sections).
- **Core Topics**: Magnetic reluctance, reference frame transformations (dq0 Clarke and Park transforms), Permanent Magnet Synchronous Machine (PMSM) dynamic equations, Space Vector PWM (SVPWM), inverter dead-time compensation, high-bandwidth current/torque loop tuning, and field-weakening control.

### ROB 401: Nonlinear & Geometric Control
- **Prerequisites**: ROB 301, ROB 302
- **Texts & Reading Scope**: Jean-Jacques Slotine & Weiping Li – *Applied Nonlinear Control*; Taeyoung Lee, Melvin Leok & N. Harris McClamroch – *Geometric Control of Mechanical Systems on Lie Groups* (selected $\mathrm{SO}(3)$ / $\mathrm{SE}(3)$ tracking papers/notes).
- **Core Topics**: Phase plane portraits, Lyapunov stability theory, Control Lyapunov Functions (CLFs), feedback linearization, sliding mode control, adaptive control, Cartesian impedance control, and coordinate-free geometric attitude/pose tracking on $\mathrm{SO}(3)$ and $\mathrm{SE}(3)$.

### ROB 402: Motion Planning & Model Predictive Control
- **Prerequisites**: ROB 301, ROB 305, CS 201, MATH 204
- **Texts & Reading Scope**: Steven LaValle – *Planning Algorithms*; Stephen Boyd & Lieven Vandenberghe – *Convex Optimization* (selected QP/conic chapters); James Rawlings et al. – *Model Predictive Control: Theory, Computation, and Design*.
- **Core Topics**: Configuration space obstacles, sampling-based kinodynamic planning (PRM, RRT, RRT*), trajectory smoothing, convex Quadratic Programming (QP), receding-horizon Model Predictive Control (MPC), and real-time embedded solver deployment (OSQP/acados).

---

## Tier 5: 500-Level Graduate Synthesis & Autonomous Machines

### ROB 501: Underactuated Robotics & Trajectory Optimization
- **Prerequisites**: ROB 401, ROB 402
- **Texts & Reading Scope**: Russ Tedrake – *Underactuated Robotics*.
- **Core Topics**: Underactuated mechanical systems, acrobot/pendulum swing-up, partial feedback linearization, limit cycles, Poincaré maps, hybrid zero dynamics for legged locomotion, centroidal momentum dynamics, and direct transcription/collocation trajectory optimization.

### ROB 502: Deep Learning & Reinforcement Learning for Robotics
- **Prerequisites**: ROB 303, ROB 304, MATH 203
- **Texts & Reading Scope**: Simon Prince – *Understanding Deep Learning*; Richard Sutton & Andrew Barto – *Reinforcement Learning: An Introduction*.
- **Core Topics**: Convolutional networks, Residual networks, Transformer attention architectures, Diffusion action policies, Markov Decision Processes (MDPs), temporal-difference learning, actor-critic policy gradients (PPO), domain randomization, and Sim-to-Real reinforcement learning transfer.

---

## Capstone Project Listing

| Capstone | Title | Unlocking Courses | Scope & Deliverables | Estimated BOM |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Custom 32-Bit RISC-V SoC, 6-Layer PCB, Compiler & Preemptive RTOS** | ECE 401, CS 301, CS 302 | Synthesize a custom 5-stage pipelined RISC-V CPU on an FPGA; design a 6-layer controlled-impedance carrier PCB in KiCad with onboard SDRAM and QSPI Flash; verify PCB trace impedance via TDR on a LiteVNA; port a C compiler backend and boot a custom preemptive RTOS kernel (optional Tiny Tapeout Sky130 ASIC submission). | \$120–\$250 |
| **2** | **Custom 915 MHz / 2.4 GHz ISM SDR Transceiver & Patch Array Link** | EE 401 | Design and assemble an RF front-end PCB and microstrip patch antenna array tuned for the 915 MHz ISM band; validate link performance over coax using 30 dB SMA attenuators or under legal sub-1 mW ISM radiated limits; characterize $S_{11}$ reflection and spectral emissions on LiteVNA and tinySA Ultra. | \$80–\$150 |
| **3** | **Smart 6S LiFePO4 BMS & Multi-Rail Power Distribution Unit** | EE 402 | Build a 6S ( $< 25.2\text{ V}$ SELV limit) smart BMS PCB integrating a TI BQ769x2 Analog Front-End, STM32 supervisor MCU, isolated CAN-FD transceiver, solid-state bidirectional e-fuse, and high-efficiency synchronous buck converters; implement an online EKF for real-time State-of-Charge estimation, validated on a 150W DC electronic load. | \$100–\$180 |
| **4** | **High-Torque Quasi-Direct-Drive (QDD) Actuator & 20 kHz FOC Drive** | EE 403 | Pair a pancake frameless BLDC motor (5010/8108 size) with an integrated 8:1 cycloidal reducer fabricated from PA-CF 3D prints, ground steel dowel pins, thin-section bearings, and cloud-milled aluminum plates; build a 24V 3-phase inverter PCB with DFN5x6 MOSFETs and a 14-bit magnetic encoder (AS5047P), closing a 20 kHz Field-Oriented Control (FOC) torque loop on an STM32G4 MCU. | \$90–\$140 / act. |
| **5** | **Desktop 6-DOF Precision Robot Arm & 6-Axis Force/Torque Wrist** | ROB 401, ROB 402 | Assemble a 500 mm reach desktop 6-DOF industrial robot arm driven by 6x Capstone 4 actuators, 3K carbon-fiber structural tubes, and SendCutSend CNC aluminum brackets; design and calibrate a Maltese-cross wrist flexure outfitted with 6 mini load cells and a 24-bit ADC (ADS1256); implement real-time gravity compensation, Cartesian impedance control, and RRT* obstacle avoidance. | \$600–\$900 |
| **6** | **Synchronized Visual-Inertial-LiDAR SLAM & Spatial AI Pod** | ROB 303, ROB 304, ROB 502 | Build a rigid sensor payload containing dual OV9281 global-shutter monochrome cameras (stereo baseline), an industrial BMI088 6-axis IMU, and a Livox Mid-360 or RPLiDAR unit; implement sub-microsecond hardware trigger synchronization using an MCU/FPGA; calibrate spatial-temporal transforms using Kalibr; execute real-time factor-graph visual-inertial-LiDAR odometry (VIO/SLAM) and spatial neural network object detection. | \$250–\$650 |
| **7** | **Sub-250g Ducted Carbon-Fiber Quadrotor with Custom Flight Computer** | ME 305, ROB 401, ROB 501 | Fabricate a sub-250g prop-guarded airframe using SendCutSend CNC carbon-fiber plates and energy-absorbing 3D-printed TPU ducts; develop a custom STM32 flight controller PCB, low-noise IMU, and 915 MHz SDR teleoperation link (Capstone 2); deploy coordinate-free $\mathrm{SE}(3)$ geometric tracking control and optical flow/VIO indoor collision-avoidance algorithms within safety netting or tethered harnesses. | \$180–\$280 |
| **8** | **Apex Thesis: Desktop-Scale 12-DOF Torque-Controlled Quadruped / Wheeled-Biped** | ROB 501, ROB 502, ENGR 401 | Build an 8–10 kg dynamic legged quadruped (MIT Mini-Cheetah / ODRI Solo-12 class) serving as the system-level convergence of Capstone 1 (central compute brain), Capstone 2 (wireless telemetry), Capstone 3 (smart BMS power rail), Capstone 4 (12x quasi-direct-drive joint actuators), and Capstone 6 (spatial SLAM pod); execute dynamic trot, jump, and rough-terrain gaits suspended under a doorway pull-up bar safety bungee gantry using convex Model Predictive Control (MPC) and Sim-to-Real reinforcement learning policies. | \$900–\$1,500 incr. |

---

## Phased Home-Lab Infrastructure & Safety Protocols

### Workbench Tooling Blueprint

#### 1. Electronics & SMD Bench (~USD 500–900 phased over curriculum)
- **Oscilloscope**: 4-channel 70–100 MHz digital storage oscilloscope (e.g., Rigol DHO804 or Siglent SDS1104X-E).
- **Power & Load**: 30V/5A programmable dual-channel current-limited DC bench power supply paired with a 150W DC programmable electronic load.
- **Logic & Debugging**: \$15 USB 24 MHz 8-channel logic analyzer (Sigrok/PulseView compatible), hardware ST-Link/JTAG programmer-debuggers, and a USB-to-CAN-FD interface adapter.
- **Assembly & Soldering**: Temperature-controlled soldering iron (Pinecil or Hakko), MHP30 mini reflow hotplate, hot-air SMD rework station, stainless steel solder stencils, and Engineer PA-09/PA-24 ratcheting crimp tools for Molex Micro-Fit, JST-GH, and XT30 connectors.

#### 2. RF & Metrology Bench (~USD 250 phased in Tier 3)
- **Vector Network Analyzer & Spectrum Analyzer**: LiteVNA 64 (50 kHz to 6.3 GHz) with an SMA Open/Short/Load calibration kit (for $S_{11}$ / $S_{21}$ sweeps and TDR PCB trace impedance analysis); tinySA Ultra spectrum analyzer (up to 5.3 GHz).
- **RF Accessories**: 20 dB and 30 dB SMA inline attenuators for direct coaxial cable transmitter verification without unshielded radiation.
- **Metrology**: Digital vernier calipers, 0.01 mm dial indicator with a heavy magnetic base, and a budget USB-C thermal camera ( \$150 ) for monitoring thermal boundaries.

#### 3. Mechanical Prototyping Bench (~USD 400–800)
- **Additive Manufacturing**: Enclosed CoreXY 3D printer with a hardened steel nozzle capable of extruding engineering filaments (PA-CF, PETG-CF, polycarbonate, TPU).
- **Hardware Fasteners & Bearings**: Heat-set insert press, assortment of metric socket-head screws, ground shoulder bolts, steel dowel pins, and thin-section precision ball bearings.
- **Mechanical Test Rig**: Modular 2020-extrusion frame with an HX711-interfaced 50 kg load cell for destructive tensile/creep coupons (MATS 101) and propeller thrust/torque measurements (ME 305).
- **Cloud Digital Manufacturing**: Turnkey on-demand laser cutting, CNC sheet bending, and 5-axis aluminum milling services (SendCutSend, JLCCNC, PCBWay CNC) for 6061-T6 aluminum and 3K carbon-fiber brackets.

### Residential Safety Protocols

#### Electrical & Energy Storage Safety
- **SELV Voltage Ceiling**: All battery configurations are strictly limited to 6S ( $< 25.2\text{ V}$ ) to maintain all exposed circuits and busbars within Safe Extra-Low Voltage (SELV) regulations.
- **Current-Limited Bring-Up**: Initial hardware bring-up of motor drives, inverters, power distribution boards, and BMS circuits must always be conducted using a current-limited bench power supply before connecting live chemistry.
- **Battery Storage & Charging Containment**: Lithium-based battery packs must be charged and stored inside fiberglass fireproof LiPo bags or sealed steel ammo cans.
- **Emergency Stop (E-Stop)**: An emergency physical mushroom shut-off switch (E-stop) must be wired directly in series with the battery pack power feed.

#### Mechanical & Flight Testing Safety
- **Firmware Guardrails**: High-torque actuators (Capstone 4), multi-axis arms (Capstone 5), multirotors (Capstone 7), and legged platforms (Capstone 8) must be configured with hard software velocity, current, and travel limits in firmware.
- **Enclosed Flight Testing**: Aerial vehicle dynamic testing must take place strictly indoors inside protective safety netting or tethered to the ceiling.
- **Overhead Bungee Gantry**: Dynamic legged robots must be suspended from an overhead doorway pull-up bar using an elastic bungee gantry during all gait bring-up, tuning, and reinforcement learning policy deployments.
