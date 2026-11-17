# Apex Systems Engineering

This companion textbook is written for engineers and aspiring engineers who know general programming plus undergraduate math and physics and want to master processor architecture, circuit-board physics, motor control, and legged robotics from first principles.

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
    <span class="stat-label">Verified Steps and Labs</span>
  </div>
  <div class="book-hero-stat">
    <span class="stat-num">100%</span>
    <span class="stat-label">Live-Synced Code</span>
  </div>
</div>

---

## Preface

**Apex** unifies digital logic, printed-circuit electromagnetics, compiler construction, power electronics, and dynamic control around a single cohesive machine: an indoor-safe (about 2.5 kg, under 22 V) autonomous quadruped built without throwaway prototypes.
Across eight chronological parts, we design a custom 32-bit processor implementing the open-standard **Reduced Instruction Set Computer, Fifth Generation** (RISC-V) architecture and deploy it onto a reprogrammable logic chip (**Field-Programmable Gate Array**, or FPGA).
We then route a 6-layer controlled-impedance circuit board, write a C compiler and a deterministic task scheduler (**Real-Time Operating System**, or RTOS), build 20 kHz brushless motor drives and solid-state battery protection, and close whole-body locomotion and stereo navigation loops.

Every chapter develops one primary engineering discipline—combining gentle mathematical derivations, interactive visualizers, verified source code in `systems/`, and closing hardware bench labs—growing section by section as each implementation step lands.

---

## Start Reading

The prologue establishes the locked electrical, mechanical, and communication contracts shared across all six subsystems, and Chapter 1 begins Part I by constructing the software golden reference processor.
Every chapter combines gentle mathematical derivations, interactive hardware visualizers, and live-synced code excerpts designed to be read sequentially:

- **[Prologue — System Architecture and Contracts](/vision)** — How the six physical subsystems bolt directly into the final quadruped without circuit-board redesigns or throwaway bench builds.
- **[Chapter 1 — Instruction Set Architecture](/brain/01_isa_and_binary_arithmetic)** — Software golden reference modeling, fixed-width modular binary arithmetic and two's complement, 32-bit instruction encoding, memory-mapped device registers, and fault or interrupt redirects (**traps**).

---

## Complete Syllabus

The thirty-four chapters below follow the exact dependency order of `roadmap.yaml`, progressing from digital logic gates and board physics through actuators, power electronics, single-leg dynamics, quadruped walking, and stereo vision.
Each part builds one major engineering layer and links directly to its subsystem reference contract.

### Part I — Digital Logic and Processor Architecture

Part I constructs the custom 32-bit `brain` processor from fixed-width binary arithmetic up to a 5-stage pipelined hardware design accelerated by a custom two-lane 16-bit **Multiply-Accumulate** (`mac`) instruction.
Every combinational circuit, register file, arithmetic unit, and trap path is verified instruction-for-instruction against a software reference model and timing-closed on reprogrammable FPGA fabric ([`brain` Reference](/brain/)).

| Ch. | Title and Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **1** | **[Instruction Set Architecture](/brain/01_isa_and_binary_arithmetic)**<br/>Golden reference modeling, modular binary arithmetic and two's complement, 32-bit instruction encoding, memory-mapped device registers, and hardware traps. | `brain-01` | <span class="book-status-live">Published</span> |
| **2** | **Combinational and Sequential Logic**<br/>Carry-chain adders, single-cycle barrel shifters, signed and unsigned comparators, clocked flip-flops, timing windows, 32×32 register files, and sign extension. | `brain-02` to `brain-03` | <span class="book-status-upcoming">Upcoming</span> |
| **3** | **Clock Domains and Serial Framing**<br/>Flip-flop metastability, two-stage synchronizers, 16×-oversampled serial framing with byte queues, and logic-analyzer hardware capture. | `brain-04` to `brain-05` | <span class="book-status-upcoming">Upcoming</span> |
| **4** | **Single-Cycle Processor Design**<br/>Control-table decoding, conditional branches, little-endian byte and halfword alignment, on-chip static memory, and 10k-instruction lockstep verification. | `brain-06` to `brain-08` | <span class="book-status-upcoming">Upcoming</span> |
| **5** | **Multi-Cycle Arithmetic and Traps**<br/>Valid/ready handshakes, shift-add multiply and restoring divide, two-lane 16-bit `mac` dot-product hardware, control registers, and 64-bit cycle timers. | `brain-09` to `brain-11` | <span class="book-status-upcoming">Upcoming</span> |
| **6** | **Pipelined Processor Design**<br/>Five-stage throughput versus latency, data-hazard forwarding networks, load-use stalls, precise trap flushes, 100k-instruction stress testing, and 50 MHz timing closure. | `brain-12` to `brain-16` | <span class="book-status-upcoming">Upcoming</span> |

### Part II — Circuit-Board Physics and Memory Interconnects

Part II moves off the bare processor core onto the central 6-layer Spine circuit board connecting the processor, battery, and leg buses, modeling copper traces as electromagnetic waveguides and designing clean switching power rails.
We then build the on-chip memory crossbar, external flash and dynamic **Random-Access Memory** (RAM) controllers, and real-time sensor and motor-bus peripherals ([`brain` Reference](/brain/)).

| Ch. | Title and Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **7** | **Power Delivery and Transmission Lines**<br/>Synchronous step-down switching physics, USB-C power negotiation, copper traces as waveguides, impedance reflections, and multi-stage ceramic capacitor networks. | `brain-17` to `brain-18` | <span class="book-status-upcoming">Upcoming</span> |
| **8** | **Six-Layer Circuit Board Design**<br/>Unbroken ground return planes, four-wire voltage sensing, series damping, 120 Ω differential bus termination, test coupons, length matching, and layout verification. | `brain-19` to `brain-23` | <span class="book-status-upcoming">Upcoming</span> |
| **9** | **Memory Bus and External Controllers**<br/>Address-decoded bus crossbars, 4-wire persistent flash direct-execution engines, and dynamic RAM capacitor refresh, row/column timing, and burst scheduling. | `brain-24` to `brain-26` | <span class="book-status-upcoming">Upcoming</span> |
| **10** | **System-on-Chip Peripherals and Clocking**<br/>Motion-sensor serial bursts, sub-microsecond camera shutter latching, differential motor-bus framing and checksums, phase-shifted clock capture, and dock boot. | `brain-27` to `brain-29` | <span class="book-status-upcoming">Upcoming</span> |

### Part III — Compilers and Real-Time Operating Systems

Part III builds the complete software toolchain and operating kernel that run natively on our custom processor without external black-box libraries.
We implement a two-pass assembler, linker, optimizing C subset compiler (SysC), preemptive real-time kernel, and custom-board hardware validation suite ([`brain` Reference](/brain/)).

| Ch. | Title and Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **11** | **Assembly and C Front-End Parsing**<br/>Two-pass label resolution, upper/lower address relocations, Flash-to-RAM linker maps, lexical scanning, recursive-descent parsing, pointer typing, and intermediate lowering. | `brain-30` to `brain-32` | <span class="book-status-upcoming">Upcoming</span> |
| **12** | **Compiler Optimization and Code Generation**<br/>Fixed-point optimization with hardware-register ordering barriers, backward liveness, linear-scan register allocation, stack frames, `mac` emission, and equivalence checks. | `brain-33` to `brain-35` | <span class="book-status-upcoming">Upcoming</span> |
| **13** | **Preemptive Real-Time Kernel**<br/>Bare-metal startup, Flash-to-RAM bootloading, 31-register trap-scratchpad (`mscratch`) context switching, priority-inheritance locks, and single-producer ring buffers. | `brain-36` to `brain-37` | <span class="book-status-upcoming">Upcoming</span> |
| **14** | **Fixed-Point Control and Bring-Up**<br/>Scaled-integer attitude filtering, 1 kHz feedback jitter histograms, interactive `ash` serial shell, sub-millisecond 16-bit neural inference, trace-reflection sweeps, and board graduation. | `brain-38` to `brain-42` | <span class="book-status-upcoming">Upcoming</span> |

### Part IV — Brushless Motors and Power Inverters

Part IV develops the `drive` force-controlled joint actuator, deriving permanent-magnet brushless motor physics and rotating-frame current control from electromagnetic first principles.
We design a 4-layer three-phase power inverter, write 20 kHz bare-metal motor firmware, and machine an 8:1 low-backlash planetary gearbox ([`drive` Reference](/drive/)).

| Ch. | Title and Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **15** | **Field-Oriented Motor Control**<br/>Three-phase motor induced voltage and magnetic torque, rotating coordinate transforms, space-vector modulation headroom, and nested 20 kHz current plus 1 kHz stiffness loops. | `drive-01` to `drive-04` | <span class="book-status-upcoming">Upcoming</span> |
| **16** | **Three-Phase Power Inverters**<br/>Low-side resistor current sampling, scaled-integer motor packets, transistor switching losses and gate-drive charge pumps, ringing damping, and 4-layer circular board layout. | `drive-05` to `drive-12`, `drive-14` | <span class="book-status-upcoming">Upcoming</span> |
| **17** | **Real-Time Motor Control Firmware**<br/>Shift-add fixed-point trigonometry, timer-triggered analog sampling, 14-bit magnetic angle speed tracking, coil resistance/inductance calibration, cogging compensation, and zero-wait RAM execution. | `drive-13`, `drive-15` to `drive-21` | <span class="book-status-upcoming">Upcoming</span> |
| **18** | **Planetary Geartrains and Actuator Bring-Up**<br/>Reflected rotor inertia, 8:1 gear-tooth geometry, parametric 3D **Computer-Aided Design** (CAD), finite-element tooth stress analysis, tolerance stack-ups, oscilloscope switching checks, and haptic wheel graduation. | `drive-22` to `drive-30` | <span class="book-status-upcoming">Upcoming</span> |

### Part V — Battery Systems and Solid-State Protection

Part V engineers the touch-safe (under 22 V) `power` distribution spine that feeds twelve dynamic actuators without brownouts or hazardous fault currents.
We model six-cell lithium-iron-phosphate battery dynamics, design microsecond solid-state circuit breakers, and test real short-circuit cutoffs on the bench ([`power` Reference](/power/)).

| Ch. | Title and Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **19** | **Battery Dynamics and State Estimation**<br/>Six-cell lithium-iron-phosphate internal impedance and flat voltage plateaus, capacitive startup surge and regenerative braking energy, and nonlinear Kalman fuel-gauge estimation. | `power-01` to `power-03` | <span class="book-status-upcoming">Upcoming</span> |
| **20** | **Solid-State Circuit Breakers**<br/>Back-to-back transistor current blocking, transient-clamped inductive turn-off, 5 V step-down loop stability, emergency-stop latching, and thick-copper thermal board layout. | `power-04` to `power-11`, `power-14` | <span class="book-status-upcoming">Upcoming</span> |
| **21** | **Power Supervision and Fault Testing**<br/>Numerically stable C covariance updates, pre-trigger black-box fault logs, soft pre-charge short-circuit guards, thermistor temperature calibration, and sub-5 µs short-circuit bench tests. | `power-12` to `power-13`, `power-15` to `power-24` | <span class="book-status-upcoming">Upcoming</span> |

### Part VI — Rigid-Body Kinematics and Compliant Limbs

Part VI combines three `drive` actuators into the 3-joint `limb` assembly that later bolts directly onto the quadruped as Front-Left Leg #1.
We derive 3D rigid-body kinematics, recursive inverse dynamics, sensorless impact detection, and foot-space spring-damper hopping control ([`limb` Reference](/limb/)).

| Ch. | Title and Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **22** | **Rigid-Body Kinematics**<br/>3D rotation matrices and rigid-body twists, exponential-map forward kinematics, closed-form geometric inverse kinematics with singularity clamping, and virtual-work Jacobian torque mapping. | `limb-01` to `limb-04` | <span class="book-status-upcoming">Upcoming</span> |
| **23** | **Inverse Dynamics and Impedance Control**<br/>Linear-time Newton-Euler gravity and inertia sweeps, 3D foot-space spring-damper control, and physics-engine verification with 64× reflected rotor inertia. | `limb-05` to `limb-07` | <span class="book-status-upcoming">Upcoming</span> |
| **24** | **Contact Estimation and Hopping Control**<br/>Sensorless momentum-based impact detection, smooth polynomial foot swing paths, spring-loaded pogo energy control, fixed-point C kinematics, and hardware-to-physics co-simulation. | `limb-08` to `limb-12` | <span class="book-status-upcoming">Upcoming</span> |
| **25** | **Low-Inertia Limb Mechanics**<br/>Hip-mounted belt transmissions, landing impulse and column buckling, neutral-axis cable routing, 4g landing stress analysis, vertical rail test stand CAD, and software torque limits. | `limb-13` to `limb-21` | <span class="book-status-upcoming">Upcoming</span> |
| **26** | **Embedded Leg Control and Hopping**<br/>1 kHz C leg control loop, joint zero-offset calibration, dynamic friction identification, weightless gravity float, soft drop landings, and 30-hop rail graduation. | `limb-22` to `limb-28` | <span class="book-status-upcoming">Upcoming</span> |

### Part VII — Optimal Balance and Learned Locomotion

Part VII assembles four legs, the `power` spine, and the `brain` computer into the complete 12-joint `walker` quadruped.
We implement floating-base state estimation, receding-horizon convex force control, and scaled-integer (**quantized**) reinforcement-learning policies executing directly on our custom `mac` datapath ([`walker` Reference](/walker/)).

| Ch. | Title and Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **27** | **Floating-Base State Estimation**<br/>Unanchored 18-degree-of-freedom body modeling, foot-contact Kalman speed/height estimation, friction-cone force optimization, capture-point footholds, motor voltage limits, and fall reflexes. | `walker-01` to `walker-07` | <span class="book-status-upcoming">Upcoming</span> |
| **28** | **Centroidal Model Predictive Control**<br/>Single-rigid-body linearization, 200 ms receding-horizon convex force optimization, predictive diagonal trotting, slip reflexes, and energy-efficiency benchmarks. | `walker-08` to `walker-14` | <span class="book-status-upcoming">Upcoming</span> |
| **29** | **Learned Locomotion Policies**<br/>Partially observable locomotion formulation, from-scratch policy-gradient reinforcement learning, parallel physics domain randomization, 16-bit `mac` export, and cycle-accurate walking simulation. | `walker-15` to `walker-22` | <span class="book-status-upcoming">Upcoming</span> |
| **30** | **Quadruped Chassis and Field Walking**<br/>Carbon sandwich torso CAD, diagonal-trot torsional stress analysis, twisted-pair motor-bus harnesses, overhead safety gantry, actuator system identification, and untethered walking graduation. | `walker-23` to `walker-34` | <span class="book-status-upcoming">Upcoming</span> |

### Part VIII — Stereo Vision and Autonomous Navigation

Part VIII mounts the `sight` synchronized stereo-camera head onto `walker`, phase-locking global-shutter exposures to `brain`'s hardware timer within microseconds.
We derive projective camera geometry, visual-inertial odometry, 3D obstacle mapping, and collision-free trajectory planning for untethered indoor autonomy ([`sight` Reference](/sight/)).

| Ch. | Title and Scope | Steps | Status |
| :---: | :--- | :--- | :---: |
| **31** | **Stereo Camera Geometry**<br/>Pinhole optics and lens distortion, stereo image rectification and quadratic depth error, feature optical flow with outlier rejection, inertial integration, and sub-50 µs shutter sync. | `sight-01` to `sight-06` | <span class="book-status-upcoming">Upcoming</span> |
| **32** | **Visual-Inertial Odometry and Mapping**<br/>Rotation-manifold visual-inertial state estimation, sparse bundle adjustment, loop closure, probabilistic 2.5D/3D obstacle grids, metric scale observability, and the 2 Mbps `brain`–`sight` link. | `sight-07` to `sight-13` | <span class="book-status-upcoming">Upcoming</span> |
| **33** | **Motion Planning and Navigation Safety**<br/>Robot-radius obstacle inflation with graph/tree path search, dynamic-window velocity tracking, 8-bit neural safety margins, 150 ms communication-timeout safe stops, and full autonomy simulation. | `sight-14` to `sight-18` | <span class="book-status-upcoming">Upcoming</span> |
| **34** | **Stereo Vision Hardware and Autonomy**<br/>Global-shutter stereo baseline sizing, rigid head pod CAD, shutter-sync cable interface, calibration target geometry, handheld room mapping, and untethered obstacle-avoiding quadruped graduation. | `sight-19` to `sight-28` | <span class="book-status-upcoming">Upcoming</span> |
