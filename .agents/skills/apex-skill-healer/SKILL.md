---
name: apex-skill-healer
description: Closed-loop 4-step subset-recall PR review and skill self-healing protocol. Sanity-checks PR comments with optional pushback and anti-cheating persona proposals first, establishes frozen-prompt isolated blind subset recall before editing deliverables, converges clean-room fixes with diff-regression guarding, resolves answered PR threads, and merges cleanly on LGTM.
---
# Apex 4-Step Subset-Recall Review & Self-Healing Protocol

Execute this skill whenever user feedback arrives on an open PR or in chat during `in_review` (`docs/REVIEW_PROCESS.md`). Pure mechanical typos (`Tier 0`) fix directly; local editorial polish (`Tier 1`) skips rubric edits and Step 2 recall; only cross-discipline gaps (`Tier 2`) run full Steps 1–4.

## Step 1: Comment Sanity Check, Pushback & Persona Proposal (Human Gate 1)

1. Harvest feedback **outside** the repository workspace and record the untouched `HEAD` SHA:
   ```bash
   python3 scripts/harvest_feedback.py --pr <N> --out /tmp/apex-feedback/pr-<N>.json
   ```
2. Audit each comment (`U1..Uk`) against text/code: mark `AGREE`, `CLARIFY`, or respectful `PUSHBACK`, then classify as **Tier 1** (local phrasing/naming fix; zero per-chapter rule files, escalate only if recurring across `2+` subsystem chapters) or **Tier 2** (systemic cross-discipline gap transferable across unrelated chapters).
3. Draft proposed edits to `.agents/skills/*/SKILL.md`, `references/rubric_*.md`, `GEMINI.md`, or `scripts/check_*.py` strictly for **Tier 2** items as **universal, domain-agnostic rules**—never referencing chapter symbols, formulas, hex values, widget names, or line numbers; avoid rigid quotas and replace conflicting wording cleanly.
4. Publish triage, Tier 1/Tier 2 split, and proposed rules in `pr_<N>_step1_triage.md` (`UserFacing: true`, `RequestFeedback: true`) and **STOP** until Gate 1 approves `U_agreed`. Immediately delete `/tmp/apex-feedback/pr-<N>.json` once Gate 1 signs off so no feedback JSON remains on disk during Step 2.

---

## Step 2: Persona Update & Frozen-Prompt Subset-Recall Loop (Conditional Gate 2)

1. Apply only the approved **Tier 2** persona/rubric/gate updates and sync `.agents/skills/*` into `~/.gemini` via `save_skill(overwrite=True)`. **Do NOT edit deliverable files or `references/calibration_log.md` yet.** (If every agreed item is Tier 1, proceed directly to Step 3.)
2. Run deterministic checks (`check_code.py`, `check_book.py`, `check_visuals.py`) and generate the frozen review manifest on the **untouched** pre-fix snapshot:
   ```bash
   python3 scripts/build_review_plan.py --chapter <chapter_path>
   ```
   - **Zero Orchestrator Bias & Zero Leakage**: Invoke every emitted shard/global `research` subagent using `build_review_plan.py`'s **exact frozen prompt**—never hand-write custom prompts hinting at current comments, and forbid reading `/tmp/`, triage artifacts, `calibration_log.md`, `gh`, or session logs.
3. Map every **Tier 2** item in `U_agreed` semantically to `CAUGHT_BY_GATE`, `CAUGHT_BY_BLIND_SUBAGENT`, or `MISSED`.
4. If any Tier 2 item is `MISSED`, generalize the governing rubric/skill/gate rule cleanly, re-sync via `save_skill`, and re-run **fresh** frozen-prompt subagents on affected shards until $\text{U}_{\text{tier2}} \subseteq \text{Panel} \cup \text{Gates}$.
5. **Conditional Gate 2**: If Step 2 altered any persona/rubric prompt beyond Step 1's approved diff, **STOP** for human anti-cheating sign-off; otherwise continue directly to Step 3.

---

## Step 3: Deliverable Healing, Diff Guard & Clean-Room Convergence

1. Fix **all** panel, gate, and `U_agreed` findings across code, tests, widgets, CSS, and chapter prose (`apex-artifact-author` + `apex-textbook-author`).
2. Append the retrospective root-cause entry to the relevant `references/calibration_log.md` and run all verification gates (`pytest --cov-fail-under=95`, `check_code.py`, `sync_book.py --check`, `check_book.py`, `build.py --check`, `BOOK_BASE=/apex/ npm --prefix book run build`, `check_visuals.py --screenshot-dir .cache/visual-audit`).
3. Generate the Step 3 manifest including the pre-fix diff baseline and converge **fresh** frozen-prompt clean-room reviewers:
   ```bash
   python3 scripts/build_review_plan.py --chapter <chapter_path> --base-ref <untouched_head_sha>
   ```
   Iterate until every shard, the `Global Structure & Visual Critic`, and the `Diff & Flow Regression Guardian` return zero P0/P1/P2 defects.

---

## Step 4: Fast-Forward PR Update, Thread Resolution, Book Deploy & `LGTM` Close-Out

1. Commit and push fast-forward updates cleanly (keeping the Ready-for-Review PR open across cycles without force-pushing).
2. Post concise inline replies on every addressed PR comment (`gh api -X POST repos/<owner>/<repo>/pulls/<N>/comments/<id>/replies`) noting both the deliverable fix and the upstream persona/rubric/gate change.
3. Resolve every addressed GitHub review thread via GraphQL `resolveReviewThread`, leaving a thread unresolved **only** if a genuine open question remains.
4. Confirm GitHub Actions CI + GitHub Pages deploy pass, update bookmarks if needed, and await the next review cycle.
5. **On Explicit `LGTM`**: Run `python3 scripts/step.py approve <step-id> --commit <sha>`, `python3 scripts/build.py --check`, merge changes to `main`, close/merge the PR, and delete temporary branches locally and on `origin`.