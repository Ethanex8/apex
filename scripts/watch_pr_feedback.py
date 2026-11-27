#!/usr/bin/env python3
"""Poll a GitHub PR for new human reviews, comments, or merge/close and exit cleanly.

Purpose:
  Run as a lightweight background watcher while the reviewer reads a live PR
  preview so the agent session wakes automatically as soon as a new PR review,
  inline thread, reply, conversation comment, or 1-tap Merge/Close occurs.

Usage:
  python3 scripts/watch_pr_feedback.py --pr 9
  python3 scripts/watch_pr_feedback.py --pr 9 --interval 25

Outputs:
  Prints detected feedback items in Markdown (or PR merge/close status) and
  exits 0; exits 1 on invalid CLI arguments or persistent `gh` errors; exits 2
  when `--max-polls` or `--max-duration` (default 3600s / 1 hour) expires with
  no new activity or state transition.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass

import harvest_feedback

DEFAULT_POLL_INTERVAL_S = 25.0
DEFAULT_MAX_DURATION_S = 3600.0
DEFAULT_MAX_CONSECUTIVE_ERRORS = 5
DEFAULT_GH_TIMEOUT_S = 30.0
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_TIMEOUT = 2


@dataclass(frozen=True)
class FeedbackSnapshot:
    """Immutable baseline of PR comment/reply keys and human review IDs."""

    comment_keys: frozenset[str]
    review_ids: frozenset[int]


@dataclass(frozen=True)
class PrCloseState:
    """Immutable PR closure state indicating whether the PR closed or merged."""

    closed: bool
    merged: bool


def _extract_comment_keys(items: list[dict[str, object]]) -> frozenset[str]:
    """Collect source-namespaced root and reply keys from `harvest_feedback` items."""
    keys: set[str] = set()
    for item in items:
        source = str(item.get("source") or "unknown")
        item_id = item.get("id")
        if item_id is not None:
            keys.add(f"{source}:{item_id}")
        replies = item.get("replies")
        if isinstance(replies, list):
            for reply in replies:
                if isinstance(reply, dict) and reply.get("id") is not None:
                    # Prefix reply IDs with `source` because inline/issue comments use separate ID spaces.
                    keys.add(f"{source}:reply:{reply['id']}")
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
        # Skip unsent draft reviews; only submitted human review events should wake the watcher.
        if state == "PENDING":
            continue
        if isinstance(raw_id := rev.get("id"), int):
            ids.add(raw_id)
    return frozenset(ids)


def fetch_gh_object(endpoint: str) -> dict[str, object]:
    """Invoke `gh api <endpoint>` for a single-resource JSON object, failing fast on errors."""
    gh_bin = shutil.which("gh")
    if not gh_bin:
        raise RuntimeError("Missing required 'gh' CLI binary on PATH.")
    try:
        proc = subprocess.run(
            [gh_bin, "api", endpoint],
            capture_output=True,
            text=True,
            check=False,
            timeout=DEFAULT_GH_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"gh api '{endpoint}' timed out after {DEFAULT_GH_TIMEOUT_S:g}s.") from exc
    if proc.returncode != 0:
        raise RuntimeError(f"gh api '{endpoint}' failed: {proc.stderr.strip() or proc.stdout.strip()}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON payload from '{endpoint}': {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected non-object JSON payload from '{endpoint}': {type(payload).__name__}")
    return payload


def capture_snapshot(repo: str, pr_number: int) -> FeedbackSnapshot:
    """Capture current comment/reply keys and submitted human review IDs for `pr_number`."""
    # Include resolved threads in the delta baseline so resolving an existing thread doesn't get skipped or miscounted.
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


def _fetch_pr_close_state(repo: str, pr_number: int) -> PrCloseState:
    """Return `PrCloseState(closed, merged)` for `pr_number` from single-PR GitHub metadata."""
    # Query single-object endpoint directly because `harvest_feedback.fetch_gh_json` rejects non-list payloads.
    data = fetch_gh_object(f"repos/{repo}/pulls/{pr_number}")
    return PrCloseState(
        closed=str(data.get("state") or "").lower() == "closed",
        merged=bool(data.get("merged") or data.get("merged_at")),
    )


def _validate_watch_params(
    pr_number: int,
    interval_s: float,
    max_polls: int | None,
    max_duration_s: float | None,
    max_consecutive_errors: int,
) -> None:
    """Validate watcher loop bounds upfront so invalid parameters fail before API calls."""
    if pr_number <= 0:
        raise ValueError(f"--pr must be positive (got {pr_number}).")
    if not math.isfinite(interval_s) or interval_s <= 0:
        raise ValueError(f"--interval must be finite and positive (got {interval_s}).")
    if max_polls is not None and max_polls <= 0:
        raise ValueError(f"--max-polls must be positive when set (got {max_polls}).")
    if max_duration_s is not None and (not math.isfinite(max_duration_s) or max_duration_s <= 0):
        raise ValueError(f"--max-duration must be finite and positive when set (got {max_duration_s}).")
    if max_consecutive_errors <= 0:
        raise ValueError(f"max_consecutive_errors must be positive (got {max_consecutive_errors}).")


def _emit_detected_activity(
    repo: str,
    pr_number: int,
    new_comments: list[str],
    new_reviews: list[int],
) -> None:
    """Print newly detected feedback count and unresolved items in Markdown."""
    # Emit only unresolved items to surface open reviewer actionables cleanly upon wakeup.
    unresolved = harvest_feedback.normalize_pr_feedback(repo, pr_number)
    print(
        f"Detected new activity on PR #{pr_number}: "
        f"{len(new_comments)} comment(s), {len(new_reviews)} review(s)."
    )
    print(harvest_feedback.format_feedback_markdown(pr_number, unresolved))


def _emit_close_state(pr_number: int, close_state: PrCloseState) -> None:
    """Print merged or closed PR lifecycle summary for wakeup consumers."""
    outcome = "merged" if close_state.merged else "closed"
    print(f"PR #{pr_number} {outcome} — review cycle complete.")


def _emit_idle_pause(pr_number: int, elapsed_s: float) -> None:
    """Print clean pause notice when the idle watch window expires."""
    minutes = max(1, round(elapsed_s / 60.0)) if elapsed_s >= 60.0 else 0
    window = f"{minutes} minute(s)" if minutes else f"{elapsed_s:g}s"
    print(f"No new activity on PR #{pr_number} after {window}; pausing watcher.")


def watch_pr_until_feedback(
    repo: str,
    pr_number: int,
    *,
    interval_s: float = DEFAULT_POLL_INTERVAL_S,
    max_polls: int | None = None,
    max_duration_s: float | None = DEFAULT_MAX_DURATION_S,
    max_consecutive_errors: int = DEFAULT_MAX_CONSECUTIVE_ERRORS,
) -> int:
    """Poll `repo` PR `#pr_number`; return `0` on feedback or merge/close, or `2` on timeout."""
    _validate_watch_params(pr_number, interval_s, max_polls, max_duration_s, max_consecutive_errors)

    # Check PR state before sleeping so an already-merged or closed PR exits immediately.
    close_state = _fetch_pr_close_state(repo, pr_number)
    if close_state.closed:
        _emit_close_state(pr_number, close_state)
        return EXIT_OK

    baseline = capture_snapshot(repo, pr_number)
    start_t = time.monotonic()
    deadline = start_t + max_duration_s if max_duration_s is not None else None
    polls = 0
    consecutive_errors = 0
    last_error: RuntimeError | None = None
    while max_polls is None or polls < max_polls:
        if deadline is not None:
            remaining_s = deadline - time.monotonic()
            if remaining_s <= 0:
                if last_error is not None:
                    raise last_error
                _emit_idle_pause(pr_number, time.monotonic() - start_t)
                return EXIT_TIMEOUT
            time.sleep(min(interval_s, remaining_s))
        else:
            time.sleep(interval_s)
        polls += 1
        try:
            current = capture_snapshot(repo, pr_number)
            new_comments, new_reviews = find_new_activity(baseline, current)
            if new_comments or new_reviews:
                _emit_detected_activity(repo, pr_number, new_comments, new_reviews)
                return EXIT_OK
            close_state = _fetch_pr_close_state(repo, pr_number)
            consecutive_errors = 0
            last_error = None
        except RuntimeError as exc:
            consecutive_errors += 1
            last_error = exc
            print(
                f"WARN: transient poll error ({consecutive_errors}/{max_consecutive_errors}): {exc}",
                file=sys.stderr,
            )
            if consecutive_errors >= max_consecutive_errors:
                raise
            continue
        if close_state.closed:
            _emit_close_state(pr_number, close_state)
            return EXIT_OK
    # Surface unresolved trailing gh errors even when max_polls < max_consecutive_errors.
    if last_error is not None:
        raise last_error
    return EXIT_TIMEOUT


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for polling a GitHub PR until new human activity or close arrives."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pr", type=int, required=True, help="Pull request number.")
    parser.add_argument("--repo", default=None, help="Optional owner/repo (defaults to active gh repo).")
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL_S,
        help="Poll interval in seconds.",
    )
    parser.add_argument("--max-polls", type=int, default=None, help="Optional max poll iterations.")
    parser.add_argument(
        "--max-duration",
        type=float,
        default=DEFAULT_MAX_DURATION_S,
        help=f"Max idle watch duration in seconds before pausing (default {DEFAULT_MAX_DURATION_S:g}s / 1 hour).",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # Map argparse's default exit code 2 to EXIT_ERROR (1) so EXIT_TIMEOUT (2) stays unambiguous.
        return EXIT_OK if exc.code in (0, None) else EXIT_ERROR

    try:
        _validate_watch_params(
            args.pr,
            args.interval,
            args.max_polls,
            args.max_duration,
            DEFAULT_MAX_CONSECUTIVE_ERRORS,
        )
        repo = harvest_feedback.resolve_repo_slug(args.repo)
        return watch_pr_until_feedback(
            repo,
            args.pr,
            interval_s=args.interval,
            max_polls=args.max_polls,
            max_duration_s=args.max_duration,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
