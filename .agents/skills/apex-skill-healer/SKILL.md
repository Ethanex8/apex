---
name: apex-skill-healer
description: Closed-loop 4-step subset-recall PR review and skill self-healing protocol. Sanity-checks PR comments with optional pushback and anti-pendulum rule checks first, establishes frozen-prompt isolated blind subset recall and precision checks before editing deliverables, converges clean-room fixes with diff-regression guarding, resolves answered PR threads, and prepares 1-tap human merge on GitHub.
---
# Apex 4-Step Subset-Recall Review & Self-Healing Protocol

Execute this skill whenever user feedback arrives on an open PR or in chat (`docs/REVIEW_PROCESS.md`). Unambiguous `Tier 0` typos and unambiguous `Tier 1` local polish (zero rule edits, zero pushback/clarify) skip Gate 1 and Step 2; `Tier 2` rules, pushback, or open questions run full Steps 1–4.

## Step 1: Comment Sanity Check, 3-Tier Split & Conflict Audit (Gate 1)

1. Harvest **unresolved** feedback **outside** the repository workspace and record the untouched `HEAD` SHA:
   ```bash
   python3 scripts/harvest_feedback.py --pr <N> [--since <ISO_TS>] --out /tmp/apex-feedback/pr-<N>.json
   ```
2. Audit each item (`U1..Uk`) against text/code (`AGREE`, `CLARIFY`, or respectful `PUSHBACK`) and classify:
   - **Tier 0**: Mechanical typos or broken links—purge `/tmp` JSON, fix directly, push, reply, and resolve.
   - **Tier 1**: Local wording, naming, or single-chapter clarity without new rules—if **every** item is unambiguous Tier 1 (`AGREE`, zero `PUSHBACK`/`CLARIFY`), purge `/tmp` JSON and go directly to **Step 3**.
   - **Tier 2**: Systemic gap transferable across unrelated chapters or codebases (or recurring across `2+` chapters).
3. Whenever **any** item is **Tier 2**, `PUSHBACK`, or `CLARIFY`: draft domain-agnostic edits in the canonical rubric/gate/skill file (never copy-pasting across files or citing chapter tokens), run a **Rule Conflict & Counterbalance Check**, publish `pr_<N>_step1_triage.md`, and **STOP at Gate 1**. Purge `/tmp/apex-feedback/pr-<N>.json` immediately upon sign-off.

---

## Step 2: Rule Update & Frozen-Prompt Recall + Precision Loop (Conditional Gate 2)

1. Apply only Gate-1-approved **Tier 2** rule/gate updates and sync `.agents/skills/*` into `~/.gemini` via `save_skill(overwrite=True)`. **Do NOT edit deliverables or `docs/calibration/*` yet.**
2. Run static/visual gates (`check_code.py`, `check_book.py`, `check_visuals.py`), ensure `docs/CHAPTER_INDEX.md` is fresh (`build.py`), and generate the frozen full-sweep manifest on the **untouched** pre-fix snapshot:
   ```bash
   python3 scripts/build_review_plan.py [--chapter <chapter_path>] [--code <file1> ...]
   ```
   - Invoke **every** emitted task verbatim (`Cold-Reader`, `Math Editor`, `Macro Critic`, `Visual Critic`, and/or `--code` auditors), forbidding `/tmp/`, triage artifacts, `docs/calibration/*`, `gh`, or session logs.
3. Score every Tier-2 item (`CAUGHT_BY_GATE`, `CAUGHT_BY_BLIND_SUBAGENT`, or `MISSED`) **and** check **Precision** (did any new rule trigger noisy/boilerplate false positives on clean passages?).
4. If any Tier-2 item is `MISSED` or noisy, generalize/counterbalance the rule cleanly, re-sync via `save_skill`, and re-run **fresh** frozen-prompt subagents on affected shards until Recall holds with clean Precision.
5. **Conditional Gate 2**: If Step 2 altered any rubric/skill prompt beyond Step 1's approved diff, **STOP** for human anti-cheating sign-off; otherwise continue to Step 3.

---

## Step 3: Deliverable Healing, Diff Guard & Clean-Room Convergence

1. Fix **all** panel, gate, and `U_agreed` findings (`apex-artifact-author` + `apex-textbook-author`), refreshing `approved_date` on the PR branch via `step.py approve <step-id>` if needed.
2. For Tier-2/substantive cycles, append the root-cause entry to `docs/calibration/<skill>.md` (never inside `.agents/skills/`), run `python3 scripts/build.py`, all code/book/coverage gates (`check_code.py`, `pytest --cov-fail-under=95`, `sync_book.py --check`, `check_book.py`, `build.py --check`), `BOOK_BASE=/apex/ npm --prefix book run build`, and `check_visuals.py --screenshot-dir .cache/visual-audit`.
3. Converge **fresh** frozen-prompt clean-room reviewers with `--base-ref <untouched_head_sha>`: run a **full sweep** on Round 1, then deterministic **scoped** sweeps (`--changed-since <round_r_sha>`) on Round $r+1$ until every emitted task returns zero P0/P1/P2 defects:
   ```bash
   python3 scripts/build_review_plan.py [--chapter <chapter_path>] [--code <file1> ...] --base-ref <untouched_head_sha> [--changed-since <round_r_sha>]
   ```

---

## Step 4: Fast-Forward PR Update, Thread Resolution & 1-Tap Merge Close-Out

1. Commit and push fast-forward updates strictly to the open `step/<step-id>` PR branch (never directly to `main`, and never force-push reviewed commits).
2. Post concise inline replies (`gh api -X POST repos/<owner>/<repo>/pulls/<N>/comments/<id>/replies`) on every addressed PR comment noting the fix and any upstream rule/gate update.
3. Resolve every addressed GitHub review thread via GraphQL `resolveReviewThread`, leaving a thread unresolved **only** when an open question remains.
4. Confirm `Apex CI` and the `/apex/pr-<N>/` preview deploy pass, update bookmarks if needed, and await the reviewer's **1-tap Merge** on GitHub (never call `gh pr merge` unilaterally).