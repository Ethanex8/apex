# Apex PR Review & Self-Healing Calibration Log

Persistent ledger of PR review tooling, pickup acknowledgment, and attribution lessons graduated into [SKILL.md](../../.agents/skills/apex-skill-healer/SKILL.md), [harvest_feedback.py](../../scripts/harvest_feedback.py), and the preview review overlay.

## Entry 001 — Review Pickup Reactions, Batch Clarity & Agent Attribution (`U9`, 2026-11-25)

- **Trigger**: PR #10 conversation feedback (`U9`) asking whether clicking `Submit` batches comments atomically, requesting `eyes` pickup reactions, and asking for visible distinction between agent replies and human comments posted under the shared GitHub token.
- **What Was Needed Upstream**:
  1. Harvesting unresolved feedback left no visible signal on GitHub that the agent had picked up a new human comment or follow-up reply until the full fix cycle finished.
  2. Agent replies shared the personal token's GitHub login without a structured prefix or preview badge, making thread dialogue ambiguous.
  3. Clicking `Submit` batched inline comments cleanly while firing non-inline actions sequentially, without surfacing that split in the drawer footer.
- **Healed By**:
  1. Added `--ack-eyes` (`ack_feedback_eyes`) in [harvest_feedback.py](../../scripts/harvest_feedback.py) and Step 1 of [SKILL.md](../../.agents/skills/apex-skill-healer/SKILL.md) to post `content=eyes` (`👀`) reactions onto newly harvested human inline/issue comments (skipping threads whose latest reply already carries `🤖 [Antigravity]` and top-level review summaries unsupported by GitHub Reactions).
  2. Standardized the `🤖 [Antigravity]` agent reply prefix in Step 4 of [SKILL.md](../../.agents/skills/apex-skill-healer/SKILL.md), and updated [githubClient.ts](../../book/.vitepress/theme/review/githubClient.ts) + [PrReviewOverlay.vue](../../book/.vitepress/theme/review/PrReviewOverlay.vue) to strip the marker and render a distinct `🤖 Antigravity` badge alongside a 1-line `summarizeSubmitBatch()` footer breakdown.
