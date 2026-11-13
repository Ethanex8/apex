#!/usr/bin/env python3
"""Validate roadmap.yaml invariants and generate ROADMAP.md and README.md."""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
import re
import sys
import yaml


ROOT_DIR = Path(__file__).resolve().parent.parent
ROADMAP_YAML_PATH = ROOT_DIR / "roadmap.yaml"
ROADMAP_MD_PATH = ROOT_DIR / "ROADMAP.md"
README_MD_PATH = ROOT_DIR / "README.md"

VALID_MODES = {"couch", "bench"}
VALID_STATUSES = {"pending", "in_review", "approved"}


def render_progress_bar(pct: float, width: int = 12) -> str:
    filled = round(max(0.0, min(100.0, pct)) / 100.0 * width)
    return "█" * filled + "░" * (width - filled)


def validate_roadmap(data: dict) -> list[str]:
    """Validate all schema, DAG, phase, and step invariants in roadmap.yaml."""
    errors: list[str] = []

    for top_key in ("repository", "safety_guardrails", "phased_procurement", "systems", "steps"):
        if top_key not in data or not data[top_key]:
            errors.append(f"Missing or empty top-level section '{top_key}' in roadmap.yaml")

    systems = data.get("systems", [])
    steps = data.get("steps", [])

    sys_by_id: dict[str, dict] = {}
    phase_to_sys: dict[str, str] = {}
    for idx, sys_obj in enumerate(systems, 1):
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

        for p in sys_obj.get("phases", []):
            pid = p.get("id")
            if not pid:
                errors.append(f"[{sid}] Phase missing 'id'")
                continue
            if pid in phase_to_sys:
                errors.append(f"[{sid}] Duplicate phase id '{pid}'")
            if not str(pid).startswith(f"{sid}-"):
                errors.append(f"[{sid}] Phase id '{pid}' must start with '{sid}-'")
            if not p.get("name"):
                errors.append(f"[{sid}] Phase '{pid}' missing 'name'")
            phase_to_sys[pid] = sid

    # Validate system dependency DAG acyclicity
    indegree: dict[str, int] = {sid: 0 for sid in sys_by_id}
    adj: dict[str, list[str]] = defaultdict(list)
    for sid, sys_obj in sys_by_id.items():
        for dep in sys_obj.get("depends_on", []):
            if dep not in sys_by_id:
                errors.append(f"[{sid}] Unknown dependency '{dep}' in depends_on")
            elif dep == sid:
                errors.append(f"[{sid}] Self-dependency in depends_on")
            else:
                adj[dep].append(sid)
                indegree[sid] += 1

    q = deque([sid for sid, deg in indegree.items() if deg == 0])
    visited = 0
    while q:
        cur = q.popleft()
        visited += 1
        for nxt in adj[cur]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                q.append(nxt)
    if visited != len(sys_by_id):
        errors.append("Cycle detected in systems depends_on graph")

    # Validate all steps
    seen_steps: set[str] = set()
    sys_step_nums: dict[str, list[int]] = defaultdict(list)
    for step in steps:
        step_id = step.get("id")
        if not step_id:
            errors.append("Step missing 'id'")
            continue
        if step_id in seen_steps:
            errors.append(f"Duplicate step id '{step_id}'")
        seen_steps.add(step_id)

        sid = step.get("system")
        pid = step.get("phase")
        if sid not in sys_by_id:
            errors.append(f"[{step_id}] Unknown system '{sid}'")
        if pid not in phase_to_sys:
            errors.append(f"[{step_id}] Unknown phase '{pid}'")
        elif sid in sys_by_id and phase_to_sys[pid] != sid:
            errors.append(f"[{step_id}] Phase '{pid}' belongs to '{phase_to_sys[pid]}', not '{sid}'")

        m = re.match(r"^([a-z][a-z0-9_-]*)-(\d{2})$", str(step_id))
        if not m:
            errors.append(f"[{step_id}] Step id must follow '<system>-NN' format")
        else:
            if m.group(1) != sid:
                errors.append(f"[{step_id}] Step prefix '{m.group(1)}' does not match system '{sid}'")
            sys_step_nums[sid].append(int(m.group(2)))

        mode = step.get("mode")
        if mode not in VALID_MODES:
            errors.append(f"[{step_id}] Invalid mode '{mode}' (expected one of {sorted(VALID_MODES)})")

        status = step.get("status")
        if status not in VALID_STATUSES:
            errors.append(
                f"[{step_id}] Invalid status '{status}' (expected one of {sorted(VALID_STATUSES)})"
            )

        if status == "approved" and step.get("approved_date"):
            try:
                datetime.strptime(str(step["approved_date"]), "%Y-%m-%d")
            except ValueError:
                errors.append(
                    f"[{step_id}] Invalid approved_date '{step['approved_date']}' (expected YYYY-MM-DD)"
                )

        if not step.get("title"):
            errors.append(f"[{step_id}] Missing 'title'")
        deliverables = step.get("deliverables")
        if not isinstance(deliverables, list) or not deliverables:
            errors.append(f"[{step_id}] 'deliverables' must be a non-empty list")
        if not step.get("verification"):
            errors.append(f"[{step_id}] Missing 'verification'")
        if not step.get("first_principles"):
            errors.append(f"[{step_id}] Missing 'first_principles'")
        if not step.get("reference_reading"):
            errors.append(f"[{step_id}] Missing 'reference_reading'")

    # Ensure sequential 1..N step numbering per system
    for sid, nums in sys_step_nums.items():
        expected = list(range(1, len(nums) + 1))
        if nums != expected:
            errors.append(f"[{sid}] Step numbers must be sequential 01..{len(nums):02d}, got {nums}")

    for sid in sys_by_id:
        if not sys_step_nums.get(sid):
            errors.append(f"[{sid}] System has 0 steps")

    return errors


def compute_metrics(data: dict) -> dict:
    """Compute progress metrics per system, phase, and across the entire robot."""
    systems = data["systems"]
    steps = data["steps"]

    steps_by_sys: dict[str, list[dict]] = defaultdict(list)
    steps_by_phase: dict[str, list[dict]] = defaultdict(list)
    for st in steps:
        steps_by_sys[st["system"]].append(st)
        steps_by_phase[st["phase"]].append(st)

    sys_metrics: list[dict] = []
    total_approved = 0
    total_in_review = 0
    total_couch = 0
    total_couch_done = 0
    total_bench = 0
    total_bench_done = 0

    for sys_obj in systems:
        sid = sys_obj["id"]
        s_steps = steps_by_sys[sid]
        approved = sum(1 for s in s_steps if s["status"] == "approved")
        in_review = sum(1 for s in s_steps if s["status"] == "in_review")
        couch = sum(1 for s in s_steps if s["mode"] == "couch")
        couch_done = sum(1 for s in s_steps if s["mode"] == "couch" and s["status"] == "approved")
        bench = sum(1 for s in s_steps if s["mode"] == "bench")
        bench_done = sum(1 for s in s_steps if s["mode"] == "bench" and s["status"] == "approved")

        total_approved += approved
        total_in_review += in_review
        total_couch += couch
        total_couch_done += couch_done
        total_bench += bench
        total_bench_done += bench_done

        pct = (approved / len(s_steps) * 100.0) if s_steps else 0.0
        if approved == len(s_steps):
            sys_status = "completed"
        elif approved > 0 or in_review > 0:
            sys_status = "in_progress"
        else:
            sys_status = "ready" if not sys_obj.get("depends_on") else "queued"

        next_step = next((s for s in s_steps if s["status"] != "approved"), None)

        phase_stats = []
        for p in sys_obj["phases"]:
            ps = steps_by_phase[p["id"]]
            p_done = sum(1 for s in ps if s["status"] == "approved")
            p_couch = sum(1 for s in ps if s["mode"] == "couch")
            p_bench = sum(1 for s in ps if s["mode"] == "bench")
            phase_stats.append(
                {
                    "id": p["id"],
                    "name": p["name"],
                    "total": len(ps),
                    "done": p_done,
                    "couch": p_couch,
                    "bench": p_bench,
                    "pct": (p_done / len(ps) * 100.0) if ps else 0.0,
                    "steps": ps,
                }
            )

        sys_metrics.append(
            {
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
                "next_step": next_step,
                "phases": phase_stats,
            }
        )

    active_step = next((s for s in steps if s["status"] == "in_review"), None)
    if active_step is None:
        active_step = next((s for s in steps if s["status"] == "pending"), None)

    return {
        "total_steps": len(steps),
        "total_approved": total_approved,
        "total_in_review": total_in_review,
        "total_couch": total_couch,
        "total_couch_done": total_couch_done,
        "total_bench": total_bench,
        "total_bench_done": total_bench_done,
        "pct_total": (total_approved / len(steps) * 100.0) if steps else 0.0,
        "pct_couch": (total_couch / len(steps) * 100.0) if steps else 0.0,
        "sys_metrics": sys_metrics,
        "active_step": active_step,
    }


def status_badge(status: str) -> str:
    return {
        "approved": "✅ Approved",
        "in_review": "🔍 In Review",
        "pending": "⬜ Pending",
    }[status]


def mode_badge(mode: str) -> str:
    return "🛋️ Couch" if mode == "couch" else "🔧 Bench"


def render_roadmap_md(data: dict, metrics: dict) -> str:
    repo = data["repository"]
    lines: list[str] = []

    lines.append("# Apex Engineering Roadmap (Couch-to-Silicon)")
    lines.append("")
    lines.append(
        f"Generated from [`roadmap.yaml`](./roadmap.yaml). Tracks **{len(metrics['sys_metrics'])} integrated systems** "
        f"and **{metrics['total_steps']} atomic steps** "
        f"(**{metrics['total_couch']} couch** `{metrics['pct_couch']:.0f}%` / **{metrics['total_bench']} bench**) "
        f"building one cohesive `{repo['robot_class']}`."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Overall Progress")
    lines.append("")
    lines.append(
        f"- **Total Completion**: `{render_progress_bar(metrics['pct_total'], 16)}` "
        f"**{metrics['total_approved']} / {metrics['total_steps']} steps** (`{metrics['pct_total']:.1f}%`)"
    )
    lines.append(
        f"- **Couch Steps**: **{metrics['total_couch_done']} / {metrics['total_couch']}** · "
        f"**Bench Sessions**: **{metrics['total_bench_done']} / {metrics['total_bench']}**"
    )
    if metrics["active_step"]:
        st = metrics["active_step"]
        lines.append(
            f"- **Active Step**: **`{st['id']}`** ({mode_badge(st['mode'])}, {status_badge(st['status'])}) — {st['title']}"
        )
    lines.append("")
    lines.append("| # | System | Role | Progress | Couch / Bench | Est. Timeline | Workspace |")
    lines.append("| :---: | :--- | :--- | :--- | :---: | :---: | :--- |")
    for sm in metrics["sys_metrics"]:
        sys_obj = sm["system"]
        bar = render_progress_bar(sm["pct"], 10)
        lines.append(
            f"| **{sys_obj['order']}** | [`{sys_obj['id']}`](#{sys_obj['id']}-{re.sub(r'[^a-z0-9-]+', '', sys_obj['name'].lower().replace(' ', '-'))}) "
            f"— {sys_obj['name']} | {sys_obj['role']} | "
            f"`{bar}` {sm['approved']}/{sm['total']} (`{sm['pct']:.0f}%`) | "
            f"{sm['couch']} / {sm['bench']} | {sys_obj['est_weeks']} | [{sys_obj['workspace']}]({sys_obj['workspace']}) |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## System Dependency Graph")
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart LR")
    for sm in metrics["sys_metrics"]:
        sys_obj = sm["system"]
        sid = sys_obj["id"]
        lines.append(f'    {sid}["{sys_obj["order"]}. {sid}<br/>{sm["approved"]}/{sm["total"]} steps"]')
    for sm in metrics["sys_metrics"]:
        sid = sm["system"]["id"]
        for dep in sm["system"].get("depends_on", []):
            lines.append(f"    {dep} --> {sid}")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Home Safety & Phased Procurement")
    lines.append("")
    for sg in data["safety_guardrails"]:
        lines.append(f"- **{sg['name']}**: {sg['description']}")
    lines.append("")
    lines.append("| Stage | Est. Cost | What You Order |")
    lines.append("| :--- | :---: | :--- |")
    for item in data["phased_procurement"]:
        lines.append(f"| **{item['stage']}** | **{item['est_cost_usd']}** | {item['items']} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## System-by-System Execution Plan")
    lines.append("")

    for sm in metrics["sys_metrics"]:
        sys_obj = sm["system"]
        sid = sys_obj["id"]
        lines.append(f"### {sys_obj['order']}. `{sid}` — {sys_obj['name']}")
        lines.append("")
        lines.append(f"- **Role**: {sys_obj['role']}")
        lines.append(f"- **Workspace**: [`{sys_obj['workspace']}`]({sys_obj['workspace']})")
        deps = ", ".join(f"`{d}`" for d in sys_obj.get("depends_on", [])) or "None (Start Here)"
        lines.append(f"- **Builds On**: {deps}")
        lines.append(f"- **Graduation Demo**: {sys_obj['graduation_demo']}")
        lines.append(
            f"- **Progress**: `{render_progress_bar(sm['pct'], 12)}` **{sm['approved']} / {sm['total']}** "
            f"(`{sm['couch']}` couch / `{sm['bench']}` bench)"
        )
        lines.append("")
        lines.append("| Phase | Steps Done | Couch / Bench | Progress |")
        lines.append("| :--- | :---: | :---: | :--- |")
        for ph in sm["phases"]:
            lines.append(
                f"| **{ph['name']}** | {ph['done']} / {ph['total']} | {ph['couch']} / {ph['bench']} | "
                f"`{render_progress_bar(ph['pct'], 10)}` `{ph['pct']:.0f}%` |"
            )
        lines.append("")
        lines.append(f"<details>")
        lines.append(f"<summary><strong>View All {sm['total']} Steps for <code>{sid}</code></strong></summary>")
        lines.append("")
        for ph in sm["phases"]:
            lines.append(f"#### {ph['name']}")
            lines.append("")
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
        lines.append("</details>")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_readme_md(data: dict, metrics: dict) -> str:
    repo = data["repository"]
    lines: list[str] = []

    lines.append(f"# {repo['title']}")
    lines.append("")
    lines.append(repo["tagline"])
    lines.append("")
    lines.append(f"- **Target Machine**: {repo['robot_class']}")
    lines.append(f"- **Estimated Cost**: {repo['estimated_total_bom_usd']}")
    lines.append(
        f"- **Workflow**: **{metrics['total_couch']} / {metrics['total_steps']} steps (`{metrics['pct_couch']:.0f}%`)** "
        f"built by AI agents & verified in simulation or automated board checks for mobile **couch review**, paired with "
        f"**{metrics['total_bench']} batched weekend bench sessions**."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Active Step Queue")
    lines.append("")
    if metrics["active_step"]:
        st = metrics["active_step"]
        lines.append(
            f"**Current Focus**: **`{st['id']}`** ({mode_badge(st['mode'])} · {status_badge(st['status'])}) — **{st['title']}**"
        )
        lines.append("")
        lines.append(f"- **First Principles**: {st['first_principles']}")
        lines.append(f"- **Verification Gate**: `{st['verification']}`")
    else:
        lines.append("All 186 steps completed!")
    lines.append("")
    lines.append("```bash")
    lines.append("python3 scripts/step.py status          # Progress across all 6 systems")
    lines.append("python3 scripts/step.py next            # Inspect next pending step & verification gate")
    lines.append("python3 scripts/build.py --check        # Validate roadmap invariants & zero doc drift")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## The 6 Zero-Throwaway Systems")
    lines.append("")
    lines.append("| # | System | What It Builds | Steps (Done / Total) | Couch / Bench | Timeline |")
    lines.append("| :---: | :--- | :--- | :---: | :---: | :---: |")
    for sm in metrics["sys_metrics"]:
        sys_obj = sm["system"]
        bar = render_progress_bar(sm["pct"], 8)
        lines.append(
            f"| **{sys_obj['order']}** | [**`{sys_obj['id']}`**]({sys_obj['workspace']}) | "
            f"{sys_obj['name']} | `{bar}` **{sm['approved']} / {sm['total']}** | "
            f"{sm['couch']} / {sm['bench']} | {sys_obj['est_weeks']} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Repository Guide")
    lines.append("")
    lines.append("- [**`VISION.md`**](./VISION.md) — Two-Brain architecture, locked hardware/protocol interfaces, home safety & parts budget.")
    lines.append("- [**`ROADMAP.md`**](./ROADMAP.md) — Full phase breakdowns, ordering schedule & all 186 step checklists.")
    lines.append("- [**`roadmap.yaml`**](./roadmap.yaml) — Canonical declarative source of truth for systems, steps & review state.")
    lines.append("- [**`systems/`**](./systems/brain/README.md) — Subsystem workspaces (`brain`, `drive`, `power`, `limb`, `walker`, `sight`).")
    lines.append("- [**`scripts/step.py`**](./scripts/step.py) & [**`scripts/build.py`**](./scripts/build.py) — Step lifecycle CLI, invariant validator & Markdown generator.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## How Couch-to-Silicon Works")
    lines.append("")
    lines.append("1. **Agent Implements & Verifies One Atomic Step (roughly 50–150 LOC)**: Runs real `Verilator` digital simulations, `Yosys`/`nextpnr` FPGA builds, KiCad circuit-board checks (`ERC`/`DRC`), trace-impedance solvers, `MuJoCo` physics, or `pytest` inside the VM.")
    lines.append("2. **You Review From Your Phone**: Inspect a 5-minute Textbook First-Principles Brief, interactive visual diagrams/waveforms/copper-layer renders, a guided PR diff, and 2–3 intuition checks.")
    lines.append("3. **Ask Why, Then `LGTM`**: Interrogate any derivation or trade-off; the agent is blocked from starting Step `N+1` until you approve Step `N`.")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate invariants and check if ROADMAP.md and README.md are up to date without writing.",
    )
    args = parser.parse_args(argv)

    if not ROADMAP_YAML_PATH.exists():
        print("ERROR: roadmap.yaml not found.", file=sys.stderr)
        return 1

    with open(ROADMAP_YAML_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    errors = validate_roadmap(data)
    if errors:
        print("Roadmap invariant validation FAILED:", file=sys.stderr)
        for err in errors:
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
            f"{metrics['total_approved']} approved; ROADMAP.md and README.md are 100% in sync."
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
