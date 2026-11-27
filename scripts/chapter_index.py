#!/usr/bin/env python3
"""Compile compact, factual structural and consumer indexes for Apex textbook chapters.

Purpose:
  Generate `docs/CHAPTER_INDEX.md` deterministically from `systems/*/chapters/*.md`
  so isolated sharded reviewers and human readers have a zero-hint, whole-chapter
  map of section line shares, newly defined terms/helpers, inline drills, widgets,
  and downstream consumers.

Usage:
  python3 scripts/chapter_index.py
  python3 scripts/build.py

Outputs:
  Writes or returns formatted Markdown tables covering every textbook chapter.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CHAPTER_INDEX_MD_PATH = ROOT_DIR / "docs" / "CHAPTER_INDEX.md"

H1_RE = re.compile(r"^#\s+(.+)$")
H2_RE = re.compile(r"^##\s+(.+)$")
H3_RE = re.compile(r"^###\s+(.+)$")
FENCE_TOGGLE_RE = re.compile(r"^(`{3,}|~{3,})")
VUE_TAG_RE = re.compile(r"^<([A-Z][A-Za-z0-9]*)(?:\s*/>|\s|>).*$")
MD_SYMBOL_RE = re.compile(r"\[`([A-Za-z_][A-Za-z0-9_.]*)`\]\([^)]+\)")
INLINE_BOLD_RE = re.compile(r"\*\*([A-Za-z0-9][^*\n|]{1,48})\*\*")
INLINE_CODE_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]{2,})`")

GENERIC_STOPWORDS = frozenset({
    "and", "the", "for", "with", "from", "into", "via", "using", "based",
    "core", "base", "step", "bits", "bit", "byte", "word", "halfword",
    "true", "false", "none", "else", "self", "val", "res", "ret", "tmp",
    "out", "note", "solution", "worked", "summary", "check", "example",
    "for example", "notice", "hardware", "software",
})


@dataclass
class SubsectionMeta:
    """Factual structural and symbol summary for one `##` or `###` span."""

    level: int
    label: str
    short_ref: str
    start_line: int
    end_line: int
    line_count: int
    pct_chapter: float
    defined_terms: list[str] = field(default_factory=list)
    code_symbols: list[str] = field(default_factory=list)
    widgets: list[str] = field(default_factory=list)
    consumers: list[str] = field(default_factory=list)
    raw_text_lower: str = ""


@dataclass
class ChapterMeta:
    """Parsed title, total line count, and section metadata list for one chapter."""

    title: str
    total_lines: int
    sections: list[SubsectionMeta]


def _short_section_ref(heading: str, current_h2_num: str, sub_idx: int) -> str:
    """Format a compact section identifier like `Sec 2` or `2.4`."""
    if heading.startswith("## "):
        m = re.match(r"^##\s+(\d+)\.", heading)
        return f"Sec {m.group(1)}" if m else heading[3:22]
    if current_h2_num:
        return f"{current_h2_num}.{sub_idx}"
    return heading[4:22]


def _extract_spans(lines: list[str]) -> list[SubsectionMeta]:
    """Parse all `##` and `###` headings and contiguous line ranges from `lines`."""
    headers: list[tuple[int, int, str]] = []
    in_fence = False
    for idx, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if FENCE_TOGGLE_RE.match(stripped):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if H2_RE.match(stripped):
            headers.append((2, idx, stripped))
        elif H3_RE.match(stripped):
            headers.append((3, idx, stripped))

    total = max(1, len(lines))
    metas: list[SubsectionMeta] = []
    cur_h2_num = ""
    sub_idx = 0
    for pos, (lvl, start, text) in enumerate(headers):
        if lvl == 2:
            m = re.match(r"^##\s+(\d+)\.", text)
            cur_h2_num = m.group(1) if m else ""
            sub_idx = 0
            end = next((headers[j][1] - 1 for j in range(pos + 1, len(headers)) if headers[j][0] == 2), len(lines))
        else:
            sub_idx += 1
            end = (headers[pos + 1][1] - 1) if pos + 1 < len(headers) else len(lines)
        count = end - start + 1
        metas.append(
            SubsectionMeta(
                level=lvl,
                label=text.lstrip("#").strip(),
                short_ref=_short_section_ref(text, cur_h2_num, sub_idx),
                start_line=start,
                end_line=end,
                line_count=count,
                pct_chapter=(100.0 * count) / total,
            )
        )
    return metas


def _dedupe_novel(items: list[str], seen_prior: set[str], limit: int) -> list[str]:
    """Collect newly introduced unique items (skipping anything seen in earlier sections)."""
    out: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen_prior:
            continue
        seen_prior.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _populate_meta_tokens(
    meta: SubsectionMeta,
    slice_lines: list[str],
    seen_terms: set[str],
    seen_syms: set[str],
) -> None:
    """Populate newly introduced terms, symbols, and widgets for `meta`."""
    in_fence = False
    terms: list[str] = []
    symbols: list[str] = []
    widgets: list[str] = []

    for raw in slice_lines:
        stripped = raw.strip()
        if FENCE_TOGGLE_RE.match(stripped):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if wm := VUE_TAG_RE.match(stripped):
            widgets.append(f"<{wm.group(1)} />")
        for sm in MD_SYMBOL_RE.finditer(stripped):
            tok = sm.group(1)
            if not tok.endswith((".py", ".sv", ".c", ".h", ".sh")):
                symbols.append(tok)
        if not stripped.startswith("|"):
            for bm in INLINE_BOLD_RE.finditer(stripped):
                phrase = bm.group(1).strip().rstrip(":")
                if phrase and phrase.lower() not in GENERIC_STOPWORDS and not phrase.startswith(("Problem ", "Example ")):
                    terms.append(phrase)
        for cm in INLINE_CODE_RE.finditer(stripped):
            tok = cm.group(1)
            if tok.lower() not in GENERIC_STOPWORDS and not tok.startswith("0x"):
                symbols.append(tok)

    meta.defined_terms = _dedupe_novel(terms, seen_terms, 4)
    meta.code_symbols = _dedupe_novel(symbols, seen_syms, 5)
    meta.widgets = _dedupe_novel(widgets, set(), 3)
    meta.raw_text_lower = "\n".join(slice_lines).lower()


_GENERIC_H_WORDS = frozenset({
    "integers", "integer", "arithmetic", "circuits", "hardware", "software",
    "summary", "problem", "problems", "general", "register", "registers",
})


def _link_downstream_consumers(metas: list[SubsectionMeta]) -> None:
    """Find later subsections referencing newly introduced symbols or terms in each leaf span."""
    leaves = [m for m in metas if m.raw_text_lower]
    for pos, src in enumerate(leaves):
        needles: list[str] = [sym.lower() for sym in src.code_symbols if len(sym) >= 3]
        for term in src.defined_terms[:3]:
            norm = re.sub(r"[^a-z0-9\s-]", "", term.lower()).strip()
            if len(norm) >= 6:
                needles.append(norm)
                if " " in norm:
                    needles.append(norm.replace(" ", "-"))
        for hword in re.findall(r"[a-z]{8,}", src.label.lower()):
            if hword not in _GENERIC_H_WORDS:
                needles.append(hword)
        if not needles:
            continue
        refs: list[str] = []
        for dst in leaves[pos + 1 :]:
            if any(re.search(rf"(?<![a-z0-9_]){re.escape(n)}(?![a-z0-9_])", dst.raw_text_lower) for n in needles):
                refs.append(dst.short_ref)
                if len(refs) >= 4:
                    break
        src.consumers = refs


def _build_chapter_metas(chap_path: Path) -> ChapterMeta:
    """Parse headings, novel tokens, drills, and downstream consumers for one chapter file."""
    lines = chap_path.read_text(encoding="utf-8").splitlines()
    title = chap_path.stem
    for raw in lines[:20]:
        if m := H1_RE.match(raw.strip()):
            title = m.group(1).strip()
            break
    metas = _extract_spans(lines)
    seen_terms: set[str] = set()
    seen_syms: set[str] = set()
    for idx, meta in enumerate(metas):
        has_h3 = meta.level == 2 and idx + 1 < len(metas) and metas[idx + 1].level == 3
        if not has_h3:
            _populate_meta_tokens(meta, lines[meta.start_line - 1 : meta.end_line], seen_terms, seen_syms)
    _link_downstream_consumers(metas)
    return ChapterMeta(title=title, total_lines=len(lines), sections=metas)


def _format_cell(items: list[str]) -> str:
    """Format list items concisely for Markdown table cells without pipes breaking columns."""
    if not items:
        return "—"
    return ", ".join(i.replace("|", "\\|") for i in items)


def render_chapter_index_md(root_dir: Path | None = None) -> str:
    """Compile `docs/CHAPTER_INDEX.md` across all `systems/*/chapters/*.md` files."""
    resolved_root = (root_dir or ROOT_DIR).resolve()
    chapters = sorted(resolved_root.glob("systems/*/chapters/*.md"))
    out = [
        "# Apex Textbook Chapter Index",
        "",
        "Compact, auto-generated structural and dependency map (`scripts/build.py`) for isolated textbook reviewers and readers.",
        "",
    ]
    if not chapters:
        out.append("*(No textbook chapters authored yet.)*")
        return "\n".join(out) + "\n"

    for chap_path in chapters:
        rel = chap_path.relative_to(resolved_root).as_posix()
        cmeta = _build_chapter_metas(chap_path)
        out.extend([
            f"## {cmeta.title} (`{rel}`, {cmeta.total_lines} lines)",
            "",
            "| Section | Lines (% Ch.) | Newly Defined Terms & Symbols | First Later Consumers | Visuals |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])
        for m in cmeta.sections:
            sec_label = f"**{m.short_ref}: {m.label}**" if m.level == 2 else f"↳ `{m.short_ref}` {m.label}"
            span = f"`L{m.start_line}..L{m.end_line}` ({m.line_count}, {m.pct_chapter:.1f}%)"
            toks = [*m.defined_terms[:3], *(f"`{s}`" for s in m.code_symbols[:4])]
            out.append(
                f"| {sec_label} | {span} | {_format_cell(toks)} | "
                f"{_format_cell(m.consumers)} | {_format_cell(m.widgets)} |"
            )
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    """Regenerate `docs/CHAPTER_INDEX.md` directly and print path summary."""
    rendered = render_chapter_index_md(ROOT_DIR)
    CHAPTER_INDEX_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHAPTER_INDEX_MD_PATH.write_text(rendered, encoding="utf-8")
    print(f"OK: Generated {CHAPTER_INDEX_MD_PATH.relative_to(ROOT_DIR)} ({len(rendered.splitlines())} lines).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
