"""Unit tests for PR diff hunk line-range metadata export (`scripts/export_pr_review_meta.py`)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import export_pr_review_meta  # noqa: E402 — repo test runner imports standalone scripts without package install
import watch_pr_feedback  # noqa: E402 — repo test runner imports standalone scripts without package install


def _git(repo: Path, *args: str) -> str:
    """Run git in `repo` and return stripped stdout."""
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def test_parse_unified_diff_ranges_handles_hunks_and_deletions() -> None:
    """Verify unified diff parser extracts merged commentable/added intervals and skips deleted files."""
    sample_diff = "\n".join([
        "diff --git a/systems/brain/chapters/01.md b/systems/brain/chapters/01.md",
        "index 1111111..2222222 100644",
        "--- a/systems/brain/chapters/01.md",
        "+++ b/systems/brain/chapters/01.md",
        "@@ -10,3 +10,4 @@",
        " context A",
        "-old line",
        "+new line A",
        "+new line B",
        " context B",
        "@@ -40 +41,2 @@",
        "+tail one",
        "+tail two",
        "\\ No newline at end of file",
        "diff --git a/old.md b/old.md",
        "deleted file mode 100644",
        "--- a/old.md",
        "+++ /dev/null",
        "@@ -1,2 +0,0 @@",
        "-gone 1",
        "-gone 2",
        'diff --git "a/dir/with space.md" "b/dir/with space.md"',
        '--- "a/dir/with space.md"',
        '+++ "b/dir/with space.md"',
        "@@ -1 +1 @@",
        "-x",
        "+y",
    ])
    parsed = export_pr_review_meta.parse_unified_diff_ranges(sample_diff)
    assert parsed["systems/brain/chapters/01.md"]["commentable"] == [[10, 13], [41, 42]]
    assert parsed["systems/brain/chapters/01.md"]["added"] == [[11, 12], [41, 42]]
    assert "old.md" not in parsed
    assert parsed["dir/with space.md"]["added"] == [[1, 1]]
    assert export_pr_review_meta._merge_intervals([]) == []
    assert export_pr_review_meta._extract_new_path("") is None


def test_export_pr_review_meta_real_git_repo_and_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify git diff integration on a temp repo, CLI file output, stdout output, and validation errors."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")

    target = repo / "chapter.md"
    target.write_text("line1\nline2\nline3\nline4\nline5\n", encoding="utf-8")
    _git(repo, "add", "chapter.md")
    _git(repo, "commit", "-m", "base")
    base_sha = _git(repo, "rev-parse", "HEAD")

    target.write_text("line1\nline2-edited\nline3\nline4\nline5\nline6-added\n", encoding="utf-8")
    _git(repo, "add", "chapter.md")
    _git(repo, "commit", "-m", "head")
    head_sha = _git(repo, "rev-parse", "HEAD")

    out_file = tmp_path / "out" / "meta.json"
    rc = export_pr_review_meta.main([
        "--pr",
        "42",
        "--repo",
        "Ethanex8/apex",
        "--base-sha",
        base_sha,
        "--head-sha",
        head_sha,
        "--repo-root",
        str(repo),
        "--out",
        str(out_file),
    ])
    assert rc == 0
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert payload["enabled"] is True
    assert payload["prNumber"] == 42
    assert payload["prUrl"] == "https://github.com/Ethanex8/apex/pull/42"
    assert payload["files"]["chapter.md"]["added"] == [[2, 2], [6, 6]]

    rc_stdout = export_pr_review_meta.main([
        "--pr",
        "42",
        "--repo",
        "Ethanex8/apex",
        "--base-sha",
        base_sha,
        "--head-sha",
        head_sha,
        "--repo-root",
        str(repo),
    ])
    assert rc_stdout == 0
    assert '"prNumber": 42' in capsys.readouterr().out

    for bad_args in (
        ["--pr", "0", "--repo", "Ethanex8/apex", "--base-sha", base_sha, "--head-sha", head_sha],
        ["--pr", "1", "--repo", "badslug", "--base-sha", base_sha, "--head-sha", head_sha],
        ["--pr", "1", "--repo", "Ethanex8/apex", "--base-sha", "bad!", "--head-sha", head_sha],
        ["--pr", "1", "--repo", "Ethanex8/apex", "--base-sha", base_sha, "--head-sha", "bad!"],
        ["--pr", "1", "--repo", "Ethanex8/apex", "--base-sha", "deadbeef", "--head-sha", head_sha, "--repo-root", str(repo)],
    ):
        assert export_pr_review_meta.main(bad_args) == 1


def test_watch_pr_feedback_detection_and_timeout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify watch_pr_feedback detects new comments/replies/reviews, respects max-polls, and handles errors."""
    monkeypatch.setattr(watch_pr_feedback.time, "sleep", lambda _sec: None)

    poll_state = {"step": 0}

    def _fake_normalize(_repo: str, _pr: int, *, include_resolved: bool = False) -> list[dict[str, object]]:
        """Simulate initial baseline followed by a new reply and inline item on poll 2."""
        if poll_state["step"] < 2:
            return [
                {
                    "id": 10,
                    "source": "inline",
                    "author": "Ethanex8",
                    "path": "a.md",
                    "line": 5,
                    "body": "Initial",
                    "replies": [{"id": 11, "author": "agent", "body": "Done"}],
                }
            ]
        return [
            {
                "id": 10,
                "source": "inline",
                "author": "Ethanex8",
                "path": "a.md",
                "line": 5,
                "body": "Initial",
                "replies": [
                    {"id": 11, "author": "agent", "body": "Done"},
                    {"id": 12, "author": "Ethanex8", "body": "Thanks"},
                ],
            }
        ]

    def _fake_gh_json(_endpoint: str) -> list[dict[str, object]]:
        """Simulate bot, PENDING, and new submitted human reviews."""
        poll_state["step"] += 1
        if poll_state["step"] < 3:
            return [
                {"id": 1, "state": "COMMENTED", "user": {"type": "Bot"}},
                {"id": 2, "state": "PENDING", "user": {"type": "User"}},
            ]
        return [
            {"id": 1, "state": "COMMENTED", "user": {"type": "Bot"}},
            {"id": 3, "state": "APPROVED", "user": {"type": "User"}},
        ]

    monkeypatch.setattr(watch_pr_feedback.harvest_feedback, "normalize_pr_feedback", _fake_normalize)
    monkeypatch.setattr(watch_pr_feedback.harvest_feedback, "fetch_gh_json", _fake_gh_json)
    monkeypatch.setattr(watch_pr_feedback.harvest_feedback, "resolve_repo_slug", lambda r: r or "Ethanex8/apex")

    rc_detect = watch_pr_feedback.main(["--pr", "9", "--repo", "Ethanex8/apex", "--interval", "0.01", "--max-polls", "3"])
    assert rc_detect == 0
    assert "Detected new activity on PR #9: 1 comment(s), 1 review(s)." in capsys.readouterr().out

    # Test timeout with zero changes
    poll_state["step"] = 0
    monkeypatch.setattr(watch_pr_feedback.harvest_feedback, "fetch_gh_json", lambda _e: [])
    rc_timeout = watch_pr_feedback.main(["--pr", "9", "--interval", "0.01", "--max-polls", "1"])
    assert rc_timeout == 2

    assert watch_pr_feedback.main(["--pr", "0"]) == 1
    monkeypatch.setattr(
        watch_pr_feedback.harvest_feedback,
        "resolve_repo_slug",
        lambda _r: (_ for _ in ()).throw(RuntimeError("no gh")),
    )
    assert watch_pr_feedback.main(["--pr", "9"]) == 1


def test_watch_pr_feedback_transient_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify transient gh poll errors retry cleanly while persistent failures raise."""
    monkeypatch.setattr(watch_pr_feedback.time, "sleep", lambda _sec: None)
    monkeypatch.setattr(watch_pr_feedback.harvest_feedback, "normalize_pr_feedback", lambda _r, _p, **_k: [])
    calls = {"count": 0}

    def _flaky_reviews(_endpoint: str) -> list[dict[str, object]]:
        """Fail once transiently, recover cleanly, then fail repeatedly to trigger abort."""
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("unexpected end of JSON input")
        if calls["count"] >= 4:
            raise RuntimeError("persistent network failure")
        return []

    monkeypatch.setattr(watch_pr_feedback.harvest_feedback, "fetch_gh_json", _flaky_reviews)
    rc_recover = watch_pr_feedback.watch_pr_until_feedback("Ethanex8/apex", 9, interval_s=0.01, max_polls=2)
    assert rc_recover == 2
    assert "WARN: transient poll error (1/5)" in capsys.readouterr().err

    with pytest.raises(RuntimeError, match="persistent network failure"):
        watch_pr_feedback.watch_pr_until_feedback(
            "Ethanex8/apex", 9, interval_s=0.01, max_polls=3, max_consecutive_errors=2
        )


