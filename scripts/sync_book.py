#!/usr/bin/env python3
"""Synchronize textbook transclusions, code links, and file line-count badges.

Purpose:
  Keep `systems/*/chapters/*.md` line ranges (`#L<start>-L<end>`), link labels
  (`line N` / `lines A–B`), and file line counts (`1,027` lines) synchronized
  with live source files using AST/parser symbols (`scripts/code_anchors.py`),
  and report prose impact when transcluded implementation lines change.

Usage:
  python3 scripts/sync_book.py                       # Update chapters in-place
  python3 scripts/sync_book.py --check               # Fail non-zero on any drift
  python3 scripts/sync_book.py --prose-impact main   # Report edited transclusions

Outputs:
  In write mode, updates `systems/*/chapters/*.md` cleanly on disk and exits 0.
  In `--check` mode, makes zero edits and exits 1 if any chapter has drift or errors.
"""

from __future__ import annotations

import argparse
import functools
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from code_anchors import AnchorError, resolve_anchor  # noqa: E402 — repo scripts run standalone without package install

ROOT_DIR = SCRIPT_DIR.parent
SYNC_DIRECTIVE_RE = re.compile(r"^<!--\s*book-sync:\s*(.+?)\s*-->$")
TRANSCLUDE_RE = re.compile(
    r"^(<<<\s+)(@/[^\s{#\[]+|\.\.?/[^\s{#\[]+)(?:#L\d+(?:-L?\d+)?)?(.*)$"
)
MD_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)\s"]+)(?:\s+"([^"]*)")?\)')
LINE_BADGE_RE = re.compile(r"^(\s*\(`?)([\d,]+)(`?\s+lines?\))")
LABEL_LINES_RE = re.compile(r"\blines?\s+\d+(?:\s*([–-])\s*\d+)?\b")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
FENCE_OPEN_RE = re.compile(r"^(`{3,}|~{3,})(.*)$")


@dataclass
class LinkRewrite:
    """Single Markdown link/badge match and replacement within one chapter line."""

    start: int
    end: int
    replacement: str


def format_line_fragment(start_ln: int, end_ln: int) -> str:
    """Format a 1-indexed line range as `#L<n>` or `#L<s>-L<e>`."""
    return f"#L{start_ln}" if start_ln == end_ln else f"#L{start_ln}-L{end_ln}"


def _format_label_match(start_ln: int, end_ln: int, match: re.Match[str]) -> str:
    """Format a single `line N` / `lines A–B` substring while preserving separator char."""
    dash = match.group(1) or "–"
    return f"line {start_ln}" if start_ln == end_ln else f"lines {start_ln}{dash}{end_ln}"


def format_label_lines(label: str, start_ln: int, end_ln: int) -> str:
    """Update `line N` or `lines A–B` inside a Markdown link's visible label text."""
    return LABEL_LINES_RE.sub(
        functools.partial(_format_label_match, start_ln, end_ln), label
    )


def infer_implicit_symbol(label: str) -> str | None:
    """Extract an implicit code symbol from a backticked link label like `` `Oracle.step()` ``."""
    stripped = label.strip()
    if not (stripped.startswith("`") and stripped.endswith("`")):
        return None
    inner = re.sub(r"\([^)]*\)$", "", stripped[1:-1].strip())
    if re.match(r"^[A-Za-z_][A-Za-z0-9_.]*$", inner):
        return inner
    return None


def is_inside_outer_backticks(line: str, pos: int) -> bool:
    """Return True if character offset `pos` falls inside an active inline code span."""
    fence_len = 0
    i = 0
    while i < pos:
        if line[i] == "\\" and fence_len == 0:
            i += 2
            continue
        if line[i] == "`":
            j = i
            while j < len(line) and line[j] == "`":
                j += 1
            run = j - i
            if fence_len == 0:
                fence_len = run
            elif run == fence_len:
                fence_len = 0
            i = j
            continue
        i += 1
    return fence_len > 0


def update_fence_state(
    stripped: str, active_fence: tuple[str, int] | None
) -> tuple[tuple[str, int] | None, bool]:
    """Track fenced code block boundaries supporting arbitrary backtick/tilde lengths."""
    fm = FENCE_OPEN_RE.match(stripped)
    if not fm:
        return active_fence, False
    marker, info = fm.groups()
    if active_fence is None:
        return (marker[0], len(marker)), True
    if marker[0] == active_fence[0] and len(marker) >= active_fence[1] and not info.strip():
        return None, True
    return active_fence, False


def resolve_target_file(chap_dir: Path, root_dir: Path, raw_target: str) -> Path | None:
    """Resolve `@/...` repo-root or relative paths, returning None if outside `root_dir`."""
    resolved_root = root_dir.resolve()
    if raw_target.startswith("@/"):
        candidate = (resolved_root / raw_target[2:]).resolve()
    else:
        candidate = (chap_dir.resolve() / raw_target).resolve()
    if not candidate.is_relative_to(resolved_root):
        return None
    return candidate


def _resolve_link_rewrite(
    match: re.Match[str],
    line: str,
    chap_path: Path,
    root_dir: Path,
    rel_chap: Path,
    line_num: int,
    line_count_cache: dict[Path, int],
    errors: list[str],
) -> LinkRewrite | None:
    """Compute a `LinkRewrite` for one relative code link or line-count badge, if changed."""
    label, href, title = match.groups()
    if href.startswith(("http://", "https://", "mailto:", "#", "/")):
        return None
    file_part, _, frag = href.partition("#")
    target_path = resolve_target_file(chap_path.parent, root_dir, file_part)
    if target_path is None:
        errors.append(f"[{rel_chap}:{line_num}] Path escapes repository root: '{href}'")
        return None
    if not target_path.exists():
        return None

    new_label, new_href = label, href
    anchor_spec = title.strip()[len("anchor:") :].strip() if title and title.strip().startswith("anchor:") else None
    is_line_frag = bool(frag and re.match(r"^L\d+(?:-L?\d+)?$", frag))
    has_line_badge = bool(not frag and target_path.is_file() and LINE_BADGE_RE.match(line[match.end() :]))

    if is_line_frag and target_path.is_file():
        spec = anchor_spec or infer_implicit_symbol(label)
        if spec is not None:
            try:
                s_ln, e_ln = resolve_anchor(target_path, spec)
            except AnchorError as exc:
                errors.append(f"[{rel_chap}:{line_num}] {exc}")
            else:
                new_href = f"{file_part}{format_line_fragment(s_ln, e_ln)}"
                new_label = format_label_lines(label, s_ln, e_ln)
    elif not frag and target_path.is_file() and not has_line_badge:
        spec = anchor_spec or infer_implicit_symbol(label)
        if spec is not None and spec not in {target_path.name, target_path.stem}:
            try:
                s_ln, e_ln = resolve_anchor(target_path, spec)
            except AnchorError as exc:
                if anchor_spec is not None:
                    errors.append(f"[{rel_chap}:{line_num}] {exc}")
            else:
                new_href = f"{file_part}{format_line_fragment(s_ln, e_ln)}"

    title_part = f' "{title}"' if title is not None else ""
    new_link = f"[{new_label}]({new_href}{title_part})"
    end_pos = match.end()

    if has_line_badge and (badge_m := LINE_BADGE_RE.match(line[end_pos:])):
        if target_path not in line_count_cache:
            line_count_cache[target_path] = len(target_path.read_text(encoding="utf-8").splitlines())
        prefix, _, suffix = badge_m.groups()
        new_link += f"{prefix}{line_count_cache[target_path]:,}{suffix}"
        end_pos += badge_m.end()

    if new_link == line[match.start() : end_pos]:
        return None
    return LinkRewrite(match.start(), end_pos, new_link)


def _rewrite_line_links(
    line: str,
    chap_path: Path,
    root_dir: Path,
    rel_chap: Path,
    line_num: int,
    line_count_cache: dict[Path, int],
    errors: list[str],
) -> str:
    """Rewrite anchored `#L...` code links and file line-count badges on one Markdown line."""
    rewrites: list[LinkRewrite] = []
    for match in MD_LINK_RE.finditer(line):
        if is_inside_outer_backticks(line, match.start()):
            continue
        rw = _resolve_link_rewrite(
            match, line, chap_path, root_dir, rel_chap, line_num, line_count_cache, errors
        )
        if rw is not None:
            rewrites.append(rw)

    if not rewrites:
        return line
    out = line
    for rw in reversed(rewrites):
        out = out[: rw.start] + rw.replacement + out[rw.end :]
    return out


def sync_chapter_text(chap_path: Path, root_dir: Path | None = None) -> tuple[str, list[str]]:
    """Return `(synced_text, errors)` for one textbook chapter without writing to disk."""
    resolved_root = (root_dir or ROOT_DIR).resolve()
    resolved_chap = chap_path.resolve()
    rel_chap = (
        resolved_chap.relative_to(resolved_root)
        if resolved_chap.is_relative_to(resolved_root)
        else chap_path
    )
    raw_text = resolved_chap.read_text(encoding="utf-8")
    lines = raw_text.splitlines()
    errors: list[str] = []
    line_count_cache: dict[Path, int] = {}
    out_lines: list[str] = []
    active_fence: tuple[str, int] | None = None
    in_math = False
    pending_anchor: tuple[int, str] | None = None

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        active_fence, toggled = update_fence_state(stripped, active_fence)
        if toggled:
            pending_anchor = None
            out_lines.append(line)
            continue
        if active_fence is not None:
            out_lines.append(line)
            continue
        if stripped == "$$":
            in_math = not in_math
            out_lines.append(line)
            continue

        if dir_m := SYNC_DIRECTIVE_RE.match(stripped):
            pending_anchor = (idx, dir_m.group(1))
            out_lines.append(line)
            continue

        if tr_m := TRANSCLUDE_RE.match(stripped):
            prefix, raw_target, suffix = tr_m.groups()
            target_path = resolve_target_file(resolved_chap.parent, resolved_root, raw_target)
            if pending_anchor is not None:
                _, spec = pending_anchor
                if target_path is None:
                    errors.append(f"[{rel_chap}:{idx}] Transclusion escapes repository root: '{raw_target}'")
                    out_lines.append(line)
                elif not target_path.is_file():
                    errors.append(f"[{rel_chap}:{idx}] Transcluded file does not exist: '{raw_target}'")
                    out_lines.append(line)
                else:
                    try:
                        s_ln, e_ln = resolve_anchor(target_path, spec)
                    except AnchorError as exc:
                        errors.append(f"[{rel_chap}:{idx}] {exc}")
                        out_lines.append(line)
                    else:
                        indent = line[: len(line) - len(line.lstrip())]
                        out_lines.append(
                            f"{indent}{prefix}{raw_target}{format_line_fragment(s_ln, e_ln)}{suffix}"
                        )
            else:
                out_lines.append(line)
            pending_anchor = None
            continue

        if pending_anchor is not None and stripped:
            pending_anchor = None
        if in_math:
            out_lines.append(line)
            continue
        out_lines.append(
            _rewrite_line_links(line, resolved_chap, resolved_root, rel_chap, idx, line_count_cache, errors)
        )

    return "\n".join(out_lines) + ("\n" if raw_text.endswith("\n") else ""), errors


def sync_all_chapters(
    root_dir: Path | None = None, check_only: bool = False
) -> tuple[list[Path], list[str]]:
    """Sync every `systems/*/chapters/*.md`, returning `(changed_paths, errors)`."""
    resolved_root = (root_dir or ROOT_DIR).resolve()
    changed: list[Path] = []
    all_errors: list[str] = []
    for chap_path in sorted(resolved_root.glob("systems/*/chapters/*.md")):
        orig = chap_path.read_text(encoding="utf-8")
        synced, errs = sync_chapter_text(chap_path, resolved_root)
        all_errors.extend(errs)
        if synced != orig:
            changed.append(chap_path)
            if not check_only:
                chap_path.write_text(synced, encoding="utf-8")
    return changed, all_errors


def _collect_git_changed_ranges(root_dir: Path, base_ref: str) -> dict[Path, list[tuple[int, int]]]:
    """Return modified new-file line ranges per `systems/` file vs. `base_ref`."""
    resolved_root = root_dir.resolve()
    proc = subprocess.run(
        ["git", "diff", "--unified=0", base_ref, "--", "systems/"],
        cwd=resolved_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git diff against '{base_ref}' failed")

    ranges: dict[Path, list[tuple[int, int]]] = {}
    current_file: Path | None = None
    for raw in proc.stdout.splitlines():
        if raw.startswith("+++ b/"):
            current_file = (resolved_root / raw[6:]).resolve()
            ranges.setdefault(current_file, [])
        elif raw == "+++ /dev/null":
            current_file = None
        elif current_file is not None and (hm := HUNK_RE.match(raw)):
            start = int(hm.group(1))
            count = int(hm.group(2)) if hm.group(2) is not None else 1
            end = start if count == 0 else start + count - 1
            ranges[current_file].append((start, end))
    return ranges


def detect_prose_impact(base_ref: str, root_dir: Path | None = None) -> list[str]:
    """Identify chapter sections whose transcluded code lines changed relative to `base_ref`."""
    resolved_root = (root_dir or ROOT_DIR).resolve()
    diff_ranges = _collect_git_changed_ranges(resolved_root, base_ref)
    impacts: list[str] = []

    for chap_path in sorted(resolved_root.glob("systems/*/chapters/*.md")):
        rel_chap = chap_path.relative_to(resolved_root)
        lines = chap_path.read_text(encoding="utf-8").splitlines()
        heading = "(Top of chapter)"
        pending_spec: str | None = None
        active_fence: tuple[str, int] | None = None

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            active_fence, toggled = update_fence_state(stripped, active_fence)
            if toggled or active_fence is not None:
                pending_spec = None
                continue
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()
            if dir_m := SYNC_DIRECTIVE_RE.match(stripped):
                pending_spec = dir_m.group(1)
                continue
            if (tr_m := TRANSCLUDE_RE.match(stripped)) and pending_spec is not None:
                target = resolve_target_file(chap_path.parent, resolved_root, tr_m.group(2))
                hunks = diff_ranges.get(target) if target is not None else None
                if hunks and target is not None and target.is_file():
                    try:
                        s_ln, e_ln = resolve_anchor(target, pending_spec)
                    except AnchorError:
                        pending_spec = None
                        continue
                    if any(not (h_end < s_ln or h_start > e_ln) for h_start, h_end in hunks):
                        rel_target = target.relative_to(resolved_root)
                        impacts.append(
                            f"{rel_chap}:{idx} [{heading}] -> {rel_target}"
                            f"{format_line_fragment(s_ln, e_ln)} ({pending_spec})"
                        )
                pending_spec = None
            elif stripped:
                pending_spec = None
    return impacts


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `--check`, in-place sync, and `--prose-impact` checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check that all chapter transclusions, code links, and badges are synced.",
    )
    parser.add_argument(
        "--prose-impact",
        metavar="BASE_REF",
        help="Report chapter headings whose transcluded code was modified vs. git BASE_REF.",
    )
    args = parser.parse_args(argv)

    if args.prose_impact:
        try:
            impacts = detect_prose_impact(args.prose_impact, ROOT_DIR)
        except RuntimeError as exc:
            print(f"Prose impact check FAILED: {exc}", file=sys.stderr)
            return 1
        if impacts:
            print(f"PROSE IMPACT vs {args.prose_impact} ({len(impacts)} transclusion(s)):")
            for item in impacts:
                print(f"  - {item}")
        else:
            print(f"OK: No transcluded implementation lines modified vs {args.prose_impact}.")
        return 0

    changed, errors = sync_all_chapters(ROOT_DIR, check_only=args.check)
    if errors:
        print("Textbook sync FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if args.check and changed:
        print("Textbook sync drift detected:", file=sys.stderr)
        for ch in changed:
            print(f"  - {ch.relative_to(ROOT_DIR.resolve())} (run 'python3 scripts/sync_book.py')", file=sys.stderr)
        return 1

    if changed:
        print(f"OK: Synchronized {len(changed)} textbook chapter(s).")
    else:
        print("OK: All textbook chapters are already synchronized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
