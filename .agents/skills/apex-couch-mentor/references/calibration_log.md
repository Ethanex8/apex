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

## Entry 002 — Multi-Specialist Review Teams & Mandatory Post-Edit Convergence (2026-11-16)

- **Trigger**: User Chapter 1 & Python readability review (`U1..U7`) identifying regressions introduced by un-re-reviewed Round 1 fixes and attention dilution inside single-subagent Pass 3 audits.
- **Healed By**:
  1. Upgraded `apex-textbook-author` Pass 3 to **3 parallel specialist subagents** (*Sequential Novice Cold-Reader*, *Editorial Pacing & Math Editor*, *Visual Pedagogy & Diagram Critic*) and `apex-artifact-author` Pass 3 to **2 parallel specialist subagents** (*Architecture & Spec Auditor*, *Code Readability & Literary Clarity Critic*).
  2. Added **Mandatory Post-Edit Re-Review Convergence** across `apex-couch-mentor`, `apex-textbook-author`, `apex-artifact-author`, and `apex-skill-healer`: any deliverable change triggers fresh clean-room Round $r+1$ specialist audits until zero P0/P1/P2 defects remain.

## Entry 003 — Iterative Open-PR Review Loop & Active Skill Registry Sync (2026-11-17)

- **Trigger**: User workflow instruction (`W1`) on PR #4 (*"Let's keep the PR open until I give final approval. I'll leave feedback, you fix it, and we repeat until we're done. Obviously, this should become part of your repo instructions"*) + discovery that `~/.gemini` cached skills had drifted behind `.agents/skills/*/SKILL.md`.
- **Healed By**:
  1. Codified the **Iterative Open-PR Review Loop** across `GEMINI.md`, `apex-couch-mentor/SKILL.md`, and `apex-skill-healer/SKILL.md`: keep review/step PRs open across all feedback -> `apex-skill-healer` -> fix -> fast-forward push rounds (never closing/merging early and never force-pushing away reviewed commits) until explicit final user `LGTM`.
  2. Required `save_skill(skill_dir=..., overwrite=True)` in `apex-skill-healer` Step 3 whenever `.agents/skills/*` is updated so active sessions and subagents always read the latest repo skills.
