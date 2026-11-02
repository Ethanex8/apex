# Apex Curriculum & Course Design Invariants

## 1. Prerequisite Closure & Course Granularity
- **100% Prerequisite Representation**: Every prerequisite topic required to understand a course or its assigned textbook chapters must be explicitly covered in an upstream prerequisite course in the DAG.
- **Standard University Course Boundaries ("Split, Don't Cram")**: Align course scopes with standard university engineering curricula. Do not compress two distinct courses into a single hybrid course (e.g., separate Statics from Mechanics of Materials, C Systems Programming from Algorithms, Thermodynamics from Heat Transfer, Applied Electromagnetics from Microwave RF, Mechanical Vibrations from FEA, Antennas from Digital Communications, Motion Planning from MPC, and Deep Learning from Reinforcement Learning). Only fold a topic into an existing course when it is genuinely a compact module (such as the calculus of variations within Analytical Dynamics).

## 2. Textbook Selection Principles
- **Engineering Pedagogy Over Reference Handbooks**: Always select textbooks written for first-exposure engineering pedagogy (step-by-step derivations, physical intuition, worked examples, and graded exercises) rather than encyclopedic practitioner handbooks or pure-math/theoretical-physics monographs.
- **Single-Textbook Preference**: Prefer a single cohesive textbook that covers the entire course over stitching together multiple books. Only use two books when pairing a theory textbook with a dedicated lab/tooling guide (e.g., Circuit Theory + KiCad, OS Theory + xv6). If a course requires two theory textbooks from different sub-disciplines, evaluate whether the course should be split into two courses.
- **No Optional Textbook Clutter**: Prescribe a single authoritative reading path for each course. Never include parenthetical `(or ...)` alternative textbooks or optional reference lists.
- **Explicit Chapter Scoping**: Whenever a textbook includes advanced or tangential chapters covered in later courses (or outside the course scope), explicitly specify the exact chapter reading scope.
