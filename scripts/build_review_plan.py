#!/usr/bin/env python3
"""Generate deterministic, overlapping, zero-bias textbook review plans.

Purpose:
  Eliminate ad-hoc orchestrator prompt steering and cross-shard boundary misses
  by partitioning any textbook chapter into `##`/`###`-aligned overlapping shards,
  compiling a Prior-Section Ledger of previously introduced terms and code tokens,
  binding exact-line `.vue` widgets and `<<<` code slices to their containing shard,
  and emitting frozen, content-agnostic subagent prompts backed by decomposed
  `references/rubric_*.md` checklists.

Usage:
  python3 scripts/build_review_plan.py --chapter systems/brain/chapters/01_isa_and_binary_arithmetic.md
  python3 scripts/build_review_plan.py --chapter systems/brain/chapters/01_isa_and_binary_arithmetic.md --base-ref HEAD~1
  python3 scripts/build_review_plan.py --chapter systems/brain/chapters/01_isa_and_binary_arithmetic.md --json

Outputs:
  Prints a Markdown or JSON review execution manifest detailing all shard ranges,
  boundary overlaps, Prior-Section Ledgers, widget/code seams, and frozen prompts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TARGET_LINES = 450
DEFAULT_OVERLAP_LINES = 50
MAX_LEDGER_ITEMS = 80

H2_RE = re.compile(r"^##\s+(.+)$")
H3_RE = re.compile(r"^###\s+(.+)$")
H4_EX_RE = re.compile(r"^####\s+(Exercise\b.+)$", re.IGNORECASE)
FENCE_TOGGLE_RE = re.compile(r"^(`{3,}|~{3,})")
VUE_COMPONENT_RE = re.compile(r"^<([A-Z][A-Za-z0-9]*)(?:\s*/>|\s|>).*$")
TRANSCLUDE_SLICE_RE = re.compile(r"^<<<\s+(@/[^\s{#\[]+|\.\.?/[^\s{#\[]+)(?:#L(\d+)(?:-L?(\d+))?)?")
INLINE_BOLD_RE = re.compile(r"\*\*([^*\n]{2,60})\*\*")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")

RUBRIC_PATHS = {
    "cold_reader": ".agents/skills/apex-textbook-author/references/rubric_cold_reader.md",
    "math_editor": ".agents/skills/apex-textbook-author/references/rubric_math_editor.md",
    "visual_critic": ".agents/skills/apex-textbook-author/references/rubric_visual_critic.md",
    "diff_guardian": ".agents/skills/apex-textbook-author/references/rubric_diff_guardian.md",
}

ISOLATION_PROHIBITION = (
    "ISOLATION RULE: Do NOT read `/tmp/`, `*triage*`, `*calibration_log*`, "
    "session transcripts, `git log`, or run `gh`. Evaluate strictly the files "
    "and line ranges listed below."
)


@dataclass
class SectionUnit:
    """Atomic contiguous line span aligned to a `##` or `###` heading boundary."""

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
    """Deterministic inventory of terms, tokens, and headings introduced before a shard."""

    headings: list[str] = field(default_factory=list)
    bold_terms: list[str] = field(default_factory=list)
    code_tokens: list[str] = field(default_factory=list)
    exercises: list[str] = field(default_factory=list)


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
    """Complete sharded, global, and regression-check review manifest for one chapter."""

    chapter: str
    slug: str
    total_lines: int
    base_ref: str | None
    shards: list[ShardSpec]
    tasks: list[SubagentTask]


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


@dataclass
class ShardSpan:
    """Contiguous primary line span grouped from one or more section units."""

    start_line: int
    end_line: int
    headings: list[str]


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
        rel = vue_path.relative_to(root_dir).as_posix()
        mapping[vue_path.stem] = rel
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


def _dedupe_capped(items: list[str], limit: int) -> list[str]:
    """Preserve first-seen order while deduplicating and capping output length."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _build_prior_ledger(lines: list[str], before_line: int) -> PriorLedger:
    """Compile headings, bold terms, code tokens, and exercises introduced before `before_line`."""
    if before_line <= 1:
        return PriorLedger()
    headings: list[str] = []
    bold_terms: list[str] = []
    code_tokens: list[str] = []
    exercises: list[str] = []
    in_fence = False
    for raw in lines[: before_line - 1]:
        stripped = raw.strip()
        if FENCE_TOGGLE_RE.match(stripped):
            in_fence = not in_fence
            continue
        if in_fence:
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
    return PriorLedger(
        headings=headings,
        bold_terms=_dedupe_capped(bold_terms, MAX_LEDGER_ITEMS),
        code_tokens=_dedupe_capped(code_tokens, MAX_LEDGER_ITEMS),
        exercises=exercises,
    )


def _format_ledger_summary(ledger: PriorLedger) -> str:
    """Format a `PriorLedger` into compact context lines for a shard prompt."""
    if not ledger.headings and not ledger.bold_terms and not ledger.code_tokens:
        return "Prior-Section Ledger: (none — this is Shard 1 starting at Line 1)."
    parts = ["Prior-Section Ledger (already defined before this shard):"]
    if ledger.headings:
        parts.append("  - Headings: " + " | ".join(ledger.headings))
    if ledger.bold_terms:
        parts.append("  - Defined terms: " + ", ".join(ledger.bold_terms))
    if ledger.code_tokens:
        parts.append("  - Code/operator tokens: " + ", ".join(f"`{t}`" for t in ledger.code_tokens))
    if ledger.exercises:
        parts.append("  - Earlier exercises: " + "; ".join(ledger.exercises))
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
        rubric_rel,
        f"{chapter_rel}#L{shard.start_line}-L{shard.end_line}",
        *extra_files,
    ]
    prompt = "\n".join([
        f"You are `{role_prefix}` auditing Shard {shard.index}/{shard.total} of `{chapter_rel}`.",
        ISOLATION_PROHIBITION,
        f"1. Read `GEMINI.md` and `{rubric_rel}` completely before reading the chapter slice.",
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


def _render_global_task(chapter_rel: str, slug: str, total_lines: int) -> SubagentTask:
    """Render the whole-chapter macro-structure and visual pedagogy audit task."""
    rubric_rel = RUBRIC_PATHS["visual_critic"]
    allowed = [
        "GEMINI.md",
        rubric_rel,
        chapter_rel,
        "book/.vitepress/theme/custom.css",
        f".cache/visual-audit/{slug}/",
    ]
    prompt = "\n".join([
        f"You are `Global Structure & Visual Critic` auditing `{chapter_rel}` (`1..{total_lines}`).",
        ISOLATION_PROHIBITION,
        f"1. Read `GEMINI.md` and `{rubric_rel}` completely.",
        (
            f"2. Audit macro structure across `{chapter_rel}` (headings, base-before-custom section "
            "progression, end-to-end rigor balance, math-vs-hardware `#### Exercise` scoping, and "
            "`## <N>. Problems` coverage)."
        ),
        (
            f"3. Inspect `book/.vitepress/theme/custom.css` and desktop/mobile screenshots in "
            f"`.cache/visual-audit/{slug}/` using the visual rubric."
        ),
        (
            "4. Report P0/P1/P2 defects with exact line numbers or screenshot targets, or output "
            "`ZERO P0/P1/P2 DEFECTS FOUND`."
        ),
    ])
    return SubagentTask(
        role="Global Structure & Visual Critic",
        type_name="research",
        rubric_path=rubric_rel,
        allowed_files=allowed,
        prompt=prompt,
    )


def _render_diff_guardian_task(chapter_rel: str, base_ref: str) -> SubagentTask:
    """Render the Step 3 before/after flow and boilerplate regression guardian task."""
    rubric_rel = RUBRIC_PATHS["diff_guardian"]
    prompt = "\n".join([
        f"You are `Diff & Flow Regression Guardian` inspecting changes to `{chapter_rel}` since `{base_ref}`.",
        "ISOLATION RULE: Inspect only the diff (`git diff -U25 <base_ref>`), `GEMINI.md`, and the rubric. "
        "Do NOT read `/tmp/`, `*triage*`, `*calibration_log*`, `gh`, or session logs.",
        f"1. Read `GEMINI.md` and `{rubric_rel}` completely.",
        f"2. Run `git diff -U25 {base_ref} -- {chapter_rel} book/.vitepress/theme/components/`.",
        (
            "3. Flag any edit that worsens prose flow, introduces prose-math walls, pastes repetitive "
            "rule-compliance boilerplate across items, or creates cross-section forward references."
        ),
        "4. Report P0/P1/P2 regressions with exact lines/hunks, or output `ZERO P0/P1/P2 DEFECTS FOUND`.",
    ])
    return SubagentTask(
        role="Diff & Flow Regression Guardian",
        type_name="research",
        rubric_path=rubric_rel,
        allowed_files=["GEMINI.md", rubric_rel, chapter_rel],
        prompt=prompt,
    )


def build_review_plan(
    chapter_path: Path,
    *,
    root_dir: Path | None = None,
    target_lines: int = DEFAULT_TARGET_LINES,
    overlap_lines: int = DEFAULT_OVERLAP_LINES,
    base_ref: str | None = None,
) -> ReviewPlan:
    """Build a complete overlapping-shard and global `ReviewPlan` for `chapter_path`."""
    resolved_root = (root_dir or ROOT_DIR).resolve()
    resolved_chap = chapter_path if chapter_path.is_absolute() else (resolved_root / chapter_path)
    resolved_chap = resolved_chap.resolve()
    if not resolved_chap.is_file():
        raise FileNotFoundError(f"Chapter file not found: '{chapter_path}'")

    try:
        chapter_rel = resolved_chap.relative_to(resolved_root).as_posix()
    except ValueError:
        chapter_rel = resolved_chap.as_posix()
    lines = resolved_chap.read_text(encoding="utf-8").splitlines()
    total_lines = len(lines)
    vue_map = _index_vue_components(resolved_root)

    units = _collect_section_units(lines, target_lines)
    packed = _pack_units_into_ranges(units, target_lines)
    total_shards = len(packed)

    shards: list[ShardSpec] = []
    tasks: list[SubagentTask] = []
    for idx, span in enumerate(packed, start=1):
        start_line, end_line, headings = span.start_line, span.end_line, span.headings
        ov_prev = (max(1, start_line - overlap_lines), start_line - 1) if start_line > 1 else None
        ov_next = (
            (end_line + 1, min(total_lines, end_line + overlap_lines))
            if end_line < total_lines
            else None
        )
        widgets, transclusions = _collect_shard_seams(
            lines, start_line, end_line, resolved_chap, resolved_root, vue_map
        )
        shard = ShardSpec(
            index=idx,
            total=total_shards,
            start_line=start_line,
            end_line=end_line,
            overlap_prev=ov_prev,
            overlap_next=ov_next,
            headings=headings,
            widgets=widgets,
            transclusions=transclusions,
        )
        shards.append(shard)
        ledger = _build_prior_ledger(lines, start_line)
        vue_files = [w.split("-> ", 1)[1] for w in widgets if "<unresolved:" not in w]
        slice_files = sorted({s.split(": ", 1)[1] for s in transclusions})
        tasks.append(
            _render_shard_task(
                "Cold-Reader", "cold_reader", chapter_rel, shard, ledger, [*vue_files, *slice_files]
            )
        )
        tasks.append(
            _render_shard_task("Math & Logic Editor", "math_editor", chapter_rel, shard, ledger, slice_files)
        )

    tasks.append(_render_global_task(chapter_rel, resolved_chap.stem, total_lines))
    if base_ref:
        tasks.append(_render_diff_guardian_task(chapter_rel, base_ref))

    return ReviewPlan(
        chapter=chapter_rel,
        slug=resolved_chap.stem,
        total_lines=total_lines,
        base_ref=base_ref,
        shards=shards,
        tasks=tasks,
    )


def format_plan_markdown(plan: ReviewPlan) -> str:
    """Render `plan` as a readable Markdown manifest of shards, seams, and frozen prompts."""
    out = [
        f"# Review Plan: `{plan.chapter}` ({plan.total_lines} lines, {len(plan.shards)} shards, {len(plan.tasks)} tasks)",
        "",
        "## Shards & Seams",
    ]
    for s in plan.shards:
        out.append(
            f"- **Shard {s.index}/{s.total}** (`L{s.start_line}..L{s.end_line}`, "
            f"prev={s.overlap_prev}, next={s.overlap_next}): {len(s.widgets)} widget(s), "
            f"{len(s.transclusions)} code slice(s)"
        )
    out.extend(["", "## Frozen Subagent Prompts"])
    for t in plan.tasks:
        out.extend([f"### {t.role}", f"- Rubric: `{t.rubric_path}`", "```text", t.prompt, "```", ""])
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point generating deterministic sharded textbook review manifests."""
    parser = argparse.ArgumentParser(description="Build deterministic overlapping review shards and frozen prompts.")
    parser.add_argument("--chapter", required=True, help="Path to textbook chapter Markdown file.")
    parser.add_argument("--base-ref", default=None, help="Optional pre-fix git ref for Diff Regression Guardian.")
    parser.add_argument("--target-lines", type=int, default=DEFAULT_TARGET_LINES, help="Max primary lines per shard.")
    parser.add_argument("--overlap-lines", type=int, default=DEFAULT_OVERLAP_LINES, help="Boundary overlap line count.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of Markdown.")
    args = parser.parse_args(argv)

    try:
        plan = build_review_plan(
            Path(args.chapter),
            target_lines=args.target_lines,
            overlap_lines=args.overlap_lines,
            base_ref=args.base_ref,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(asdict(plan), indent=2))
    else:
        print(format_plan_markdown(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
