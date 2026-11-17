#!/usr/bin/env python3
"""Validate roadmap/book invariants, sync chapter anchors, and build Markdown indexes.

Purpose:
  Compile canonical `roadmap.yaml` into `ROADMAP.md` and `README.md`, synchronize
  code-to-textbook references via `sync_book`, and enforce DAG/schema/chapter/code
  invariants without allowing documentation drift.

Usage:
  python3 scripts/build.py           # Sync book anchors and regenerate ROADMAP.md / README.md
  python3 scripts/build.py --check   # Verify zero drift and exit 1 if anything is stale

Outputs:
  Updates `systems/*/chapters/*.md`, `ROADMAP.md`, and `README.md` in default mode.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_book  # noqa: E402 — repo scripts run standalone without package install
import sync_book  # noqa: E402 — repo scripts run standalone without package install

ROOT_DIR = SCRIPT_DIR.parent
ROADMAP_YAML_PATH = ROOT_DIR / "roadmap.yaml"
ROADMAP_MD_PATH = ROOT_DIR / "ROADMAP.md"
README_MD_PATH = ROOT_DIR / "README.md"
PAGES_BOOK_URL = "https://ethanex8.github.io/apex/"

VALID_MODES = {"couch", "bench"}
VALID_STATUSES = {"pending", "in_review", "approved"}
# Reject human prose notes like "pytest ... (note)" inside automated couch verification commands.
PROSE_PAREN_RE = re.compile(r"\s+\(")


def _load_roadmap(path: Path) -> dict:
    """Load and type-check `roadmap.yaml`, raising `ValueError` on missing or invalid YAML."""
    if not path.is_file():
        raise ValueError(f"{path.name} not found.")
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"Failed to parse {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} root must be a YAML mapping, got {type(data).__name__}.")
    return data


def render_progress_bar(pct: float, width: int = 12) -> str:
    """Render an ASCII Unicode progress bar for percentage `pct` at `width` cells."""
    filled = round(max(0.0, min(100.0, pct)) / 100.0 * width)
    return "█" * filled + "░" * (width - filled)


def _validate_systems_and_phases(
    systems: list[dict], errors: list[str]
) -> tuple[dict[str, dict], dict[str, str]]:
    """Validate system metadata ordering and unique phase prefixes, returning lookup maps."""
    if not isinstance(systems, list):
        errors.append("'systems' must be a list")
        return {}, {}
    sys_by_id: dict[str, dict] = {}
    phase_to_sys: dict[str, str] = {}
    for idx, sys_obj in enumerate(systems, 1):
        if not isinstance(sys_obj, dict):
            errors.append(f"System entry #{idx} must be a mapping")
            continue
        sid = sys_obj.get("id")
        if not sid or not re.match(r"^[a-z][a-z0-9_-]*$", str(sid)):
            errors.append(f"Invalid system id '{sid}'")
            continue
        if sid in sys_by_id:
            errors.append(f"Duplicate system id '{sid}'")
        if sys_obj.get("order") != idx:
            errors.append(f"[{sid}] Expected order={idx}, got {sys_obj.get('order')}")
        sys_by_id[sid] = sys_obj

        for req_field in ("name", "role", "workspace", "est_weeks", "graduation_demo", "phases"):
            if not sys_obj.get(req_field):
                errors.append(f"[{sid}] Missing required field '{req_field}'")

        phases = sys_obj.get("phases") or []
        if not isinstance(phases, list):
            errors.append(f"[{sid}] 'phases' must be a list")
            continue
        for phase in phases:
            pid = phase.get("id") if isinstance(phase, dict) else None
            if not pid:
                errors.append(f"[{sid}] Phase missing 'id'")
                continue
            if pid in phase_to_sys:
                errors.append(f"[{sid}] Duplicate phase id '{pid}'")
            if not str(pid).startswith(f"{sid}-"):
                errors.append(f"[{sid}] Phase id '{pid}' must start with '{sid}-'")
            if not phase.get("name"):
                errors.append(f"[{sid}] Phase '{pid}' missing 'name'")
            phase_to_sys[pid] = sid
    return sys_by_id, phase_to_sys


def _validate_dependency_dag(sys_by_id: dict[str, dict], errors: list[str]) -> None:
    """Verify system `depends_on` edges reference valid systems and form an acyclic DAG."""
    indegree: dict[str, int] = {sid: 0 for sid in sys_by_id}
    adj: dict[str, list[str]] = defaultdict(list)
    for sid, sys_obj in sys_by_id.items():
        for dep in sys_obj.get("depends_on") or []:
            if dep not in sys_by_id:
                errors.append(f"[{sid}] Unknown dependency '{dep}' in depends_on")
            elif dep == sid:
                errors.append(f"[{sid}] Self-dependency in depends_on")
            else:
                adj[dep].append(sid)
                indegree[sid] += 1

    queue = deque([sid for sid, deg in indegree.items() if deg == 0])
    visited = 0
    while queue:
        cur = queue.popleft()
        visited += 1
        for nxt in adj[cur]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if visited != len(sys_by_id):
        errors.append("Cycle detected in systems depends_on graph")


def _validate_single_step(
    step: dict,
    sys_by_id: dict[str, dict],
    phase_to_sys: dict[str, str],
    seen_steps: set[str],
    sys_step_nums: dict[str, list[int]],
    errors: list[str],
) -> None:
    """Validate schema, status, naming, deliverables, and verification command for one step."""
    step_id = step.get("id")
    if not step_id:
        errors.append("Step missing 'id'")
        return
    if step_id in seen_steps:
        errors.append(f"Duplicate step id '{step_id}'")
        return
    seen_steps.add(step_id)

    sid, pid = step.get("system"), step.get("phase")
    if sid not in sys_by_id:
        errors.append(f"[{step_id}] Unknown system '{sid}'")
    if pid not in phase_to_sys:
        errors.append(f"[{step_id}] Unknown phase '{pid}'")
    elif sid in sys_by_id and phase_to_sys[pid] != sid:
        errors.append(f"[{step_id}] Phase '{pid}' belongs to '{phase_to_sys[pid]}', not '{sid}'")

    if m := re.match(r"^([a-z][a-z0-9_-]*)-(\d{2})$", str(step_id)):
        if m.group(1) != sid:
            errors.append(f"[{step_id}] Step prefix '{m.group(1)}' does not match system '{sid}'")
        sys_step_nums[sid].append(int(m.group(2)))
    else:
        errors.append(f"[{step_id}] Step id must follow '<system>-NN' format")

    mode, status = step.get("mode"), step.get("status")
    if mode not in VALID_MODES:
        errors.append(f"[{step_id}] Invalid mode '{mode}' (expected one of {sorted(VALID_MODES)})")
    if status not in VALID_STATUSES:
        errors.append(f"[{step_id}] Invalid status '{status}' (expected one of {sorted(VALID_STATUSES)})")
    if status == "approved":
        adate = step.get("approved_date")
        if not adate:
            errors.append(
                f"[{step_id}] Approved step missing required 'approved_date' (expected YYYY-MM-DD)"
            )
        else:
            try:
                datetime.strptime(str(adate), "%Y-%m-%d")
            except ValueError:
                errors.append(f"[{step_id}] Invalid approved_date '{adate}' (expected YYYY-MM-DD)")

    for req in ("title", "first_principles", "reference_reading"):
        if not step.get(req):
            errors.append(f"[{step_id}] Missing '{req}'")
    deliverables = step.get("deliverables")
    if not isinstance(deliverables, list) or not deliverables:
        errors.append(f"[{step_id}] 'deliverables' must be a non-empty list")
    ver = step.get("verification")
    if not ver:
        errors.append(f"[{step_id}] Missing 'verification'")
    elif mode == "couch":
        valid_prefixes = ("uv run ", "python3 ", "make ", "bash ", "kicad-cli ")
        if not str(ver).startswith(valid_prefixes) or PROSE_PAREN_RE.search(str(ver)):
            errors.append(
                f"[{step_id}] Couch step 'verification' must start with {valid_prefixes}, got: {ver}"
            )


def _int_to_roman(num: int) -> str:
    """Convert positive integer `num` into uppercase Roman numerals."""
    table = ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
    parts: list[str] = []
    rem = num
    for val, sym in table:
        while rem >= val:
            parts.append(sym)
            rem -= val
    return "".join(parts)


def _validate_book_chapter(
    chap: object,
    part_id: str,
    part_sys: str | None,
    exp_num: int,
    step_sys_by_id: dict[str, str],
    seen_chaps: set[str],
    assigned_steps: set[str],
    declared_slugs: set[tuple[str, str]],
    errors: list[str],
) -> None:
    """Validate one chapter entry inside `book.parts` and record its step assignments."""
    if not isinstance(chap, dict):
        errors.append(f"[{part_id}] Chapter entry #{exp_num} must be a mapping")
        return
    cid = chap.get("id")
    if not cid or cid in seen_chaps:
        errors.append(f"[{part_id}] Missing or duplicate chapter id '{cid}'")
    else:
        seen_chaps.add(str(cid))
    if chap.get("number") != exp_num:
        errors.append(f"[{cid or part_id}] Expected chapter number={exp_num}, got {chap.get('number')}")
    slug = str(chap.get("slug") or "")
    if not re.match(rf"^{exp_num:02d}_[a-z0-9_]+$", slug):
        errors.append(f"[{cid or part_id}] Chapter slug '{slug}' must start with '{exp_num:02d}_'")
    elif part_sys:
        declared_slugs.add((part_sys, slug))
    for req in ("title", "summary"):
        if not chap.get(req):
            errors.append(f"[{cid or part_id}] Chapter missing '{req}'")
    c_title = str(chap.get("title") or "").strip()
    if c_title and (len(c_title.split()) > 6 or any(ch in c_title for ch in ("&", ":", ","))):
        errors.append(
            f"[{cid or part_id}] Chapter title '{c_title}' must be concise (<= 6 words, "
            "focused on the primary topic without '&', ':', or comma lists)"
        )
    c_steps = chap.get("steps")
    if not isinstance(c_steps, list) or not c_steps:
        errors.append(f"[{cid or part_id}] Chapter 'steps' must be a non-empty list")
        return
    for sid in c_steps:
        if sid not in step_sys_by_id:
            errors.append(f"[{cid or part_id}] Chapter references unknown step '{sid}'")
        elif sid in assigned_steps:
            errors.append(f"[{cid or part_id}] Step '{sid}' assigned to multiple chapters")
        else:
            assigned_steps.add(str(sid))
            if part_sys and step_sys_by_id[sid] != part_sys:
                errors.append(
                    f"[{cid or part_id}] Step '{sid}' belongs to '{step_sys_by_id[sid]}', not '{part_sys}'"
                )


def _validate_book_outline(
    data: dict,
    sys_by_id: dict[str, dict],
    step_sys_by_id: dict[str, str],
    root_dir: Path | None,
    errors: list[str],
) -> None:
    """Validate `book.parts` sequential numbering, exact step coverage, and disk chapter files."""
    book = data.get("book")
    if not isinstance(book, dict):
        errors.append("Missing or invalid top-level 'book' mapping in roadmap.yaml")
        return
    for req in ("title", "subtitle"):
        if not book.get(req):
            errors.append(f"[book] Missing '{req}'")
    parts = book.get("parts")
    if not isinstance(parts, list) or not parts:
        errors.append("[book] 'parts' must be a non-empty list")
        return

    seen_parts: set[str] = set()
    seen_chaps: set[str] = set()
    assigned_steps: set[str] = set()
    declared_slugs: set[tuple[str, str]] = set()
    chap_num = 1

    for idx, part in enumerate(parts, 1):
        if not isinstance(part, dict):
            errors.append(f"[book] Part entry #{idx} must be a mapping")
            continue
        pid = part.get("id")
        if not pid or pid in seen_parts:
            errors.append(f"[book] Missing or duplicate part id '{pid}'")
        else:
            seen_parts.add(str(pid))
        if part.get("number") != _int_to_roman(idx):
            errors.append(f"[{pid or 'book'}] Expected part number={_int_to_roman(idx)}, got {part.get('number')}")
        part_sys = part.get("system")
        if part_sys not in sys_by_id:
            errors.append(f"[{pid or 'book'}] Unknown part system '{part_sys}'")
            part_sys = None
        for req in ("title", "summary"):
            if not part.get(req):
                errors.append(f"[{pid or 'book'}] Part missing '{req}'")
        chaps = part.get("chapters")
        if not isinstance(chaps, list) or not chaps:
            errors.append(f"[{pid or 'book'}] Part 'chapters' must be a non-empty list")
            continue
        for chap in chaps:
            _validate_book_chapter(
                chap, str(pid or f"part-{idx}"), part_sys, chap_num,
                step_sys_by_id, seen_chaps, assigned_steps, declared_slugs, errors,
            )
            chap_num += 1

    missing_steps = [sid for sid in step_sys_by_id if sid not in assigned_steps]
    if missing_steps:
        errors.append(f"[book] Unmapped steps missing from book chapters: {missing_steps}")
    if root_dir is not None:
        for md_path in sorted(root_dir.glob("systems/*/chapters/*.md")):
            sys_id = md_path.parent.parent.name
            if (sys_id, md_path.stem) not in declared_slugs:
                errors.append(
                    f"[book] Chapter file '{md_path.relative_to(root_dir)}' is not registered in book.parts"
                )


def validate_roadmap(data: dict, root_dir: Path | None = None) -> list[str]:
    """Validate all schema, DAG, phase, step, and book-outline invariants in `roadmap.yaml`."""
    errors: list[str] = []
    for top_key in ("repository", "safety_guardrails", "phased_procurement", "systems", "book", "steps"):
        if not data.get(top_key):
            errors.append(f"Missing or empty top-level section '{top_key}' in roadmap.yaml")

    systems = data.get("systems") or []
    steps = data.get("steps") or []
    sys_by_id, phase_to_sys = _validate_systems_and_phases(systems, errors)
    _validate_dependency_dag(sys_by_id, errors)

    seen_steps: set[str] = set()
    sys_step_nums: dict[str, list[int]] = defaultdict(list)
    step_sys_by_id: dict[str, str] = {}
    if not isinstance(steps, list):
        errors.append("'steps' must be a list")
    else:
        for step in steps:
            if not isinstance(step, dict):
                errors.append("Step entry must be a mapping")
                continue
            _validate_single_step(step, sys_by_id, phase_to_sys, seen_steps, sys_step_nums, errors)
            if step.get("id") and step.get("system"):
                step_sys_by_id[str(step["id"])] = str(step["system"])

    for sid, nums in sys_step_nums.items():
        if nums != list(range(1, len(nums) + 1)):
            errors.append(f"[{sid}] Step numbers must be sequential 01..{len(nums):02d}, got {nums}")
    for sid in sys_by_id:
        if not sys_step_nums.get(sid):
            errors.append(f"[{sid}] System has 0 steps")

    _validate_book_outline(data, sys_by_id, step_sys_by_id, root_dir, errors)
    return errors


def _compute_system_metric(
    sys_obj: dict, s_steps: list[dict], steps_by_phase: dict[str, list[dict]]
) -> dict:
    """Aggregate completion counts and per-phase statistics for one system."""
    approved = sum(1 for s in s_steps if s["status"] == "approved")
    in_review = sum(1 for s in s_steps if s["status"] == "in_review")
    couch = sum(1 for s in s_steps if s["mode"] == "couch")
    couch_done = sum(1 for s in s_steps if s["mode"] == "couch" and s["status"] == "approved")
    bench = sum(1 for s in s_steps if s["mode"] == "bench")
    bench_done = sum(1 for s in s_steps if s["mode"] == "bench" and s["status"] == "approved")

    pct = (approved / len(s_steps) * 100.0) if s_steps else 0.0
    if approved == len(s_steps):
        sys_status = "completed"
    elif approved > 0 or in_review > 0:
        sys_status = "in_progress"
    else:
        sys_status = "ready" if not sys_obj.get("depends_on") else "queued"

    phase_stats = []
    for phase in sys_obj["phases"]:
        ps = steps_by_phase[phase["id"]]
        p_done = sum(1 for s in ps if s["status"] == "approved")
        phase_stats.append(
            {
                "id": phase["id"],
                "name": phase["name"],
                "total": len(ps),
                "done": p_done,
                "couch": sum(1 for s in ps if s["mode"] == "couch"),
                "bench": sum(1 for s in ps if s["mode"] == "bench"),
                "pct": (p_done / len(ps) * 100.0) if ps else 0.0,
                "steps": ps,
            }
        )

    return {
        "system": sys_obj,
        "total": len(s_steps),
        "approved": approved,
        "in_review": in_review,
        "couch": couch,
        "couch_done": couch_done,
        "bench": bench,
        "bench_done": bench_done,
        "pct": pct,
        "status": sys_status,
        "next_step": next((s for s in s_steps if s["status"] != "approved"), None),
        "phases": phase_stats,
    }


def compute_metrics(data: dict) -> dict:
    """Compute progress metrics per system, phase, and across the entire robot."""
    steps = data["steps"]
    steps_by_sys: dict[str, list[dict]] = defaultdict(list)
    steps_by_phase: dict[str, list[dict]] = defaultdict(list)
    for st in steps:
        steps_by_sys[st["system"]].append(st)
        steps_by_phase[st["phase"]].append(st)

    sys_metrics = [
        _compute_system_metric(sys_obj, steps_by_sys[sys_obj["id"]], steps_by_phase)
        for sys_obj in data["systems"]
    ]
    total_couch = sum(sm["couch"] for sm in sys_metrics)
    total_approved = sum(sm["approved"] for sm in sys_metrics)

    active_step = next((s for s in steps if s["status"] == "in_review"), None)
    if active_step is None:
        active_step = next((s for s in steps if s["status"] == "pending"), None)

    parts = [p for p in ((data.get("book") or {}).get("parts") or []) if isinstance(p, dict)]
    book_chapters = sum(len(p.get("chapters") or []) for p in parts)

    return {
        "total_steps": len(steps),
        "total_approved": total_approved,
        "total_in_review": sum(sm["in_review"] for sm in sys_metrics),
        "total_couch": total_couch,
        "total_couch_done": sum(sm["couch_done"] for sm in sys_metrics),
        "total_bench": sum(sm["bench"] for sm in sys_metrics),
        "total_bench_done": sum(sm["bench_done"] for sm in sys_metrics),
        "pct_total": (total_approved / len(steps) * 100.0) if steps else 0.0,
        "pct_couch": (total_couch / len(steps) * 100.0) if steps else 0.0,
        "book_parts": len(parts),
        "book_chapters": book_chapters,
        "sys_metrics": sys_metrics,
        "active_step": active_step,
    }


def status_badge(status: str) -> str:
    """Return human-friendly emoji badge string for step `status`."""
    badges = {
        "approved": "✅ Approved",
        "in_review": "🔍 In Review",
        "pending": "⬜ Pending",
    }
    if status not in badges:
        raise ValueError(f"Invalid step status '{status}' (expected one of {sorted(badges)})")
    return badges[status]


def mode_badge(mode: str) -> str:
    """Return human-friendly emoji badge string for `couch` vs. `bench` step mode."""
    badges = {"couch": "🛋️ Couch", "bench": "🔧 Bench"}
    if mode not in badges:
        raise ValueError(f"Invalid step mode '{mode}' (expected one of {sorted(badges)})")
    return badges[mode]


def _render_roadmap_overview(data: dict, metrics: dict) -> list[str]:
    """Render header summary, summary table, dependency DAG, and procurement sections."""
    repo = data["repository"]
    lines: list[str] = [
        "# Apex Engineering Roadmap",
        "",
        (
            f"Generated from [`roadmap.yaml`](./roadmap.yaml). Tracks **{len(metrics['sys_metrics'])} integrated subsystems** "
            f"and **{metrics['total_steps']} engineering milestones** "
            f"(**{metrics['total_couch']} design & simulation** `{metrics['pct_couch']:.0f}%` / **{metrics['total_bench']} bench sessions**) "
            f"for a unified hardware platform ({repo['robot_class']})."
        ),
        "",
        "---",
        "",
        "## Overall Progress",
        "",
        (
            f"- **Total Completion**: `{render_progress_bar(metrics['pct_total'], 16)}` "
            f"**{metrics['total_approved']} / {metrics['total_steps']} steps** (`{metrics['pct_total']:.1f}%`)"
        ),
        (
            f"- **Design & Simulation**: **{metrics['total_couch_done']} / {metrics['total_couch']}** · "
            f"**Hardware Bench Sessions**: **{metrics['total_bench_done']} / {metrics['total_bench']}**"
        ),
    ]
    if metrics["active_step"]:
        st = metrics["active_step"]
        lines.append(
            f"- **Active Step**: **`{st['id']}`** ({mode_badge(st['mode'])}, {status_badge(st['status'])}) — {st['title']}"
        )
    lines.extend(["", "| # | Subsystem | Role | Progress | Design / Bench | Est. Timeline | Workspace |"])
    lines.append("| :---: | :--- | :--- | :--- | :---: | :---: | :--- |")
    for sm in metrics["sys_metrics"]:
        sys_obj = sm["system"]
        slug = re.sub(r"[^a-z0-9-]+", "", sys_obj["name"].lower().replace(" ", "-"))
        bar = render_progress_bar(sm["pct"], 10)
        lines.append(
            f"| **{sys_obj['order']}** | [`{sys_obj['id']}`](#{sys_obj['id']}-{slug}) "
            f"— {sys_obj['name']} | {sys_obj['role']} | "
            f"`{bar}` {sm['approved']}/{sm['total']} (`{sm['pct']:.0f}%`) | "
            f"{sm['couch']} / {sm['bench']} | {sys_obj['est_weeks']} | [{sys_obj['workspace']}]({sys_obj['workspace']}) |"
        )
    lines.extend(["", "---", "", "## System Dependency Graph", "", "```mermaid", "flowchart LR"])
    for sm in metrics["sys_metrics"]:
        sys_obj = sm["system"]
        sid = sys_obj["id"]
        lines.append(f'    {sid}["{sys_obj["order"]}. {sid}<br/>{sm["approved"]}/{sm["total"]} steps"]')
    for sm in metrics["sys_metrics"]:
        sid = sm["system"]["id"]
        for dep in sm["system"].get("depends_on") or []:
            lines.append(f"    {dep} --> {sid}")
    lines.extend(["```", "", "---", "", "## Safety Guardrails & Phased Procurement", ""])
    for sg in data["safety_guardrails"]:
        lines.append(f"- **{sg['name']}**: {sg['description']}")
    lines.extend(["", "| Stage | Est. Cost | Components & Equipment |", "| :--- | :---: | :--- |"])
    for item in data["phased_procurement"]:
        lines.append(f"| **{item['stage']}** | **{item['est_cost_usd']}** | {item['items']} |")
    return lines


def _render_system_section(sm: dict) -> list[str]:
    """Render one system's phase progress table and collapsible step checklists."""
    sys_obj = sm["system"]
    sid = sys_obj["id"]
    deps = ", ".join(f"`{d}`" for d in sys_obj.get("depends_on") or []) or "None (Entry Subsystem)"
    lines = [
        f"### {sys_obj['order']}. `{sid}` — {sys_obj['name']}",
        "",
        f"- **Role**: {sys_obj['role']}",
        f"- **Workspace**: [`{sys_obj['workspace']}`]({sys_obj['workspace']})",
        f"- **Builds On**: {deps}",
        f"- **Integration Milestone**: {sys_obj['graduation_demo']}",
        (
            f"- **Progress**: `{render_progress_bar(sm['pct'], 12)}` **{sm['approved']} / {sm['total']}** "
            f"(`{sm['couch']}` design / `{sm['bench']}` bench)"
        ),
        "",
        "| Phase | Steps Done | Design / Bench | Progress |",
        "| :--- | :---: | :---: | :--- |",
    ]
    for ph in sm["phases"]:
        lines.append(
            f"| **{ph['name']}** | {ph['done']} / {ph['total']} | {ph['couch']} / {ph['bench']} | "
            f"`{render_progress_bar(ph['pct'], 10)}` `{ph['pct']:.0f}%` |"
        )
    lines.extend(
        [
            "",
            "<details>",
            f"<summary><strong>View All {sm['total']} Steps for <code>{sid}</code></strong></summary>",
            "",
        ]
    )
    for ph in sm["phases"]:
        lines.extend([f"#### {ph['name']}", ""])
        for st in ph["steps"]:
            chk = "x" if st["status"] == "approved" else " "
            meta_bits = [mode_badge(st["mode"]), status_badge(st["status"])]
            if st.get("approved_date"):
                meta_bits.append(f"approved `{st['approved_date']}`")
            if st.get("pr_url"):
                meta_bits.append(f"[PR]({st['pr_url']})")
            lines.append(f"- [{chk}] **`{st['id']}`** — **{st['title']}** *({' · '.join(meta_bits)})*")
            lines.append(f"  - **Deliverables**: {'; '.join(f'`{d}`' for d in st['deliverables'])}")
            lines.append(f"  - **Verify**: `{st['verification']}`")
            lines.append(f"  - **First Principles**: {st['first_principles']} *({st['reference_reading']})*")
        lines.append("")
    lines.extend(["</details>", ""])
    return lines


def render_roadmap_md(data: dict, metrics: dict) -> str:
    """Compile full `ROADMAP.md` Markdown text from validated `roadmap.yaml` and `metrics`."""
    lines = _render_roadmap_overview(data, metrics)
    lines.extend(["", "---", "", "## System-by-System Execution Plan", ""])
    for sm in metrics["sys_metrics"]:
        lines.extend(_render_system_section(sm))
    return "\n".join(lines).rstrip() + "\n"


def _render_readme_guide(total_steps: int, book_parts: int, book_chapters: int) -> list[str]:
    """Return the Repository Guide and Engineering Methodology sections for `README.md`."""
    return [
        "",
        "---",
        "",
        "## Repository Guide",
        "",
        f"- [**`Apex Interactive Textbook`**]({PAGES_BOOK_URL}) — {book_parts}-part, {book_chapters}-chapter VitePress textbook ([`book/`](./book/index.md)) compiling `systems/*/chapters/*.md` with synchronized source excerpts and interactive hardware figures.",
        "- [**`VISION.md`**](./VISION.md) — Dual-processor architecture, electrical and protocol interface contracts, safety limits, and bill of materials.",
        f"- [**`ROADMAP.md`**](./ROADMAP.md) — Phase breakdowns, procurement schedule, and all {total_steps} step checklists.",
        "- [**`roadmap.yaml`**](./roadmap.yaml) — Declarative manifest of subsystems, milestones, textbook outline, and verification state.",
        "- [**`systems/`**](./systems/brain/README.md) — Subsystem workspaces (`brain`, `drive`, `power`, `limb`, `walker`, `sight`).",
        "- [**`scripts/`**](./scripts/step.py) — [`step.py`](./scripts/step.py), [`build.py`](./scripts/build.py), [`sync_book.py`](./scripts/sync_book.py), [`check_book.py`](./scripts/check_book.py), and [`check_code.py`](./scripts/check_code.py) milestone tracking, documentation synchronization, and static checks.",
        "",
        "---",
        "",
        "## Engineering Methodology",
        "",
        "1. **Incremental Specification & Simulation**: Each design milestone implements a bounded module verified in `Verilator` digital simulation, `Yosys`/`nextpnr` FPGA synthesis, KiCad electrical/layout checks (`ERC`/`DRC`), transmission-line solvers, `MuJoCo` rigid-body dynamics, or `pytest`.",
        "2. **First-Principles Textbook Documentation**: Design milestones pair verified source code and hardware descriptions with chapters in `systems/<system>/chapters/`, linking code anchors directly to the analytical derivations.",
        "3. **Staged Hardware Bring-Up**: Subsystems pass automated simulation and board-level verification gates before physical assembly, current-limited power-on testing, and system integration.",
    ]


def render_readme_md(data: dict, metrics: dict) -> str:
    """Compile top-level `README.md` dashboard pointing to GitHub Pages textbook and tooling."""
    repo = data["repository"]
    lines: list[str] = [
        f"# {repo['title']}",
        "",
        repo["tagline"],
        "",
        f"- **Target Platform**: {repo['robot_class']}",
        f"- **Estimated BOM**: {repo['estimated_total_bom_usd']}",
        (
            f"- **Scope**: **{metrics['total_couch']} / {metrics['total_steps']} design & simulation steps (`{metrics['pct_couch']:.0f}%`)** "
            f"paired with **{metrics['total_bench']} hardware assembly and laboratory bring-up sessions**."
        ),
        "",
        "---",
        "",
        "## Active Milestone",
        "",
    ]
    if metrics["active_step"]:
        st = metrics["active_step"]
        lines.extend(
            [
                f"**Current Focus**: **`{st['id']}`** ({mode_badge(st['mode'])} · {status_badge(st['status'])}) — **{st['title']}**",
                "",
                f"- **First Principles**: {st['first_principles']}",
                f"- **Verification Gate**: `{st['verification']}`",
            ]
        )
    else:
        lines.append(f"All {metrics['total_steps']} steps completed!")
    lines.extend(
        [
            "",
            "```bash",
            "python3 scripts/step.py status          # Progress across all 6 subsystems",
            "python3 scripts/step.py next            # Inspect next pending step & verification gate",
            "python3 scripts/check_code.py           # Run AST docstring/modularity, Ruff, and ShellCheck gates",
            "python3 scripts/build.py --check        # Validate roadmap invariants, book sync & doc consistency",
            "```",
            "",
            "---",
            "",
            "## Subsystems",
            "",
            "| # | Subsystem | Scope | Progress | Design / Bench | Timeline |",
            "| :---: | :--- | :--- | :---: | :---: | :---: |",
        ]
    )
    for sm in metrics["sys_metrics"]:
        sys_obj = sm["system"]
        bar = render_progress_bar(sm["pct"], 8)
        lines.append(
            f"| **{sys_obj['order']}** | [**`{sys_obj['id']}`**]({sys_obj['workspace']}) | "
            f"{sys_obj['name']} | `{bar}` **{sm['approved']} / {sm['total']}** | "
            f"{sm['couch']} / {sm['bench']} | {sys_obj['est_weeks']} |"
        )
    lines.extend(
        _render_readme_guide(metrics["total_steps"], metrics["book_parts"], metrics["book_chapters"])
    )
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for validating invariants and syncing/generating Markdown docs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate invariants and check if chapters, ROADMAP.md, and README.md are up to date without writing.",
    )
    args = parser.parse_args(argv)

    try:
        data = _load_roadmap(ROADMAP_YAML_PATH)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors = validate_roadmap(data, ROOT_DIR)
    if errors:
        print("Roadmap invariant validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if not args.check:
        _, sync_errs = sync_book.sync_all_chapters(ROOT_DIR, check_only=False)
        if sync_errs:
            print("Textbook sync FAILED:", file=sys.stderr)
            for err in sync_errs:
                print(f"  - {err}", file=sys.stderr)
            return 1

    book_errors, _, _ = check_book.validate_chapters(ROOT_DIR)
    if book_errors:
        print("Textbook invariant validation FAILED:", file=sys.stderr)
        for err in book_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    metrics = compute_metrics(data)
    roadmap_md = render_roadmap_md(data, metrics)
    readme_md = render_readme_md(data, metrics)

    if args.check:
        drift: list[str] = []
        if not ROADMAP_MD_PATH.exists() or ROADMAP_MD_PATH.read_text(encoding="utf-8") != roadmap_md:
            drift.append("ROADMAP.md is out of sync with roadmap.yaml")
        if not README_MD_PATH.exists() or README_MD_PATH.read_text(encoding="utf-8") != readme_md:
            drift.append("README.md is out of sync with roadmap.yaml")
        if drift:
            for d in drift:
                print(f"ERROR: {d}. Run 'python3 scripts/build.py' to regenerate.", file=sys.stderr)
            return 1
        print(
            f"OK: Validated {len(metrics['sys_metrics'])} systems, {metrics['total_steps']} steps "
            f"({metrics['total_couch']} couch / {metrics['total_bench']} bench), and "
            f"{metrics['total_approved']} approved; chapters, ROADMAP.md, and README.md are 100% in sync."
        )
        return 0

    ROADMAP_MD_PATH.write_text(roadmap_md, encoding="utf-8")
    README_MD_PATH.write_text(readme_md, encoding="utf-8")
    print(
        f"OK: Validated {len(metrics['sys_metrics'])} systems, {metrics['total_steps']} steps "
        f"({metrics['total_couch']} couch / {metrics['total_bench']} bench), and "
        f"{metrics['total_approved']} approved; generated ROADMAP.md and README.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
