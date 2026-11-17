#!/usr/bin/env python3
"""Unit tests for `scripts/build.py` and `scripts/step.py` roadmap/lifecycle tooling.

Purpose:
  Verify DAG/schema/step validation, metric computation, dynamic Markdown compilation,
  `--check` drift detection, safe YAML parsing, `step.py` CLI transitions (`status`,
  `next`, `review`, `approve`, `reset`), and atomic rollback on failure.

Usage:
  PYTHONPATH=scripts uv run --with pytest --with pytest-cov --with pyyaml pytest -v \\
    --cov=build --cov=step --cov-fail-under=95 scripts/tests/test_lifecycle.py

Invariants:
  - Executes exclusively against `tmp_path` fixtures without touching repository `roadmap.yaml`.
  - Maintains >=95% line coverage across both `scripts/build.py` and `scripts/step.py`.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build  # noqa: E402 — repo test runner imports standalone scripts without package install
import check_book  # noqa: E402 — repo test runner imports standalone scripts without package install
import step  # noqa: E402 — repo test runner imports standalone scripts without package install
import sync_book  # noqa: E402 — repo test runner imports standalone scripts without package install


def _sample_book() -> dict:
    """Return a valid two-part, two-chapter book manifest covering `alpha-01` and `beta-01`."""
    return {
        "title": "Demo Apex Textbook",
        "subtitle": "From logic gates to locomotion",
        "parts": [
            {
                "id": "part-1",
                "number": "I",
                "system": "alpha",
                "title": "Alpha Foundations",
                "summary": "Core digital concepts",
                "chapters": [
                    {
                        "id": "ch-01",
                        "number": 1,
                        "slug": "01_alpha_core",
                        "title": "Alpha Core",
                        "summary": "Foundations",
                        "steps": ["alpha-01"],
                    }
                ],
            },
            {
                "id": "part-2",
                "number": "II",
                "system": "beta",
                "title": "Beta Actuation",
                "summary": "Drive hardware",
                "chapters": [
                    {
                        "id": "ch-02",
                        "number": 2,
                        "slug": "02_beta_drive",
                        "title": "Beta Drive",
                        "summary": "Torque stage",
                        "steps": ["beta-01"],
                    }
                ],
            },
        ],
    }


def _sample_roadmap() -> dict:
    """Build a valid minimal two-system (`alpha` -> `beta`) roadmap dictionary for testing."""
    return {
        "repository": {
            "title": "Demo Apex",
            "tagline": "Test tagline",
            "robot_class": "2.5 kg quadruped",
            "estimated_total_bom_usd": "\\$500",
        },
        "safety_guardrails": [{"name": "SELV", "description": "Under 22V"}],
        "phased_procurement": [{"stage": "Phase A", "est_cost_usd": "\\$100", "items": "Dev board"}],
        "systems": [
            {
                "id": "alpha",
                "order": 1,
                "name": "Alpha Core",
                "role": "Compute",
                "workspace": "systems/alpha",
                "est_weeks": "2w",
                "graduation_demo": "Runs sim",
                "depends_on": [],
                "phases": [{"id": "alpha-p1", "name": "Phase 1"}],
            },
            {
                "id": "beta",
                "order": 2,
                "name": "Beta Drive",
                "role": "Actuator",
                "workspace": "systems/beta",
                "est_weeks": "2w",
                "graduation_demo": "Spins motor",
                "depends_on": ["alpha"],
                "phases": [{"id": "beta-p1", "name": "Phase 1"}],
            },
        ],
        "book": _sample_book(),
        "steps": [
            {
                "id": "alpha-01",
                "system": "alpha",
                "phase": "alpha-p1",
                "mode": "couch",
                "status": "pending",
                "title": "Step Alpha 1",
                "first_principles": "Discrete math",
                "reference_reading": "Ch 1",
                "deliverables": ["systems/alpha/a.py"],
                "verification": "python3 -m pytest systems/alpha",
            },
            {
                "id": "beta-01",
                "system": "beta",
                "phase": "beta-p1",
                "mode": "bench",
                "status": "pending",
                "title": "Step Beta 1",
                "first_principles": "Torque",
                "reference_reading": "Ch 2",
                "deliverables": ["bench"],
                "verification": "Spin motor cleanly",
            },
        ],
    }


def _patch_tmp_repo(tmp_path: Path, mp: pytest.MonkeyPatch, data: dict) -> Path:
    """Point `build` and `step` module globals to `tmp_path` and write `roadmap.yaml`."""
    yaml_path = tmp_path / "roadmap.yaml"
    yaml_path.write_text(yaml.dump(data, sort_keys=False), encoding="utf-8")
    mp.setattr(build, "ROOT_DIR", tmp_path)
    mp.setattr(build, "ROADMAP_YAML_PATH", yaml_path)
    mp.setattr(build, "ROADMAP_MD_PATH", tmp_path / "ROADMAP.md")
    mp.setattr(build, "README_MD_PATH", tmp_path / "README.md")
    mp.setattr(step, "ROOT_DIR", tmp_path)
    mp.setattr(step, "ROADMAP_YAML_PATH", yaml_path)
    return yaml_path


def test_validate_roadmap_dag_and_yaml_loader(tmp_path: Path) -> None:
    """Verify valid roadmaps pass, DAG cycles/self/unknown deps fail, and `_load_roadmap` guards bad YAML."""
    data = _sample_roadmap()
    assert build.validate_roadmap(data) == []

    cyc = copy.deepcopy(data)
    cyc["systems"][0]["depends_on"] = ["beta"]
    assert "Cycle detected" in "\n".join(build.validate_roadmap(cyc))

    self_dep = copy.deepcopy(data)
    self_dep["systems"][0]["depends_on"] = ["alpha"]
    assert "Self-dependency" in "\n".join(build.validate_roadmap(self_dep))

    unk_dep = copy.deepcopy(data)
    unk_dep["systems"][0]["depends_on"] = ["ghost"]
    assert "Unknown dependency 'ghost'" in "\n".join(build.validate_roadmap(unk_dep))

    with pytest.raises(ValueError, match="not found"):
        build._load_roadmap(tmp_path / "missing.yaml")
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("systems: [unclosed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Failed to parse"):
        build._load_roadmap(bad_yaml)
    scalar_yaml = tmp_path / "scalar.yaml"
    scalar_yaml.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        build._load_roadmap(scalar_yaml)


def test_validate_roadmap_schema_and_step_edge_cases() -> None:
    """Verify system, phase, step ID, status/date, verification command, and type checks."""
    d = _sample_roadmap()
    d["systems"][0].update({"id": "BAD_ID", "order": 9, "name": "", "phases": "not_list"})
    d["systems"].append(
        {
            "id": "beta",
            "order": 2,
            "name": "Dup",
            "role": "r",
            "workspace": "w",
            "est_weeks": "1w",
            "graduation_demo": "d",
            "phases": [{}, {"id": "beta-p1", "name": ""}, {"id": "wrong-p2", "name": "ok"}],
        }
    )
    d["systems"].append("not_a_dict")
    d["steps"].extend(
        [
            "bad_step_type",
            {"title": "no id"},
            copy.deepcopy(d["steps"][0]),
            {
                "id": "alpha-03",
                "system": "missing_sys",
                "phase": "beta-p1",
                "mode": "invalid_mode",
                "status": "approved",
                "title": "",
                "first_principles": "fp",
                "reference_reading": "rr",
                "deliverables": [],
                "verification": "",
            },
            {
                "id": "badformat",
                "system": "beta",
                "phase": "missing_phase",
                "mode": "couch",
                "status": "bad_status",
                "title": "t",
                "first_principles": "fp",
                "reference_reading": "rr",
                "deliverables": ["x"],
                "verification": "uv run pytest (prose note)",
            },
            {
                "id": "beta-02",
                "system": "beta",
                "phase": "alpha-p1",
                "mode": "couch",
                "status": "approved",
                "approved_date": "not-a-date",
                "title": "t",
                "first_principles": "fp",
                "reference_reading": "rr",
                "deliverables": ["x"],
                "verification": "pytest_bare_bad",
            },
        ]
    )
    joined = "\n".join(build.validate_roadmap(d))
    for expected in (
        "Invalid system id",
        "Duplicate system id 'beta'",
        "Phase missing 'id'",
        "Duplicate phase id 'beta-p1'",
        "must start with 'beta-'",
        "Duplicate step id 'alpha-01'",
        "missing required 'approved_date'",
        "Invalid approved_date 'not-a-date'",
        "Step numbers must be sequential",
        "Couch step 'verification' must start with",
    ):
        assert expected in joined

    empty_types = {"systems": "bad", "steps": "bad"}
    empty_errs = "\n".join(build.validate_roadmap(empty_types))
    assert "'systems' must be a list" in empty_errs
    assert "'steps' must be a list" in empty_errs


def test_metrics_badges_and_dynamic_markdown_rendering() -> None:
    """Verify progress bars, badge errors, active/completed queues, and dynamic step counts."""
    assert build.render_progress_bar(50.0, width=10) == "█████░░░░░"
    assert build.status_badge("in_review") == "🔍 In Review"
    assert build.mode_badge("couch") == "🛋️ Couch"
    with pytest.raises(ValueError, match="Invalid step mode"):
        build.mode_badge("teleport")

    data = _sample_roadmap()
    data["steps"][0].update(
        {"status": "approved", "approved_date": "2026-11-15", "pr_url": "https://pr/1"}
    )
    data["steps"][1]["status"] = "approved"
    data["steps"][1]["approved_date"] = "2026-11-16"
    metrics = build.compute_metrics(data)
    assert metrics["total_approved"] == 2
    assert metrics["active_step"] is None

    readme = build.render_readme_md(data, metrics)
    roadmap_md = build.render_roadmap_md(data, metrics)
    assert "All 2 steps completed!" in readme
    assert "all 2 step checklists" in readme
    assert "2-part, 2-chapter" in readme
    assert "186" not in readme
    assert "[PR](https://pr/1)" in roadmap_md


def test_build_main_modes_and_invariant_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify build.main() rejects invalid roadmaps before syncing and handles check/write drift."""
    data = _sample_roadmap()
    with monkeypatch.context() as mp:
        yaml_path = _patch_tmp_repo(tmp_path, mp, data)
        # Invalid roadmap fails BEFORE touching sync_book
        sync_called = False

        def spy_sync(*_a: object, **_kw: object) -> tuple[list[Path], list[str]]:
            """Record invocation when verifying sync_all_chapters is skipped."""
            nonlocal sync_called
            sync_called = True
            return [], []

        mp.setattr(sync_book, "sync_all_chapters", spy_sync)
        bad = copy.deepcopy(data)
        bad["systems"][0]["depends_on"] = ["alpha"]
        yaml_path.write_text(yaml.dump(bad, sort_keys=False), encoding="utf-8")
        assert build.main([]) == 1
        assert not sync_called

    with monkeypatch.context() as mp:
        yaml_path = _patch_tmp_repo(tmp_path, mp, data)
        assert build.main(["--check"]) == 1  # Missing ROADMAP.md / README.md
        assert build.main([]) == 0
        assert build.main(["--check"]) == 0

        mp.setattr(sync_book, "sync_all_chapters", lambda *_a, **_kw: ([], ["sync boom"]))
        assert build.main([]) == 1
        mp.setattr(sync_book, "sync_all_chapters", lambda *_a, **_kw: ([], []))
        mp.setattr(check_book, "validate_chapters", lambda *_a, **_kw: (["book boom"], 0, 0))
        assert build.main([]) == 1

        yaml_path.unlink()
        assert build.main(["--check"]) == 1


def test_validate_book_outline_parts_and_chapters() -> None:
    """Verify Roman numerals, part/chapter schema checks, and step-partitioning errors."""
    assert [build._int_to_roman(n) for n in (1, 4, 5, 9, 10)] == ["I", "IV", "V", "IX", "X"]

    no_book = _sample_roadmap()
    no_book["book"] = "bad"
    assert "Missing or invalid top-level 'book'" in "\n".join(build.validate_roadmap(no_book))

    bad_parts = _sample_roadmap()
    bad_parts["book"] = {"parts": []}
    joined = "\n".join(build.validate_roadmap(bad_parts))
    assert "[book] Missing 'title'" in joined
    assert "[book] 'parts' must be a non-empty list" in joined

    d = _sample_roadmap()
    d["book"]["parts"] = [
        "bad_part",
        {"id": "", "number": "IX", "system": "ghost", "chapters": []},
        {
            "id": "part-x",
            "number": "III",
            "system": "alpha",
            "title": "Ok",
            "summary": "Ok",
            "chapters": ["bad_chap", {"id": "", "number": 9, "slug": "bad", "steps": []}],
        },
        {
            "id": "part-x",
            "number": "IV",
            "system": "beta",
            "title": "Dup",
            "summary": "Dup",
            "chapters": [
                {
                    "id": "ch-dup",
                    "number": 3,
                    "slug": "03_beta_drive",
                    "title": "T",
                    "summary": "S",
                    "steps": ["alpha-01", "ghost-01"],
                },
                {
                    "id": "ch-dup",
                    "number": 4,
                    "slug": "04_beta_extra",
                    "title": "T2",
                    "summary": "S2",
                    "steps": ["alpha-01"],
                },
            ],
        },
    ]
    errs = "\n".join(build.validate_roadmap(d))
    for msg in (
        "Part entry #1 must be a mapping",
        "Missing or duplicate part id",
        "Unknown part system 'ghost'",
        "Part 'chapters' must be a non-empty list",
        "Chapter entry #1 must be a mapping",
        "Chapter slug 'bad' must start with '02_'",
        "Chapter 'steps' must be a non-empty list",
        "Missing or duplicate part id 'part-x'",
        "Missing or duplicate chapter id 'ch-dup'",
        "references unknown step 'ghost-01'",
        "belongs to 'alpha', not 'beta'",
        "assigned to multiple chapters",
        "Unmapped steps missing from book chapters",
    ):
        assert msg in errs


def test_validate_book_disk_consistency_and_lookup(tmp_path: Path) -> None:
    """Verify disk chapter registration checks and `step.find_book_chapter` behavior."""
    d = _sample_roadmap()
    chap_dir = tmp_path / "systems" / "alpha" / "chapters"
    chap_dir.mkdir(parents=True)
    registered = chap_dir / "01_alpha_core.md"
    registered.write_text("# Chapter 1\n", encoding="utf-8")
    assert build.validate_roadmap(d, tmp_path) == []

    orphan = chap_dir / "99_orphan.md"
    orphan.write_text("# Orphan\n", encoding="utf-8")
    disk_errs = "\n".join(build.validate_roadmap(d, tmp_path))
    assert "is not registered in book.parts" in disk_errs

    found = step.find_book_chapter(d, "ALPHA-01")
    assert found is not None
    assert found.part["number"] == "I"
    assert found.chapter["number"] == 1
    assert found.step_index == 1
    assert step.find_book_chapter(d, "missing-99") is None


def test_step_cli_lifecycle_and_atomic_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify step.py CLI subcommands, flag validation, and rollback when build.main fails."""
    data = _sample_roadmap()
    with monkeypatch.context() as mp:
        yaml_path = _patch_tmp_repo(tmp_path, mp, data)

        assert step.main(["status"]) == 0
        assert step.main(["status", "alpha"]) == 0
        assert step.main(["status", "unknown_sys"]) == 1
        assert step.main(["next"]) == 0
        next_out = capsys.readouterr().out
        assert "Book Chapter    : Part I · Ch. 1 — Alpha Core" in next_out
        assert "(systems/alpha/chapters/01_alpha_core.md · step 1/1)" in next_out
        assert step.main(["next", "beta"]) == 0
        assert step.main(["next", "unknown_sys"]) == 1

        # Reject empty --pr and unknown step
        assert step.main(["review", "alpha-01", "--pr", "   "]) == 1
        assert step.main(["review", "unknown-99"]) == 1
        assert step.main(["review", "alpha-01", "--pr", "https://example.com/pr/9"]) == 0
        loaded = step.load_roadmap()
        assert loaded["steps"][0]["status"] == "in_review"
        assert loaded["steps"][0]["pr_url"] == "https://example.com/pr/9"

        # Reject invalid approve flags, then approve cleanly
        for bad_args in (
            ["approve", "unknown-99"],
            ["approve", "alpha-01", "--date", "  "],
            ["approve", "alpha-01", "--date", "2026/11/15"],
            ["approve", "alpha-01", "--commit", " "],
        ):
            assert step.main(bad_args) == 1
        assert step.main(["approve", "alpha-01", "--date", "2026-11-15", "--commit", "abc1234"]) == 0

        # Moving approved -> in_review clears approved_date & commit
        assert step.main(["review", "alpha-01"]) == 0
        assert step.load_roadmap()["steps"][0]["approved_date"] is None
        assert step.load_roadmap()["steps"][0]["commit"] is None

        # Approve all steps so `next` reports completion, then reset
        assert step.main(["approve", "alpha-01", "--date", "2026-11-15"]) == 0
        assert step.main(["approve", "beta-01", "--date", "2026-11-15"]) == 0
        capsys.readouterr()
        assert step.main(["next"]) == 0
        assert "All matching steps are approved!" in capsys.readouterr().out
        assert step.main(["reset", "unknown-99"]) == 1
        assert step.main(["reset", "alpha-01"]) == 0

        # save_and_rebuild: invalid roadmap does not mutate disk; failed build.main rolls back
        before = yaml_path.read_text(encoding="utf-8")
        bad_save = copy.deepcopy(data)
        bad_save["steps"][0]["mode"] = "bad_mode"
        assert step.save_and_rebuild(bad_save) == 1
        assert yaml_path.read_text(encoding="utf-8") == before

        mp.setattr(build, "main", lambda _argv=None: 1)
        mutated = copy.deepcopy(data)
        mutated["steps"][0]["title"] = "Should roll back"
        assert step.save_and_rebuild(mutated) == 1
        assert yaml_path.read_text(encoding="utf-8") == before
