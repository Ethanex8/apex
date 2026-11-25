#!/usr/bin/env python3
"""Export PR diff hunk line intervals as JSON for VitePress inline review previews.

Purpose:
  Run `git diff --unified=3` between a pull request's base and head commits so
  the static PR textbook preview knows which right-side file lines lie inside
  commentable GitHub diff hunks vs. out-of-hunk or unmodified files.

Usage:
  python3 scripts/export_pr_review_meta.py --pr 42 --repo Ethanex8/apex \
    --base-sha <base> --head-sha <head> --out /tmp/apex-pr-review-meta.json

Outputs:
  Writes JSON metadata to `--out` (or stdout if omitted); exits 1 on invalid
  arguments or git diff failures.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_SLUG_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _merge_intervals(line_numbers: list[int]) -> list[list[int]]:
    """Collapse sorted or unsorted 1-indexed line numbers into inclusive `[start, end]` ranges."""
    if not line_numbers:
        return []
    ordered = sorted(set(line_numbers))
    ranges: list[list[int]] = [[ordered[0], ordered[0]]]
    for num in ordered[1:]:
        if num <= ranges[-1][1] + 1:
            ranges[-1][1] = num
        else:
            ranges.append([num, num])
    return ranges


def _extract_new_path(raw_header: str) -> str | None:
    """Return normalized repo-relative path from a `+++ b/<path>` diff header, or None for `/dev/null`."""
    cleaned = raw_header.strip()
    if cleaned == "/dev/null":
        return None
    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) >= 2:
        cleaned = cleaned[1:-1]
    if cleaned.startswith("b/"):
        return cleaned[2:]
    return cleaned or None


def _finalize_file_entry(
    files: dict[str, dict[str, list[list[int]]]],
    current_path: str | None,
    commentable: list[int],
    added: list[int],
) -> None:
    """Store merged `commentable` and `added` line intervals for `current_path` when present."""
    if current_path is None:
        return
    files[current_path] = {
        "commentable": _merge_intervals(commentable),
        "added": _merge_intervals(added),
    }


def parse_unified_diff_ranges(diff_text: str) -> dict[str, dict[str, list[list[int]]]]:
    """Parse `git diff -U3` output into merged right-side `commentable` and `added` line ranges."""
    files: dict[str, dict[str, list[list[int]]]] = {}
    current_path: str | None = None
    commentable: list[int] = []
    added: list[int] = []
    in_hunk = False
    new_line = 0

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            _finalize_file_entry(files, current_path, commentable, added)
            current_path = None
            commentable = []
            added = []
            in_hunk = False
            continue
        if line.startswith("+++ "):
            current_path = _extract_new_path(line[4:])
            in_hunk = False
            continue
        if line.startswith("--- ") and not in_hunk:
            continue
        if m := HUNK_HEADER_RE.match(line):
            new_line = int(m.group(1))
            in_hunk = True
            continue
        if not in_hunk or current_path is None:
            continue
        if line.startswith("+"):
            commentable.append(new_line)
            added.append(new_line)
            new_line += 1
        elif line.startswith(" "):
            commentable.append(new_line)
            new_line += 1
        elif line.startswith(("-", "\\")):
            continue

    _finalize_file_entry(files, current_path, commentable, added)
    return files


def _run_git_diff(repo_root: Path, base_sha: str, head_sha: str) -> str:
    """Execute `git diff --unified=3` across `base_sha...head_sha` and return stdout."""
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "-c",
            "core.quotePath=false",
            "diff",
            "--unified=3",
            "--no-color",
            "--no-ext-diff",
            f"{base_sha}...{head_sha}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "unknown git diff error"
        raise RuntimeError(f"git diff failed for {base_sha}...{head_sha}: {detail}")
    return proc.stdout


def export_pr_review_meta(
    pr_number: int,
    repo: str,
    base_sha: str,
    head_sha: str,
    repo_root: Path,
) -> dict[str, object]:
    """Validate inputs, inspect git diff hunks, and return PR preview review metadata JSON."""
    if pr_number <= 0:
        raise ValueError(f"Invalid --pr '{pr_number}' (must be positive)")
    cleaned_repo = repo.strip()
    if not REPO_SLUG_RE.match(cleaned_repo):
        raise ValueError(f"Invalid --repo '{repo}' (expected owner/repo)")
    if not SHA_RE.match(base_sha.strip()):
        raise ValueError(f"Invalid --base-sha '{base_sha}'")
    if not SHA_RE.match(head_sha.strip()):
        raise ValueError(f"Invalid --head-sha '{head_sha}'")

    diff_text = _run_git_diff(repo_root.resolve(), base_sha.strip(), head_sha.strip())
    return {
        "enabled": True,
        "repo": cleaned_repo,
        "prNumber": pr_number,
        "baseSha": base_sha.strip(),
        "headSha": head_sha.strip(),
        "prUrl": f"https://github.com/{cleaned_repo}/pull/{pr_number}",
        "files": parse_unified_diff_ranges(diff_text),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for writing PR diff hunk metadata JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True, help="Pull request number.")
    parser.add_argument("--repo", required=True, help="GitHub repository slug (owner/repo).")
    parser.add_argument("--base-sha", required=True, help="PR base commit SHA.")
    parser.add_argument("--head-sha", required=True, help="PR head commit SHA.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output file path.")
    args = parser.parse_args(argv)

    try:
        payload = export_pr_review_meta(args.pr, args.repo, args.base_sha, args.head_sha, args.repo_root)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    encoded = json.dumps(payload, indent=2) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
