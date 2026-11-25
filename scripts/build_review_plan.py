#!/usr/bin/env python3
"""Generate deterministic, overlapping, zero-bias textbook and code review plans.

Purpose:
  Eliminate ad-hoc orchestrator prompt steering and cross-shard boundary misses
  by partitioning textbook chapters and large code artifacts into aligned
  overlapping shards, verifying `docs/CHAPTER_INDEX.md` freshness, compiling
  Prior-Section Ledgers, binding exact widget/code/diff seams, supporting
  deterministic Round r+1 scoped re-convergence (`--changed-since`), and
  emitting frozen, content-agnostic subagent prompts backed by `rubric_*.md`.

Usage:
  python3 scripts/build_review_plan.py --chapter systems/brain/chapters/01_isa_and_binary_arithmetic.md
  python3 scripts/build_review_plan.py --code systems/brain/sim/oracle.py --base-ref HEAD~1
  python3 scripts/build_review_plan.py --chapter <chap> --base-ref <pre_fix> --changed-since <r1_sha>

Outputs:
  Prints a Markdown or JSON review execution manifest detailing all shard ranges,
  boundary overlaps, Prior-Section Ledgers, widget/code seams, and frozen prompts.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import chapter_index  # noqa: E402 — repo scripts run standalone without package install

ROOT_DIR = SCRIPT_DIR.parent
DEFAULT_TARGET_LINES = 450
DEFAULT_OVERLAP_LINES = 50
MAX_LEDGER_ITEMS = 250

H2_RE = re.compile(r"^##\s+(.+)$")
H3_RE = re.compile(r"^###\s+(.+)$")
H4_EX_RE = re.compile(r"^####\s+(Example\b.+)$", re.IGNORECASE)
FENCE_TOGGLE_RE = re.compile(r"^(`{3,}|~{3,})")
VUE_COMPONENT_RE = re.compile(r"^<([A-Z][A-Za-z0-9]*)(?:\s*/>|\s|>).*$")
TRANSCLUDE_SLICE_RE = re.compile(r"^<<<\s+(@/[^\s{#\[]+|\.\.?/[^\s{#\[]+)(?:#L(\d+)(?:-L?(\d+))?)?")
INLINE_BOLD_RE = re.compile(r"\*\*([^*\n]{2,60})\*\*")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
INLINE_MATH_RE = re.compile(r"(?<!\\)\$\$(?:\\.|[^$])*?(?<!\\)\$\$|(?<!\\)\$(?:\\.|[^$\\])*?(?<!\\)\$")
MATH_TOKEN_RE = re.compile(
    r"\\operatorname\{[A-Za-z0-9_]+\}|\\(?:gcd|lfloor|rfloor|lceil|rceil|pmod|bmod)\b"
    r"|\b[A-Za-z][A-Za-z0-9]*_\{?[A-Za-z0-9\\]+\}?"
)
DIFF_HUNK_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")
STRUCTURAL_EDIT_RE = re.compile(r"^(?:#{2,4}\s+|\$\$)|(?:\*\*[^*\n]{2,60}\*\*)")
SV_BLOCK_RE = re.compile(r"^\s*(?:module|function|task)\s+([A-Za-z_]\w*)\b")
C_FUNC_START_RE = re.compile(r"^(?:[A-Za-z_][\w\s\*]*?[\s\*])([A-Za-z_]\w*)\s*\([^;]*$")

RUBRIC_PATHS = {
    "cold_reader": ".agents/skills/technical-writing-author/references/rubric_cold_reader.md",
    "math_editor": ".agents/skills/technical-writing-author/references/rubric_math_editor.md",
    "macro_critic": ".agents/skills/technical-writing-author/references/rubric_macro_critic.md",
    "visual_critic": ".agents/skills/technical-writing-author/references/rubric_visual_critic.md",
    "diff_guardian": ".agents/skills/technical-writing-author/references/rubric_diff_guardian.md",
    "code_arch": ".agents/skills/code-author/references/rubric_code_arch.md",
    "code_clarity": ".agents/skills/code-author/references/rubric_code_clarity.md",
}

ISOLATION_PROHIBITION = (
    "ISOLATION RULE: Do NOT read `/tmp/`, `*triage*`, `*calibration_log*`, "
    "`docs/calibration/*`, session transcripts, `git log`, or run `gh`. "
    "Evaluate strictly the files and line ranges listed below."
)


@dataclass
class SectionUnit:
    """Atomic contiguous line span aligned to a heading or code-unit boundary."""

    start_line: int
    end_line: int
    heading: str


@dataclass
class ShardSpec:
    """One overlapping review shard plus its exact widget and code-slice seams."""

    index: int
    total: int
    start_line: int
    end_line: int
    overlap_prev: tuple[int, int] | None
    overlap_next: tuple[int, int] | None
    headings: list[str] = field(default_factory=list)
    widgets: list[str] = field(default_factory=list)
    transclusions: list[str] = field(default_factory=list)


@dataclass
class PriorLedger:
    """Deterministic inventory of terms, code tokens, and math symbols before a shard."""

    headings: list[str] = field(default_factory=list)
    bold_terms: list[str] = field(default_factory=list)
    code_tokens: list[str] = field(default_factory=list)
    math_symbols: list[str] = field(default_factory=list)
    exercises: list[str] = field(default_factory=list)
    bold_overflow: int = 0
    code_overflow: int = 0
    math_overflow: int = 0


@dataclass
class SubagentTask:
    """Frozen, zero-bias subagent invocation specification."""

    role: str
    type_name: str
    rubric_path: str
    allowed_files: list[str]
    prompt: str


@dataclass
class ReviewPlan:
    """Complete sharded, global, code, and regression-check review manifest."""

    chapter: str | None
    slug: str
    total_lines: int
    base_ref: str | None
    changed_since: str | None
    scope_note: str
    code_files: list[str] = field(default_factory=list)
    shards: list[ShardSpec] = field(default_factory=list)
    tasks: list[SubagentTask] = field(default_factory=list)


@dataclass
class ShardSpan:
    """Contiguous primary line span grouped from one or more section units."""

    start_line: int
    end_line: int
    headings: list[str]


@dataclass
class DiffChangeSummary:
    """Line-level diff impact extracted since `--changed-since` for scoped re-reviews."""

    touched_lines: set[int]
    structural_change: bool
    visual_change: bool


def _collect_section_units(lines: list[str], target_lines: int) -> list[SectionUnit]:
    """Partition `lines` into `##` blocks, splitting oversized blocks at `###` headings."""
    h2_starts: list[tuple[int, str]] = []
    in_fence = False
    for idx, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if FENCE_TOGGLE_RE.match(stripped):
            in_fence = not in_fence
            continue
        if not in_fence and H2_RE.match(stripped):
            h2_starts.append((idx, stripped))

    if not h2_starts:
        return [SectionUnit(1, max(1, len(lines)), "(Full Chapter)")]

    units: list[SectionUnit] = []
    for pos, (h2_line, h2_title) in enumerate(h2_starts):
        span_start = 1 if pos == 0 else h2_line
        span_end = (h2_starts[pos + 1][0] - 1) if pos + 1 < len(h2_starts) else len(lines)
        if span_end - span_start + 1 <= target_lines:
            units.append(SectionUnit(span_start, span_end, h2_title))
        else:
            units.extend(_split_oversized_h2(lines, span_start, span_end, h2_title))
    return units


def _split_oversized_h2(
    lines: list[str], span_start: int, span_end: int, h2_title: str
) -> list[SectionUnit]:
    """Split an oversized `##` section along `###` boundaries without breaking subsections."""
    h3_starts: list[tuple[int, str]] = []
    in_fence = False
    for idx in range(span_start, span_end + 1):
        stripped = lines[idx - 1].strip()
        if FENCE_TOGGLE_RE.match(stripped):
            in_fence = not in_fence
            continue
        if not in_fence and H3_RE.match(stripped):
            h3_starts.append((idx, stripped))

    if len(h3_starts) <= 1:
        return [SectionUnit(span_start, span_end, h2_title)]

    sub_units: list[SectionUnit] = []
    for pos, (h3_line, h3_title) in enumerate(h3_starts):
        sub_start = span_start if pos == 0 else h3_line
        sub_end = (h3_starts[pos + 1][0] - 1) if pos + 1 < len(h3_starts) else span_end
        sub_units.append(SectionUnit(sub_start, sub_end, h3_title))
    return sub_units


def _pack_units_into_ranges(
    units: list[SectionUnit], target_lines: int
) -> list[ShardSpan]:
    """Greedily pack contiguous `SectionUnit` spans into shards capped near `target_lines`."""
    packed: list[ShardSpan] = []
    cur_start = units[0].start_line
    cur_end = units[0].end_line
    cur_headings = [units[0].heading]

    for unit in units[1:]:
        candidate_len = unit.end_line - cur_start + 1
        if candidate_len <= target_lines:
            cur_end = unit.end_line
            cur_headings.append(unit.heading)
        else:
            packed.append(ShardSpan(cur_start, cur_end, cur_headings))
            cur_start = unit.start_line
            cur_end = unit.end_line
            cur_headings = [unit.heading]
    packed.append(ShardSpan(cur_start, cur_end, cur_headings))
    return packed


def _index_vue_components(root_dir: Path) -> dict[str, str]:
    """Map Vue component tag names to repository-relative `.vue` file paths."""
    comp_dir = root_dir / "book" / ".vitepress" / "theme" / "components"
    if not comp_dir.is_dir():
        return {}
    mapping: dict[str, str] = {}
    for vue_path in sorted(comp_dir.rglob("*.vue")):
        mapping[vue_path.stem] = vue_path.relative_to(root_dir).as_posix()
    return mapping


def _resolve_transclusion_target(chapter_path: Path, raw_target: str, root_dir: Path) -> str:
    """Resolve `@/...` or relative `<<<` slice path into a repo-relative POSIX string."""
    if raw_target.startswith("@/"):
        candidate = root_dir / raw_target[2:]
    else:
        candidate = (chapter_path.parent / raw_target).resolve()
    try:
        return candidate.resolve().relative_to(root_dir.resolve()).as_posix()
    except ValueError:
        return raw_target


def _collect_shard_seams(
    lines: list[str],
    start_line: int,
    end_line: int,
    chapter_path: Path,
    root_dir: Path,
    vue_map: dict[str, str],
) -> tuple[list[str], list[str]]:
    """Return `(widget_seams, transclusion_seams)` occurring within `[start_line, end_line]`."""
    widgets: list[str] = []
    transclusions: list[str] = []
    in_fence = False
    for idx in range(start_line, end_line + 1):
        stripped = lines[idx - 1].strip()
        if FENCE_TOGGLE_RE.match(stripped):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if wm := VUE_COMPONENT_RE.match(stripped):
            tag = wm.group(1)
            rel_vue = vue_map.get(tag, f"<unresolved:{tag}.vue>")
            widgets.append(f"L{idx}: <{tag} /> -> {rel_vue}")
        if tm := TRANSCLUDE_SLICE_RE.match(stripped):
            rel_src = _resolve_transclusion_target(chapter_path, tm.group(1), root_dir)
            frag = f"#L{tm.group(2)}-L{tm.group(3)}" if tm.group(2) and tm.group(3) else ""
            transclusions.append(f"L{idx}: {rel_src}{frag}")
    return widgets, transclusions


def _dedupe_capped(items: list[str], limit: int) -> tuple[list[str], int]:
    """Preserve first-seen order while deduplicating, returning `(kept, overflow_count)`."""
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique[:limit], max(0, len(unique) - limit)


def _build_prior_ledger(lines: list[str], before_line: int) -> PriorLedger:
    """Compile headings, bold terms, code tokens, math symbols, and exercises before `before_line`."""
    if before_line <= 1:
        return PriorLedger()
    headings: list[str] = []
    bold_terms: list[str] = []
    code_tokens: list[str] = []
    math_symbols: list[str] = []
    exercises: list[str] = []
    in_fence = False
    in_display_math = False
    for raw in lines[: before_line - 1]:
        stripped = raw.strip()
        if FENCE_TOGGLE_RE.match(stripped):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped == "$$":
            in_display_math = not in_display_math
            continue
        if in_display_math:
            math_symbols.extend(MATH_TOKEN_RE.findall(stripped))
            continue
        if H2_RE.match(stripped) or H3_RE.match(stripped):
            headings.append(stripped)
            continue
        if em := H4_EX_RE.match(stripped):
            exercises.append(em.group(1))
            continue
        for bmatch in INLINE_BOLD_RE.finditer(stripped):
            term = bmatch.group(1).strip().rstrip(":")
            if term and not term.startswith(("Note", "Solution")):
                bold_terms.append(term)
        for cmatch in INLINE_CODE_RE.finditer(stripped):
            tok = cmatch.group(1).strip()
            if tok and len(tok) <= 32:
                code_tokens.append(tok)
        for mmatch in INLINE_MATH_RE.finditer(stripped):
            math_symbols.extend(MATH_TOKEN_RE.findall(mmatch.group(0)))

    kept_bold, bold_ov = _dedupe_capped(bold_terms, MAX_LEDGER_ITEMS)
    kept_code, code_ov = _dedupe_capped(code_tokens, MAX_LEDGER_ITEMS)
    kept_math, math_ov = _dedupe_capped(math_symbols, MAX_LEDGER_ITEMS)
    return PriorLedger(
        headings=headings,
        bold_terms=kept_bold,
        code_tokens=kept_code,
        math_symbols=kept_math,
        exercises=exercises,
        bold_overflow=bold_ov,
        code_overflow=code_ov,
        math_overflow=math_ov,
    )


def _format_ledger_summary(ledger: PriorLedger) -> str:
    """Format a `PriorLedger` into compact context lines for a shard prompt."""
    if not ledger.headings and not ledger.bold_terms and not ledger.code_tokens and not ledger.math_symbols:
        return "Prior-Section Ledger: (none — this is Shard 1 starting at Line 1)."
    parts = ["Prior-Section Ledger (already defined before this shard):"]
    if ledger.headings:
        parts.append("  - Headings: " + " | ".join(ledger.headings))
    if ledger.bold_terms:
        tail = f" (+{ledger.bold_overflow} more)" if ledger.bold_overflow else ""
        parts.append("  - Defined terms: " + ", ".join(ledger.bold_terms) + tail)
    if ledger.code_tokens:
        tail = f" (+{ledger.code_overflow} more)" if ledger.code_overflow else ""
        parts.append("  - Code/operator tokens: " + ", ".join(f"`{t}`" for t in ledger.code_tokens) + tail)
    if ledger.math_symbols:
        tail = f" (+{ledger.math_overflow} more)" if ledger.math_overflow else ""
        parts.append("  - Math symbols/macros: " + ", ".join(f"`{m}`" for m in ledger.math_symbols) + tail)
    if ledger.exercises:
        parts.append("  - Earlier examples: " + "; ".join(ledger.exercises))
    return "\n".join(parts)


def _render_shard_task(
    role_prefix: str,
    rubric_key: str,
    chapter_rel: str,
    shard: ShardSpec,
    ledger: PriorLedger,
    extra_files: list[str],
) -> SubagentTask:
    """Render one deterministic, content-agnostic shard audit task."""
    rubric_rel = RUBRIC_PATHS[rubric_key]
    prev_txt = f"L{shard.overlap_prev[0]}-L{shard.overlap_prev[1]}" if shard.overlap_prev else "none"
    next_txt = f"L{shard.overlap_next[0]}-L{shard.overlap_next[1]}" if shard.overlap_next else "none"
    widget_txt = "\n".join(f"  - {w}" for w in shard.widgets) if shard.widgets else "  - (none in this shard)"
    slice_txt = (
        "\n".join(f"  - {s}" for s in shard.transclusions)
        if shard.transclusions
        else "  - (none in this shard)"
    )
    allowed = [
        "GEMINI.md",
        "docs/CHAPTER_INDEX.md",
        rubric_rel,
        f"{chapter_rel}#L{shard.start_line}-L{shard.end_line}",
        *extra_files,
    ]
    prompt = "\n".join([
        f"You are `{role_prefix}` auditing Shard {shard.index}/{shard.total} of `{chapter_rel}`.",
        ISOLATION_PROHIBITION,
        f"1. Read `GEMINI.md`, `docs/CHAPTER_INDEX.md`, and `{rubric_rel}` completely before reading the chapter slice.",
        (
            f"2. Audit `{chapter_rel}` primary lines **L{shard.start_line}..L{shard.end_line}** "
            f"(read-only boundary context: previous overlap `{prev_txt}`, next overlap `{next_txt}`)."
        ),
        "3. Inspect every widget and code slice listed below at its exact Markdown insertion line:",
        "Widgets:\n" + widget_txt,
        "Transcluded code slices:\n" + slice_txt,
        _format_ledger_summary(ledger),
        (
            "4. Check every rubric item systematically. Report P0 (critical), P1 (major), or P2 (minor) "
            "findings with exact line numbers and fixes, or output `ZERO P0/P1/P2 DEFECTS FOUND`."
        ),
    ])
    return SubagentTask(
        role=f"{role_prefix} (Shard {shard.index}/{shard.total})",
        type_name="research",
        rubric_path=rubric_rel,
        allowed_files=allowed,
        prompt=prompt,
    )


def _render_macro_task(chapter_rel: str, total_lines: int) -> SubagentTask:
    """Render the dedicated whole-chapter macro architecture and dependency audit task."""
    rubric_rel = RUBRIC_PATHS["macro_critic"]
    allowed = ["GEMINI.md", "docs/CHAPTER_INDEX.md", rubric_rel, chapter_rel]
    prompt = "\n".join([
        f"You are `Global Macro & Dependency Critic` auditing `{chapter_rel}` (`1..{total_lines}`).",
        ISOLATION_PROHIBITION,
        f"1. Read `GEMINI.md`, `docs/CHAPTER_INDEX.md`, and `{rubric_rel}` completely.",
        (
            f"2. For every section and subsection in `docs/CHAPTER_INDEX.md`, read its opening lines in "
            f"`{chapter_rel}` and verify each topic sits cleanly with its prerequisite representations "
            "or first motivating subsystem rather than floating detached."
        ),
        (
            "3. Audit base-before-custom layering, end-to-end rigor balance, selective `#### Example` scoping, "
            "absence of problem sets or `<details>` drills, and concise headings."
        ),
        "4. Report P0/P1/P2 defects with exact line numbers, or output `ZERO P0/P1/P2 DEFECTS FOUND`.",
    ])
    return SubagentTask(
        role="Global Macro & Dependency Critic",
        type_name="research",
        rubric_path=rubric_rel,
        allowed_files=allowed,
        prompt=prompt,
    )


def _resolve_visual_slug(resolved_chap: Path) -> str:
    """Resolve `check_visuals.py`'s `<system>__<stem>` screenshot subdirectory name."""
    if resolved_chap.parent.name == "chapters" and resolved_chap.parent.parent.name:
        return f"{resolved_chap.parent.parent.name}__{resolved_chap.stem}"
    return resolved_chap.stem


def _visual_cache_status(
    resolved_root: Path, resolved_chap: Path, visual_slug: str
) -> str:
    """Return freshness status (including dark PNG count) under `.cache/visual-audit/<visual_slug>/`."""
    shot_dir = resolved_root / ".cache" / "visual-audit" / visual_slug
    pngs = sorted(shot_dir.glob("*.png")) if shot_dir.is_dir() else []
    if not pngs:
        return "MISSING (run `check_visuals.py` before relying on PNGs)"
    dark_cnt = sum(1 for p in pngs if p.stem.endswith("_dark"))
    latest_png = max(p.stat().st_mtime for p in pngs)
    comp_dir = resolved_root / "book" / ".vitepress" / "theme" / "components"
    sources = [resolved_chap, *(comp_dir.rglob("*.vue") if comp_dir.is_dir() else [])]
    css_file = resolved_root / "book" / ".vitepress" / "theme" / "custom.css"
    if css_file.is_file():
        sources.append(css_file)
    if sources and max(s.stat().st_mtime for s in sources) > latest_png:
        return "STALE (chapter/widgets modified after PNG capture; re-run `check_visuals.py`)"
    return f"FRESH ({len(pngs)} PNGs, {dark_cnt} dark)"


def _render_visual_task(
    chapter_rel: str,
    visual_slug: str,
    cache_status: str,
    total_lines: int,
    all_widgets: list[str],
) -> SubagentTask:
    """Render the visual pedagogy, widget surface, CSS, and MathJax audit task."""
    rubric_rel = RUBRIC_PATHS["visual_critic"]
    shot_rel = f".cache/visual-audit/{visual_slug}/"
    vue_files = sorted({w.split("-> ", 1)[1] for w in all_widgets if "-> " in w and "<unresolved:" not in w})
    widget_txt = "\n".join(f"  - {w}" for w in all_widgets) if all_widgets else "  - (none in chapter)"
    allowed = [
        "GEMINI.md",
        rubric_rel,
        chapter_rel,
        "book/.vitepress/theme/custom.css",
        *vue_files,
        shot_rel,
    ]
    prompt = "\n".join([
        f"You are `Visual Pedagogy Critic` auditing `{chapter_rel}` (`1..{total_lines}`).",
        ISOLATION_PROHIBITION,
        f"1. Read `GEMINI.md` and `{rubric_rel}` completely.",
        "2. Inspect `.vue` widgets at their exact Markdown insertion lines plus `book/.vitepress/theme/custom.css`:",
        widget_txt,
        f"3. Inspect light/dark desktop and mobile screenshots in `{shot_rel}` [Status: {cache_status}] using `{rubric_rel}`.",
        "4. Report P0/P1/P2 defects with exact lines or screenshots, or output `ZERO P0/P1/P2 DEFECTS FOUND`.",
    ])
    return SubagentTask(
        role="Visual Pedagogy Critic",
        type_name="research",
        rubric_path=rubric_rel,
        allowed_files=allowed,
        prompt=prompt,
    )


def _format_untracked_patch(resolved_root: Path, rel_path: str) -> str:
    """Render a synthetic unified diff hunk (`--- /dev/null`) for an untracked file."""
    target = resolved_root / rel_path
    if not target.is_file():
        return ""
    content = target.read_text(encoding="utf-8", errors="replace").splitlines()
    header = [
        f"diff --git a/{rel_path} b/{rel_path}",
        "new file mode 100644",
        "--- /dev/null",
        f"+++ b/{rel_path}",
        f"@@ -0,0 +1,{len(content)} @@",
    ]
    return "\n".join([*header, *(f"+{ln}" for ln in content)]) + "\n"


def _write_diff_patch(
    resolved_root: Path,
    chapter_rel: str | None,
    slug: str,
    base_ref: str,
    code_rels: list[str] | None = None,
) -> str:
    """Write unified diff (tracked + untracked files) since `base_ref` under `.cache/review-diff/`."""
    diff_rel = f".cache/review-diff/{slug}.patch"
    diff_path = resolved_root / diff_rel
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    if not (resolved_root / ".git").exists():
        diff_path.write_text(
            f"# No .git directory under {resolved_root.name}; base_ref={base_ref}\n",
            encoding="utf-8",
        )
        return diff_rel
    pathspecs: list[str] = []
    if chapter_rel:
        pathspecs.extend([chapter_rel, "book/.vitepress/theme/"])
    for crel in code_rels or []:
        if crel not in pathspecs:
            pathspecs.append(crel)
    proc = subprocess.run(
        ["git", "-C", str(resolved_root), "diff", "-U25", base_ref, "--", *pathspecs],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff failed for base_ref '{base_ref}': {proc.stderr.strip()}")
    untracked_proc = subprocess.run(
        ["git", "-C", str(resolved_root), "ls-files", "--others", "--exclude-standard", "--", *pathspecs],
        capture_output=True,
        text=True,
        check=False,
    )
    extra_patches = [
        _format_untracked_patch(resolved_root, rel)
        for rel in untracked_proc.stdout.splitlines()
        if rel.strip()
    ]
    combined = proc.stdout + "".join(extra_patches)
    body = combined if combined.strip() else f"# Empty diff against {base_ref} for {', '.join(pathspecs)}\n"
    diff_path.write_text(body, encoding="utf-8")
    return diff_rel


def _render_diff_guardian_task(
    target_label: str, base_ref: str, diff_rel: str, extra_files: list[str]
) -> SubagentTask:
    """Render the Step 3 before/after flow and boilerplate regression guardian task."""
    rubric_rel = RUBRIC_PATHS["diff_guardian"]
    prompt = "\n".join([
        f"You are `Diff & Flow Regression Guardian` inspecting changes to `{target_label}` since `{base_ref}`.",
        f"ISOLATION RULE: Inspect only `{diff_rel}`, `GEMINI.md`, `{rubric_rel}`, and listed targets. "
        "Do NOT read `/tmp/`, `*triage*`, `*calibration_log*`, `docs/calibration/*`, `git log`, `gh`, or session logs.",
        f"1. Read `GEMINI.md` and `{rubric_rel}` completely.",
        f"2. Read `{diff_rel}` completely (pre-generated unified diff including CSS/widgets/untracked files).",
        (
            "3. Flag any edit that worsens prose flow, introduces prose-math walls, pastes repetitive "
            "rule-compliance boilerplate across items, deletes invariants, or creates forward references."
        ),
        "4. Report P0/P1/P2 regressions with exact lines/hunks, or output `ZERO P0/P1/P2 DEFECTS FOUND`.",
    ])
    return SubagentTask(
        role="Diff & Flow Regression Guardian",
        type_name="research",
        rubric_path=rubric_rel,
        allowed_files=["GEMINI.md", rubric_rel, diff_rel, *extra_files],
        prompt=prompt,
    )


def _check_chapter_index_freshness(resolved_root: Path, allow_stale: bool) -> None:
    """Fail fast when `docs/CHAPTER_INDEX.md` is missing or stale relative to repo chapters."""
    if allow_stale:
        return
    idx_path = resolved_root / "docs" / "CHAPTER_INDEX.md"
    if not idx_path.is_file() and not (resolved_root / "roadmap.yaml").is_file():
        return
    expected = chapter_index.render_chapter_index_md(resolved_root)
    if not idx_path.is_file() or idx_path.read_text(encoding="utf-8") != expected:
        raise RuntimeError(
            "docs/CHAPTER_INDEX.md is missing or stale; run 'python3 scripts/build.py' before building review plan"
        )


def _collect_code_units(code_path: Path, lines: list[str], target_lines: int) -> list[SectionUnit]:
    """Partition large code/RTL/C/Vue files into AST or block-aligned `SectionUnit` spans."""
    if len(lines) <= target_lines:
        return [SectionUnit(1, max(1, len(lines)), code_path.name)]
    suf = code_path.suffix.lower()
    starts: list[tuple[int, str]] = []
    if suf == ".py":
        try:
            tree = ast.parse("\n".join(lines))
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    first = min([d.lineno for d in node.decorator_list] + [node.lineno])
                    starts.append((first, node.name))
        except SyntaxError:
            starts = []
    elif suf in {".sv", ".v"}:
        for i, ln in enumerate(lines, start=1):
            if m := SV_BLOCK_RE.match(ln):
                starts.append((i, m.group(1)))
    elif suf in {".c", ".h"}:
        for i, ln in enumerate(lines, start=1):
            if m := C_FUNC_START_RE.match(ln.strip()):
                starts.append((i, m.group(1)))
    elif suf == ".vue":
        for i, ln in enumerate(lines, start=1):
            if ln.lstrip().startswith(("<script", "<template", "<style")):
                starts.append((i, ln.strip().split(">")[0]))

    if len(starts) <= 1:
        step = max(1, target_lines)
        return [
            SectionUnit(s, min(len(lines), s + step - 1), f"{code_path.name}:L{s}")
            for s in range(1, len(lines) + 1, step)
        ]
    units: list[SectionUnit] = []
    for pos, (s_ln, label) in enumerate(starts):
        span_start = 1 if pos == 0 else s_ln
        span_end = (starts[pos + 1][0] - 1) if pos + 1 < len(starts) else len(lines)
        units.append(SectionUnit(span_start, span_end, label))
    return units


def _discover_code_context_files(resolved_root: Path, code_path: Path) -> list[str]:
    """Return paired `systems/<sys>/README.md` and `tb/test_*.py` files for `code_path` if present."""
    extras: list[str] = []
    try:
        rel_parts = code_path.resolve().relative_to(resolved_root).parts
    except ValueError:
        return extras
    if len(rel_parts) >= 3 and rel_parts[0] == "systems":
        sys_dir = resolved_root / "systems" / rel_parts[1]
        readme = sys_dir / "README.md"
        if readme.is_file():
            extras.append(readme.relative_to(resolved_root).as_posix())
        stem = code_path.stem.removeprefix("test_")
        for cand in (sys_dir / "tb" / f"test_{stem}.py", sys_dir / "sim" / f"{stem}.py"):
            if cand.is_file() and cand.resolve() != code_path.resolve():
                extras.append(cand.relative_to(resolved_root).as_posix())
    return extras


def _render_code_shard_tasks(
    code_rel: str,
    span: ShardSpan,
    idx: int,
    total: int,
    header_end: int,
    context_files: list[str],
) -> list[SubagentTask]:
    """Emit frozen-prompt Architecture & Code Clarity tasks for one code shard."""
    allowed_base = ["GEMINI.md", ".agents/skills/code-author/SKILL.md", *context_files]
    hdr_note = (
        f"Read module context header `L1..L{header_end}` plus primary lines **L{span.start_line}..L{span.end_line}**"
        if idx > 1 and header_end > 0
        else f"Audit `{code_rel}` lines **L{span.start_line}..L{span.end_line}**"
    )
    shard_suffix = f" ({code_rel} Shard {idx}/{total})" if total > 1 else f" ({code_rel})"
    tasks: list[SubagentTask] = []
    for role_base, rubric_key in (
        ("Architecture & Spec-Correctness Auditor", "code_arch"),
        ("Code Readability & Literary Clarity Critic", "code_clarity"),
    ):
        rubric_rel = RUBRIC_PATHS[rubric_key]
        prompt = "\n".join([
            f"You are `{role_base}` auditing `{code_rel}` (Shard {idx}/{total}).",
            ISOLATION_PROHIBITION,
            f"1. Read `GEMINI.md`, `.agents/skills/code-author/SKILL.md`, and `{rubric_rel}` completely.",
            f"2. {hdr_note} of `{code_rel}` alongside paired spec/test files: {', '.join(context_files) or '(none)'}.",
            "3. Check every rubric criterion systematically. Report P0/P1/P2 findings with line numbers, or `ZERO P0/P1/P2 DEFECTS FOUND`.",
        ])
        tasks.append(
            SubagentTask(
                role=f"{role_base}{shard_suffix}",
                type_name="research",
                rubric_path=rubric_rel,
                allowed_files=[*allowed_base, rubric_rel, f"{code_rel}#L{span.start_line}-L{span.end_line}"],
                prompt=prompt,
            )
        )
    return tasks


def _git_diff_summary(resolved_root: Path, since_ref: str, rel_path: str) -> DiffChangeSummary:
    """Compute touched line numbers and structural/visual flags for `rel_path` since `since_ref`."""
    if not (resolved_root / ".git").exists():
        return DiffChangeSummary(set(), False, False)
    untracked = subprocess.run(
        ["git", "-C", str(resolved_root), "ls-files", "--others", "--exclude-standard", "--", rel_path],
        capture_output=True,
        text=True,
        check=False,
    )
    if untracked.stdout.strip():
        lines = (resolved_root / rel_path).read_text(encoding="utf-8", errors="replace").splitlines()
        return DiffChangeSummary(set(range(1, len(lines) + 1)), True, True)

    proc = subprocess.run(
        ["git", "-C", str(resolved_root), "diff", "-U0", since_ref, "--", rel_path],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff failed for changed_since '{since_ref}': {proc.stderr.strip()}")
    touched: set[int] = set()
    structural = False
    visual = False
    for raw in proc.stdout.splitlines():
        if hm := DIFF_HUNK_RE.match(raw):
            start = int(hm.group(3))
            cnt = int(hm.group(4)) if hm.group(4) is not None else 1
            if cnt == 0:
                touched.add(max(1, start))
            else:
                touched.update(range(start, start + cnt))
        elif raw.startswith(("+", "-")) and not raw.startswith(("+++", "---")):
            body = raw[1:].strip()
            if STRUCTURAL_EDIT_RE.search(body):
                structural = True
            if VUE_COMPONENT_RE.match(body) or body == "$$" or "mermaid" in body.lower():
                visual = True
    return DiffChangeSummary(touched, structural, visual)


def _theme_changed_since(resolved_root: Path, since_ref: str) -> bool:
    """Return True if any `.vue`/CSS file under `book/.vitepress/theme/` changed or is untracked."""
    if not (resolved_root / ".git").exists():
        return False
    theme_dir = "book/.vitepress/theme/"
    proc = subprocess.run(
        ["git", "-C", str(resolved_root), "diff", "--name-only", since_ref, "--", theme_dir],
        capture_output=True,
        text=True,
        check=False,
    )
    untracked = subprocess.run(
        ["git", "-C", str(resolved_root), "ls-files", "--others", "--exclude-standard", "--", theme_dir],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(proc.stdout.strip() or untracked.stdout.strip())


def _select_scoped_chapter_shards(
    shards: list[ShardSpec], summary: DiffChangeSummary, overlap_lines: int
) -> tuple[list[int], bool]:
    """Return `(selected_shard_indices, run_macro)` based on `DiffChangeSummary`."""
    if not summary.touched_lines:
        return [], False
    direct: list[int] = []
    for sh in shards:
        lo = max(1, sh.start_line - overlap_lines)
        hi = sh.end_line + overlap_lines
        if any(lo <= ln <= hi for ln in summary.touched_lines):
            direct.append(sh.index)
    if summary.structural_change and direct:
        min_idx = min(direct)
        return [sh.index for sh in shards if sh.index >= min_idx], True
    return direct, False


def _relativize(path: Path, resolved_root: Path) -> str:
    """Return POSIX path relative to `resolved_root`, or absolute POSIX path if outside."""
    try:
        return path.resolve().relative_to(resolved_root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


@dataclass
class ChapterPlanBundle:
    """Compiled chapter shards, tasks, and metadata returned by `_build_chapter_tasks`."""

    chapter_rel: str
    slug: str
    total_lines: int
    shards: list[ShardSpec]
    tasks: list[SubagentTask]


def _changed_files_since(resolved_root: Path, since_ref: str, rel_paths: list[str]) -> set[str]:
    """Return subset of `rel_paths` modified or untracked relative to `since_ref`."""
    if not rel_paths or not (resolved_root / ".git").exists():
        return set()
    proc = subprocess.run(
        ["git", "-C", str(resolved_root), "diff", "--name-only", since_ref, "--", *rel_paths],
        capture_output=True,
        text=True,
        check=False,
    )
    untracked = subprocess.run(
        ["git", "-C", str(resolved_root), "ls-files", "--others", "--exclude-standard", "--", *rel_paths],
        capture_output=True,
        text=True,
        check=False,
    )
    return {ln.strip() for ln in (proc.stdout + "\n" + untracked.stdout).splitlines() if ln.strip()}


def _build_chapter_tasks(
    chapter_path: Path,
    resolved_root: Path,
    target_lines: int,
    overlap_lines: int,
    changed_since: str | None,
    allow_stale_index: bool,
    scope_reasons: list[str],
) -> ChapterPlanBundle:
    """Build chapter shards, PriorLedgers, and frozen textbook subagent tasks."""
    resolved_chap = (chapter_path if chapter_path.is_absolute() else (resolved_root / chapter_path)).resolve()
    if not resolved_chap.is_file():
        raise FileNotFoundError(f"Chapter file not found: '{chapter_path}'")
    _check_chapter_index_freshness(resolved_root, allow_stale_index)
    chapter_rel = _relativize(resolved_chap, resolved_root)
    lines = resolved_chap.read_text(encoding="utf-8").splitlines()
    total_lines = len(lines)
    vue_map = _index_vue_components(resolved_root)
    packed = _pack_units_into_ranges(_collect_section_units(lines, target_lines), target_lines)
    shards: list[ShardSpec] = []
    for idx, span in enumerate(packed, start=1):
        ov_prev = (
            (max(1, span.start_line - overlap_lines), span.start_line - 1)
            if overlap_lines > 0 and span.start_line > 1
            else None
        )
        ov_next = (
            (span.end_line + 1, min(total_lines, span.end_line + overlap_lines))
            if overlap_lines > 0 and span.end_line < total_lines
            else None
        )
        widgets, transclusions = _collect_shard_seams(
            lines, span.start_line, span.end_line, resolved_chap, resolved_root, vue_map
        )
        shards.append(
            ShardSpec(idx, len(packed), span.start_line, span.end_line, ov_prev, ov_next, span.headings, widgets, transclusions)
        )

    selected = [s.index for s in shards]
    run_macro, run_visual = True, True
    if changed_since:
        summary = _git_diff_summary(resolved_root, changed_since, chapter_rel)
        selected, run_macro = _select_scoped_chapter_shards(shards, summary, overlap_lines)
        seam_vues = sorted({w.split("-> ", 1)[1] for s in shards for w in s.widgets if "<unresolved:" not in w})
        seam_slices = sorted({sl.split(": ", 1)[1].split("#", 1)[0] for s in shards for sl in s.transclusions})
        changed_seams = _changed_files_since(resolved_root, changed_since, [*seam_vues, *seam_slices])
        for s in shards:
            s_files = {w.split("-> ", 1)[1] for w in s.widgets if "-> " in w} | {
                sl.split(": ", 1)[1].split("#", 1)[0] for sl in s.transclusions
            }
            if s.index not in selected and (s_files & changed_seams):
                selected.append(s.index)
        selected.sort()
        run_visual = summary.visual_change or _theme_changed_since(resolved_root, changed_since) or bool(
            set(seam_vues) & changed_seams
        )
        scope_reasons.append(
            f"shards={selected}" + (" +macro(structural)" if run_macro else "") + (" +visual" if run_visual else "")
        )

    tasks: list[SubagentTask] = []
    for sh in shards:
        if sh.index not in selected:
            continue
        ledger = _build_prior_ledger(lines, sh.start_line)
        vue_files = [w.split("-> ", 1)[1] for w in sh.widgets if "<unresolved:" not in w]
        slice_files = sorted({s.split(": ", 1)[1] for s in sh.transclusions})
        tasks.append(_render_shard_task("Cold-Reader", "cold_reader", chapter_rel, sh, ledger, [*vue_files, *slice_files]))
        tasks.append(_render_shard_task("Math & Logic Editor", "math_editor", chapter_rel, sh, ledger, slice_files))
    if run_macro:
        tasks.append(_render_macro_task(chapter_rel, total_lines))
    if run_visual:
        visual_slug = _resolve_visual_slug(resolved_chap)
        cache_status = _visual_cache_status(resolved_root, resolved_chap, visual_slug)
        tasks.append(_render_visual_task(chapter_rel, visual_slug, cache_status, total_lines, [w for s in shards for w in s.widgets]))
    return ChapterPlanBundle(chapter_rel, resolved_chap.stem, total_lines, shards, tasks)


def _build_code_tasks(
    code_paths: list[Path],
    resolved_root: Path,
    target_lines: int,
    changed_since: str | None,
    scope_reasons: list[str],
) -> tuple[list[str], list[SubagentTask]]:
    """Build sharded frozen-prompt architecture and clarity tasks for `--code` files."""
    code_rels: list[str] = []
    seen_rels: set[str] = set()
    tasks: list[SubagentTask] = []
    for cpath in code_paths:
        resolved_code = (cpath if cpath.is_absolute() else (resolved_root / cpath)).resolve()
        if not resolved_code.is_file():
            raise FileNotFoundError(f"Code file not found: '{cpath}'")
        crel = _relativize(resolved_code, resolved_root)
        if crel in seen_rels:
            continue
        seen_rels.add(crel)
        code_rels.append(crel)
        c_lines = resolved_code.read_text(encoding="utf-8").splitlines()
        c_units = _collect_code_units(resolved_code, c_lines, target_lines)
        c_packed = _pack_units_into_ranges(c_units, target_lines)
        c_diff = _git_diff_summary(resolved_root, changed_since, crel) if changed_since else None
        header_end = min(60, max(0, (c_units[1].start_line - 1) if len(c_units) > 1 else 0))
        ctx_files = _discover_code_context_files(resolved_root, resolved_code)
        for cidx, cspan in enumerate(c_packed, start=1):
            if c_diff is not None and not any(cspan.start_line <= ln <= cspan.end_line for ln in c_diff.touched_lines):
                continue
            tasks.extend(_render_code_shard_tasks(crel, cspan, cidx, len(c_packed), header_end, ctx_files))
            if changed_since:
                scope_reasons.append(f"code:{crel}#S{cidx}")
    return code_rels, tasks


def build_review_plan(
    chapter_path: Path | None = None,
    *,
    code_paths: list[Path] | None = None,
    root_dir: Path | None = None,
    target_lines: int = DEFAULT_TARGET_LINES,
    overlap_lines: int = DEFAULT_OVERLAP_LINES,
    base_ref: str | None = None,
    changed_since: str | None = None,
    allow_stale_index: bool = False,
) -> ReviewPlan:
    """Build a complete overlapping-shard, code, global, and regression `ReviewPlan`."""
    if chapter_path is None and not code_paths:
        raise ValueError("Provide --chapter and/or --code target files.")
    if target_lines <= 0:
        raise ValueError(f"--target-lines must be positive, got {target_lines}")
    if overlap_lines < 0:
        raise ValueError(f"--overlap-lines must be non-negative, got {overlap_lines}")
    resolved_root = (root_dir or ROOT_DIR).resolve()
    tasks: list[SubagentTask] = []
    shards: list[ShardSpec] = []
    chapter_rel: str | None = None
    total_lines = 0
    slug = "code_bundle"
    scope_reasons: list[str] = []

    if chapter_path is not None:
        bundle = _build_chapter_tasks(
            chapter_path, resolved_root, target_lines, overlap_lines, changed_since, allow_stale_index, scope_reasons
        )
        chapter_rel, slug, total_lines, shards = (
            bundle.chapter_rel,
            bundle.slug,
            bundle.total_lines,
            bundle.shards,
        )
        tasks.extend(bundle.tasks)

    code_rels, code_tasks = _build_code_tasks(code_paths or [], resolved_root, target_lines, changed_since, scope_reasons)
    tasks.extend(code_tasks)
    if chapter_path is None and code_paths:
        slug = f"code_{code_paths[0].stem}"

    if base_ref:
        diff_rel = _write_diff_patch(resolved_root, chapter_rel, slug, base_ref, code_rels)
        label = chapter_rel or ", ".join(code_rels)
        extras = [*( [chapter_rel] if chapter_rel else [] ), *code_rels]
        tasks.append(_render_diff_guardian_task(label, base_ref, diff_rel, extras))

    scope_note = f"SCOPED (since {changed_since}: {', '.join(scope_reasons) or 'diff-only'})" if changed_since else "FULL SWEEP"
    return ReviewPlan(
        chapter=chapter_rel,
        slug=slug,
        total_lines=total_lines,
        base_ref=base_ref,
        changed_since=changed_since,
        scope_note=scope_note,
        code_files=code_rels,
        shards=shards,
        tasks=tasks,
    )


def format_plan_markdown(plan: ReviewPlan) -> str:
    """Render `plan` as a readable Markdown manifest of shards, seams, and frozen prompts."""
    target = plan.chapter or ", ".join(plan.code_files)
    out = [
        f"# Review Plan: `{target}` ({plan.scope_note}, {len(plan.shards)} chapter shards, {len(plan.tasks)} tasks)",
        "",
        "## Shards & Seams",
    ]
    for s in plan.shards:
        out.append(
            f"- **Shard {s.index}/{s.total}** (`L{s.start_line}..L{s.end_line}`, "
            f"prev={s.overlap_prev}, next={s.overlap_next}): {len(s.widgets)} widget(s), "
            f"{len(s.transclusions)} code slice(s)"
        )
    if plan.code_files:
        out.append(f"- **Code Targets**: {', '.join(f'`{c}`' for c in plan.code_files)}")
    out.extend(["", "## Frozen Subagent Prompts"])
    for t in plan.tasks:
        out.extend([f"### {t.role}", f"- Rubric: `{t.rubric_path}`", "```text", t.prompt, "```", ""])
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point generating deterministic sharded textbook and code review manifests."""
    parser = argparse.ArgumentParser(description="Build deterministic overlapping review shards and frozen prompts.")
    parser.add_argument("--chapter", default=None, help="Path to textbook chapter Markdown file.")
    parser.add_argument("--code", nargs="+", default=None, help="Code, RTL, C, script, or Vue files to audit.")
    parser.add_argument("--base-ref", default=None, help="Optional pre-fix git ref for Diff Regression Guardian.")
    parser.add_argument("--changed-since", default=None, help="Optional Round-r git ref for scoped Round r+1 re-convergence.")
    parser.add_argument("--allow-stale-index", action="store_true", help="Bypass docs/CHAPTER_INDEX.md freshness check.")
    parser.add_argument("--target-lines", type=int, default=DEFAULT_TARGET_LINES, help="Max primary lines per shard.")
    parser.add_argument("--overlap-lines", type=int, default=DEFAULT_OVERLAP_LINES, help="Boundary overlap line count.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of Markdown.")
    args = parser.parse_args(argv)

    try:
        plan = build_review_plan(
            Path(args.chapter) if args.chapter else None,
            code_paths=[Path(c) for c in args.code] if args.code else None,
            target_lines=args.target_lines,
            overlap_lines=args.overlap_lines,
            base_ref=args.base_ref,
            changed_since=args.changed_since,
            allow_stale_index=args.allow_stale_index,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(asdict(plan), indent=2))
    else:
        print(format_plan_markdown(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
