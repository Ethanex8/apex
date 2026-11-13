#!/usr/bin/env python3
"""CLI helper for managing Couch-to-Silicon step states in roadmap.yaml."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
import sys
import yaml

sys.dont_write_bytecode = True
import build


ROOT_DIR = Path(__file__).resolve().parent.parent
ROADMAP_YAML_PATH = ROOT_DIR / "roadmap.yaml"


def load_roadmap() -> dict:
    with open(ROADMAP_YAML_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_and_rebuild(data: dict) -> int:
    with open(ROADMAP_YAML_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True, width=110)
    return build.main([])


def find_step(data: dict, step_id: str) -> dict | None:
    target = step_id.strip().lower()
    for st in data.get("steps", []):
        if st["id"].lower() == target:
            return st
    return None


def cmd_status(args: argparse.Namespace) -> int:
    data = load_roadmap()
    metrics = build.compute_metrics(data)
    target_sys = args.system.strip().lower() if args.system else None

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
        print(
            f"[{sys_obj['order']}. {sys_obj['id']}] {sys_obj['name']} ({sm['status']})"
        )
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
    data = load_roadmap()
    target_sys = args.system.strip().lower() if args.system else None
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
    print(f"Title           : {st['title']}")
    print(f"First Principles: {st['first_principles']}")
    print(f"Reference       : {st['reference_reading']}")
    print("Deliverables    :")
    for d in st["deliverables"]:
        print(f"  - {d}")
    print(f"Verification    : {st['verification']}")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    data = load_roadmap()
    st = find_step(data, args.step_id)
    if not st:
        print(f"ERROR: Unknown step '{args.step_id}'", file=sys.stderr)
        return 1
    st["status"] = "in_review"
    if args.pr:
        st["pr_url"] = args.pr
    print(f"Marked [{st['id']}] as in_review" + (f" (PR: {args.pr})" if args.pr else ""))
    return save_and_rebuild(data)


def cmd_approve(args: argparse.Namespace) -> int:
    data = load_roadmap()
    st = find_step(data, args.step_id)
    if not st:
        print(f"ERROR: Unknown step '{args.step_id}'", file=sys.stderr)
        return 1

    adate = args.date or date.today().strftime("%Y-%m-%d")
    try:
        datetime.strptime(adate, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Invalid date '{adate}' (expected YYYY-MM-DD)", file=sys.stderr)
        return 1

    st["status"] = "approved"
    st["approved_date"] = adate
    if args.commit:
        st["commit"] = args.commit
    print(f"Approved [{st['id']}] on {adate}")
    return save_and_rebuild(data)


def cmd_reset(args: argparse.Namespace) -> int:
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


def main() -> int:
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

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
