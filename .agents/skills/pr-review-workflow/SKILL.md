---
name: pr-review-workflow
description: End-to-end GitHub PR lifecycle and 3-tier review protocol—atomic Ready-for-Review PRs, honest comment sanity checks with anti-pendulum rule updates, blind subset-recall verification, clean-room diff convergence, non-auto-resolving cross-channel replies, and 1-tap human merge.
file_names:
    - references/gh_commands.md
---
# GitHub PR Workflow & 3-Tier Review Protocol

Use this skill whenever opening pull requests or addressing PR/chat review feedback (`docs/REVIEW_PROCESS.md` if present).
For repos without custom `harvest_feedback.py` / `watch_pr_feedback.py` scripts, use [`references/gh_commands.md`](references/gh_commands.md).

## Core PR Hygiene

- Open Ready-for-Review PRs from atomic feature branches targeting `main` (never `--draft` when requesting review, never push directly to `main`, never force-push reviewed commits, and never call `gh pr merge` unilaterally).

## Step 1: Comment Sanity Check, 3-Tier Split & Conflict Audit (Gate 1)

1. Harvest **unresolved** feedback **outside** the repo workspace (`scripts/harvest_feedback.py --pr <N> --ack-eyes --out /tmp/pr-feedback/pr-<N>.json` if present, else `gh api`), react with `eyes` on picked-up comments, and record untouched `HEAD`.
2. Audit each item (`U1..Uk`) critically against code/docs (`AGREE`, `CLARIFY`, or respectful `PUSHBACK`) and classify:
   - **Tier 0**: Mechanical typos or broken links—purge `/tmp` JSON, fix directly, push, and reply (leaving resolution to the reviewer).
   - **Tier 1**: Local wording, naming, or isolated fix without rule edits—if **every** item is unambiguous Tier 1 (`AGREE`, zero `PUSHBACK`/`CLARIFY`), purge `/tmp` JSON and go directly to **Step 3**.
   - **Tier 2**: Systemic rule/linter/skill lesson transferable across unrelated files or projects (or recurring across `2+` places).
3. Whenever **any** item is **Tier 2**, `PUSHBACK`, or `CLARIFY`: draft domain-agnostic edits in the canonical rubric/skill/check file (never citing deliverable tokens), run a **Rule Conflict & Counterbalance Check**, publish `pr_<N>_step1_triage.md`, and **STOP at Gate 1**. Purge `/tmp` JSON on sign-off.

## Step 2: Rule Update & Blind Recall + Precision Loop (Conditional Gate 2)

1. Apply only Gate-1-approved **Tier 2** rule/gate updates and sync `.agents/skills/*` via `save_skill(overwrite=True)` when present. **Do NOT edit deliverables yet.**
2. Run static/visual gates and launch isolated `research` reviewers on the **untouched** pre-fix snapshot (via `scripts/build_review_plan.py` if present, else the skill's `references/rubric_*.md` prompts), forbidding `/tmp/`, triage artifacts, calibration logs, `gh`, or session logs.
3. Score every Tier-2 item (`CAUGHT_BY_GATE`, `CAUGHT_BY_BLIND_SUBAGENT`, or `MISSED`) **and** check **Precision** (zero noisy false positives on clean passages).
4. If any Tier-2 item is `MISSED` or noisy, refine/counterbalance the general rule, re-sync via `save_skill`, and re-run **fresh** blind reviewers on affected shards until Recall holds with clean Precision.
5. **Conditional Gate 2**: If Step 2 altered any rubric/skill prompt beyond Step 1's approved diff, **STOP** for human sign-off; otherwise continue to Step 3.

## Step 3: Deliverable Healing, Diff Guard & Clean-Room Convergence

1. Fix **all** panel, gate, and `U_agreed` findings, record substantive Tier-2 lessons in the repo's calibration log (outside `.agents/skills/` if used), and re-run all tests, linters, builds, and visual checks.
2. Converge **fresh** isolated clean-room reviewers against `--base-ref <untouched_head_sha>` (full sweep Round 1, scoped Round $r+1$ + `rubric_diff_guardian.md`) until zero P0/P1/P2 defects or flow regressions remain.

## Step 4: Fast-Forward PR Update, Replies & 1-Tap Merge Close-Out

1. Push fast-forward commits strictly to the open PR branch (never force-push reviewed commits).
2. Prefix every agent reply with `🤖 [Antigravity]` and post across all channels (`pulls/<N>/comments/<id>/replies` for inline threads; `issues/<N>/comments` for reviews/conversation items).
3. **Do not auto-resolve threads**: leave addressed threads open so the reviewer can inspect fixes directly and click **Resolve** after verifying.
4. Confirm CI (and preview deploy, if configured) passes; if a repo watcher script exists (`scripts/watch_pr_feedback.py --pr <N>`), launch it as an async non-daemon background task (`IsDaemon=false`) before ending the turn.