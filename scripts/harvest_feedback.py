#!/usr/bin/env python3
"""Fetch and normalize GitHub PR review comments into structured calibration records.

Purpose:
  Pull inline diff comments, review summaries, and conversation comments from a
  GitHub pull request via `gh api` so `apex-skill-healer` can score blind
  subagent recall against every human critique item.

Usage:
  python3 scripts/harvest_feedback.py --pr 3
  python3 scripts/harvest_feedback.py --pr 3 --out .cache/feedback/pr-3.json

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
from pathlib import Path

REPO_SLUG_RE = re.compile(r"^[^/\s]+/[^/\s]+$")


def resolve_repo_slug(explicit_repo: str | None = None) -> str:
    """Return `owner/repo` from `--repo` or active `gh repo view`, failing fast if unavailable."""
    if explicit_repo:
        cleaned = explicit_repo.strip()
        if not REPO_SLUG_RE.match(cleaned):
            raise ValueError(f"Invalid --repo '{explicit_repo}' (expected owner/repo)")
        return cleaned
    gh_bin = shutil.which("gh")
    if not gh_bin:
        raise RuntimeError("Missing required 'gh' CLI on PATH")
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
    gh_bin = shutil.which("gh")
    if not gh_bin:
        raise RuntimeError("Missing required 'gh' CLI on PATH")
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


def normalize_pr_feedback(
    repo: str,
    pr_number: int,
    *,
    include_bots: bool = False,
) -> list[dict[str, object]]:
    """Collect and normalize inline comments, review bodies, and PR issue comments."""
    endpoints = (
        ("inline", f"repos/{repo}/pulls/{pr_number}/comments"),
        ("review", f"repos/{repo}/pulls/{pr_number}/reviews"),
        ("issue", f"repos/{repo}/issues/{pr_number}/comments"),
    )
    items: list[dict[str, object]] = []
    for source, endpoint in endpoints:
        for entry in fetch_gh_json(endpoint):
            body = str(entry.get("body") or "").strip()
            if not body:
                continue
            user = entry.get("user") if isinstance(entry.get("user"), dict) else {}
            user_type = str(user.get("type") or "")
            # Automated CI/Vercel/summary bots add noise unless explicitly requested.
            if not include_bots and user_type.lower() == "bot":
                continue
            items.append(
                {
                    "id": entry.get("id"),
                    "source": source,
                    "author": str(user.get("login") or "unknown"),
                    "path": entry.get("path"),
                    "line": entry.get("line") or entry.get("original_line"),
                    "diff_hunk": entry.get("diff_hunk"),
                    "url": entry.get("html_url"),
                    "body": body,
                }
            )
    return items


def format_feedback_markdown(pr_number: int, items: list[dict[str, object]]) -> str:
    """Format normalized PR feedback items into a scannable calibration checklist."""
    if not items:
        return f"No human feedback items found on PR #{pr_number}."
    lines = [f"# Harvested Feedback for PR #{pr_number} ({len(items)} item(s))", ""]
    for idx, item in enumerate(items, start=1):
        loc = f"{item['path']}:{item['line']}" if item.get("path") else str(item["source"])
        snippet = str(item["body"]).replace("\r\n", "\n").strip()
        lines.append(f"{idx}. **[{item['source']}] `{loc}`** (@{item['author']}): {snippet}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for harvesting PR feedback into calibration formats."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True, help="Pull request number.")
    parser.add_argument("--repo", default=None, help="Optional owner/repo (defaults to active gh repo).")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output file path.")
    parser.add_argument("--include-bots", action="store_true", help="Include bot-authored comments.")
    args = parser.parse_args(argv)

    try:
        repo = resolve_repo_slug(args.repo)
        items = normalize_pr_feedback(repo, args.pr, include_bots=args.include_bots)
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
