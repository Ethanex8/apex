#!/usr/bin/env python3
"""Validate curriculum.yaml against GEMINI.md invariants and generate CURRICULUM.md and README.md."""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from pathlib import Path
import re
import sys
import yaml


ROOT_DIR = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT_DIR / "curriculum.yaml"
CURRICULUM_MD_PATH = ROOT_DIR / "CURRICULUM.md"
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


def render_curriculum_md(data: dict) -> str:
    """Render CURRICULUM.md from curriculum.yaml."""
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

    # Edges for courses grouped by tier (Tier 1 & Tier 2 share first block, then blank line before Tier 3, 4, 5)
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
        # In Mermaid, capstone prerequisites (C1..C7) come first for C8
        if cap["id"] == "C8":
            cap_srcs = [u for u in unlocks if is_capstone_id(u)]
            course_srcs = [course_by_id[u]["node_id"] for u in unlocks if not is_capstone_id(u)]
            mermaid_srcs = cap_srcs + course_srcs
        else:
            mermaid_srcs = [
                u if is_capstone_id(u) else course_by_id[u]["node_id"] for u in unlocks
            ]
        lines.append(f"    {' & '.join(mermaid_srcs)} --> {cap['id']}")

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
            for idx, tr in enumerate(t["tracks"]):
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


def render_readme_md(data: dict) -> str:
    """Render README.md from curriculum.yaml."""
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
        "- [`curriculum.yaml`](./curriculum.yaml) — The declarative single source of truth "
        "defining all courses, prerequisite DAG edges, textbook chapter partitions, capstones, "
        "and home-lab specifications."
    )
    lines.append(
        "- [`scripts/build.py`](./scripts/build.py) — Automated invariant validator and "
        "generator that enforces [`GEMINI.md`](./GEMINI.md) rules and compiles `curriculum.yaml` "
        "into `CURRICULUM.md` and `README.md`."
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate invariants and check if CURRICULUM.md and README.md are up to date without writing.",
    )
    args = parser.parse_args()

    with open(YAML_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    errors = validate_curriculum(data)
    if errors:
        print("Curriculum invariant validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    curriculum_md = render_curriculum_md(data)
    readme_md = render_readme_md(data)

    if args.check:
        drift: list[str] = []
        if not CURRICULUM_MD_PATH.exists() or CURRICULUM_MD_PATH.read_text(encoding="utf-8") != curriculum_md:
            drift.append("CURRICULUM.md is out of sync with curriculum.yaml")
        if not README_MD_PATH.exists() or README_MD_PATH.read_text(encoding="utf-8") != readme_md:
            drift.append("README.md is out of sync with curriculum.yaml")
        if drift:
            for d in drift:
                print(f"ERROR: {d}. Run 'python3 scripts/build.py' to regenerate.", file=sys.stderr)
            return 1
        print(
            f"OK: Validated {len(data['courses'])} courses and {len(data['capstones'])} capstones; "
            "CURRICULUM.md and README.md are 100% in sync."
        )
        return 0

    CURRICULUM_MD_PATH.write_text(curriculum_md, encoding="utf-8")
    README_MD_PATH.write_text(readme_md, encoding="utf-8")
    print(
        f"OK: Validated {len(data['courses'])} courses and {len(data['capstones'])} capstones; "
        "generated CURRICULUM.md and README.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
