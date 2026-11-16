# Apex Couch-Mentor Calibration Log

Persistent ledger of workflow, PR hygiene, and review-loop lessons graduated into [SKILL.md](../SKILL.md) and `apex-skill-healer`.

## Entry 001 — Closed-Loop Review & Single-Branch Cleanup (`brain-01`, 2026-11-16)

- **Trigger**: User inline PR review experiment establishing blind-subagent recall convergence + post-review branch cleanup.
- **Lessons & Upstream Fixes**:
  1. **Automatic Self-Healing on Critique**: Any Tier 1/Tier 2 review critique must trigger `apex-skill-healer` before patching deliverable files so missed defects never recur in future steps (`brain-02`..`sight-15`).
     - *Healed By*: Created [apex-skill-healer](../../apex-skill-healer/SKILL.md) and [harvest_feedback.py](../../../../scripts/harvest_feedback.py); wired mandatory hook into `SKILL.md`.
  2. **Clean Branch & PR Lifecycle**: Author each atomic step cleanly on `step/<step-id>` targeting `main`, include live Pages link + `scripts/check_visuals.py` verification before requesting review, and upon `LGTM`, approve, merge, and delete `step/<step-id>` locally and remotely so only `main` remains between steps.
     - *Healed By*: Codified in `SKILL.md` Rules 2, 5, and 6.
  3. **Zero Unverified Visuals**: Static builds do not catch CSS cascade bugs (`.vp-doc p` into Mermaid SVGs, mobile MathJax overflow, active button hover contrast). Running headless Chromium visual verification (`scripts/check_visuals.py`) before review is mandatory locally and in CI.
     - *Healed By*: Added `scripts/check_visuals.py` to Pass 4 locally and in `.github/workflows/ci.yml` + `book.yml`.
