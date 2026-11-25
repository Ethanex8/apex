#!/usr/bin/env python3
"""Poll a GitHub PR for new human reviews or comments and exit when activity arrives.

Purpose:
  Run as a lightweight background watcher while the reviewer reads a live PR
  preview so the agent session wakes automatically as soon as a new PR review,
  inline thread, reply, or conversation comment is submitted.

Usage:
  python3 scripts/watch_pr_feedback.py --pr 9
  python3 scripts/watch_pr_feedback.py --pr 9 --interval 25

Outputs:
  Prints detected feedback items in Markdown when new PR activity arrives and
  exits 0; exits 1 on `gh` errors or 2 if `--max-polls` expires with no activity.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass

import harvest_feedback


@dataclass(frozen=True)
class FeedbackSnapshot:
    """Immutable baseline of PR comment/reply keys and human review IDs."""

    comment_keys: frozenset[str]
    review_ids: frozenset[int]


def _extract_comment_keys(items: list[dict[str, object]]) -> frozenset[str]:
    """Collect unique root and reply keys from normalized `harvest_feedback` items."""
    keys: set[str] = set()
    for item in items:
        keys.add(f"{item.get('source')}:{item.get('id')}")
        replies = item.get("replies")
        if isinstance(replies, list):
            for reply in replies:
                if isinstance(reply, dict) and reply.get("id") is not None:
                    keys.add(f"reply:{reply['id']}")
    return frozenset(keys)


def _extract_human_review_ids(repo: str, pr_number: int) -> frozenset[int]:
    """Fetch PR review IDs authored by non-bot accounts (including bodyless approvals)."""
    reviews = harvest_feedback.fetch_gh_json(f"repos/{repo}/pulls/{pr_number}/reviews")
    ids: set[int] = set()
    for rev in reviews:
        user_raw = rev.get("user")
        user = user_raw if isinstance(user_raw, dict) else {}
        if str(user.get("type") or "").lower() == "bot":
            continue
        state = str(rev.get("state") or "").upper()
        if state == "PENDING":
            continue
        if isinstance(raw_id := rev.get("id"), int):
            ids.add(raw_id)
    return frozenset(ids)


def capture_snapshot(repo: str, pr_number: int) -> FeedbackSnapshot:
    """Capture current comment/reply keys and submitted human review IDs for `pr_number`."""
    items = harvest_feedback.normalize_pr_feedback(repo, pr_number, include_resolved=True)
    return FeedbackSnapshot(
        comment_keys=_extract_comment_keys(items),
        review_ids=_extract_human_review_ids(repo, pr_number),
    )


def find_new_activity(
    baseline: FeedbackSnapshot, current: FeedbackSnapshot
) -> tuple[list[str], list[int]]:
    """Return sorted `(new_comment_keys, new_review_ids)` added since `baseline`."""
    new_comments = sorted(current.comment_keys - baseline.comment_keys)
    new_reviews = sorted(current.review_ids - baseline.review_ids)
    return new_comments, new_reviews


def watch_pr_until_feedback(
    repo: str,
    pr_number: int,
    *,
    interval_s: float = 25.0,
    max_polls: int | None = None,
    max_consecutive_errors: int = 5,
) -> int:
    """Poll `repo` PR `#pr_number` until new feedback appears, then print summary and exit 0."""
    baseline = capture_snapshot(repo, pr_number)
    polls = 0
    consecutive_errors = 0
    while max_polls is None or polls < max_polls:
        time.sleep(interval_s)
        polls += 1
        try:
            current = capture_snapshot(repo, pr_number)
            consecutive_errors = 0
        except RuntimeError as exc:
            consecutive_errors += 1
            print(f"WARN: transient poll error ({consecutive_errors}/{max_consecutive_errors}): {exc}", file=sys.stderr)
            if consecutive_errors >= max_consecutive_errors:
                raise
            continue
        new_comments, new_reviews = find_new_activity(baseline, current)
        if new_comments or new_reviews:
            unresolved = harvest_feedback.normalize_pr_feedback(repo, pr_number)
            print(
                f"Detected new activity on PR #{pr_number}: "
                f"{len(new_comments)} comment(s), {len(new_reviews)} review(s)."
            )
            print(harvest_feedback.format_feedback_markdown(pr_number, unresolved))
            return 0
    return 2


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for polling a GitHub PR until new human feedback arrives."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True, help="Pull request number.")
    parser.add_argument("--repo", default=None, help="Optional owner/repo (defaults to active gh repo).")
    parser.add_argument("--interval", type=float, default=25.0, help="Poll interval in seconds.")
    parser.add_argument("--max-polls", type=int, default=None, help="Optional max poll iterations.")
    args = parser.parse_args(argv)

    if args.pr <= 0 or args.interval <= 0:
        print("ERROR: --pr and --interval must be positive.", file=sys.stderr)
        return 1
    try:
        repo = harvest_feedback.resolve_repo_slug(args.repo)
        return watch_pr_until_feedback(
            repo,
            args.pr,
            interval_s=args.interval,
            max_polls=args.max_polls,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
