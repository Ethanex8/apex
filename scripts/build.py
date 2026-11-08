#!/usr/bin/env python3
"""Validate curriculum.yaml and progress.yaml against GEMINI.md invariants and generate CURRICULUM.md, PROGRESS.md, and README.md."""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
import math
from pathlib import Path
import re
import sys
import yaml


ROOT_DIR = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT_DIR / "curriculum.yaml"
PROGRESS_YAML_PATH = ROOT_DIR / "progress.yaml"
CURRICULUM_MD_PATH = ROOT_DIR / "CURRICULUM.md"
PROGRESS_MD_PATH = ROOT_DIR / "PROGRESS.md"
README_MD_PATH = ROOT_DIR / "README.md"


def parse_int_ranges(spec: str | int | None) -> list[int]:
    """Parse a chapter/part range string like '1-11, 15' into a list of integers."""
    if spec is None or spec == "":
        return []
    spec_str = str(spec)
    nums: list[int] = []
    for m in re.finditer(r"(\d+)(?:[–-](\d+))?", spec_str):
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        if end < start:
            raise ValueError(f"Descending range '{m.group(0)}' in '{spec_str}'")
        nums.extend(range(start, end + 1))
    return nums


def parse_letter_ranges(spec: str | None) -> list[str]:
    """Parse an appendix range string like 'A-E' into a list of uppercase letters."""
    if not spec:
        return []
    letters: list[str] = []
    for m in re.finditer(r"([A-Z])(?:[–-]([A-Z]))?", spec):
        start = ord(m.group(1))
        end = ord(m.group(2)) if m.group(2) else start
        letters.extend(chr(c) for c in range(start, end + 1))
    return letters


def extract_scope_parts(scope: str) -> tuple[list[int], list[int], list[str], list[str], list[str]]:
    """Extract (assigned_nums, skipped_nums, assigned_apps, skipped_apps, referenced_courses) from a scope string."""
    if "; skip" in scope:
        assigned_str, skip_str = scope.split("; skip", 1)
    else:
        assigned_str, skip_str = scope, ""

    refs = re.findall(r"\b[A-Z]{2,4} \d{3}\b", skip_str)

    # Strip course IDs (e.g. MATH 102) and dimension tokens (e.g. 3D) before extracting chapter numbers
    assigned_clean = re.sub(r"\b(?:[A-Z]{2,4} \d{3}|\d+D)\b", "", assigned_str)
    skip_clean = re.sub(r"\b(?:[A-Z]{2,4} \d{3}|\d+D)\b", "", skip_str)

    a_nums = parse_int_ranges(assigned_clean)
    s_nums = parse_int_ranges(skip_clean)

    app_a_match = re.search(r"Appendices ([A-Z][–-][A-Z])", assigned_str)
    app_s_match = re.search(r"Appendices ([A-Z][–-][A-Z])", skip_str)
    a_apps = parse_letter_ranges(app_a_match.group(1) if app_a_match else None)
    s_apps = parse_letter_ranges(app_s_match.group(1) if app_s_match else None)

    return a_nums, s_nums, a_apps, s_apps, refs


def validate_textbook_unit(
    cid: str,
    book_title: str,
    unit_obj: dict,
    all_course_ids: set[str],
    shared_book_totals: dict[str, int],
    errors: list[str],
) -> None:
    """Validate a single textbook or volume entry against GEMINI.md textbook invariants."""
    total = unit_obj.get("total_units")
    if not isinstance(total, int) or total < 1:
        errors.append(f"[{cid}] '{book_title}': invalid total_units={total}")
        return

    book_key = f"{book_title}::{unit_obj.get('volume', '')}"
    if book_key in shared_book_totals and shared_book_totals[book_key] != total:
        errors.append(
            f"[{cid}] '{book_title}': inconsistent total_units={total} "
            f"(previously declared as {shared_book_totals[book_key]})"
        )
    shared_book_totals[book_key] = total

    assigned_nums = parse_int_ranges(unit_obj.get("assigned"))
    skipped_nums = parse_int_ranges(unit_obj.get("skipped"))
    partial_overlap = set(unit_obj.get("partial_overlap_chapters", []))

    expected_set = set(range(1, total + 1))
    union_set = set(assigned_nums) | set(skipped_nums)
    missing = sorted(expected_set - union_set)
    extra = sorted(union_set - expected_set)
    overlap = sorted((set(assigned_nums) & set(skipped_nums)) - partial_overlap)

    if missing:
        errors.append(
            f"[{cid}] '{book_title}': unmentioned chapter gap(s) {missing} in 1..{total}"
        )
    if extra:
        errors.append(
            f"[{cid}] '{book_title}': chapter(s) {extra} exceed total_units={total}"
        )
    if overlap:
        errors.append(
            f"[{cid}] '{book_title}': overlapping assigned and skipped chapter(s) {overlap}"
        )

    # Cross-check prose scope against structured fields
    scope = unit_obj.get("scope", "")
    if not scope:
        errors.append(f"[{cid}] '{book_title}': missing 'scope' string")
        return

    if "(or " in scope.lower():
        errors.append(f"[{cid}] '{book_title}': prohibited optional '(or ...)' clutter in scope")

    s_a_nums, s_s_nums, s_a_apps, s_s_apps, s_refs = extract_scope_parts(scope)
    if sorted(set(s_a_nums)) != sorted(set(assigned_nums)):
        errors.append(
            f"[{cid}] '{book_title}': scope assigned chapters {sorted(set(s_a_nums))} "
            f"!= structured assigned {sorted(set(assigned_nums))}"
        )
    if sorted(set(s_s_nums)) != sorted(set(skipped_nums)):
        errors.append(
            f"[{cid}] '{book_title}': scope skipped chapters {sorted(set(s_s_nums))} "
            f"!= structured skipped {sorted(set(skipped_nums))}"
        )

    # Check appendices partition if present
    a_apps = parse_letter_ranges(unit_obj.get("assigned_appendices"))
    s_apps = parse_letter_ranges(unit_obj.get("skipped_appendices"))
    if a_apps or s_apps or s_a_apps or s_s_apps:
        if a_apps != s_a_apps or s_apps != s_s_apps:
            errors.append(
                f"[{cid}] '{book_title}': appendix mismatch between structured fields and scope"
            )
        all_apps = set(a_apps) | set(s_apps)
        max_app = max(all_apps)
        expected_apps = {chr(c) for c in range(ord("A"), ord(max_app) + 1)}
        if all_apps != expected_apps or (set(a_apps) & set(s_apps)):
            errors.append(
                f"[{cid}] '{book_title}': appendices do not cleanly partition A..{max_app}"
            )

    declared_refs = unit_obj.get("covered_in", [])
    if declared_refs != s_refs:
        errors.append(
            f"[{cid}] '{book_title}': covered_in {declared_refs} != scope references {s_refs}"
        )
    for ref_cid in declared_refs:
        if ref_cid not in all_course_ids:
            errors.append(
                f"[{cid}] '{book_title}': references unknown course '{ref_cid}' in covered_in"
            )


def expected_unit_labels_for_text(t: dict) -> list[str]:
    """Return the canonical ordered list of assigned unit labels (e.g. 'Ch. 1', 'App. A') for a curriculum textbook entry."""
    labels: list[str] = []
    if "volumes" in t:
        for v in t["volumes"]:
            vol_prefix = f"{v['volume']} "
            unit_prefix = v.get("unit", "Ch.")
            for n in parse_int_ranges(v.get("assigned")):
                labels.append(f"{vol_prefix}{unit_prefix} {n}")
            for app in parse_letter_ranges(v.get("assigned_appendices")):
                labels.append(f"{vol_prefix}App. {app}")
    else:
        unit_prefix = t.get("unit", "Ch.")
        for n in parse_int_ranges(t.get("assigned")):
            labels.append(f"{unit_prefix} {n}")
        for app in parse_letter_ranges(t.get("assigned_appendices")):
            labels.append(f"App. {app}")
    return labels


def parse_iso_date(val: str | None, context: str, errors: list[str]) -> date | None:
    """Validate and parse an ISO YYYY-MM-DD date string."""
    if val is None:
        return None
    if not isinstance(val, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", val):
        errors.append(f"{context}: invalid ISO date '{val}' (expected YYYY-MM-DD)")
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d").date()
    except ValueError as exc:
        errors.append(f"{context}: invalid calendar date '{val}': {exc}")
        return None


def validate_progress(curriculum_data: dict, progress_data: dict) -> list[str]:
    """Validate progress.yaml against curriculum.yaml textbook scopes and date/status invariants."""
    errors: list[str] = []
    if not isinstance(progress_data, dict):
        return ["progress.yaml root must be a mapping"]

    settings = progress_data.get("settings", {})
    if settings.get("started_date") is not None:
        parse_iso_date(str(settings["started_date"]), "[settings.started_date]", errors)
    window = settings.get("rolling_window_days", 30)
    if not isinstance(window, int) or window < 1:
        errors.append(f"[settings.rolling_window_days] must be a positive integer, got {window}")

    course_by_id = {c["id"]: c for c in curriculum_data.get("courses", [])}
    prog_courses = progress_data.get("courses", {})
    if not isinstance(prog_courses, dict):
        errors.append("[progress.yaml] 'courses' must be a mapping")
        return errors

    valid_statuses = {"not_started", "in_progress", "completed"}

    for cid, cprog in prog_courses.items():
        if cid not in course_by_id:
            errors.append(f"[progress.yaml::{cid}] Unknown course ID (not in curriculum.yaml)")
            continue

        status = cprog.get("status")
        if status not in valid_statuses:
            errors.append(
                f"[progress.yaml::{cid}] Invalid status '{status}', expected one of {sorted(valid_statuses)}"
            )

        curr_texts = {t["title"]: t for t in course_by_id[cid].get("texts", [])}
        prog_texts = cprog.get("texts", [])
        total_sections = 0
        completed_sections = 0

        for pt in prog_texts:
            btitle = pt.get("title", "")
            if btitle not in curr_texts:
                errors.append(
                    f"[progress.yaml::{cid}] Textbook '{btitle}' does not match any assigned textbook in curriculum.yaml"
                )
                continue

            expected_units = expected_unit_labels_for_text(curr_texts[btitle])
            units = pt.get("units", [])
            if not units:
                continue

            actual_units = [u.get("unit", "") for u in units]
            if actual_units != expected_units:
                missing_u = [u for u in expected_units if u not in set(actual_units)]
                extra_u = [u for u in actual_units if u not in set(expected_units)]
                errors.append(
                    f"[progress.yaml::{cid}] '{btitle}' units do not match curriculum.yaml assigned scope "
                    f"(missing={missing_u}, extra={extra_u})"
                )

            seen_sec_ids: set[str] = set()
            for u in units:
                ulabel = u.get("unit", "?")
                utitle = u.get("title", "")
                if not utitle:
                    errors.append(f"[progress.yaml::{cid}::{ulabel}] Missing unit title")
                secs = u.get("sections", [])
                if not secs:
                    errors.append(f"[progress.yaml::{cid}::{ulabel}] Unit must have at least 1 section")
                for s in secs:
                    sid = str(s.get("id", "")).strip()
                    stitle = str(s.get("title", "")).strip()
                    comp = s.get("completed")
                    cdate = s.get("completed_date")

                    if not sid:
                        errors.append(f"[progress.yaml::{cid}::{ulabel}] Section missing 'id'")
                    elif sid in seen_sec_ids:
                        errors.append(
                            f"[progress.yaml::{cid}::{ulabel}] Duplicate section id '{sid}' in '{btitle}'"
                        )
                    seen_sec_ids.add(sid)

                    if not stitle:
                        errors.append(
                            f"[progress.yaml::{cid}::{ulabel}::{sid}] Section missing 'title'"
                        )
                    if not isinstance(comp, bool):
                        errors.append(
                            f"[progress.yaml::{cid}::{ulabel}::{sid}] 'completed' must be boolean, got {comp!r}"
                        )
                    if comp is True:
                        if cdate is None:
                            errors.append(
                                f"[progress.yaml::{cid}::{ulabel}::{sid}] 'completed_date' required when completed=true"
                            )
                        else:
                            parse_iso_date(
                                str(cdate),
                                f"[progress.yaml::{cid}::{ulabel}::{sid}]",
                                errors,
                            )
                        completed_sections += 1
                    elif comp is False and cdate is not None:
                        errors.append(
                            f"[progress.yaml::{cid}::{ulabel}::{sid}] 'completed_date' must be null when completed=false"
                        )
                    total_sections += 1

        if total_sections > 0:
            if completed_sections == total_sections and status != "completed":
                errors.append(
                    f"[progress.yaml::{cid}] All {total_sections} sections are completed, so status must be 'completed' (got '{status}')"
                )
            elif 0 < completed_sections < total_sections and status != "in_progress":
                errors.append(
                    f"[progress.yaml::{cid}] {completed_sections}/{total_sections} sections completed, so status must be 'in_progress' (got '{status}')"
                )
            elif completed_sections == 0 and status == "completed":
                errors.append(
                    f"[progress.yaml::{cid}] 0/{total_sections} sections completed, cannot have status='completed'"
                )

    return errors


def validate_curriculum(data: dict) -> list[str]:
    """Validate all GEMINI.md invariants on the loaded curriculum data."""
    errors: list[str] = []
    courses = data.get("courses", [])
    capstones = data.get("capstones", [])

    course_by_id: dict[str, dict] = {}
    node_to_id: dict[str, str] = {}

    for c in courses:
        cid = c["id"]
        nid = c["node_id"]
        if cid in course_by_id:
            errors.append(f"Duplicate course id: {cid}")
        if nid in node_to_id:
            errors.append(f"Duplicate node_id: {nid}")
        course_by_id[cid] = c
        node_to_id[nid] = cid

    all_course_ids = set(course_by_id.keys())
    capstone_ids = {cap["id"] for cap in capstones}
    all_graph_ids = all_course_ids | capstone_ids

    # Build directed graph for DAG & Capstone convergence checks
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {gid: 0 for gid in all_graph_ids}

    shared_book_totals: dict[str, int] = {}

    for c in courses:
        cid = c["id"]
        prereqs = c.get("prerequisites", [])
        coreqs = c.get("corequisites", [])
        if prereqs and coreqs:
            errors.append(f"[{cid}] Cannot have both prerequisites and corequisites in current schema")

        for p in prereqs + coreqs:
            if p not in all_course_ids:
                errors.append(f"[{cid}] Unknown prerequisite/corequisite '{p}'")
            else:
                adj[p].append(cid)
                in_degree[cid] += 1

        texts = c.get("texts", [])
        if not (1 <= len(texts) <= 2):
            errors.append(
                f"[{cid}] Must have 1 textbook (or 2 for theory + lab guide), found {len(texts)}"
            )

        for t in texts:
            btitle = t.get("title", "")
            if "volumes" in t:
                for vol in t["volumes"]:
                    validate_textbook_unit(
                        cid, btitle, vol, all_course_ids, shared_book_totals, errors
                    )
            else:
                validate_textbook_unit(
                    cid, btitle, t, all_course_ids, shared_book_totals, errors
                )

    for cap in capstones:
        cap_id = cap["id"]
        unlocks = cap.get("unlocking_courses", [])
        if not unlocks:
            errors.append(f"[{cap_id}] Capstone has no unlocking_courses")
        for u in unlocks:
            if u not in all_graph_ids:
                errors.append(f"[{cap_id}] Unknown unlocking course/capstone '{u}'")
            else:
                adj[u].append(cap_id)
                in_degree[cap_id] += 1

    # 1. Check DAG acyclicity (Kahn's algorithm)
    q = deque([gid for gid, deg in in_degree.items() if deg == 0])
    visited_count = 0
    while q:
        curr = q.popleft()
        visited_count += 1
        for nxt in adj[curr]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                q.append(nxt)

    if visited_count != len(all_graph_ids):
        errors.append("Cycle detected in curriculum prerequisite/capstone DAG!")

    # 2. Check Zero Dangling Leaf Courses (every course must reach at least one Capstone C1..C8)
    rev_adj: dict[str, list[str]] = defaultdict(list)
    for src, dsts in adj.items():
        for dst in dsts:
            rev_adj[dst].append(src)

    reachable_from_capstones: set[str] = set(capstone_ids)
    rq = deque(capstone_ids)
    while rq:
        curr = rq.popleft()
        for prev in rev_adj[curr]:
            if prev not in reachable_from_capstones:
                reachable_from_capstones.add(prev)
                rq.append(prev)

    dangling_courses = sorted(all_course_ids - reachable_from_capstones)
    if dangling_courses:
        errors.append(
            f"Dangling leaf course(s) with no path to any Capstone: {dangling_courses}"
        )

    return errors


def count_course_assigned_units(c: dict) -> tuple[int, int]:
    """Return (assigned_chapters_count, assigned_appendices_count) for a course in curriculum.yaml."""
    ch_count = 0
    app_count = 0
    for t in c.get("texts", []):
        if "volumes" in t:
            for v in t["volumes"]:
                ch_count += len(parse_int_ranges(v.get("assigned")))
                app_count += len(parse_letter_ranges(v.get("assigned_appendices")))
        else:
            ch_count += len(parse_int_ranges(t.get("assigned")))
            app_count += len(parse_letter_ranges(t.get("assigned_appendices")))
    return ch_count, app_count


def compute_progress_metrics(curriculum_data: dict, progress_data: dict) -> dict:
    """Compute course, tier, and curriculum-wide progress and forecasting metrics."""
    courses = curriculum_data["courses"]
    capstones = curriculum_data["capstones"]
    tiers = curriculum_data["tiers"]
    prog_courses = progress_data.get("courses", {})
    settings = progress_data.get("settings", {})
    rolling_window_days = int(settings.get("rolling_window_days", 30))

    # 1. Empirical sections-per-chapter and sections-per-appendix across all populated units
    populated_ch_units = 0
    populated_ch_sections = 0
    populated_app_units = 0
    populated_app_sections = 0

    all_completion_events: list[dict] = []

    for cid, cprog in prog_courses.items():
        for pt in cprog.get("texts", []):
            for u in pt.get("units", []):
                ulabel = u["unit"]
                secs = u.get("sections", [])
                if "App." in ulabel:
                    populated_app_units += 1
                    populated_app_sections += len(secs)
                else:
                    populated_ch_units += 1
                    populated_ch_sections += len(secs)
                for s in secs:
                    if s.get("completed") and s.get("completed_date"):
                        all_completion_events.append(
                            {
                                "date": str(s["completed_date"]),
                                "date_obj": datetime.strptime(
                                    str(s["completed_date"]), "%Y-%m-%d"
                                ).date(),
                                "course_id": cid,
                                "unit": ulabel,
                                "unit_title": u["title"],
                                "section_id": str(s["id"]),
                                "section_title": str(s["title"]),
                            }
                        )

    avg_sec_per_ch = (
        populated_ch_sections / populated_ch_units if populated_ch_units > 0 else 7.0
    )
    avg_sec_per_app = (
        populated_app_sections / populated_app_units if populated_app_units > 0 else 1.0
    )

    # Sort completion events chronologically (then by course/section)
    all_completion_events.sort(key=lambda e: (e["date"], e["course_id"], e["section_id"]))

    # 2. Per-course stats
    course_metrics: dict[str, dict] = {}
    for c in courses:
        cid = c["id"]
        ch_count, app_count = count_course_assigned_units(c)
        total_units = ch_count + app_count
        cprog = prog_courses.get(cid)
        has_toc = False
        if cprog and any(pt.get("units") for pt in cprog.get("texts", [])):
            has_toc = True

        if has_toc:
            status = cprog.get("status", "not_started")
            sec_total = 0
            sec_done = 0
            units_done_equiv = 0.0
            next_section = None
            for pt in cprog.get("texts", []):
                for u in pt.get("units", []):
                    secs = u.get("sections", [])
                    u_total = len(secs)
                    u_done = sum(1 for s in secs if s.get("completed"))
                    sec_total += u_total
                    sec_done += u_done
                    if u_total > 0:
                        units_done_equiv += u_done / u_total
                    for s in secs:
                        if not s.get("completed") and next_section is None:
                            next_section = {
                                "unit": u["unit"],
                                "id": str(s["id"]),
                                "title": str(s["title"]),
                            }
        else:
            status = cprog.get("status", "not_started") if cprog else "not_started"
            sec_total = round(ch_count * avg_sec_per_ch + app_count * avg_sec_per_app)
            sec_done = 0
            units_done_equiv = 0.0
            next_section = None

        course_metrics[cid] = {
            "id": cid,
            "node_id": c["node_id"],
            "title": c["title"],
            "tier": c["tier"],
            "track": c.get("track"),
            "status": status,
            "has_toc": has_toc,
            "ch_count": ch_count,
            "app_count": app_count,
            "total_units": total_units,
            "units_done": units_done_equiv,
            "sec_done": sec_done,
            "sec_total": sec_total,
            "sec_remaining": max(0, sec_total - sec_done),
            "pct_sections": (sec_done / sec_total * 100.0) if sec_total > 0 else 0.0,
            "pct_units": (units_done_equiv / total_units * 100.0) if total_units > 0 else 0.0,
            "next_section": next_section,
        }

    # 3. Determine DAG node states (completed, in_progress, unlocked, locked)
    node_states: dict[str, str] = {}
    for c in courses:
        cid = c["id"]
        cm = course_metrics[cid]
        if cm["status"] == "completed":
            node_states[cid] = "completed"
        elif cm["status"] == "in_progress":
            node_states[cid] = "in_progress"
        else:
            prereqs = c.get("prerequisites", [])
            coreqs = c.get("corequisites", [])
            prereqs_ok = all(course_metrics[p]["status"] == "completed" for p in prereqs)
            coreqs_ok = all(
                course_metrics[co]["status"] in ("completed", "in_progress") for co in coreqs
            )
            node_states[cid] = "unlocked" if (prereqs_ok and coreqs_ok) else "locked"
        cm["dag_state"] = node_states[cid]

    capstone_states: dict[str, str] = {}
    for cap in capstones:
        cap_id = cap["id"]
        unlocks = cap.get("unlocking_courses", [])
        all_ready = all(
            (capstone_states.get(u) == "completed" if is_capstone_id(u) else node_states.get(u) == "completed")
            for u in unlocks
        )
        capstone_states[cap_id] = "unlocked" if all_ready else "locked"

    # 4. Velocity & Date Calculations
    total_completed_sections = sum(cm["sec_done"] for cm in course_metrics.values())
    total_estimated_sections = sum(cm["sec_total"] for cm in course_metrics.values())
    total_units_all = sum(cm["total_units"] for cm in course_metrics.values())
    total_units_done = sum(cm["units_done"] for cm in course_metrics.values())

    if all_completion_events:
        earliest_event_date = min(e["date_obj"] for e in all_completion_events)
        latest_event_date = max(e["date_obj"] for e in all_completion_events)
    else:
        earliest_event_date = None
        latest_event_date = None

    if settings.get("started_date"):
        start_date = datetime.strptime(str(settings["started_date"]), "%Y-%m-%d").date()
    else:
        start_date = earliest_event_date

    as_of_date = latest_event_date or start_date
    if start_date and as_of_date:
        elapsed_days = max(1, (as_of_date - start_date).days + 1)
    else:
        elapsed_days = 0

    overall_velocity = (
        total_completed_sections / elapsed_days if elapsed_days > 0 else 0.0
    )

    if as_of_date and elapsed_days > 0:
        window_days_effective = min(elapsed_days, rolling_window_days)
        window_cutoff = as_of_date - timedelta(days=window_days_effective - 1)
        window_completed = sum(
            1 for e in all_completion_events if e["date_obj"] >= window_cutoff
        )
        rolling_velocity = window_completed / window_days_effective
    else:
        window_days_effective = 0
        window_completed = 0
        rolling_velocity = 0.0

    def forecast_eta(remaining_sections: int, velocity: float) -> tuple[str, int | None]:
        if remaining_sections <= 0:
            return ("Completed", 0)
        if velocity <= 0 or as_of_date is None:
            return ("TBD", None)
        days_needed = math.ceil(remaining_sections / velocity)
        eta_date = as_of_date + timedelta(days=days_needed)
        return (eta_date.strftime("%Y-%m-%d"), days_needed)

    active_rem_total = sum(
        cm["sec_remaining"] for cm in course_metrics.values() if cm["status"] == "in_progress"
    )
    cum_rem_by_cid: dict[str, int] = {}
    for c in courses:
        cid = c["id"]
        cm = course_metrics[cid]
        if cm["status"] in ("completed", "in_progress"):
            cum_rem_by_cid[cid] = cm["sec_remaining"]
        else:
            prereqs = c.get("prerequisites", []) + c.get("corequisites", [])
            prereq_rem = max(
                (cum_rem_by_cid.get(p, 0) for p in prereqs),
                default=active_rem_total,
            )
            base_rem = max(prereq_rem, active_rem_total)
            cum_rem_by_cid[cid] = base_rem + cm["sec_remaining"]

        study_days = (
            math.ceil(cm["sec_remaining"] / overall_velocity)
            if overall_velocity > 0 and cm["sec_remaining"] > 0
            else (0 if cm["sec_remaining"] <= 0 else None)
        )
        eta_str, days_rem = forecast_eta(cum_rem_by_cid[cid], overall_velocity)
        cm["study_days"] = study_days
        cm["eta_date"] = eta_str
        cm["eta_days"] = days_rem

    # 5. Tier breakdown & cumulative tier forecasts
    tier_metrics: list[dict] = []
    cumulative_remaining_secs = 0
    for t in tiers:
        t_num = t["tier"]
        t_courses = [course_metrics[c["id"]] for c in courses if c["tier"] == t_num]
        t_courses_done = sum(1 for cm in t_courses if cm["status"] == "completed")
        t_courses_active = sum(1 for cm in t_courses if cm["status"] == "in_progress")
        t_units_done = sum(cm["units_done"] for cm in t_courses)
        t_units_total = sum(cm["total_units"] for cm in t_courses)
        t_sec_done = sum(cm["sec_done"] for cm in t_courses)
        t_sec_total = sum(cm["sec_total"] for cm in t_courses)
        t_sec_rem = max(0, t_sec_total - t_sec_done)
        cumulative_remaining_secs += t_sec_rem
        eta_str, eta_days = forecast_eta(cumulative_remaining_secs, overall_velocity)
        tier_metrics.append(
            {
                "tier": t_num,
                "level": t["level"],
                "heading": t["heading"],
                "courses_done": t_courses_done,
                "courses_active": t_courses_active,
                "courses_total": len(t_courses),
                "units_done": t_units_done,
                "units_total": t_units_total,
                "sec_done": t_sec_done,
                "sec_total": t_sec_total,
                "sec_remaining": t_sec_rem,
                "cumulative_sec_remaining": cumulative_remaining_secs,
                "pct_sections": (t_sec_done / t_sec_total * 100.0) if t_sec_total > 0 else 0.0,
                "pct_units": (t_units_done / t_units_total * 100.0) if t_units_total > 0 else 0.0,
                "cumulative_eta_date": eta_str,
                "cumulative_eta_days": eta_days,
            }
        )

    curriculum_sec_remaining = max(0, total_estimated_sections - total_completed_sections)
    curr_eta_date, curr_eta_days = forecast_eta(curriculum_sec_remaining, overall_velocity)

    return {
        "start_date": start_date.strftime("%Y-%m-%d") if start_date else None,
        "as_of_date": as_of_date.strftime("%Y-%m-%d") if as_of_date else None,
        "as_of_date_obj": as_of_date,
        "elapsed_days": elapsed_days,
        "rolling_window_days": rolling_window_days,
        "window_days_effective": window_days_effective,
        "window_completed": window_completed,
        "overall_velocity": overall_velocity,
        "rolling_velocity": rolling_velocity,
        "avg_sec_per_ch": avg_sec_per_ch,
        "avg_sec_per_app": avg_sec_per_app,
        "populated_ch_units": populated_ch_units,
        "populated_ch_sections": populated_ch_sections,
        "total_courses": len(courses),
        "courses_completed": sum(1 for cm in course_metrics.values() if cm["status"] == "completed"),
        "courses_in_progress": sum(1 for cm in course_metrics.values() if cm["status"] == "in_progress"),
        "courses_unlocked": sum(1 for cm in course_metrics.values() if cm["dag_state"] == "unlocked"),
        "total_units": total_units_all,
        "total_units_done": total_units_done,
        "pct_units": (total_units_done / total_units_all * 100.0) if total_units_all > 0 else 0.0,
        "total_sec_done": total_completed_sections,
        "total_sec_estimated": total_estimated_sections,
        "total_sec_remaining": curriculum_sec_remaining,
        "pct_sections": (
            total_completed_sections / total_estimated_sections * 100.0
            if total_estimated_sections > 0
            else 0.0
        ),
        "curriculum_eta_date": curr_eta_date,
        "curriculum_eta_days": curr_eta_days,
        "course_metrics": course_metrics,
        "node_states": node_states,
        "capstone_states": capstone_states,
        "tier_metrics": tier_metrics,
        "completion_events": all_completion_events,
    }


def render_progress_bar(pct: float, width: int = 10) -> str:
    """Render an ASCII block progress bar like '████████░░'."""
    pct_clamped = max(0.0, min(100.0, pct))
    filled = round((pct_clamped / 100.0) * width)
    if 0 < pct_clamped < (100.0 / width) and filled == 0:
        filled = 1
    return "█" * filled + "░" * (width - filled)


def slugify_heading(heading: str) -> str:
    """Convert a Markdown heading to a GitHub-style TOC anchor slug."""
    slug = heading.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = slug.replace(" ", "-")
    return slug


def format_course_texts(texts: list[dict]) -> str:
    """Render the '- **Texts & Reading Scope**:' value for a course."""
    parts: list[str] = []
    for t in texts:
        authors = t["authors"]
        title = t["title"]
        if "volumes" in t:
            vol_strs = [
                f"{v['volume']}: *{v['title']}*, {v['scope']}" for v in t["volumes"]
            ]
            scope_full = "; ".join(vol_strs)
            parts.append(f"{authors} – *{title}* ({scope_full})")
        else:
            parts.append(f"{authors} – *{title}* ({t['scope']})")
    return "; ".join(parts) + "."


def is_capstone_id(uid: str) -> bool:
    """Return True if uid is a Capstone identifier like C1..C8."""
    return bool(re.match(r"^C\d+$", uid))


def format_unlocking_display(unlock_ids: list[str]) -> str:
    """Format a Capstone's unlocking_courses list for the Capstone Project Listing table."""
    courses_part = [u for u in unlock_ids if not is_capstone_id(u)]
    caps_part = [u[1:] for u in unlock_ids if is_capstone_id(u)]
    items = list(courses_part)
    if len(caps_part) == 1:
        items.append(f"Capstone {caps_part[0]}")
    elif len(caps_part) > 1:
        items.append(f"Capstones {', '.join(caps_part)}")
    return ", ".join(items)


def render_curriculum_md(data: dict, metrics: dict) -> str:
    """Render CURRICULUM.md from curriculum.yaml and progress metrics."""
    repo = data["repository"]
    tiers = data["tiers"]
    courses = data["courses"]
    capstones = data["capstones"]
    home_lab = data["home_lab"]

    course_by_id = {c["id"]: c for c in courses}
    course_by_node = {c["node_id"]: c for c in courses}

    lines: list[str] = []
    lines.append(f"# {repo['curriculum_title']}")
    lines.append("")
    lines.append(repo["curriculum_intro"])
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Table of Contents")
    lines.append("")
    lines.append("- [Curriculum Architecture & Overview](#curriculum-architecture--overview)")
    for t in tiers:
        lines.append(f"- [{t['heading']}](#{slugify_heading(t['heading'])})")
        for tr in t.get("tracks", []):
            lines.append(f"  - [{tr['heading']}](#{slugify_heading(tr['heading'])})")
    lines.append("- [Capstone Project Listing](#capstone-project-listing)")
    lines.append(f"- [{home_lab['heading']}](#{slugify_heading(home_lab['heading'])})")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Curriculum Architecture & Overview")
    lines.append("")
    lines.append(
        "> **DAG Node Legend**: "
        "🟩 **Completed** (`completed`) · "
        "🟨 **In Progress** (`in_progress`) · "
        "🟦 **Unlocked / Ready** (`unlocked`) · "
        "⬜ **Locked** (awaiting prerequisites). "
        "See [`PROGRESS.md`](./PROGRESS.md) for section-level tracking and completion forecasts."
    )
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart TD")

    # Subgraphs for tiers
    for t in tiers:
        t_num = t["tier"]
        lines.append(f'    subgraph {t["mermaid_id"]}["{t["mermaid_label"]}"]')
        if "tracks" in t:
            lines.append("        direction TB")
            for tr in t["tracks"]:
                lines.append(f'        subgraph {tr["mermaid_id"]}["{tr["mermaid_label"]}"]')
                tr_courses = [
                    c for c in courses if c["tier"] == t_num and c.get("track") == tr["id"]
                ]
                for c in tr_courses:
                    lines.append(
                        f'            {c["node_id"]}["{c["id"]}: {c["mermaid_title"]}"]'
                    )
                lines.append("        end")
        else:
            t_courses = [c for c in courses if c["tier"] == t_num]
            for c in t_courses:
                lines.append(f'        {c["node_id"]}["{c["id"]}: {c["mermaid_title"]}"]')
        lines.append("    end")
        lines.append("")

    # Subgraph for Capstones
    lines.append('    subgraph Capstones["Capstone Projects"]')
    for cap in capstones:
        lines.append(f'        {cap["id"]}["{cap["mermaid_title"]}"]')
    lines.append("    end")
    lines.append("")

    # Edges for courses grouped by tier
    for t in tiers:
        t_num = t["tier"]
        if "mermaid_edge_order" in t:
            t_courses = [course_by_node[nid] for nid in t["mermaid_edge_order"]]
        else:
            t_courses = [c for c in courses if c["tier"] == t_num]

        for c in t_courses:
            srcs = c.get("prerequisites", []) + c.get("corequisites", [])
            if srcs:
                src_nids = " & ".join(course_by_id[s]["node_id"] for s in srcs)
                lines.append(f"    {src_nids} --> {c['node_id']}")
        if t_num >= 2:
            lines.append("")

    # Edges for Capstones
    for cap in capstones:
        unlocks = cap["unlocking_courses"]
        if cap["id"] == "C8":
            cap_srcs = [u for u in unlocks if is_capstone_id(u)]
            course_srcs = [course_by_id[u]["node_id"] for u in unlocks if not is_capstone_id(u)]
            mermaid_srcs = cap_srcs + course_srcs
        else:
            mermaid_srcs = [
                u if is_capstone_id(u) else course_by_id[u]["node_id"] for u in unlocks
            ]
        lines.append(f"    {' & '.join(mermaid_srcs)} --> {cap['id']}")

    # Node status styling in Mermaid DAG
    lines.append("")
    lines.append("    classDef completed fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#155724")
    lines.append("    classDef in_progress fill:#fff3cd,stroke:#d39e00,stroke-width:2.5px,color:#856404")
    lines.append("    classDef unlocked fill:#e7f3fe,stroke:#0d6efd,stroke-width:1.5px,color:#084298")

    completed_nodes = [
        c["node_id"] for c in courses if metrics["node_states"].get(c["id"]) == "completed"
    ] + [
        cap["id"] for cap in capstones if metrics["capstone_states"].get(cap["id"]) == "completed"
    ]
    in_progress_nodes = [
        c["node_id"] for c in courses if metrics["node_states"].get(c["id"]) == "in_progress"
    ]
    unlocked_nodes = [
        c["node_id"] for c in courses if metrics["node_states"].get(c["id"]) == "unlocked"
    ] + [
        cap["id"] for cap in capstones if metrics["capstone_states"].get(cap["id"]) == "unlocked"
    ]

    if completed_nodes:
        lines.append(f"    class {','.join(completed_nodes)} completed")
    if in_progress_nodes:
        lines.append(f"    class {','.join(in_progress_nodes)} in_progress")
    if unlocked_nodes:
        lines.append(f"    class {','.join(unlocked_nodes)} unlocked")

    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Course listings by Tier and Track
    for t in tiers:
        t_num = t["tier"]
        lines.append(f"## {t['heading']}")
        lines.append("")
        if "tracks" in t:
            for tr in t["tracks"]:
                lines.append(f"### {tr['heading']}")
                lines.append("")
                tr_courses = [
                    c for c in courses if c["tier"] == t_num and c.get("track") == tr["id"]
                ]
                for c in tr_courses:
                    lines.extend(render_course_block(c, heading_level=4))
                lines.append("---")
                lines.append("")
        else:
            t_courses = [c for c in courses if c["tier"] == t_num]
            for c in t_courses:
                lines.extend(render_course_block(c, heading_level=3))
            lines.append("---")
            lines.append("")

    # Capstone Project Listing
    lines.append("## Capstone Project Listing")
    lines.append("")
    lines.append("| Capstone | Title | Unlocking Courses | Scope & Deliverables | Estimated BOM |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    for cap in capstones:
        unlock_disp = format_unlocking_display(cap["unlocking_courses"])
        lines.append(
            f"| **{cap['number']}** | **{cap['title']}** | {unlock_disp} | "
            f"{cap['scope_and_deliverables']} | {cap['estimated_bom']} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Home-Lab & Safety Protocols
    lines.append(f"## {home_lab['heading']}")
    lines.append("")
    wb = home_lab["workbench_blueprint"]
    lines.append(f"### {wb['heading']}")
    lines.append("")
    for bench in wb["benches"]:
        lines.append(f"#### {bench['heading']}")
        for item in bench["items"]:
            lines.append(f"- **{item['label']}**: {item['description']}")
        lines.append("")

    sp = home_lab["safety_protocols"]
    lines.append(f"### {sp['heading']}")
    lines.append("")
    for idx, cat in enumerate(sp["categories"]):
        lines.append(f"#### {cat['heading']}")
        for item in cat["items"]:
            lines.append(f"- **{item['label']}**: {item['description']}")
        if idx < len(sp["categories"]) - 1:
            lines.append("")

    return "\n".join(lines) + "\n"


def render_course_block(c: dict, heading_level: int) -> list[str]:
    """Render a single course's Markdown section."""
    hashes = "#" * heading_level
    prereqs = c.get("prerequisites", [])
    coreqs = c.get("corequisites", [])
    if coreqs:
        prereq_str = f"Co-requisite {', '.join(coreqs)}"
    elif prereqs:
        prereq_str = ", ".join(prereqs)
    else:
        prereq_str = "None"

    texts_str = format_course_texts(c["texts"])
    return [
        f"{hashes} {c['id']}: {c['title']}",
        f"- **Prerequisites**: {prereq_str}",
        f"- **Texts & Reading Scope**: {texts_str}",
        f"- **{c['topics_label']}**: {c['core_topics']}",
        "",
    ]


def render_progress_md(curriculum_data: dict, progress_data: dict, metrics: dict) -> str:
    """Render PROGRESS.md dashboard from curriculum.yaml, progress.yaml, and computed metrics."""
    courses_by_id = {c["id"]: c for c in curriculum_data["courses"]}
    prog_courses = progress_data.get("courses", {})
    cm_map = metrics["course_metrics"]

    lines: list[str] = []
    lines.append("# Apex Curriculum Progress & Completion Forecast")
    lines.append("")
    lines.append(
        "Section-level study tracker and chapter-weighted completion forecaster generated from "
        "[`curriculum.yaml`](./curriculum.yaml) and [`progress.yaml`](./progress.yaml). "
        "Courses with loaded Table of Contents (TOCs) are tracked at exact textbook section granularity, "
        f"while unstarted courses are forecasted using their {metrics['total_units']} assigned chapters and appendices "
        f"scaled by the empirical section density ({metrics['avg_sec_per_ch']:.2f} sections/chapter)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Executive Summary & Velocity Forecast")
    lines.append("")

    v_day = metrics["overall_velocity"]
    v_week = v_day * 7.0
    rv_day = metrics["rolling_velocity"]
    rv_week = rv_day * 7.0

    active_cids = [
        cid for cid, cm in cm_map.items() if cm["status"] == "in_progress"
    ]
    active_str = ", ".join(f"**{cid}** ({cm_map[cid]['title']})" for cid in active_cids) or "None"

    lines.append("| Metric | Current Value | Notes |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(
        f"| **Active Course(s)** | {active_str} | "
        f"{metrics['courses_completed']} / {metrics['total_courses']} courses completed; "
        f"{metrics['courses_unlocked']} additional courses unlocked |"
    )
    lines.append(
        f"| **Study Timeline** | `{metrics['start_date'] or 'N/A'}` → `{metrics['as_of_date'] or 'N/A'}` | "
        f"{metrics['elapsed_days']} active span days |"
    )
    lines.append(
        f"| **Overall Velocity** | **{v_day:.2f} sections/day** ({v_week:.1f} sections/week) | "
        f"{metrics['total_sec_done']} sections completed across {metrics['elapsed_days']} days |"
    )
    lines.append(
        f"| **{metrics['rolling_window_days']}-Day Rolling Velocity** | "
        f"**{rv_day:.2f} sections/day** ({rv_week:.1f} sections/week) | "
        f"{metrics['window_completed']} sections in trailing {metrics['window_days_effective']}-day window |"
    )
    lines.append(
        f"| **Assigned Units Completed** | **{metrics['total_units_done']:.2f} / {metrics['total_units']}** "
        f"(`{metrics['pct_units']:.2f}%`) | "
        "Fractional chapter & appendix completion across 58 courses |"
    )
    lines.append(
        f"| **Curriculum Sections Completed** | **{metrics['total_sec_done']} / ~{metrics['total_sec_estimated']:,}** "
        f"(`{metrics['pct_sections']:.2f}%`) | "
        f"Exact for TOC-loaded courses; {metrics['avg_sec_per_ch']:.2f} sec/ch estimate for unstarted courses |"
    )
    for cid in active_cids:
        cm = cm_map[cid]
        nxt = cm["next_section"]
        nxt_label = f"Next: `{nxt['id']}` ({nxt['title']})" if nxt else "All sections done"
        lines.append(
            f"| **{cid} Completion Forecast** | **`{cm['eta_date']}`** ({cm['eta_days']}d remaining) | "
            f"{cm['sec_done']} / {cm['sec_total']} sections (`{cm['pct_sections']:.1f}%`) · {nxt_label} |"
        )
    t1 = metrics["tier_metrics"][0]
    lines.append(
        f"| **Tier 1 (100-Level) Forecast** | **`{t1['cumulative_eta_date']}`** ({t1['cumulative_eta_days']}d remaining) | "
        f"{t1['sec_done']} / ~{t1['sec_total']} est. sections (`{t1['pct_sections']:.2f}%`) across {t1['courses_total']} courses |"
    )
    lines.append(
        f"| **Full Curriculum (Tiers 1–5) Forecast** | **`{metrics['curriculum_eta_date']}`** "
        f"({metrics['curriculum_eta_days']:,}d / ~{metrics['curriculum_eta_days'] / 365.25:.1f} yrs) | "
        f"{metrics['total_sec_remaining']:,} estimated sections remaining at {v_day:.2f} sec/day |"
    )
    lines.append("")

    # Pace Sensitivity / What-If Table
    if metrics["as_of_date_obj"] is not None:
        as_of = metrics["as_of_date_obj"]
        lines.append("### Pace Sensitivity Scenarios")
        lines.append("")
        active_hdrs = " | ".join(f"{cid} ETA" for cid in active_cids)
        active_sep = " | ".join(":---" for _ in active_cids)
        if active_hdrs:
            lines.append(
                f"| Study Pace | Weekly Volume | {active_hdrs} | Tier 1 (100-Level) ETA | Full Curriculum (58 Courses) ETA |"
            )
            lines.append(f"| :--- | :--- | {active_sep} | :--- | :--- |")
        else:
            lines.append(
                "| Study Pace | Weekly Volume | Tier 1 (100-Level) ETA | Full Curriculum (58 Courses) ETA |"
            )
            lines.append("| :--- | :--- | :--- | :--- |")
        t1_rem = t1["cumulative_sec_remaining"]
        all_rem = metrics["total_sec_remaining"]

        scenarios = [
            (f"**Current Pace ({v_day:.2f} sec/day)**", v_day),
            ("1.00 section/day", 1.0),
            ("1.50 sections/day", 1.5),
            ("2.00 sections/day", 2.0),
            ("3.00 sections/day", 3.0),
        ]
        for label, rate in scenarios:
            if rate <= 0:
                continue
            active_cells: list[str] = []
            for cid in active_cids:
                c_rem = cm_map[cid]["sec_remaining"]
                c_d = math.ceil(c_rem / rate)
                c_dt = (as_of + timedelta(days=c_d)).strftime("%Y-%m-%d")
                active_cells.append(f"`{c_dt}` ({c_d}d)")
            t1_d = math.ceil(t1_rem / rate)
            all_d = math.ceil(all_rem / rate)
            t1_dt = (as_of + timedelta(days=t1_d)).strftime("%Y-%m-%d")
            all_dt = (as_of + timedelta(days=all_d)).strftime("%Y-%m-%d")
            active_row_str = (" | ".join(active_cells) + " | ") if active_cells else ""
            lines.append(
                f"| {label} | {rate * 7:.1f} sec/wk | {active_row_str}"
                f"`{t1_dt}` ({t1_d / 365.25:.1f}y) | `{all_dt}` ({all_d / 365.25:.1f}y) |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Tier-by-Tier Progress & Forecasts")
    lines.append("")
    lines.append(
        "| Tier | Level | Courses (Done / Active / Total) | Assigned Units | Sections (Done / Est.) | Progress | Cumulative ETA |"
    )
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for tm in metrics["tier_metrics"]:
        bar = render_progress_bar(tm["pct_sections"], width=10)
        lines.append(
            f"| **Tier {tm['tier']}** | {tm['level']} | "
            f"{tm['courses_done']} / {tm['courses_active']} / {tm['courses_total']} | "
            f"{tm['units_done']:.2f} / {tm['units_total']} (`{tm['pct_units']:.1f}%`) | "
            f"{tm['sec_done']} / ~{tm['sec_total']:,} | "
            f"`{bar}` `{tm['pct_sections']:.1f}%` | `{tm['cumulative_eta_date']}` |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Course-Level Section Tracking (TOC-Populated Courses)")
    lines.append("")

    status_badges = {
        "completed": "🟩 Completed",
        "in_progress": "🟨 In Progress",
        "not_started": "⬜ Not Started",
    }

    ordered_prog_cids = [
        c["id"] for c in curriculum_data["courses"] if c["id"] in prog_courses
    ]
    for cid in ordered_prog_cids:
        cprog = prog_courses[cid]
        c = courses_by_id[cid]
        cm = cm_map[cid]
        badge = status_badges.get(cm["status"], cm["status"])
        bar = render_progress_bar(cm["pct_sections"], width=16)

        lines.append(f"### {cid}: {c['title']}")
        lines.append("")
        lines.append(f"- **Status**: {badge}")
        lines.append(
            f"- **Section Progress**: `{bar}` **{cm['sec_done']} / {cm['sec_total']} sections** (`{cm['pct_sections']:.1f}%`)"
        )
        lines.append(
            f"- **Chapter/Appendix Unit Progress**: **{cm['units_done']:.2f} / {cm['total_units']} units** (`{cm['pct_units']:.1f}%`)"
        )
        if cm["next_section"]:
            nxt = cm["next_section"]
            lines.append(
                f"- **Next Section Up**: `{nxt['id']}` — *{nxt['title']}* ({nxt['unit']})"
            )
        if cm["status"] == "not_started" and cm["study_days"] != cm["eta_days"]:
            lines.append(
                f"- **Projected Course Completion**: `{cm['eta_date']}` "
                f"(~{cm['study_days']} study days; {cm['eta_days']} days from latest activity after prerequisites)"
            )
        else:
            lines.append(
                f"- **Projected Course Completion**: `{cm['eta_date']}` ({cm['eta_days']} days remaining at current pace)"
            )
        lines.append("")

        for pt in cprog.get("texts", []):
            ed_str = f", {pt['edition']}" if pt.get("edition") else ""
            lines.append(f"#### {pt['authors']} – *{pt['title']}*{ed_str}")
            lines.append("")
            lines.append("| Unit | Title | Sections Done | Progress | Latest Completion |")
            lines.append("| :--- | :--- | :--- | :--- | :--- |")
            for u in pt.get("units", []):
                secs = u.get("sections", [])
                u_total = len(secs)
                u_done = sum(1 for s in secs if s.get("completed"))
                u_pct = (u_done / u_total * 100.0) if u_total > 0 else 0.0
                u_bar = render_progress_bar(u_pct, width=10)
                comp_dates = [
                    str(s["completed_date"])
                    for s in secs
                    if s.get("completed") and s.get("completed_date")
                ]
                latest_dt = f"`{max(comp_dates)}`" if comp_dates else "—"
                lines.append(
                    f"| **{u['unit']}** | {u['title']} | {u_done} / {u_total} | "
                    f"`{u_bar}` `{u_pct:.0f}%` | {latest_dt} |"
                )
            lines.append("")

            lines.append(
                f"<details>\n<summary><strong>View All {cm['sec_total']} Sections for {cid} ({cm['sec_done']} completed)</strong></summary>\n"
            )
            for u in pt.get("units", []):
                lines.append(f"**{u['unit']}: {u['title']}**")
                for s in u.get("sections", []):
                    if s.get("completed"):
                        lines.append(
                            f"- [x] `{s['id']}` {s['title']} *(completed `{s['completed_date']}`)*"
                        )
                    else:
                        lines.append(f"- [ ] `{s['id']}` {s['title']}")
                lines.append("")
            lines.append("</details>")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Recent Section Completion Log")
    lines.append("")
    if metrics["completion_events"]:
        lines.append("| Date | Course | Unit | Section | Title |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for ev in reversed(metrics["completion_events"]):
            lines.append(
                f"| `{ev['date']}` | **{ev['course_id']}** | {ev['unit']} | "
                f"`{ev['section_id']}` | {ev['section_title']} |"
            )
    else:
        lines.append("*No sections recorded yet.*")
    lines.append("")

    return "\n".join(lines) + "\n"


def render_readme_md(data: dict, metrics: dict) -> str:
    """Render README.md from curriculum.yaml and progress metrics."""
    repo = data["repository"]
    tiers = data["tiers"]
    courses = data["courses"]
    capstones = data["capstones"]

    lines: list[str] = []
    lines.append(f"# {repo['readme_title']}")
    lines.append("")
    lines.append(repo["readme_intro"])
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Repository Structure")
    lines.append("")
    lines.append(
        f"- [`CURRICULUM.md`](./CURRICULUM.md) — The comprehensive {len(tiers)}-tier course "
        f"syllabus ({len(courses)} courses), textbook reading scopes, core topic breakdowns, "
        f"{len(capstones)} capstone engineering specifications, phased home-lab tooling blueprints, "
        f"and residential safety protocols."
    )
    lines.append(
        "- [`PROGRESS.md`](./PROGRESS.md) — Live section-level study progress dashboard, "
        "velocity analytics, and chapter-weighted completion forecasts across all 5 tiers."
    )
    lines.append(
        "- [`curriculum.yaml`](./curriculum.yaml) — The declarative single source of truth "
        "defining all courses, prerequisite DAG edges, textbook chapter partitions, capstones, "
        "and home-lab specifications."
    )
    lines.append(
        "- [`progress.yaml`](./progress.yaml) — Incremental textbook section Table of Contents "
        "and dated completion records."
    )
    lines.append(
        "- [`scripts/build.py`](./scripts/build.py) & [`scripts/track.py`](./scripts/track.py) — "
        "Automated invariant validator, Markdown generator, and CLI progress tracker."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Core Pillars")
    lines.append("")
    for idx, pillar in enumerate(repo["core_pillars"], 1):
        lines.append(f"{idx}. **{pillar['name']}**: {pillar['description']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Curriculum at a Glance")
    lines.append("")
    lines.append("| Tier | Level | Focus Areas |")
    lines.append("| :--- | :--- | :--- |")
    for t in tiers:
        lines.append(f"| **Tier {t['tier']}** | **{t['level']}** | {t['readme_focus']} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Curriculum Progress")
    lines.append("")
    v_day = metrics["overall_velocity"]
    active_cms = [
        cm for cm in metrics["course_metrics"].values() if cm["status"] == "in_progress"
    ]
    if len(active_cms) == 1:
        ac = active_cms[0]
        lines.append(
            f"Currently studying **{ac['id']} ({ac['title']})**: "
            f"**{ac['sec_done']} / {ac['sec_total']} sections** (`{ac['pct_sections']:.1f}%`, "
            f"ETA `{ac['eta_date']}` at **{v_day:.2f} sections/day**)."
        )
        lines.append("")
    elif len(active_cms) > 1:
        lines.append(f"Currently studying ({v_day:.2f} sections/day overall velocity):")
        for ac in active_cms:
            lines.append(
                f"- **{ac['id']} ({ac['title']})**: "
                f"**{ac['sec_done']} / {ac['sec_total']} sections** (`{ac['pct_sections']:.1f}%`, "
                f"ETA `{ac['eta_date']}`)"
            )
        lines.append("")
    lines.append("| Tier | Courses Done | Assigned Units | Sections (Done / Est.) | Progress | Cumulative ETA |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for tm in metrics["tier_metrics"]:
        bar = render_progress_bar(tm["pct_sections"], width=10)
        lines.append(
            f"| **Tier {tm['tier']} ({tm['level']})** | {tm['courses_done']} / {tm['courses_total']} | "
            f"{tm['units_done']:.2f} / {tm['units_total']} | {tm['sec_done']} / ~{tm['sec_total']:,} | "
            f"`{bar}` `{tm['pct_sections']:.1f}%` | `{tm['cumulative_eta_date']}` |"
        )
    lines.append("")
    lines.append(
        "For section-by-section checklists, velocity trends, and pace scenarios, see [**PROGRESS.md**](./PROGRESS.md)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Capstones Matrix")
    lines.append("")
    lines.append(repo["capstones_intro"])
    lines.append("")
    for cap in capstones:
        lines.append(f"- **{cap['readme_label']}**: {cap['readme_title']}")
    lines.append("")
    lines.append(
        "For complete details, textbook scopes, BOMs, and lab safety protocols, "
        "see [**CURRICULUM.md**](./CURRICULUM.md)."
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate invariants and check if CURRICULUM.md, PROGRESS.md, and README.md are up to date without writing.",
    )
    args = parser.parse_args(argv)

    with open(YAML_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not PROGRESS_YAML_PATH.exists():
        print("ERROR: progress.yaml not found.", file=sys.stderr)
        return 1

    with open(PROGRESS_YAML_PATH, encoding="utf-8") as f:
        progress_data = yaml.safe_load(f)

    errors = validate_curriculum(data)
    errors.extend(validate_progress(data, progress_data))
    if errors:
        print("Curriculum / Progress invariant validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    metrics = compute_progress_metrics(data, progress_data)
    curriculum_md = render_curriculum_md(data, metrics)
    progress_md = render_progress_md(data, progress_data, metrics)
    readme_md = render_readme_md(data, metrics)

    if args.check:
        drift: list[str] = []
        if not CURRICULUM_MD_PATH.exists() or CURRICULUM_MD_PATH.read_text(encoding="utf-8") != curriculum_md:
            drift.append("CURRICULUM.md is out of sync with curriculum.yaml / progress.yaml")
        if not PROGRESS_MD_PATH.exists() or PROGRESS_MD_PATH.read_text(encoding="utf-8") != progress_md:
            drift.append("PROGRESS.md is out of sync with curriculum.yaml / progress.yaml")
        if not README_MD_PATH.exists() or README_MD_PATH.read_text(encoding="utf-8") != readme_md:
            drift.append("README.md is out of sync with curriculum.yaml / progress.yaml")
        if drift:
            for d in drift:
                print(f"ERROR: {d}. Run 'python3 scripts/build.py' to regenerate.", file=sys.stderr)
            return 1
        print(
            f"OK: Validated {len(data['courses'])} courses, {len(data['capstones'])} capstones, and "
            f"{metrics['total_sec_done']} completed sections; CURRICULUM.md, PROGRESS.md, and README.md are 100% in sync."
        )
        return 0

    CURRICULUM_MD_PATH.write_text(curriculum_md, encoding="utf-8")
    PROGRESS_MD_PATH.write_text(progress_md, encoding="utf-8")
    README_MD_PATH.write_text(readme_md, encoding="utf-8")
    print(
        f"OK: Validated {len(data['courses'])} courses, {len(data['capstones'])} capstones, and "
        f"{metrics['total_sec_done']} completed sections; generated CURRICULUM.md, PROGRESS.md, and README.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
