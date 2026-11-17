#!/usr/bin/env python3
"""CLI helper for managing Couch-to-Silicon step states in roadmap.yaml.

Purpose:
  Provide deterministic subcommands (`status`, `next`, `review`, `approve`, `reset`)
  to inspect and advance atomic steps in `roadmap.yaml` while delegating validation
  and Markdown regeneration to `scripts/build.py`.

Usage:
  python3 scripts/step.py status [system]
  python3 scripts/step.py next [system]
  python3 scripts/step.py review <step-id> [--pr URL]
  python3 scripts/step.py approve <step-id> [--commit SHA] [--date YYYY-MM-DD]
  python3 scripts/step.py reset <step-id>

Outputs:
  Prints status summaries to stdout; updates `roadmap.yaml`, `ROADMAP.md`, and `README.md`
  on state transitions.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path
from typing import NamedTuple

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build  # noqa: E402 — repo scripts run standalone without package install

ROOT_DIR = SCRIPT_DIR.parent
ROADMAP_YAML_PATH = ROOT_DIR / "roadmap.yaml"


class BookChapterMatch(NamedTuple):
    """Matched book part, chapter metadata, and 1-based step position within the chapter."""

    part: dict
    chapter: dict
    step_index: int


def load_roadmap() -> dict:
    """Parse and return `roadmap.yaml` as a Python dictionary."""
    return build._load_roadmap(ROADMAP_YAML_PATH)


def save_and_rebuild(data: dict) -> int:
    """Validate, atomically persist `data` to `roadmap.yaml`, and run `scripts/build.py`."""
    errors = build.validate_roadmap(data)
    if errors:
        print("Roadmap invariant validation FAILED (roadmap.yaml left unchanged):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    backup = ROADMAP_YAML_PATH.read_text(encoding="utf-8") if ROADMAP_YAML_PATH.exists() else None
    with open(ROADMAP_YAML_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True, width=110)

    rc = build.main([])
    if rc != 0:
        if backup is not None:
            ROADMAP_YAML_PATH.write_text(backup, encoding="utf-8")
        else:
            ROADMAP_YAML_PATH.unlink(missing_ok=True)
    return rc


def find_step(data: dict, step_id: str) -> dict | None:
    """Locate a step dictionary in `data['steps']` by case-insensitive ID."""
    target = step_id.strip().lower()
    for st in data.get("steps", []):
        if st["id"].lower() == target:
            return st
    return None


def find_book_chapter(data: dict, step_id: str) -> BookChapterMatch | None:
    """Return `BookChapterMatch` for `step_id`, or None if unmapped."""
    target = step_id.strip().lower()
    for part in (data.get("book") or {}).get("parts") or []:
        for chap in part.get("chapters") or []:
            for idx, sid in enumerate(chap.get("steps") or [], 1):
                if str(sid).lower() == target:
                    return BookChapterMatch(part=part, chapter=chap, step_index=idx)
    return None


def _validate_target_system(data: dict, system_arg: str | None) -> str | None:
    """Return normalized system ID if valid, None if omitted, or raise ValueError if unknown."""
    if not system_arg:
        return None
    target = system_arg.strip().lower()
    valid = {str(s["id"]).lower() for s in data.get("systems") or [] if isinstance(s, dict) and s.get("id")}
    if target not in valid:
        raise ValueError(f"Unknown system '{system_arg}' (expected one of {sorted(valid)})")
    return target


def cmd_status(args: argparse.Namespace) -> int:
    """Print overall and per-system progress metrics across `roadmap.yaml`."""
    data = load_roadmap()
    target_sys = _validate_target_system(data, args.system)
    metrics = build.compute_metrics(data)

    print("=== Apex Couch-to-Silicon Engineering Progress ===")
    print(
        f"Overall : {metrics['total_approved']} / {metrics['total_steps']} steps approved "
        f"({metrics['pct_total']:.1f}%) | "
        f"Couch: {metrics['total_couch_done']}/{metrics['total_couch']} | "
        f"Bench: {metrics['total_bench_done']}/{metrics['total_bench']}"
    )
    if metrics["active_step"]:
        ast = metrics["active_step"]
        print(f"Active  : {ast['id']} [{ast['mode']} | {ast['status']}] — {ast['title']}")
    print()

    for sm in metrics["sys_metrics"]:
        sys_obj = sm["system"]
        if target_sys and sys_obj["id"] != target_sys:
            continue
        bar = build.render_progress_bar(sm["pct"], width=16)
        print(f"[{sys_obj['order']}. {sys_obj['id']}] {sys_obj['name']} ({sm['status']})")
        print(
            f"  Progress : [{bar}] {sm['approved']}/{sm['total']} ({sm['pct']:.1f}%) "
            f"| Couch {sm['couch_done']}/{sm['couch']} | Bench {sm['bench_done']}/{sm['bench']}"
        )
        if sm["next_step"]:
            nxt = sm["next_step"]
            print(f"  Next Up  : {nxt['id']} [{nxt['mode']}] — {nxt['title']}")
        print()
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    """Display metadata, deliverables, and verification gate for the next unapproved step."""
    data = load_roadmap()
    target_sys = _validate_target_system(data, args.system)
    candidates = [
        s
        for s in data.get("steps", [])
        if (not target_sys or s["system"] == target_sys) and s["status"] != "approved"
    ]
    if not candidates:
        print("All matching steps are approved!")
        return 0

    st = next((s for s in candidates if s["status"] == "in_review"), candidates[0])
    print(f"Step ID         : {st['id']} ({st['mode']}, {st['status']})")
    print(f"System / Phase  : {st['system']} / {st['phase']}")
    if chap_info := find_book_chapter(data, st["id"]):
        part, chap, pos = chap_info
        total_in_chap = len(chap.get("steps") or [])
        chap_path = f"systems/{part['system']}/chapters/{chap['slug']}.md"
        print(f"Book Chapter    : Part {part['number']} · Ch. {chap['number']} — {chap['title']}")
        print(f"                  ({chap_path} · step {pos}/{total_in_chap})")
    print(f"Title           : {st['title']}")
    print(f"First Principles: {st['first_principles']}")
    print(f"Reference       : {st['reference_reading']}")
    print("Deliverables    :")
    for d in st["deliverables"]:
        print(f"  - {d}")
    print(f"Verification    : {st['verification']}")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    """Transition `args.step_id` to `in_review`, clearing prior approval fields cleanly."""
    if args.pr is not None and not args.pr.strip():
        print("ERROR: --pr URL cannot be empty", file=sys.stderr)
        return 1
    data = load_roadmap()
    st = find_step(data, args.step_id)
    if not st:
        print(f"ERROR: Unknown step '{args.step_id}'", file=sys.stderr)
        return 1
    st["status"] = "in_review"
    st["approved_date"] = None
    st["commit"] = None
    if args.pr:
        st["pr_url"] = args.pr.strip()
    print(f"Marked [{st['id']}] as in_review" + (f" (PR: {st['pr_url']})" if args.pr else ""))
    return save_and_rebuild(data)


def cmd_approve(args: argparse.Namespace) -> int:
    """Mark `args.step_id` as `approved` with a validated `YYYY-MM-DD` date."""
    if args.date is not None and not args.date.strip():
        print("ERROR: --date cannot be empty (expected YYYY-MM-DD)", file=sys.stderr)
        return 1
    if args.commit is not None and not args.commit.strip():
        print("ERROR: --commit SHA cannot be empty", file=sys.stderr)
        return 1
    data = load_roadmap()
    st = find_step(data, args.step_id)
    if not st:
        print(f"ERROR: Unknown step '{args.step_id}'", file=sys.stderr)
        return 1

    adate = args.date.strip() if args.date else date.today().strftime("%Y-%m-%d")
    try:
        datetime.strptime(adate, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Invalid date '{adate}' (expected YYYY-MM-DD)", file=sys.stderr)
        return 1

    st["status"] = "approved"
    st["approved_date"] = adate
    if args.commit:
        st["commit"] = args.commit.strip()
    print(f"Approved [{st['id']}] on {adate}")
    return save_and_rebuild(data)


def cmd_reset(args: argparse.Namespace) -> int:
    """Reset `args.step_id` back to `pending` and clear review/approval metadata."""
    data = load_roadmap()
    st = find_step(data, args.step_id)
    if not st:
        print(f"ERROR: Unknown step '{args.step_id}'", file=sys.stderr)
        return 1
    st["status"] = "pending"
    st["pr_url"] = None
    st["commit"] = None
    st["approved_date"] = None
    print(f"Reset [{st['id']}] to pending")
    return save_and_rebuild(data)


def main(argv: list[str] | None = None) -> int:
    """Parse CLI subcommands and dispatch step lifecycle updates."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status", help="Show progress across systems")
    p_status.add_argument("system", nargs="?", help="Optional system id (e.g. brain)")
    p_status.set_defaults(func=cmd_status)

    p_next = sub.add_parser("next", help="Show details of the next unapproved step")
    p_next.add_argument("system", nargs="?", help="Optional system id (e.g. brain)")
    p_next.set_defaults(func=cmd_next)

    p_review = sub.add_parser("review", help="Mark a step as in_review after passing verification")
    p_review.add_argument("step_id", help="Step ID (e.g. brain-01)")
    p_review.add_argument("--pr", help="Optional GitHub PR URL")
    p_review.set_defaults(func=cmd_review)

    p_approve = sub.add_parser("approve", help="Mark a step as approved after explicit LGTM")
    p_approve.add_argument("step_id", help="Step ID (e.g. brain-01)")
    p_approve.add_argument("--commit", help="Optional commit SHA")
    p_approve.add_argument("--date", help="Approval date YYYY-MM-DD (defaults to today)")
    p_approve.set_defaults(func=cmd_approve)

    p_reset = sub.add_parser("reset", help="Reset a step back to pending")
    p_reset.add_argument("step_id", help="Step ID (e.g. brain-01)")
    p_reset.set_defaults(func=cmd_reset)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
