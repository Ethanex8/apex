#!/usr/bin/env python3
"""Validate textbook chapters: synced transclusions, anchored links, and prose hygiene.

Purpose:
  Enforce zero drift between `systems/*/chapters/*.md` and live source files by
  requiring `<!-- book-sync: <anchor> -->` directives on every `<<<` transclusion,
  requiring symbol/title anchors on every `#L...` Markdown link, banning unanchored
  bare prose line numbers, and checking GFM tilde and math/code-fence hygiene.

Usage:
  python3 scripts/check_book.py

Outputs:
  Prints summary count of validated chapters and anchors; exits 1 on any violation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from code_anchors import AnchorError, resolve_anchor  # noqa: E402 — repo scripts run standalone without package install
from sync_book import (  # noqa: E402 — repo scripts run standalone without package install
    MD_LINK_RE,
    SYNC_DIRECTIVE_RE,
    format_line_fragment,
    infer_implicit_symbol,
    is_inside_outer_backticks,
    resolve_target_file,
    sync_chapter_text,
    update_fence_state,
)

ROOT_DIR = SCRIPT_DIR.parent
LEGACY_EXPECT_RE = re.compile(r"^<!--\s*expect-symbol:\s*(.+?)\s*-->$")
TRANSCLUDE_RE = re.compile(
    r"^<<<\s+(@/[^\s{#\[]+|\.\.?/[^\s{#\[]+)(?:#L(\d+)(?:-L?(\d+))?)?"
)
BARE_PROSE_LINE_RE = re.compile(r"\blines?\s+`?\d+(?:\s*[–-]\s*\d+)?", re.IGNORECASE)
INLINE_CODE_RE = re.compile(r"(`+)(?:\\.|.)*?\1")
INLINE_MATH_RE = re.compile(
    r"(?<!\\)\$\$(?:\\.|[^$])*?(?<!\\)\$\$|(?<!\\)\$(?:\\.|[^$\\])*?(?<!\\)\$"
)


def _append_unique(errors: list[str], msg: str) -> None:
    """Append `msg` to `errors` only if an identical diagnostic is not already recorded."""
    if msg not in errors:
        errors.append(msg)


def _read_lines_cached(path: Path, cache: dict[Path, list[str]]) -> list[str]:
    """Read and cache UTF-8 lines for `path`."""
    resolved = path.resolve()
    if resolved not in cache:
        cache[resolved] = resolved.read_text(encoding="utf-8").splitlines()
    return cache[resolved]


def _strip_inline_code_and_math(line: str) -> str:
    """Remove inline code spans and unescaped `$...$` math spans before checking tildes."""
    without_code = INLINE_CODE_RE.sub("", line)
    return INLINE_MATH_RE.sub("", without_code)


def _validate_transclusion(
    raw_line: str,
    idx: int,
    rel_chap: Path,
    chap_path: Path,
    root_dir: Path,
    pending_anchor: tuple[int, str] | None,
    file_cache: dict[Path, list[str]],
    errors: list[str],
) -> bool:
    """Validate one `<<<` transclusion line against its `book-sync` anchor."""
    tr_match = TRANSCLUDE_RE.match(raw_line.strip())
    if not tr_match:
        return False

    raw_target, start_s, end_s = tr_match.groups()
    target_path = resolve_target_file(chap_path.parent, root_dir, raw_target)
    if target_path is None:
        _append_unique(errors, f"[{rel_chap}:{idx}] Transclusion escapes repository root: '{raw_target}'")
        return True
    if not target_path.exists() or not target_path.is_file():
        _append_unique(errors, f"[{rel_chap}:{idx}] Transcluded file does not exist: '{raw_target}'")
        return True

    src_lines = _read_lines_cached(target_path, file_cache)
    if start_s is not None:
        s_ln = int(start_s)
        e_ln = int(end_s) if end_s is not None else s_ln
        if not (1 <= s_ln <= e_ln <= len(src_lines)):
            _append_unique(
                errors,
                f"[{rel_chap}:{idx}] Out-of-bounds transclusion #L{s_ln}-L{e_ln} "
                f"for '{raw_target}' ({len(src_lines)} lines)",
            )
            return True

    if pending_anchor is None:
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Missing '<!-- book-sync: <anchor> -->' before transclusion '{raw_target}'",
        )
        return True

    _, spec = pending_anchor
    try:
        exp_s, exp_e = resolve_anchor(target_path, spec)
    except AnchorError as exc:
        _append_unique(errors, f"[{rel_chap}:{idx}] {exc}")
        return True

    exp_frag = format_line_fragment(exp_s, exp_e)
    actual_frag = format_line_fragment(int(start_s), int(end_s or start_s)) if start_s else ""
    if actual_frag != exp_frag:
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Transclusion drift for '{spec}': got '{actual_frag}', expected '{exp_frag}'",
        )
    return True


def _validate_markdown_links(
    raw_line: str,
    idx: int,
    rel_chap: Path,
    chap_path: Path,
    root_dir: Path,
    file_cache: dict[Path, list[str]],
    errors: list[str],
) -> int:
    """Validate relative Markdown file links, `#L...` ranges, and anchor metadata."""
    count = 0
    for match in MD_LINK_RE.finditer(raw_line):
        if is_inside_outer_backticks(raw_line, match.start()):
            continue
        label, href, title = match.groups()
        if href.startswith(("http://", "https://", "mailto:", "#", "/")):
            continue
        file_part, _, frag = href.partition("#")
        target_path = resolve_target_file(chap_path.parent, root_dir, file_part)
        if target_path is None:
            _append_unique(errors, f"[{rel_chap}:{idx}] Path escapes repository root: '{href}'")
            continue
        if not target_path.exists():
            _append_unique(errors, f"[{rel_chap}:{idx}] Broken relative link target '{href}'")
            continue
        count += 1
        if frag and target_path.is_file():
            ln_m = re.match(r"^L(\d+)(?:-L?(\d+))?$", frag)
            if not ln_m:
                continue
            s_ln = int(ln_m.group(1))
            e_ln = int(ln_m.group(2)) if ln_m.group(2) else s_ln
            src_lines = _read_lines_cached(target_path, file_cache)
            if not (1 <= s_ln <= e_ln <= len(src_lines)):
                _append_unique(
                    errors,
                    f"[{rel_chap}:{idx}] Out-of-bounds line citation '{href}' ({len(src_lines)} lines)",
                )
                continue
            spec = (
                title.strip()[len("anchor:") :].strip()
                if title and title.strip().startswith("anchor:")
                else infer_implicit_symbol(label)
            )
            if spec is None:
                _append_unique(
                    errors,
                    f"[{rel_chap}:{idx}] Unanchored #L link '{href}' (add symbol label or '\"anchor: <spec>\"' title)",
                )
                continue
            try:
                exp_s, exp_e = resolve_anchor(target_path, spec)
            except AnchorError as exc:
                _append_unique(errors, f"[{rel_chap}:{idx}] {exc}")
                continue
            if (s_ln, e_ln) != (exp_s, exp_e):
                _append_unique(
                    errors,
                    f"[{rel_chap}:{idx}] Line link drift for '{spec}': got '#{frag}', expected '{format_line_fragment(exp_s, exp_e)}'",
                )
    return count


def _check_prose_hygiene(raw_line: str, idx: int, rel_chap: Path, errors: list[str]) -> None:
    """Reject accidental GFM strikethrough tildes and unanchored bare prose line numbers."""
    prose_only = _strip_inline_code_and_math(raw_line)
    if prose_only.count("~") >= 2 and "~~" not in prose_only:
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Multiple '~' in prose triggers GFM strikethrough; "
            "use 'about'/'roughly' or wrap in backticks",
        )

    without_links = MD_LINK_RE.sub("", raw_line)
    without_comments = re.sub(r"<!--.*?-->", "", without_links)
    without_math = INLINE_MATH_RE.sub("", without_comments)
    if m := BARE_PROSE_LINE_RE.search(without_math):
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Unanchored prose line number '{m.group(0).strip()}'; "
            "name the construct directly or use an anchored code link",
        )


def _validate_single_chapter(
    chap_path: Path, root_dir: Path, file_cache: dict[Path, list[str]], errors: list[str]
) -> int:
    """Validate one textbook chapter file and return verified anchor count."""
    resolved_chap = chap_path.resolve()
    resolved_root = root_dir.resolve()
    rel_chap = resolved_chap.relative_to(resolved_root)
    orig_text = resolved_chap.read_text(encoding="utf-8")
    lines = orig_text.splitlines()

    synced_text, sync_errs = sync_chapter_text(resolved_chap, resolved_root)
    for err in sync_errs:
        _append_unique(errors, err)
    if not sync_errs and synced_text != orig_text:
        _append_unique(
            errors,
            f"[{rel_chap}] Line references or file line-count badge out of sync "
            "(run 'python3 scripts/sync_book.py')",
        )

    active_fence: tuple[str, int] | None = None
    in_math = False
    pending_anchor: tuple[int, str] | None = None
    anchor_count = 0

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        active_fence, toggled = update_fence_state(stripped, active_fence)
        if toggled:
            pending_anchor = None
            continue
        if active_fence is not None:
            continue
        if stripped == "$$":
            in_math = not in_math
            continue

        if LEGACY_EXPECT_RE.match(stripped):
            _append_unique(
                errors,
                f"[{rel_chap}:{idx}] Legacy '<!-- expect-symbol: ... -->' must be upgraded to '<!-- book-sync: <anchor> -->'",
            )
            continue
        if dir_m := SYNC_DIRECTIVE_RE.match(stripped):
            pending_anchor = (idx, dir_m.group(1))
            continue

        if _validate_transclusion(raw_line, idx, rel_chap, resolved_chap, resolved_root, pending_anchor, file_cache, errors):
            anchor_count += 1
            pending_anchor = None
            continue

        if pending_anchor is not None and stripped:
            _append_unique(
                errors,
                f"[{rel_chap}:{pending_anchor[0]}] Unused book-sync directive '{pending_anchor[1]}' "
                "(must immediately precede a '<<<' transclusion)",
            )
            pending_anchor = None

        if in_math:
            continue

        anchor_count += _validate_markdown_links(raw_line, idx, rel_chap, resolved_chap, resolved_root, file_cache, errors)
        _check_prose_hygiene(raw_line, idx, rel_chap, errors)

    if active_fence is not None:
        _append_unique(errors, f"[{rel_chap}] Unclosed fenced code block at end of file")
    if in_math:
        _append_unique(errors, f"[{rel_chap}] Unclosed '$$' math block at end of file")
    return anchor_count


def validate_chapters(root_dir: Path | None = None) -> tuple[list[str], int, int]:
    """Return `(errors, chapter_count, verified_anchor_count)` across `systems/*/chapters/*.md`."""
    resolved_root = (root_dir or ROOT_DIR).resolve()
    errors: list[str] = []
    file_cache: dict[Path, list[str]] = {}
    chapter_paths = sorted(resolved_root.glob("systems/*/chapters/*.md"))
    anchor_count = sum(
        _validate_single_chapter(chap_path, resolved_root, file_cache, errors)
        for chap_path in chapter_paths
    )
    return errors, len(chapter_paths), anchor_count


def main() -> int:
    """CLI entry point for textbook validation."""
    errors, chap_count, anchor_count = validate_chapters(ROOT_DIR)
    if errors:
        print("Textbook validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(
        f"OK: Validated {chap_count} textbook chapter(s) and {anchor_count} code/file anchor(s) with zero drift."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
