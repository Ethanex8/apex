---
name: apex-skill-healer
description: Closed-loop skill and verification-gate self-healing protocol triggered when user review feedback reveals a blind spot in Apex authoring or auditing pipelines. Runs blind-subagent recall replay against harvested comments and graduates generalizable critiques into deterministic Python/Playwright gates and calibration ledgers before patching deliverable files.
---

# Apex Self-Healing Skill & Gate Protocol

Execute this skill automatically whenever user feedback (PR inline comments or chat critique during `in_review`) reveals a defect that our authoring, audit, or verification pipeline should have prevented or caught independently.

## Step 0: Classify Feedback Tier

- **Tier 0 (Pure Typo / Accidental Slip)**: Localized misspelling or typo already prohibited by existing rules. Fix directly; no replay overhead needed.
- **Tier 1 (Single Localized Generalizable Nit)**: One self-contained flaw lacking a check. Add a deterministic check (`scripts/check_*.py` + test fixture) or tighten the governing rule + `references/calibration_log.md`, verify, then fix the deliverable.
- **Tier 2 (`2+` Comments OR Any Structural, Pedagogical, Visual, or Code-Readability Critique)**: Mandatory **Blind Recall Convergence Loop** (Steps 1–5 below). **Never edit deliverable code/chapter files before Steps 1–4 converge.**

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

Spawn isolated `research` subagent(s) (`invoke_subagent`, `Model: 'inherit'`, `Workspace: 'inherit'`, `Role: Blind Calibration Auditor`) to review the **unmodified** target files (plus `.cache/visual-audit/<slug>/*.png` for chapters/widgets) using only `.agents/skills/*/SKILL.md` and `GEMINI.md`.

- **Strict Isolation Rule**: Never paste, hint at, or summarize any user comment (`U1..Uk`) inside any subagent prompt.

---

## Step 3: Recall Matrix & Upstream-First Healing

Compare blind findings (plus deterministic outputs from `check_code.py`, `check_book.py`, and `check_visuals.py`) against `U1..Uk`:
- Mark each generalizable item **`CAUGHT_BY_GATE`**, **`CAUGHT_BY_BLIND_SUBAGENT`**, or **`MISSED`**.

For every **`MISSED`** generalizable item, ask *"Why did our pipeline miss this without user help?"* and heal **upstream first**:
1. **Deterministic Gate First (Preferred)**: If mechanically checkable (line length, slice size, syntax, ASCII fences, abrupt heading openings, tuple returns, local imports, compound asserts, SVG clipping, viewport overflow, contrast), add it to `scripts/check_book.py`, `scripts/check_code.py`, or `scripts/check_visuals.py` plus regression tests in `scripts/tests/`.
2. **Skill Prompt + Calibration Ledger + Active Registry Sync**: If judgment/pedagogical/architectural, sharpen the rule in `.agents/skills/<skill>/SKILL.md` and `GEMINI.md`—keeping every `SKILL.md <= 120` lines—append a root-cause entry (`Defect`, `Why Missed`, `Gate/Skill Fix`) to `references/calibration_log.md`, and immediately sync modified skills into `~/.gemini` via `save_skill(skill_dir=..., overwrite=True)` so `lookup_skills` and subagents never read stale rules.

---

## Step 4: Blind Convergence Replay

Re-run deterministic checks AND the **fresh** isolated parallel specialist subagent team (using the updated `apex-textbook-author` / `apex-artifact-author` specialist roles, with zero shared conversation history and zero user comments leaked) on the **still-unmodified pre-fix snapshot**:
- Confirm every Tier 2 generalizable feedback item now triggers cleanly as **`CAUGHT_BY_GATE`** or **`CAUGHT_BY_BLIND_SUBAGENT`**.
- If any item stays `MISSED`, refine the gate/skill rule in Step 3 and replay again until `100%` recall convergence.

---

## Step 5: Heal Deliverable, Converge & Update Open PR Without Closing

Only after Step 4 convergence (and before pushing/re-requesting review):
1. Apply all fixes cleanly to deliverable source code, tests, chapter prose, CSS, and Vue widgets via `apex-artifact-author` and `apex-textbook-author`.
2. Run the full static, visual, and coverage verification suite (`check_code.py`, `sync_book.py --check`, `check_book.py`, `build.py --check`, `BOOK_BASE=/apex/ npm --prefix book run build`, `check_visuals.py --screenshot-dir .cache/visual-audit`, and `pytest --cov-fail-under=95`).
3. **Mandatory Post-Edit Re-Review Convergence**: Run the full multi-specialist clean-room subagent review team on the modified deliverables + regenerated `.cache/visual-audit/` PNGs; if any P0/P1/P2 defects remain after edits, patch, rebuild, and spawn a fresh Round $r+1$ specialist round until a full pass returns zero defects.
4. **Preserve Open Review PRs**: Push a fast-forward commit to the open PR branch—**never** close/merge the PR before explicit final user `LGTM`, and **never** force-push away already-reviewed commits so inline threads and *"Changes since last review"* stay intact. Include a brief **Pipeline Self-Healing Note** in the reply.
