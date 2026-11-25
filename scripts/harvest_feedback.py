#!/usr/bin/env python3
"""Fetch and normalize GitHub PR review comments into structured calibration records.

Purpose:
  Pull inline diff threads, review summaries, and conversation comments from a
  GitHub pull request via `gh api` so `apex-skill-healer` can score blind
  subagent recall against every unresolved human critique item.

Usage:
  python3 scripts/harvest_feedback.py --pr 3
  python3 scripts/harvest_feedback.py --pr 3 --out /tmp/apex-feedback/pr-3.json
  python3 scripts/harvest_feedback.py --pr 3 --since 2026-11-24T00:00:00Z --after-review-id 100

Outputs:
  Prints a readable Markdown feedback checklist to stdout and optionally writes
  normalized JSON to `--out`; exits 1 on missing `gh` CLI or API errors.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

REPO_SLUG_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
PREVIEW_COMMENT_MARKER = "<!-- apex-book-preview -->"
PREVIEW_LOC_RE = re.compile(
    r"<!--\s*apex-preview-loc:\s*path=([^\s>]+?)(?:\s+line=(\d+)(?:-\d+)?)?\s*-->"
)
PREVIEW_RESOLVED_RE = re.compile(r"<!--\s*apex-preview-resolved:\s*1\s*-->")
PREVIEW_REPLY_RE = re.compile(r"<!--\s*apex-preview-reply-to:\s*(\d+)\s*-->")
PREVIEW_STATE_RE = re.compile(r"<!--\s*apex-preview-state:\s*root=(\d+)\s+resolved=(0|1)\s*-->")
UNKNOWN_AUTHOR = "unknown"
REVIEW_THREADS_QUERY = """
query($owner: String!, $name: String!, $pr: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          isResolved
          isOutdated
          comments(first: 100) {
            nodes {
              databaseId
            }
          }
        }
      }
    }
  }
}
""".strip()


@dataclass(frozen=True)
class ReviewThreadState:
    """GraphQL thread identity and resolution status for an inline PR comment."""

    thread_id: str
    is_resolved: bool
    is_outdated: bool


def parse_iso_timestamp(raw: str) -> datetime:
    """Parse an ISO-8601 timestamp string into an aware UTC `datetime`."""
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("Timestamp cannot be empty")
    normalized = cleaned[:-1] + "+00:00" if cleaned.endswith(("Z", "z")) else cleaned
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _require_gh_bin() -> str:
    """Return resolved `gh` binary path on PATH or raise `RuntimeError`."""
    gh_bin = shutil.which("gh")
    if not gh_bin:
        raise RuntimeError("Missing required 'gh' CLI on PATH")
    return gh_bin


def _extract_user(entry: dict[str, object]) -> dict[str, object]:
    """Return the normalized `user` mapping from a GitHub comment or review payload."""
    user_raw = entry.get("user")
    return user_raw if isinstance(user_raw, dict) else {}


def _author_login(user: dict[str, object]) -> str:
    """Extract author login from `user`, falling back to `UNKNOWN_AUTHOR`."""
    return str(user.get("login") or UNKNOWN_AUTHOR)


def resolve_repo_slug(explicit_repo: str | None = None) -> str:
    """Return `owner/repo` from `--repo` or active `gh repo view`, failing fast if unavailable."""
    if explicit_repo:
        cleaned = explicit_repo.strip()
        if not REPO_SLUG_RE.match(cleaned):
            raise ValueError(f"Invalid --repo '{explicit_repo}' (expected owner/repo)")
        return cleaned
    gh_bin = _require_gh_bin()
    proc = subprocess.run(
        [gh_bin, "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"Failed to detect GitHub repository: {proc.stderr.strip() or 'unknown error'}")
    return proc.stdout.strip()


def fetch_gh_json(endpoint: str) -> list[dict[str, object]]:
    """Invoke `gh api --paginate` for `endpoint` and decode single or multi-page JSON arrays."""
    gh_bin = _require_gh_bin()
    proc = subprocess.run(
        [gh_bin, "api", "--paginate", endpoint],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh api '{endpoint}' failed: {proc.stderr.strip() or proc.stdout.strip()}")
    raw = proc.stdout.strip()
    if not raw:
        return []

    # `gh api --paginate` concatenates one JSON array per page (`[...][...]`) across >30-item endpoints.
    decoder = json.JSONDecoder()
    items: list[dict[str, object]] = []
    idx = 0
    while idx < len(raw):
        while idx < len(raw) and raw[idx].isspace():
            idx += 1
        if idx >= len(raw):
            break
        chunk, next_idx = decoder.raw_decode(raw, idx)
        if not isinstance(chunk, list):
            raise RuntimeError(f"Unexpected non-list JSON payload from '{endpoint}': {type(chunk).__name__}")
        items.extend(chunk)
        idx = next_idx
    return items


def fetch_review_thread_states(repo: str, pr_number: int) -> dict[int, ReviewThreadState]:
    """Query GraphQL `reviewThreads` and map inline comment `databaseId` to `ReviewThreadState`."""
    gh_bin = _require_gh_bin()
    owner, name = repo.split("/", 1)
    comment_map: dict[int, ReviewThreadState] = {}
    cursor: str | None = None

    while True:
        # Use raw `-f` for string variables so numeric/boolean-looking logins never coerce types.
        cmd = [
            gh_bin,
            "api",
            "graphql",
            "-f",
            f"query={REVIEW_THREADS_QUERY}",
            "-f",
            f"owner={owner}",
            "-f",
            f"name={name}",
            "-F",
            f"pr={pr_number}",
        ]
        if cursor is not None:
            cmd.extend(["-f", f"after={cursor}"])
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"gh api graphql failed: {proc.stderr.strip() or proc.stdout.strip()}")
        payload = json.loads(proc.stdout)
        if not isinstance(payload, dict):
            raise RuntimeError(f"Unexpected GraphQL payload type: {type(payload).__name__}")
        if g_errors := payload.get("errors"):
            raise RuntimeError(f"gh api graphql returned errors: {g_errors}")
        pr_node = ((payload.get("data") or {}).get("repository") or {}).get("pullRequest") or {}
        conn = pr_node.get("reviewThreads") or {}
        for node in conn.get("nodes") or []:
            if not isinstance(node, dict) or not node.get("id"):
                continue
            state = ReviewThreadState(
                thread_id=str(node["id"]),
                is_resolved=bool(node.get("isResolved")),
                is_outdated=bool(node.get("isOutdated")),
            )
            for comment in (node.get("comments") or {}).get("nodes") or []:
                if isinstance(comment, dict) and isinstance(comment.get("databaseId"), int):
                    comment_map[comment["databaseId"]] = state
        page_info = conn.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        cursor = str(page_info.get("endCursor") or "")
        if not cursor:
            raise RuntimeError("GraphQL reviewThreads pagination returned hasNextPage=True with empty endCursor")
    return comment_map


def _is_skipped_bot(user: dict[str, object], body: str, include_bots: bool) -> bool:
    """Return True when automated bot or preview banner noise should be skipped."""
    if include_bots:
        return False
    user_type = str(user.get("type") or "")
    return user_type.lower() == "bot" or PREVIEW_COMMENT_MARKER in body


def _entry_timestamp(entry: dict[str, object]) -> str:
    """Extract ISO timestamp string (`created_at` or `submitted_at`) if present."""
    raw = entry.get("created_at") or entry.get("submitted_at") or ""
    return str(raw).strip()


def _passes_since(ts_str: str, since_dt: datetime | None) -> bool:
    """Return True when `since_dt` is unset, timestamp is absent, or timestamp >= `since_dt`."""
    # Fail open when an item lacks a timestamp so undated records are never dropped silently.
    if since_dt is None or not ts_str:
        return True
    return parse_iso_timestamp(ts_str) >= since_dt


def _visible_entry_body_and_user(
    entry: dict[str, object], include_bots: bool
) -> tuple[str, dict[str, object]] | None:
    """Return `(body, user)` for non-empty visible comments, or None if blank or skipped bot noise."""
    body = str(entry.get("body") or "").strip()
    if not body:
        return None
    user = _extract_user(entry)
    if _is_skipped_bot(user, body, include_bots):
        return None
    return body, user


def _extract_preview_location(body: str) -> tuple[str | None, int | None]:
    """Parse optional `<!-- apex-preview-loc: path=... line=... -->` metadata from `body`."""
    match = PREVIEW_LOC_RE.search(body)
    if match is None:
        return None, None
    parsed_line = int(match.group(2)) if match.group(2) else None
    return match.group(1), parsed_line


def _base_feedback_item(
    entry: dict[str, object], source: str, body: str, user: dict[str, object]
) -> dict[str, object]:
    """Construct the shared normalized feedback schema from a GitHub comment or review payload."""
    fallback_path, fallback_line = _extract_preview_location(body)
    cleaned_body = PREVIEW_LOC_RE.sub("", body)
    cleaned_body = PREVIEW_RESOLVED_RE.sub("", cleaned_body)
    cleaned_body = PREVIEW_REPLY_RE.sub("", cleaned_body).strip()
    return {
        "id": entry.get("id"),
        "source": source,
        "author": _author_login(user),
        "path": entry.get("path") or fallback_path,
        "line": entry.get("line") or entry.get("original_line") or fallback_line,
        "diff_hunk": entry.get("diff_hunk"),
        "url": entry.get("html_url"),
        "created_at": _entry_timestamp(entry),
        "body": cleaned_body,
    }


class _ThreadSortKey(NamedTuple):
    """Chronological sort key placing root inline comments ahead of replies."""

    is_reply: int
    created_at: datetime
    comment_id: int


def _thread_sort_key(pair: tuple[dict[str, object], ReviewThreadState | None]) -> _ThreadSortKey:
    """Sort root comments ahead of replies and order replies chronologically in UTC."""
    entry = pair[0]
    is_reply = 0 if entry.get("in_reply_to_id") is None else 1
    ts_str = _entry_timestamp(entry)
    dt = parse_iso_timestamp(ts_str) if ts_str else datetime.max.replace(tzinfo=UTC)
    cid = raw_id if isinstance(raw_id := entry.get("id"), int) else 0
    return _ThreadSortKey(is_reply=is_reply, created_at=dt, comment_id=cid)


def _build_grouped_inline_items(
    entries: list[dict[str, object]],
    thread_states: dict[int, ReviewThreadState],
    *,
    include_bots: bool,
    include_resolved: bool,
    since_dt: datetime | None,
) -> list[dict[str, object]]:
    """Group inline comments by GraphQL thread ID (or root reply ID) into single items."""
    groups: dict[str, list[tuple[dict[str, object], ReviewThreadState | None]]] = {}
    for entry in entries:
        visible = _visible_entry_body_and_user(entry, include_bots)
        if visible is None:
            continue
        comment_id = entry.get("id")
        t_state = thread_states.get(comment_id) if isinstance(comment_id, int) else None
        if not include_resolved and t_state is not None and t_state.is_resolved:
            continue
        reply_parent = entry.get("in_reply_to_id")
        if t_state is not None:
            key = f"thread:{t_state.thread_id}"
        elif isinstance(reply_parent, int):
            key = f"root:{reply_parent}"
        else:
            key = f"root:{comment_id}"
        groups.setdefault(key, []).append((entry, t_state))

    items: list[dict[str, object]] = []
    for bucket in groups.values():
        bucket.sort(key=_thread_sort_key)
        root_entry, root_state = bucket[0]
        last_ts = _entry_timestamp(bucket[-1][0])
        # Filter on the thread's latest activity after grouping so older open threads surface new replies.
        if not _passes_since(last_ts, since_dt):
            continue
        root_body = str(root_entry.get("body") or "").strip()
        root_user = _extract_user(root_entry)
        replies = [
            {
                "id": rep_entry.get("id"),
                "author": _author_login(_extract_user(rep_entry)),
                "created_at": _entry_timestamp(rep_entry),
                "body": str(rep_entry.get("body") or "").strip(),
            }
            for rep_entry, _ in bucket[1:]
        ]
        item = _base_feedback_item(root_entry, "inline", root_body, root_user)
        item["last_activity_at"] = last_ts
        item["replies"] = replies
        item["reply_count"] = len(replies)
        item["last_author"] = str(replies[-1]["author"]) if replies else str(item["author"])
        if root_state is not None:
            item["thread_id"] = root_state.thread_id
            item["is_resolved"] = root_state.is_resolved
            item["is_outdated"] = root_state.is_outdated
        items.append(item)
    return items


def _collect_resolved_roots(
    review_entries: list[dict[str, object]], issue_entries: list[dict[str, object]]
) -> set[int]:
    """Resolve root comment/review IDs using state-comment overrides and body markers."""
    state_overrides: dict[int, bool] = {}
    for entry in issue_entries:
        if m := PREVIEW_STATE_RE.search(str(entry.get("body") or "")):
            state_overrides[int(m.group(1))] = m.group(2) == "1"

    resolved_roots: set[int] = {rid for rid, flag in state_overrides.items() if flag}
    for entry in (*review_entries, *issue_entries):
        cid = entry.get("id")
        if (
            isinstance(cid, int)
            and cid not in state_overrides
            and PREVIEW_RESOLVED_RE.search(str(entry.get("body") or ""))
        ):
            resolved_roots.add(cid)
    return resolved_roots


def _collect_conv_and_review_items(
    repo: str,
    pr_number: int,
    *,
    include_bots: bool,
    include_resolved: bool,
    since_dt: datetime | None,
    after_review_id: int | None,
) -> list[dict[str, object]]:
    """Collect PR review bodies and issue comments while grouping preview replies onto parents."""
    review_entries = fetch_gh_json(f"repos/{repo}/pulls/{pr_number}/reviews")
    issue_entries = fetch_gh_json(f"repos/{repo}/issues/{pr_number}/comments")
    resolved_roots = _collect_resolved_roots(review_entries, issue_entries)

    roots: list[dict[str, object]] = []
    roots_by_id: dict[int, dict[str, object]] = {}
    replies_by_parent: dict[int, list[dict[str, object]]] = {}
    skipped_reviews: set[int] = set()

    for source, raw_entries in (("review", review_entries), ("issue", issue_entries)):
        for entry in raw_entries:
            visible = _visible_entry_body_and_user(entry, include_bots)
            if visible is None:
                continue
            body, user = visible
            if PREVIEW_STATE_RE.search(body):
                continue
            comment_id = entry.get("id")
            if source == "review" and after_review_id is not None and isinstance(comment_id, int) and comment_id <= after_review_id:
                skipped_reviews.add(comment_id)
                continue
            reply_m = PREVIEW_REPLY_RE.search(body)
            parent_id = int(reply_m.group(1)) if reply_m else None
            is_marked_resolved = (
                (isinstance(comment_id, int) and comment_id in resolved_roots)
                or (parent_id is not None and parent_id in resolved_roots)
            )
            if not include_resolved and is_marked_resolved:
                continue
            item = _base_feedback_item(entry, source, body, user)
            if is_marked_resolved:
                item["is_resolved"] = True
            if parent_id is not None:
                replies_by_parent.setdefault(parent_id, []).append(item)
            else:
                item["replies"] = []
                item["reply_count"] = 0
                item["last_author"] = str(item["author"])
                item["last_activity_at"] = str(item["created_at"] or "")
                roots.append(item)
                if isinstance(comment_id, int):
                    roots_by_id[comment_id] = item

    for parent_id, rep_items in replies_by_parent.items():
        if parent_id in skipped_reviews:
            continue
        parent = roots_by_id.get(parent_id)
        if parent is None:
            for rep in rep_items:
                if _passes_since(str(rep.get("created_at") or ""), since_dt):
                    roots.append(rep)
            continue
        existing = parent["replies"]
        assert isinstance(existing, list)
        for rep in rep_items:
            existing.append({
                "id": rep.get("id"),
                "author": rep.get("author"),
                "created_at": rep.get("created_at"),
                "body": rep.get("body"),
            })
            if ts := str(rep.get("created_at") or ""):
                parent["last_activity_at"] = ts
        parent["reply_count"] = len(existing)
        parent["last_author"] = str(existing[-1]["author"])

    return [item for item in roots if _passes_since(str(item.get("last_activity_at") or item.get("created_at") or ""), since_dt)]


def normalize_pr_feedback(
    repo: str,
    pr_number: int,
    *,
    include_bots: bool = False,
    include_resolved: bool = False,
    since: str | None = None,
    after_review_id: int | None = None,
) -> list[dict[str, object]]:
    """Collect and normalize grouped inline threads, review bodies, and PR issue comments."""
    since_dt = parse_iso_timestamp(since) if since is not None else None
    thread_states = fetch_review_thread_states(repo, pr_number)
    inline_entries = fetch_gh_json(f"repos/{repo}/pulls/{pr_number}/comments")
    items = _build_grouped_inline_items(
        inline_entries,
        thread_states,
        include_bots=include_bots,
        include_resolved=include_resolved,
        since_dt=since_dt,
    )
    items.extend(
        _collect_conv_and_review_items(
            repo,
            pr_number,
            include_bots=include_bots,
            include_resolved=include_resolved,
            since_dt=since_dt,
            after_review_id=after_review_id,
        )
    )
    return items


def format_feedback_markdown(pr_number: int, items: list[dict[str, object]]) -> str:
    """Format normalized PR feedback items into a scannable calibration checklist."""
    if not items:
        return f"No human feedback items found on PR #{pr_number}."
    lines = [f"# Harvested Feedback for PR #{pr_number} ({len(items)} item(s))", ""]
    for idx, item in enumerate(items, start=1):
        if item.get("path") and item.get("line") is not None:
            loc = f"{item['path']}:{item['line']}"
        elif item.get("path"):
            loc = str(item["path"])
        else:
            loc = str(item["source"])
        flags: list[str] = []
        if item.get("is_resolved"):
            flags.append("resolved")
        if item.get("is_outdated"):
            flags.append("outdated")
        raw_rc = item.get("reply_count")
        if isinstance(raw_rc, int) and raw_rc > 0:
            flags.append(f"{raw_rc} repl{'y' if raw_rc == 1 else 'ies'}, last: @{item.get('last_author')}")
        status = f" ({'; '.join(flags)})" if flags else ""
        ids = f" [thread={item['thread_id']} root={item['id']}]" if item.get("thread_id") else f" [id={item.get('id')}]"
        snippet = str(item["body"]).replace("\r\n", "\n").strip()
        lines.append(f"{idx}. **[{item['source']}] `{loc}`{status}{ids}** (@{item['author']}): {snippet}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for harvesting PR feedback into calibration formats."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True, help="Pull request number.")
    parser.add_argument("--repo", default=None, help="Optional owner/repo (defaults to active gh repo).")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output file path.")
    parser.add_argument("--include-bots", action="store_true", help="Include bot-authored comments.")
    parser.add_argument("--include-resolved", action="store_true", help="Include resolved inline threads.")
    parser.add_argument("--since", default=None, help="Only keep items/threads active at or after ISO-8601 timestamp.")
    parser.add_argument(
        "--after-review-id",
        type=int,
        default=None,
        help="Skip review summary entries with numeric ID <= this value.",
    )
    args = parser.parse_args(argv)

    try:
        repo = resolve_repo_slug(args.repo)
        items = normalize_pr_feedback(
            repo,
            args.pr,
            include_bots=args.include_bots,
            include_resolved=args.include_resolved,
            since=args.since,
            after_review_id=args.after_review_id,
        )
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({"pr": args.pr, "repo": repo, "items": items}, indent=2) + "\n", encoding="utf-8")
    print(format_feedback_markdown(args.pr, items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
