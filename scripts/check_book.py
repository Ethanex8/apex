#!/usr/bin/env python3
"""Validate textbook chapters and skill budgets: synced transclusions, layout, and hygiene.

Purpose:
  Enforce zero drift between `systems/*/chapters/*.md` and live source files by
  requiring `<!-- book-sync: <anchor> -->` directives on every `<<<` transclusion,
  enforcing excerpt length caps (`<= 25` lines) and fence/Mermaid legibility limits,
  requiring symbol/title anchors on `#L...` links, banning bare prose line numbers,
  and verifying `.agents/skills/*/SKILL.md` stays within the lean prompt budget.

Usage:
  python3 scripts/check_book.py

Outputs:
  Prints summary counts of validated chapters, anchors, and skills; exits 1 on violations.
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
    FENCE_OPEN_RE,
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
MAX_TRANSCLUSION_LINES = 25
MAX_ASCII_FENCE_COLS = 80
MAX_CODE_FENCE_COLS = 100
MAX_SKILL_LINES = 120
REQUIRED_CALIBRATED_SKILLS = ("apex-couch-mentor", "apex-textbook-author", "apex-artifact-author")

LEGACY_EXPECT_RE = re.compile(r"^<!--\s*expect-symbol:\s*(.+?)\s*-->$")
BOOK_GATE_RE = re.compile(
    r"^<!--\s*book-gate:\s*(allow-long-slice|allow-wide-fence|allow-wide-mermaid)\s*\(([^)]*)\)\s*-->$"
)
TRANSCLUDE_RE = re.compile(
    r"^<<<\s+(@/[^\s{#\[]+|\.\.?/[^\s{#\[]+)(?:#L(\d+)(?:-L?(\d+))?)?"
)
BARE_PROSE_LINE_RE = re.compile(r"\blines?\s+`?\d+(?:\s*[–-]\s*\d+)?", re.IGNORECASE)
INLINE_CODE_RE = re.compile(r"(`+)(?:\\.|.)*?\1")
INLINE_MATH_RE = re.compile(
    r"(?<!\\)\$\$(?:\\.|[^$])*?(?<!\\)\$\$|(?<!\\)\$(?:\\.|[^$\\])*?(?<!\\)\$"
)
MERMAID_LR_RE = re.compile(r"^(?:flowchart|graph)\s+LR\b")
MERMAID_ARROW_RE = re.compile(r"-->|---|-\.->|==>")
HTML_ENTITY_RE = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]+|#[0-9]+|#x[0-9A-Fa-f]+);")
SEQ_MSG_SEMI_RE = re.compile(r"^[^\n:]+(?:->|--?>|->>|-->>|-x|--x|-\)|--\))[^\n:]*:.*;")


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
    allow_long_slice: bool,
    file_cache: dict[Path, list[str]],
    errors: list[str],
) -> bool:
    """Validate one `<<<` transclusion against its `book-sync` anchor and length cap."""
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
    # Large inline code dumps encourage prose paraphrase anti-patterns; force inline comments + short slices.
    if exp_e - exp_s + 1 > MAX_TRANSCLUSION_LINES and not allow_long_slice:
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Transclusion '{spec}' spans {exp_e - exp_s + 1} lines (limit {MAX_TRANSCLUSION_LINES}); "
            "move mechanics to inline source comments or add '<!-- book-gate: allow-long-slice (<reason>) -->'",
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


def _mermaid_header_and_body(
    non_empty: list[tuple[int, str]],
) -> tuple[int, str, list[tuple[int, str]]] | None:
    """Return `(header_line_no, header_text, body_lines)` skipping YAML frontmatter and `%%` comments."""
    in_yaml = False
    for idx, (ln_no, txt) in enumerate(non_empty):
        if in_yaml:
            if txt == "---":
                in_yaml = False
            continue
        if txt == "---":
            in_yaml = True
            continue
        if txt.startswith("%%"):
            continue
        return ln_no, txt, non_empty[idx + 1 :]
    return None


def _validate_fenced_block(
    rel_chap: Path,
    lang: str,
    block_lines: list[tuple[int, str]],
    allow_wide_fence: bool,
    allow_wide_mermaid: bool,
    errors: list[str],
) -> None:
    """Enforce fence column width caps and readable Mermaid diagram topology/syntax."""
    norm_lang = lang.strip().split()[0].lower() if lang.strip() else ""
    if norm_lang == "mermaid":
        non_empty = [(ln_no, txt.strip()) for ln_no, txt in block_lines if txt.strip()]
        parsed = _mermaid_header_and_body(non_empty)
        if parsed is not None:
            header_ln, header_txt, body_lines = parsed
            arrows = sum(
                len(MERMAID_ARROW_RE.findall(txt)) for _, txt in body_lines if not txt.startswith("%%")
            )
            if MERMAID_LR_RE.match(header_txt) and arrows >= 4 and not allow_wide_mermaid:
                _append_unique(
                    errors,
                    f"[{rel_chap}:{header_ln}] Wide horizontal Mermaid diagram ({arrows} edges) shrinks in VitePress; "
                    "use 'flowchart TD' or add '<!-- book-gate: allow-wide-mermaid (<reason>) -->'",
                )
            if header_txt.startswith("sequenceDiagram"):
                for ln_no, txt in body_lines:
                    if txt.startswith("%%"):
                        continue
                    cleaned = HTML_ENTITY_RE.sub("", txt)
                    if SEQ_MSG_SEMI_RE.match(cleaned):
                        _append_unique(
                            errors,
                            f"[{rel_chap}:{ln_no}] Semicolon ';' inside Mermaid sequenceDiagram message triggers parse failure",
                        )

    is_ascii = norm_lang in {"", "text", "txt", "ascii", "diagram"}
    max_cols = MAX_ASCII_FENCE_COLS if is_ascii else MAX_CODE_FENCE_COLS
    if allow_wide_fence:
        return
    for ln_no, raw in block_lines:
        if len(raw) > max_cols:
            _append_unique(
                errors,
                f"[{rel_chap}:{ln_no}] Fenced line is {len(raw)} chars (limit {max_cols} for '{norm_lang or 'ascii'}'); "
                "wrap text or add '<!-- book-gate: allow-wide-fence (<reason>) -->'",
            )
            break


def _flush_unused_anchor(
    rel_chap: Path, pending_anchor: tuple[int, str] | None, errors: list[str]
) -> None:
    """Report any unconsumed `book-sync` directive that did not immediately precede `<<<`."""
    if pending_anchor is not None:
        _append_unique(
            errors,
            f"[{rel_chap}:{pending_anchor[0]}] Unused book-sync directive '{pending_anchor[1]}' "
            "(must immediately precede a '<<<' transclusion)",
        )


def _flush_unused_gates(
    rel_chap: Path, pending_gates: dict[str, tuple[int, str]], keep_slice: bool, errors: list[str]
) -> None:
    """Report and clear unused `book-gate` directives before unrelated chapter content."""
    for kind in list(pending_gates):
        if keep_slice and kind == "allow-long-slice":
            continue
        gate_ln, _ = pending_gates.pop(kind)
        _append_unique(
            errors,
            f"[{rel_chap}:{gate_ln}] Unused book-gate directive '{kind}' (must immediately precede target block)",
        )


def _handle_fence_transition(
    rel_chap: Path,
    stripped: str,
    prev_fence: tuple[str, int] | None,
    fence_meta: tuple[str, bool, bool, list[tuple[int, str]]] | None,
    pending_gates: dict[str, tuple[int, str]],
    errors: list[str],
) -> tuple[str, bool, bool, list[tuple[int, str]]] | None:
    """Manage fence metadata on open and validate accumulated block contents on close."""
    if prev_fence is None:
        fm = FENCE_OPEN_RE.match(stripped)
        lang = fm.group(2).strip() if fm else ""
        allow_wf = pending_gates.pop("allow-wide-fence", None) is not None
        allow_wm = pending_gates.pop("allow-wide-mermaid", None) is not None
        _flush_unused_gates(rel_chap, pending_gates, keep_slice=False, errors=errors)
        return (lang, allow_wf, allow_wm, [])
    if fence_meta is not None:
        _validate_fenced_block(rel_chap, fence_meta[0], fence_meta[3], fence_meta[1], fence_meta[2], errors)
    return None


def _validate_single_chapter(
    chap_path: Path, root_dir: Path, file_cache: dict[Path, list[str]], errors: list[str]
) -> int:
    """Validate one textbook chapter file and return verified anchor count."""
    resolved_chap, resolved_root = chap_path.resolve(), root_dir.resolve()
    rel_chap = resolved_chap.relative_to(resolved_root)
    orig_text = resolved_chap.read_text(encoding="utf-8")
    synced_text, sync_errs = sync_chapter_text(resolved_chap, resolved_root)
    for err in sync_errs:
        _append_unique(errors, err)
    if not sync_errs and synced_text != orig_text:
        _append_unique(errors, f"[{rel_chap}] Line references or badge out of sync (run 'python3 scripts/sync_book.py')")

    active_fence: tuple[str, int] | None = None
    fence_meta: tuple[str, bool, bool, list[tuple[int, str]]] | None = None
    in_math, pending_anchor, anchor_count = False, None, 0
    pending_gates: dict[str, tuple[int, str]] = {}

    for idx, raw_line in enumerate(orig_text.splitlines(), start=1):
        stripped = raw_line.strip()
        prev_fence = active_fence
        active_fence, toggled = update_fence_state(stripped, active_fence)
        if toggled:
            _flush_unused_anchor(rel_chap, pending_anchor, errors)
            pending_anchor = None
            fence_meta = _handle_fence_transition(rel_chap, stripped, prev_fence, fence_meta, pending_gates, errors)
            continue
        if active_fence is not None and fence_meta is not None:
            fence_meta[3].append((idx, raw_line))
            continue
        if stripped == "$$":
            in_math = not in_math
            continue
        if gate_m := BOOK_GATE_RE.match(stripped):
            if not gate_m.group(2).strip():
                _append_unique(errors, f"[{rel_chap}:{idx}] Empty reason inside book-gate directive")
            else:
                pending_gates[gate_m.group(1)] = (idx, gate_m.group(2).strip())
            continue
        if LEGACY_EXPECT_RE.match(stripped):
            _append_unique(errors, f"[{rel_chap}:{idx}] Legacy '<!-- expect-symbol: ... -->' must be upgraded to '<!-- book-sync: <anchor> -->'")
            continue
        if dir_m := SYNC_DIRECTIVE_RE.match(stripped):
            _flush_unused_anchor(rel_chap, pending_anchor, errors)
            _flush_unused_gates(rel_chap, pending_gates, keep_slice=True, errors=errors)
            pending_anchor = (idx, dir_m.group(1))
            continue

        allow_slice = "allow-long-slice" in pending_gates
        if _validate_transclusion(
            raw_line, idx, rel_chap, resolved_chap, resolved_root, pending_anchor, allow_slice, file_cache, errors
        ):
            anchor_count += 1
            pending_anchor = None
            pending_gates.pop("allow-long-slice", None)
            _flush_unused_gates(rel_chap, pending_gates, keep_slice=False, errors=errors)
            continue

        if pending_anchor is not None and stripped:
            _flush_unused_anchor(rel_chap, pending_anchor, errors)
            pending_anchor = None
        if stripped:
            _flush_unused_gates(rel_chap, pending_gates, keep_slice=False, errors=errors)
        if in_math:
            continue
        anchor_count += _validate_markdown_links(raw_line, idx, rel_chap, resolved_chap, resolved_root, file_cache, errors)
        _check_prose_hygiene(raw_line, idx, rel_chap, errors)

    _flush_unused_anchor(rel_chap, pending_anchor, errors)
    _flush_unused_gates(rel_chap, pending_gates, keep_slice=False, errors=errors)
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


def validate_skills(root_dir: Path | None = None) -> tuple[list[str], int]:
    """Enforce frontmatter, `<= 120`-line prompt budget, and calibration logs on `.agents/skills/`."""
    resolved_root = (root_dir or ROOT_DIR).resolve()
    skills_dir = resolved_root / ".agents" / "skills"
    if not skills_dir.is_dir():
        return [], 0

    errors: list[str] = []
    skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    for sdir in skill_dirs:
        rel_dir = sdir.relative_to(resolved_root)
        skill_md = sdir / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"[{rel_dir}] Missing SKILL.md")
            continue
        lines = skill_md.read_text(encoding="utf-8").splitlines()
        # Parse leading YAML frontmatter with stdlib only so check_book stays zero-dependency in CI.
        if not lines or lines[0].strip() != "---" or "---" not in [ln.strip() for ln in lines[1:]]:
            errors.append(f"[{rel_dir}/SKILL.md:1] Missing valid YAML frontmatter delimited by '---'")
        else:
            close_idx = next(i for i, ln in enumerate(lines[1:], start=1) if ln.strip() == "---")
            fm_body = "\n".join(lines[1:close_idx])
            if not re.search(r"^name:\s*\S+", fm_body, re.MULTILINE) or not re.search(
                r"^description:\s*\S+", fm_body, re.MULTILINE
            ):
                errors.append(f"[{rel_dir}/SKILL.md:1] YAML frontmatter requires non-empty 'name' and 'description'")
        if len(lines) > MAX_SKILL_LINES:
            errors.append(
                f"[{rel_dir}/SKILL.md] Exceeds {MAX_SKILL_LINES}-line prompt budget ({len(lines)} lines); "
                "move history into references/calibration_log.md or deterministic scripts"
            )
        if sdir.name in REQUIRED_CALIBRATED_SKILLS:
            cal_log = sdir / "references" / "calibration_log.md"
            if not cal_log.is_file() or not cal_log.read_text(encoding="utf-8").strip():
                errors.append(f"[{rel_dir}] Missing non-empty references/calibration_log.md ledger")
    return errors, len(skill_dirs)


def main() -> int:
    """CLI entry point for textbook and skill validation."""
    errors, chap_count, anchor_count = validate_chapters(ROOT_DIR)
    skill_errors, skill_count = validate_skills(ROOT_DIR)
    errors.extend(skill_errors)
    if errors:
        print("Textbook validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(
        f"OK: Validated {chap_count} textbook chapter(s), {anchor_count} code/file anchor(s), "
        f"and {skill_count} skill(s) with zero drift."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
