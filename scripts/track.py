#!/usr/bin/env python3
"""CLI helper for tracking section-level progress in progress.yaml and regenerating curriculum docs."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
import re
import sys
import yaml

sys.dont_write_bytecode = True
import build


ROOT_DIR = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT_DIR / "curriculum.yaml"
PROGRESS_YAML_PATH = ROOT_DIR / "progress.yaml"


def load_data() -> tuple[dict, dict]:
    with open(YAML_PATH, encoding="utf-8") as f:
        curriculum_data = yaml.safe_load(f)
    with open(PROGRESS_YAML_PATH, encoding="utf-8") as f:
        progress_data = yaml.safe_load(f)
    return curriculum_data, progress_data


def save_and_rebuild(progress_data: dict) -> int:
    with open(PROGRESS_YAML_PATH, "w", encoding="utf-8") as f:
        yaml.dump(progress_data, f, sort_keys=False, allow_unicode=True, width=100)
    return build.main([])


def expand_section_tokens(tokens: list[str], available_ids: list[str]) -> list[str]:
    """Expand section tokens (including ranges like '1.1-1.4' or 'A-D') against available section IDs."""
    expanded: list[str] = []
    id_index = {sid: idx for idx, sid in enumerate(available_ids)}
    for tok in tokens:
        tok = tok.strip()
        if tok in id_index:
            expanded.append(tok)
            continue
        m = re.match(r"^([A-Za-z0-9.]+)[–-]([A-Za-z0-9.]+)$", tok)
        if m:
            start_id, end_id = m.group(1), m.group(2)
            if start_id in id_index and end_id in id_index:
                s_idx, e_idx = id_index[start_id], id_index[end_id]
                if s_idx <= e_idx:
                    expanded.extend(available_ids[s_idx : e_idx + 1])
                    continue
        raise ValueError(
            f"Unknown section or range '{tok}'. Available sections: {', '.join(available_ids[:10])}..."
        )
    return expanded


def sync_course_status(cprog: dict) -> None:
    """Automatically update course status based on completed section counts."""
    total = 0
    done = 0
    for pt in cprog.get("texts", []):
        for u in pt.get("sections_or_units", pt.get("units", [])):
            for s in u.get("sections", []):
                total += 1
                if s.get("completed"):
                    done += 1
    if total > 0:
        if done == total:
            cprog["status"] = "completed"
        elif done > 0:
            cprog["status"] = "in_progress"
        elif cprog.get("status") == "completed":
            cprog["status"] = "in_progress"


def cmd_start(args: argparse.Namespace) -> int:
    _, progress_data = load_data()
    cid = args.course.strip().upper()
    prog_courses = progress_data.get("courses", {})
    if cid not in prog_courses:
        print(f"ERROR: Course '{cid}' does not have a TOC entry in progress.yaml yet.", file=sys.stderr)
        return 1

    cprog = prog_courses[cid]
    if cprog.get("status") == "completed":
        print(f"Course [{cid}] is already completed.")
        return 0

    cprog["status"] = "in_progress"
    print(f"Marked [{cid}] status as in_progress")
    return save_and_rebuild(progress_data)


def cmd_done(args: argparse.Namespace) -> int:
    _, progress_data = load_data()
    cid = args.course.strip().upper()
    prog_courses = progress_data.get("courses", {})
    if cid not in prog_courses:
        print(f"ERROR: Course '{cid}' does not have a TOC entry in progress.yaml yet.", file=sys.stderr)
        return 1

    # Validate date
    cdate = args.date or date.today().strftime("%Y-%m-%d")
    try:
        datetime.strptime(cdate, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Invalid date '{cdate}' (expected YYYY-MM-DD).", file=sys.stderr)
        return 1

    cprog = prog_courses[cid]
    sec_by_id: dict[str, dict] = {}
    ordered_ids: list[str] = []
    for pt in cprog.get("texts", []):
        for u in pt.get("units", []):
            for s in u.get("sections", []):
                sid = str(s["id"])
                sec_by_id[sid] = s
                ordered_ids.append(sid)

    try:
        target_ids = expand_section_tokens(args.sections, ordered_ids)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for sid in target_ids:
        sec_by_id[sid]["completed"] = True
        sec_by_id[sid]["completed_date"] = cdate
        print(f"Marked [{cid}] Section {sid} ({sec_by_id[sid]['title']}) completed on {cdate}")

    sync_course_status(cprog)
    return save_and_rebuild(progress_data)


def cmd_undo(args: argparse.Namespace) -> int:
    _, progress_data = load_data()
    cid = args.course.strip().upper()
    prog_courses = progress_data.get("courses", {})
    if cid not in prog_courses:
        print(f"ERROR: Course '{cid}' not found in progress.yaml.", file=sys.stderr)
        return 1

    cprog = prog_courses[cid]
    sec_by_id: dict[str, dict] = {}
    ordered_ids: list[str] = []
    for pt in cprog.get("texts", []):
        for u in pt.get("units", []):
            for s in u.get("sections", []):
                sid = str(s["id"])
                sec_by_id[sid] = s
                ordered_ids.append(sid)

    try:
        target_ids = expand_section_tokens(args.sections, ordered_ids)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for sid in target_ids:
        sec_by_id[sid]["completed"] = False
        sec_by_id[sid]["completed_date"] = None
        print(f"Reset [{cid}] Section {sid} ({sec_by_id[sid]['title']}) to incomplete")

    sync_course_status(cprog)
    return save_and_rebuild(progress_data)


def cmd_status(args: argparse.Namespace) -> int:
    curriculum_data, progress_data = load_data()
    metrics = build.compute_progress_metrics(curriculum_data, progress_data)

    print("=== Apex Curriculum Progress Summary ===")
    print(
        f"Timeline         : {metrics['start_date']} -> {metrics['as_of_date']} ({metrics['elapsed_days']} active days)"
    )
    print(
        f"Overall Velocity : {metrics['overall_velocity']:.2f} sections/day ({metrics['overall_velocity'] * 7:.1f} sections/week)"
    )
    print(
        f"Assigned Units   : {metrics['total_units_done']:.2f} / {metrics['total_units']} ({metrics['pct_units']:.2f}%)"
    )
    print(
        f"Total Sections   : {metrics['total_sec_done']} / ~{metrics['total_sec_estimated']:,} ({metrics['pct_sections']:.2f}%)"
    )
    print(
        f"Full Forecast    : {metrics['curriculum_eta_date']} ({metrics['curriculum_eta_days']:,} days remaining)"
    )
    print()

    target_cids = (
        [args.course.strip().upper()]
        if args.course
        else [
            cid
            for cid, cm in metrics["course_metrics"].items()
            if cm["has_toc"] or cm["status"] != "not_started"
        ]
    )

    for cid in target_cids:
        cm = metrics["course_metrics"].get(cid)
        if not cm:
            print(f"Unknown course '{cid}'", file=sys.stderr)
            return 1
        bar = build.render_progress_bar(cm["pct_sections"], width=20)
        print(f"[{cid}] {cm['title']} ({cm['status']})")
        print(
            f"  Sections : [{bar}] {cm['sec_done']}/{cm['sec_total']} ({cm['pct_sections']:.1f}%)"
        )
        print(
            f"  Units    : {cm['units_done']:.2f}/{cm['total_units']} ({cm['pct_units']:.1f}%)"
        )
        if cm["status"] == "not_started" and cm.get("study_days") != cm["eta_days"]:
            print(
                f"  ETA      : {cm['eta_date']} (~{cm['study_days']} study days; {cm['eta_days']}d total after prerequisites)"
            )
        else:
            print(f"  ETA      : {cm['eta_date']} ({cm['eta_days']} days remaining)")
        if cm["next_section"]:
            nxt = cm["next_section"]
            print(f"  Next Up  : {nxt['id']} - {nxt['title']} ({nxt['unit']})")
        print()
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    _, progress_data = load_data()
    prog_courses = progress_data.get("courses", {})
    cid = (args.course or "MATH 101").strip().upper()
    if cid not in prog_courses:
        print(f"ERROR: Course '{cid}' does not have a TOC in progress.yaml.", file=sys.stderr)
        return 1

    cprog = prog_courses[cid]
    upcoming: list[tuple[str, str, str]] = []
    for pt in cprog.get("texts", []):
        for u in pt.get("units", []):
            for s in u.get("sections", []):
                if not s.get("completed"):
                    upcoming.append((u["unit"], str(s["id"]), str(s["title"])))
                    if len(upcoming) >= args.limit:
                        break
            if len(upcoming) >= args.limit:
                break

    print(f"Next {len(upcoming)} uncompleted sections for {cid}:")
    for unit_lbl, sid, stitle in upcoming:
        print(f"  - [{unit_lbl}] {sid}: {stitle}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser("start", help="Mark a course as in_progress")
    p_start.add_argument("course", help="Course ID, e.g. 'ENGR 101'")
    p_start.set_defaults(func=cmd_start)

    p_done = sub.add_parser("done", help="Mark one or more sections (or ranges like 1.1-1.4) as completed")
    p_done.add_argument("course", help="Course ID, e.g. 'MATH 101'")
    p_done.add_argument("sections", nargs="+", help="Section IDs or ranges, e.g. 1.5 or 2.1-2.3")
    p_done.add_argument("--date", help="Completion date (YYYY-MM-DD); defaults to today")
    p_done.set_defaults(func=cmd_done)

    p_undo = sub.add_parser("undo", help="Mark one or more sections as incomplete")
    p_undo.add_argument("course", help="Course ID, e.g. 'MATH 101'")
    p_undo.add_argument("sections", nargs="+", help="Section IDs or ranges")
    p_undo.set_defaults(func=cmd_undo)

    p_status = sub.add_parser("status", help="Show curriculum and course progress & forecasts")
    p_status.add_argument("course", nargs="?", help="Optional Course ID to inspect")
    p_status.set_defaults(func=cmd_status)

    p_next = sub.add_parser("next", help="List upcoming uncompleted sections for a course")
    p_next.add_argument("course", nargs="?", default="MATH 101", help="Course ID (default: MATH 101)")
    p_next.add_argument("--limit", type=int, default=5, help="Number of upcoming sections to list")
    p_next.set_defaults(func=cmd_next)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
