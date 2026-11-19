---
name: apex-skill-healer
description: Closed-loop 4-step subset-recall PR review and skill self-healing protocol. Sanity-checks PR comments with optional pushback and anti-cheating persona proposals first, establishes isolated blind subset recall before editing deliverables, converges clean-room fixes, resolves answered PR threads, and closes/merges branches cleanly on LGTM.
---
# Apex 4-Step Subset-Recall Review & Self-Healing Protocol

Execute this skill whenever user feedback arrives on an open PR or in chat during `in_review` (full flowchart and rationale live in `docs/REVIEW_PROCESS.md`). Pure single-character typos (`Tier 0`) may be fixed directly; all other critiques follow Steps 1–4 below without touching deliverables until Step 2 converges.

## Step 1: Comment Sanity Check, Pushback & Persona Proposal (Human Gate 1)

1. Harvest feedback **outside** the repository workspace and record the untouched `HEAD` SHA:
   ```bash
   python3 scripts/harvest_feedback.py --pr <N> --out /tmp/apex-feedback/pr-<N>.json
   ```
2. Audit each human comment (`U1..Uk`) against exact text/code: mark `AGREE`, `CLARIFY`, or respectful `PUSHBACK` when a reading may be mistaken (the human reviewer always holds the final call).
3. Draft proposed edits to `.agents/skills/*/SKILL.md`, `GEMINI.md`, or deterministic `scripts/check_*.py` strictly as **universal, content-agnostic rules**—never referencing chapter symbols, formulas, hex values, widget names, or line numbers.
4. Publish both triage and proposed persona/gate diffs in a standalone artifact (`pr_<N>_step1_triage.md`, `UserFacing: true`, `RequestFeedback: true`) and **STOP** until the user settles `U_agreed` and approves the non-cheating persona rules.

---

## Step 2: Persona Update & Isolated Subset-Recall Loop (Conditional Gate 2)

1. Apply only the approved persona/gate updates and sync `.agents/skills/*` into `~/.gemini` via `save_skill(overwrite=True)`. **Do NOT edit deliverable files or append `references/calibration_log.md` yet.**
2. Run deterministic checks (`check_code.py`, `check_book.py`, `check_visuals.py`) plus the isolated Pass-3 `research` review panel on the **untouched** pre-fix snapshot and `.cache/visual-audit/` PNGs.
   - **Zero-Leakage Isolation**: Forbid subagents from reading `/tmp/apex-feedback/`, triage artifacts, `calibration_log.md`, `gh`, or session logs; never mention human comments or hints.
3. Map every item in `U_agreed` semantically to `CAUGHT_BY_GATE`, `CAUGHT_BY_BLIND_SUBAGENT`, or `MISSED`.
4. If any item is `MISSED`, generalize the governing persona/gate rule (without leaking specific content), sync via `save_skill`, and re-run a **fresh** isolated panel until $U_{\text{agreed}} \subseteq \text{Panel} \cup \text{Gates}$.
5. **Conditional Gate 2**: If Step 2 altered any persona prompt beyond Step 1's approved diff, **STOP** for human anti-cheating sign-off; otherwise continue directly to Step 3.

---

## Step 3: Deliverable Healing & Clean-Room Convergence

1. Fix **all** panel, gate, and `U_agreed` findings across code, tests, widgets, CSS, and chapter prose (`apex-artifact-author` + `apex-textbook-author`).
2. Append the completed root-cause retrospective entry to the relevant `references/calibration_log.md`.
3. Rebuild and verify every gate (`pytest --cov-fail-under=95`, `check_code.py`, `sync_book.py --check`, `check_book.py`, `build.py --check`, `BOOK_BASE=/apex/ npm --prefix book run build`, `check_visuals.py --screenshot-dir .cache/visual-audit`).
4. Run fresh isolated clean-room panel rounds on the updated deliverables + regenerated PNGs until a full pass reports zero P0/P1/P2 defects.

---

## Step 4: Fast-Forward PR Update, Thread Resolution, Book Deploy & `LGTM` Close-Out

1. Commit and push fast-forward updates cleanly (keeping the Ready-for-Review PR open across cycles without force-pushing).
2. Post concise inline replies on every addressed PR comment (`gh api -X POST repos/<owner>/<repo>/pulls/<N>/comments/<id>/replies`) noting both the deliverable fix and the general persona/gate rule that now catches it.
3. Resolve every addressed GitHub review thread via GraphQL `resolveReviewThread`, leaving a thread unresolved **only** if a genuine open question remains for the human.
4. Confirm GitHub Actions CI + GitHub Pages deploy pass, update PR/book URL bookmarks if needed, and await the next review cycle.
5. **On Explicit `LGTM`**: Run `python3 scripts/step.py approve <step-id> --commit <sha>`, `python3 scripts/build.py --check`, merge changes to `main`, close/merge the PR, and delete temporary branches locally and on `origin`.