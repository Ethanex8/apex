# Architecture & Spec-Correctness Auditor Rubric

Audit every code, script, firmware, hardware-description, or simulation shard against the project's architecture specs/READMEs and paired test suites:

## 1. Interface Contracts, Spec Precision & Failure Safety
1. **Interface & Spec Fidelity**: Verify exact conformance to documented project contracts—API schemas, register layouts, bitmasks, byte ordering, alignment, protocol framing, and physical or safety bounds.
2. **Fixed-Width & Numeric Precision Traps**: Catch host-vs-target width/sign bugs—Python arbitrary-width signed masks, JavaScript signed `>>` vs `>>>` or 53-bit `Number` loss on 64-bit math, floor vs truncating division, and integer overflow/wrapping.
3. **Fail-Fast Preconditions & Zero Dead Branches**: Flag silent fallbacks, swallowed exceptions/API errors, CWD-fragile relative paths, unguarded inputs, or unreachable dead branches.

## 2. Conditional Domain Checks (When Authoring These Artifacts)
4. **SystemVerilog RTL (`.sv`/`.svh`)**: Flag inferred latches, blocking `=` in `always_ff` or non-blocking `<=` in `always_comb`, missing/inverted reset states, unsynchronized clock-domain crossings, width/sign truncation, and non-synthesizable constructs outside testbenches.
5. **Bare-Metal C & Assembly (`.c`/`.h`/`.S`)**: Flag missing `volatile` on hardware registers or interrupt-shared flags, signed-overflow/alignment undefined behavior, unbounded loops or heap allocation inside interrupts, missing safe-state fault paths, and callee-saved register corruption in `.S`.
6. **Hardware CAD, PCB & Physics Models (`.xml`/KiCad/Widgets)**: Flag missing ERC/DRC zero-violation exit checks, Pin-1/BOM mismatches, non-positive inertias or violated actuator/safety caps in simulation models, and unguarded numerical instability.

## 3. Adversarial & Independent Verification
7. **Independent Tests & `>= 95%` Edge Coverage**: Flag tests that copy-paste production formulas circularly, omit error/fault/boundary/reset cases, miss verifying full mutated state plus unmodified invariants, or use non-deterministic seeds.
