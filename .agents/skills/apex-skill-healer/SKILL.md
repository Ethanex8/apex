---
name: apex-skill-healer
description: Closed-loop skill and verification-gate self-healing protocol triggered when user review feedback reveals a blind spot in Apex authoring or auditing pipelines. Runs blind-subagent recall replay against harvested comments and graduates generalizable critiques into deterministic Python/Playwright gates and calibration ledgers before patching deliverable files.
---

# Apex Self-Healing Skill & Gate Protocol

Execute this skill automatically whenever user feedback (PR inline comments or chat critique during `in_review`) reveals a defect that our authoring, audit, or verification pipeline should have prevented or caught independently.

## Step 0: Classify Feedback Tier

- **Tier 0 (Pure Typo / Accidental Slip)**: Localized misspelling or typo already prohibited by existing rules. Fix directly; no replay overhead needed.
- **Tier 1 (Single Localized Generalizable Nit)**: One self-contained flaw lacking a check. Add a deterministic check (`scripts/check_*.py` + test fixture) or tighten the governing rule + `references/calibration_log.md`, verify, then fix the deliverable.
- **Tier 2 (`2+` Comments OR Any Structural, Pedagogical, Visual, or Recurring Critique)**: Mandatory **Blind Recall Convergence Loop** (Steps 1–5 below). **Never edit deliverable code/chapter files before Steps 1–4 converge.**

---

## Step 1: Harvest Feedback & Freeze Pre-Fix Snapshot

1. If feedback lives on a GitHub PR, harvest all human comments structurally:
   ```bash
   python3 scripts/harvest_feedback.py --pr <N> --out .cache/feedback/pr-<N>.json
   ```
   Combine with any chat critiques into a numbered **Ground-Truth Feedback List** (`U1..Uk`).
2. Record the unmodified pre-fix state (`git rev-parse HEAD`, or save temporary read-only path list of untouched files).

---

## Step 2: Independent Blind Baseline Audit (Zero Comment Leakage)

Spawn an isolated `research` subagent (`invoke_subagent`, `Model: 'inherit'`, `Workspace: 'inherit'`, `Role: Blind Calibration Auditor`) to review the **unmodified** target files (plus `.cache/visual-audit/<slug>/*.png` for chapters/widgets) using only `.agents/skills/*/SKILL.md` and `GEMINI.md`.

- **Strict Isolation Rule**: Never paste, hint at, or summarize any user comment (`U1..Uk`) inside the subagent prompt. Ask for Part 1 (Macro/Structural Lens A) and Part 2 (Line-by-Line Lens B).

---

## Step 3: Recall Matrix & Upstream-First Healing

Compare blind findings (plus deterministic outputs from `check_code.py`, `check_book.py`, and `check_visuals.py`) against `U1..Uk`:
- Mark each generalizable item **`CAUGHT_BY_GATE`**, **`CAUGHT_BY_BLIND_SUBAGENT`**, or **`MISSED`**.

For every **`MISSED`** generalizable item, ask *"Why did our pipeline miss this without user help?"* and heal **upstream first**:
1. **Deterministic Gate First (Preferred)**: If mechanically checkable (line length, slice size, syntax, SVG clipping, viewport overflow, contrast, missing docstring/field check), add it to `scripts/check_book.py`, `scripts/check_code.py`, or `scripts/check_visuals.py` plus a regression test in `scripts/tests/`.
2. **Skill Prompt + Calibration Ledger**: If judgment/pedagogical/architectural, sharpen the rule in `.agents/skills/<skill>/SKILL.md`—consolidating existing bullets so every `SKILL.md` stays `<= 120` lines—and append a root-cause entry (`Defect`, `Why Missed`, `Gate/Skill Fix`) to `.agents/skills/<skill>/references/calibration_log.md`.

---

## Step 4: Blind Convergence Replay

Re-run deterministic checks AND a **fresh** isolated `research` subagent (zero shared conversation history, zero user comments leaked) on the **still-unmodified pre-fix snapshot**:
- Confirm every Tier 2 generalizable feedback item now triggers cleanly as **`CAUGHT_BY_GATE`** or **`CAUGHT_BY_BLIND_SUBAGENT`**.
- If any item stays `MISSED`, refine the gate/skill rule in Step 3 and replay again until `100%` recall convergence.

---

## Step 5: Heal Deliverable & Verify Full Gate Suite

Only after convergence (and before pushing/re-requesting review):
1. Apply all fixes cleanly to deliverable source code, tests, chapter prose, CSS, and Vue widgets via `apex-artifact-author` and `apex-textbook-author`.
2. Run the full static, visual, and coverage verification suite (`check_code.py`, `sync_book.py --check`, `check_book.py`, `build.py --check`, `BOOK_BASE=/apex/ npm --prefix book run build`, `check_visuals.py --screenshot-dir .cache/visual-audit`, and `pytest --cov-fail-under=95`).
3. Include a brief **Pipeline Self-Healing Note** in the reply listing which gate/skill/calibration updates now prevent recurrence automatically.
