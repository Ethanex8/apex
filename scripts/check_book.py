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
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

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
MAX_RUBRIC_LINES = 100
MAX_SKILL_BULLET_WORDS = 50
SKILL_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.*)$")
MAX_CHAPTER_TITLE_WORDS = 6
MAX_SECTION_HEADING_WORDS = 8
MAX_PROSE_BOLD_WORDS = 6
MAX_PROSE_COORDINATE_REFS = 4
ASCII_FENCE_LANGS = {"", "text", "txt", "ascii", "diagram"}
REQUIRED_CALIBRATED_SKILLS = ("apex-couch-mentor", "apex-textbook-author", "apex-artifact-author")
PROSE_NON_CODE_TERMS = frozenset({
    "HDL", "ISA", "ISAs", "ALU", "FPGA", "FPGAs", "RTL", "EDA", "DSP", "LUT", "LUT4",
    "MMIO", "FIFO", "FIFOs", "CSR", "CSRs", "WARL", "IRQ", "IRQs", "ISR", "ISRs",
    "MLP", "SIMD", "RTOS", "PCB", "PCBA", "RAM", "ROM", "SRAM", "BRAM", "SDRAM", "DRAM",
    "QSPI", "QSPI Flash", "Boot ROM", "XIP", "DMA", "SPI", "CAN", "CAN-FD", "GPIO",
    "CLINT", "UART", "RISC-V", "RV32", "RV32I", "RV32M", "RV32IM", "Zicsr", "Xapex",
    "Xapex MAC", "MAC", "SystemVerilog", "Verilog", "Verilator", "Yosys", "nextpnr",
    "KiCad", "MuJoCo", "Python", "Linux", "ARM", "x86", "x86-64", "JVM", "POSIX",
    "CPU", "SoC", "NPU", "GPU", "M-mode", "RO", "WO",
    "MIE", "MPIE", "MPP", "MSIE", "MTIE", "MEIE", "MSIP", "MTIP", "MEIP",
})

LEGACY_EXPECT_RE = re.compile(r"^<!--\s*expect-symbol:\s*(.+?)\s*-->$")
BOOK_GATE_RE = re.compile(
    r"^<!--\s*book-gate:\s*"
    r"(allow-long-slice|allow-wide-fence|allow-wide-mermaid|allow-ascii-fence|allow-multi-sentence-line|allow-enumerative-prose)"
    r"\s*\(([^)]*)\s*\)\s*-->$"
)
TRANSCLUDE_RE = re.compile(
    r"^<<<\s+(@/[^\s{#\[]+|\.\.?/[^\s{#\[]+)(?:#L(\d+)(?:-L?(\d+))?)?"
)
BARE_PROSE_LINE_RE = re.compile(r"\blines?\s+`?\d+(?:\s*[–-]\s*\d+)?", re.IGNORECASE)
INLINE_CODE_RE = re.compile(r"(`+)((?:\\.|.)*?)\1")
INLINE_MATH_RE = re.compile(
    r"(?<!\\)\$\$(?:\\.|[^$])*?(?<!\\)\$\$|(?<!\\)\$(?:\\.|[^$\\])*?(?<!\\)\$"
)
MERMAID_LR_RE = re.compile(r"^(?:flowchart|graph)\s+LR\b")
MERMAID_ARROW_RE = re.compile(r"-->|---|-\.->|==>")
HTML_ENTITY_RE = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]+|#[0-9]+|#x[0-9A-Fa-f]+);")
SEQ_MSG_SEMI_RE = re.compile(r"^[^\n:]+(?:->|--?>|->>|-->>|-x|--x|-\)|--\))[^\n:]*:.*;")
H1_HEADING_RE = re.compile(r"^#\s+(.+)$")
HEADING_RE = re.compile(r"^(#{2,4})\s+(.+)$")
PRACTICE_HEADING_RE = re.compile(r"\b(?:Exercises?|Problems?)(?:\s+\d+(?:\.\d+)?)?\b", re.IGNORECASE)
EXERCISE_PREFIX_RE = re.compile(r"^(?:Example|Problem)\s+\d+(?:\.\d+)?:\s*(.+)$", re.IGNORECASE)
H4_EXERCISE_RE = re.compile(r"^####\s+(Exercise\b.+)$", re.IGNORECASE)
SECTION_NUM_PREFIX_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s+")
CHAPTER_PREFIX_RE = re.compile(r"^Chapter\s+\d+:\s*", re.IGNORECASE)
CHAPTER_BANNER_NOISE_RE = re.compile(
    r"\b(?:Reading Time|Interactive Figures|Primary Modules)\b|\*\*Part\s+[IVX]+:",
    re.IGNORECASE,
)
VUE_TAG_RE = re.compile(r"^<[A-Z][A-Za-z0-9]*(?:\s|/>|>)")
HTML_TAG_LINE_RE = re.compile(r"^<!--.*-->$|^</?[A-Za-z][^>]*>(?:.*</[A-Za-z][^>]*>)?$")
LIST_OPEN_RE = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
LIST_LEAD_BOLD_RE = re.compile(r"^(?:\s*(?:[-*+]|\d+[.)])\s+)\*\*([^*]+)\*\*")
BOLD_SPAN_RE = re.compile(r"\*\*([^*\n]+)\*\*")
DETACHED_TERM_DEF_RE = re.compile(r"—[^—\n]{3,120}\(\*\*[^*]+\*\*\)")
TEX_IN_CODE_RE = re.compile(r"[_^]\{[^`]+\}")
COMMA_NUM_IN_CODE_RE = re.compile(r"(?<![A-Za-z0-9_\"'])[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![A-Za-z0-9_\"'])")
BACKTICK_NUM_HYPHEN_RE = re.compile(r"`\d+`-(?:bit|byte|entry|wire|cycle|stage)\b")
BACKTICK_UNIT_RE = re.compile(r"`\d+(?:[.,]\d+)*\s+(?:MHz|kHz|GHz|Hz|ms|µs|us|ns|KB|MB|GB|W)`")
BACKTICK_COUNT_NOUN_RE = re.compile(
    r"`(?:[2-9]|\d{2,})`\s+(?:wires?|bits?|bytes?|patterns?|registers?|entries|lanes?|joints?|legs?|motors?|weights?|words?|slots?|pages?)\b"
)
ABBREV_RE = re.compile(r"\b(?:e\.g|i\.e|vs|cf|etc|approx|Sec|Ch|Fig|Eq|No)\.", re.IGNORECASE)
MULTI_SENTENCE_RE = re.compile(r"[.!?](?:['\")\]*]+)?\s+[A-Z\"`*($]")
ABRUPT_IMPERATIVE_RE = re.compile(r"^(?:Trace|Examine|Inspect|Click|Play with|Experiment with)\b")
CONVERSATIONAL_CRUTCH_RE = re.compile(r"\b(?:Wait:\s+why|Hold on:|Wait a second:)", re.IGNORECASE)
DATASHEET_SHORTHAND_RE = re.compile(r"imm\[[^\]]*\|[^\]]*\]|\[\d+\|imm|\[[\d.]+\|[\d.]+\]")
COORDINATE_BIT_RE = re.compile(r"\bBits?\s+\d+(?:\.\.\d+)?\b")


@dataclass
class MermaidBlock:
    """Parsed Mermaid diagram header line number, header text, and body lines."""

    header_line: int
    header_text: str
    body_lines: list[tuple[int, str]]


@dataclass
class FenceBlock:
    """Active fenced block metadata accumulated between opening and closing delimiters."""

    open_line: int
    lang: str
    allow_wide_fence: bool
    allow_wide_mermaid: bool
    allow_ascii_fence: bool
    lines: list[tuple[int, str]] = field(default_factory=list)


class ChapterValidationResult(NamedTuple):
    """Summary returned by `validate_chapters` across all textbook chapters."""

    errors: list[str]
    chapter_count: int
    anchor_count: int


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
    allow_wide_fence: bool,
    file_cache: dict[Path, list[str]],
    errors: list[str],
) -> bool:
    """Validate one `<<<` transclusion against its `book-sync` anchor, length cap, and column width."""
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
    if not allow_wide_fence:
        for offset, src_raw in enumerate(src_lines[exp_s - 1 : exp_e], start=exp_s):
            if len(src_raw) > MAX_CODE_FENCE_COLS:
                _append_unique(
                    errors,
                    f"[{rel_chap}:{idx}] Transcluded line {target_path.name}:{offset} is {len(src_raw)} chars "
                    f"(limit {MAX_CODE_FENCE_COLS}); wrap source comment/code or add '<!-- book-gate: allow-wide-fence (<reason>) -->'",
                )
                break
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


def _check_prose_hygiene(
    raw_line: str, idx: int, rel_chap: Path, errors: list[str], allow_enum: bool = False
) -> None:
    """Reject accidental GFM strikethrough, bare prose line numbers, filler crutches, bit shorthand, and coord walls."""
    prose_only = _strip_inline_code_and_math(raw_line)
    if prose_only.count("~") >= 2 and "~~" not in prose_only:
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Multiple '~' in prose triggers GFM strikethrough; "
            "use 'about'/'roughly' or wrap in backticks",
        )
    if m := CONVERSATIONAL_CRUTCH_RE.search(prose_only):
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Conversational crutch '{m.group(0)}'; state the technical motivation directly",
        )
    if m := DATASHEET_SHORTHAND_RE.search(raw_line):
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Cryptic bit-slice shorthand '{m.group(0)}'; use explicit 'Bits A..B' labels",
        )
    if not allow_enum and not raw_line.lstrip().startswith("|"):
        coord_hits = COORDINATE_BIT_RE.findall(prose_only)
        if len(coord_hits) > MAX_PROSE_COORDINATE_REFS:
            _append_unique(
                errors,
                f"[{rel_chap}:{idx}] Coordinate-recitation prose wall ({len(coord_hits)} 'Bits ...' refs); "
                "present bit-slice maps in a Markdown table (or add '<!-- book-gate: allow-enumerative-prose (<reason>) -->')",
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


def _validate_heading_style(
    rel_chap: Path, idx: int, stripped: str, state: _ChapterScanState, errors: list[str]
) -> bool:
    """Validate `#`/`##`/`###` conciseness and punctuation, updating `state` and returning True on headings."""
    if h1_m := H1_HEADING_RE.match(stripped):
        state.seen_h1 = True
        state.seen_h1_prose = False
        core = CHAPTER_PREFIX_RE.sub("", h1_m.group(1).strip()).strip()
        if len(core.split()) > MAX_CHAPTER_TITLE_WORDS or any(ch in core for ch in ("&", ":", ",")):
            _append_unique(
                errors,
                f"[{rel_chap}:{idx}] Chapter H1 title '{core}' must be concise "
                f"(<= {MAX_CHAPTER_TITLE_WORDS} words, primary topic only without '&', ':', or ',')",
            )
        return True

    hm = HEADING_RE.match(stripped)
    if not hm:
        return False
    hashes, body = hm.group(1), hm.group(2).strip()
    if hashes == "##":
        if not state.seen_h2 and state.seen_h1 and not state.seen_h1_prose:
            _append_unique(
                errors,
                f"[{rel_chap}:{idx}] Chapter jumps straight from H1 into '{body}' without introductory prose",
            )
        state.seen_h2 = True
    ex_m = EXERCISE_PREFIX_RE.match(body)
    core = ex_m.group(1).strip() if ex_m else SECTION_NUM_PREFIX_RE.sub("", body).strip()
    if ":" in core:
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Section heading '{body}' contains ':'; "
            "use a single direct topic phrase without 'Hook: Subtitle' colons",
        )
    if "&" in core:
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Section heading '{body}' uses '&'; write 'and' or focus on the primary topic",
        )
    if "(" in core or ")" in core:
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Section heading '{body}' contains parenthetical clutter; "
            "move symbols and details into prose",
        )
    if "`" in core:
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Section heading '{body}' wraps words in backticks; use plain English in headings",
        )
    if len(core.split()) > MAX_SECTION_HEADING_WORDS:
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Section heading '{core}' exceeds {MAX_SECTION_HEADING_WORDS} words "
            f"({len(core.split())}); tighten to the primary topic",
        )
    if hashes == "##" and PRACTICE_HEADING_RE.search(body) and core.lower() != "problems":
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Problem/exercise closing heading '{body}' should simply be 'Problems' "
            "(e.g., '## <N>. Problems')",
        )
    if hashes == "####" and H4_EXERCISE_RE.match(stripped):
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Mid-chapter exercise drill '{body}' is banned; "
            "use a visible inline '#### Example <S.K>: <Title>' block and keep practice in '## <N>. Problems'",
        )
    state.pending_heading = None if PRACTICE_HEADING_RE.search(body) else (idx, body)
    return True


def _check_frontmatter_banner(
    rel_chap: Path, idx: int, stripped: str, state: _ChapterScanState, errors: list[str]
) -> None:
    """Ban front-matter metadata blockquotes, reading-time tags, and figure inventories before first `##`."""
    if state.seen_h2 or not stripped:
        return
    if stripped.startswith(">"):
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Front-matter blockquote banner before first '##' section is banned; "
            "open directly with introductory prose",
        )
    elif not HTML_TAG_LINE_RE.match(stripped):
        state.seen_h1_prose = True
    if m := CHAPTER_BANNER_NOISE_RE.search(stripped):
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Front-matter metadata/TOC/figure inventory ('{m.group(0)}') is banned; "
            "let the sidebar TOC speak for itself",
        )


def _check_backtick_hygiene(raw_line: str, idx: int, rel_chap: Path, errors: list[str]) -> None:
    """Ban inline backticks around English acronyms, proper nouns, prose numbers/units, and raw TeX math."""
    for match in INLINE_CODE_RE.finditer(raw_line):
        code_txt = match.group(2).strip()
        if code_txt in PROSE_NON_CODE_TERMS:
            _append_unique(
                errors,
                f"[{rel_chap}:{idx}] Non-code acronym or proper noun '`{code_txt}`' wrapped in backticks; "
                "reserve backticks for literal code identifiers, instructions, and paths",
            )
        if not code_txt.startswith(('f"', "f'", 'F"', "F'")) and TEX_IN_CODE_RE.search(code_txt):
            _append_unique(
                errors,
                f"[{rel_chap}:{idx}] Raw LaTeX subscript/superscript inside backticks '`{code_txt}`'; "
                "render math with '$...$' instead of code font",
            )
        if cm := COMMA_NUM_IN_CODE_RE.search(code_txt):
            _append_unique(
                errors,
                f"[{rel_chap}:{idx}] Comma-formatted prose number '{cm.group(0)}' inside backticks '`{code_txt}`'; "
                "use plain prose numbers or Python '_' digit separators",
            )
    without_math = INLINE_MATH_RE.sub("", raw_line)
    for pat in (BACKTICK_NUM_HYPHEN_RE, BACKTICK_UNIT_RE, BACKTICK_COUNT_NOUN_RE):
        if m := pat.search(without_math):
            _append_unique(
                errors,
                f"[{rel_chap}:{idx}] Prose number/measurement '{m.group(0)}' uses backticks; "
                "write plain numbers and units without backticks",
            )


def _check_bold_and_term_adjacency(raw_line: str, idx: int, rel_chap: Path, errors: list[str]) -> None:
    """Require `( **term** )` immediately adjacent to its noun phrase and cap rhetorical bold spans."""
    code_masked = INLINE_MATH_RE.sub("MATH", INLINE_CODE_RE.sub("CODE", raw_line))
    if m := DETACHED_TERM_DEF_RE.search(code_masked):
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Detached term definition '{m.group(0)}'; "
            "place (**term**) immediately after the noun phrase it defines",
        )
    if raw_line.lstrip().startswith("|"):
        return
    body = LIST_LEAD_BOLD_RE.sub("", code_masked)
    for bm in BOLD_SPAN_RE.finditer(body):
        span = bm.group(1).strip()
        if len(span.split()) > MAX_PROSE_BOLD_WORDS:
            _append_unique(
                errors,
                f"[{rel_chap}:{idx}] Overlong bold phrase '**{span}**' ({len(span.split())} words > "
                f"{MAX_PROSE_BOLD_WORDS}); reserve boldface for defined technical terms",
            )


def _check_semantic_line_breaks(
    raw_line: str, idx: int, rel_chap: Path, allow_multi: bool, errors: list[str]
) -> None:
    """Enforce one sentence per Markdown prose line without trailing two-space hard `<br>` breaks."""
    if raw_line.endswith("  "):
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Trailing two-space hard '<br>' break; "
            "use single-newline semantic line breaks (one sentence per line)",
        )
    stripped = raw_line.strip()
    if allow_multi or not stripped or stripped.startswith(("#", "|")) or HTML_TAG_LINE_RE.match(stripped):
        return
    unlinked = MD_LINK_RE.sub(lambda m: m.group(1), stripped)
    masked = INLINE_MATH_RE.sub("MATH", INLINE_CODE_RE.sub("CODE", unlinked))
    masked = re.sub(r"^(?:>\s*)+", "", masked)
    masked = LIST_OPEN_RE.sub("", masked)
    masked = ABBREV_RE.sub("ABBR", masked)
    if MULTI_SENTENCE_RE.search(masked):
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Multiple sentences on one Markdown line; "
            "break prose into one sentence per line for clean PR review",
        )



def _mermaid_header_and_body(non_empty: list[tuple[int, str]]) -> MermaidBlock | None:
    """Return `MermaidBlock` skipping YAML frontmatter and `%%` comments, or None if empty."""
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
        return MermaidBlock(header_line=ln_no, header_text=txt, body_lines=non_empty[idx + 1 :])
    return None


def _validate_mermaid_block(
    rel_chap: Path, block: FenceBlock, errors: list[str]
) -> None:
    """Validate Mermaid topology (`flowchart TD` vs wide `LR`) and `sequenceDiagram` semicolons."""
    non_empty = [(ln_no, txt.strip()) for ln_no, txt in block.lines if txt.strip()]
    parsed = _mermaid_header_and_body(non_empty)
    if parsed is None:
        return
    arrows = sum(len(MERMAID_ARROW_RE.findall(txt)) for _, txt in parsed.body_lines if not txt.startswith("%%"))
    if MERMAID_LR_RE.match(parsed.header_text) and arrows >= 4 and not block.allow_wide_mermaid:
        _append_unique(
            errors,
            f"[{rel_chap}:{parsed.header_line}] Wide horizontal Mermaid diagram ({arrows} edges) shrinks in VitePress; "
            "use 'flowchart TD' or add '<!-- book-gate: allow-wide-mermaid (<reason>) -->'",
        )
    if parsed.header_text.startswith("sequenceDiagram"):
        for ln_no, txt in parsed.body_lines:
            if txt.startswith("%%"):
                continue
            if SEQ_MSG_SEMI_RE.match(HTML_ENTITY_RE.sub("", txt)):
                _append_unique(
                    errors,
                    f"[{rel_chap}:{ln_no}] Semicolon ';' inside Mermaid sequenceDiagram message triggers parse failure",
                )


def _validate_fenced_block(rel_chap: Path, block: FenceBlock, errors: list[str]) -> None:
    """Enforce zero raw ASCII-art fences, column width caps, and readable Mermaid topology."""
    norm_lang = block.lang.strip().split()[0].lower() if block.lang.strip() else ""
    if norm_lang == "mermaid":
        _validate_mermaid_block(rel_chap, block, errors)

    is_ascii = norm_lang in ASCII_FENCE_LANGS
    if is_ascii and not block.allow_ascii_fence:
        _append_unique(
            errors,
            f"[{rel_chap}:{block.open_line}] Raw ASCII/text diagram fence ('{norm_lang or 'unlabelled'}') banned; "
            "use a Vue widget or Mermaid figure (or add '<!-- book-gate: allow-ascii-fence (<reason>) -->')",
        )
    for ln_no, raw in block.lines:
        if m := DATASHEET_SHORTHAND_RE.search(raw):
            _append_unique(
                errors,
                f"[{rel_chap}:{ln_no}] Cryptic bit-slice shorthand '{m.group(0)}'; use explicit 'Bits A..B' labels",
            )
    if block.allow_wide_fence:
        return
    max_cols = MAX_ASCII_FENCE_COLS if is_ascii else MAX_CODE_FENCE_COLS
    for ln_no, raw in block.lines:
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
        if keep_slice and kind in ("allow-long-slice", "allow-wide-fence"):
            continue
        gate_ln, _ = pending_gates.pop(kind)
        _append_unique(
            errors,
            f"[{rel_chap}:{gate_ln}] Unused book-gate directive '{kind}' (must immediately precede target block)",
        )


def _handle_fence_transition(
    rel_chap: Path,
    line_num: int,
    stripped: str,
    prev_fence: tuple[str, int] | None,
    fence_meta: FenceBlock | None,
    pending_gates: dict[str, tuple[int, str]],
    errors: list[str],
) -> FenceBlock | None:
    """Manage fence metadata on open and validate accumulated block contents on close."""
    if prev_fence is None:
        fm = FENCE_OPEN_RE.match(stripped)
        lang = fm.group(2).strip() if fm else ""
        allow_wf = pending_gates.pop("allow-wide-fence", None) is not None
        allow_wm = pending_gates.pop("allow-wide-mermaid", None) is not None
        allow_af = pending_gates.pop("allow-ascii-fence", None) is not None
        _flush_unused_gates(rel_chap, pending_gates, keep_slice=False, errors=errors)
        return FenceBlock(line_num, lang, allow_wf, allow_wm, allow_af)
    if fence_meta is not None:
        _validate_fenced_block(rel_chap, fence_meta, errors)
    return None


def _check_heading_opening(
    rel_chap: Path,
    pending_heading: tuple[int, str] | None,
    stripped: str,
    opened_fence: bool,
    errors: list[str],
) -> tuple[int, str] | None:
    """Ensure every non-Exercise `##`/`###` heading opens with a calm introductory prose sentence."""
    if pending_heading is None:
        return None
    if not stripped or stripped.startswith("<!--"):
        return pending_heading
    h_ln, h_txt = pending_heading
    if opened_fence:
        _append_unique(
            errors,
            f"[{rel_chap}:{h_ln}] Heading '{h_txt}' jumps straight into a code/diagram block without an intro sentence",
        )
    elif VUE_TAG_RE.match(stripped):
        _append_unique(
            errors,
            f"[{rel_chap}:{h_ln}] Heading '{h_txt}' jumps straight into a Vue widget without an intro sentence",
        )
    elif stripped.startswith("<<<"):
        _append_unique(
            errors,
            f"[{rel_chap}:{h_ln}] Heading '{h_txt}' jumps straight into a code transclusion without an intro sentence",
        )
    elif stripped.startswith("|") or LIST_OPEN_RE.match(stripped) or stripped == "$$":
        _append_unique(
            errors,
            f"[{rel_chap}:{h_ln}] Heading '{h_txt}' jumps straight into a list/table/equation without an intro sentence",
        )
    elif m := ABRUPT_IMPERATIVE_RE.match(stripped):
        _append_unique(
            errors,
            f"[{rel_chap}:{h_ln}] Heading '{h_txt}' opens abruptly with '{m.group(0)}...'; add a conceptual bridge first",
        )
    return None


def _load_checked_chapter_text(
    resolved_chap: Path, resolved_root: Path, rel_chap: Path, errors: list[str]
) -> str:
    """Read chapter text and record any `sync_book` drift errors."""
    orig_text = resolved_chap.read_text(encoding="utf-8")
    synced_text, sync_errs = sync_chapter_text(resolved_chap, resolved_root)
    for err in sync_errs:
        _append_unique(errors, err)
    if not sync_errs and synced_text != orig_text:
        _append_unique(errors, f"[{rel_chap}] Line references or badge out of sync (run 'python3 scripts/sync_book.py')")
    return orig_text


@dataclass
class _ChapterScanState:
    """Mutable per-chapter parser state tracked across lines during validation."""

    active_fence: tuple[str, int] | None = None
    fence_meta: FenceBlock | None = None
    in_math: bool = False
    seen_h1: bool = False
    seen_h1_prose: bool = False
    seen_h2: bool = False
    pending_anchor: tuple[int, str] | None = None
    pending_heading: tuple[int, str] | None = None
    anchor_count: int = 0
    pending_gates: dict[str, tuple[int, str]] = field(default_factory=dict)


def _process_chapter_directive(
    rel_chap: Path,
    idx: int,
    stripped: str,
    state: _ChapterScanState,
    errors: list[str],
) -> bool:
    """Handle `book-gate`, legacy `expect-symbol`, and `book-sync` HTML directives; return True if consumed."""
    if gate_m := BOOK_GATE_RE.match(stripped):
        if not gate_m.group(2).strip():
            _append_unique(errors, f"[{rel_chap}:{idx}] Empty reason inside book-gate directive")
        else:
            state.pending_gates[gate_m.group(1)] = (idx, gate_m.group(2).strip())
        return True
    if LEGACY_EXPECT_RE.match(stripped):
        _append_unique(
            errors,
            f"[{rel_chap}:{idx}] Legacy '<!-- expect-symbol: ... -->' must be upgraded to '<!-- book-sync: <anchor> -->'",
        )
        return True
    if dir_m := SYNC_DIRECTIVE_RE.match(stripped):
        _flush_unused_anchor(rel_chap, state.pending_anchor, errors)
        _flush_unused_gates(rel_chap, state.pending_gates, keep_slice=True, errors=errors)
        state.pending_anchor = (idx, dir_m.group(1))
        return True
    return False


def _validate_prose_line(
    raw_line: str,
    stripped: str,
    idx: int,
    rel_chap: Path,
    resolved_chap: Path,
    resolved_root: Path,
    state: _ChapterScanState,
    file_cache: dict[Path, list[str]],
    errors: list[str],
) -> None:
    """Validate headings, front-matter banners, links, backticks, bold spans, and line breaks."""
    if _validate_heading_style(rel_chap, idx, stripped, state, errors):
        _flush_unused_gates(rel_chap, state.pending_gates, keep_slice=False, errors=errors)
        return

    allow_multi = bool(stripped and state.pending_gates.pop("allow-multi-sentence-line", None) is not None)
    allow_enum = bool(stripped and state.pending_gates.pop("allow-enumerative-prose", None) is not None)
    if stripped:
        _flush_unused_gates(rel_chap, state.pending_gates, keep_slice=False, errors=errors)
    _check_frontmatter_banner(rel_chap, idx, stripped, state, errors)
    state.pending_heading = _check_heading_opening(rel_chap, state.pending_heading, stripped, False, errors)
    state.anchor_count += _validate_markdown_links(
        raw_line, idx, rel_chap, resolved_chap, resolved_root, file_cache, errors
    )
    _check_prose_hygiene(raw_line, idx, rel_chap, errors, allow_enum=allow_enum)
    _check_backtick_hygiene(raw_line, idx, rel_chap, errors)
    _check_bold_and_term_adjacency(raw_line, idx, rel_chap, errors)
    _check_semantic_line_breaks(raw_line, idx, rel_chap, allow_multi, errors)


def _validate_midchapter_details(lines: list[str], rel_chap: Path, errors: list[str]) -> None:
    """Ban mid-chapter `<details>` quiz toggles outside the closing `## <N>. Problems` section."""
    active_fence: tuple[str, int] | None = None
    in_problems = False

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        active_fence, toggled = update_fence_state(stripped, active_fence)
        if toggled or active_fence is not None:
            continue
        if hm := HEADING_RE.match(stripped):
            hashes, body = hm.group(1), hm.group(2).strip()
            if hashes == "##":
                core = SECTION_NUM_PREFIX_RE.sub("", body).strip().lower()
                in_problems = core == "problems"
            continue
        if not in_problems and "<details" in stripped.lower():
            _append_unique(
                errors,
                f"[{rel_chap}:{idx}] Mid-chapter '<details>' toggle is banned outside '## <N>. Problems'; "
                "show worked steps visibly inside inline '#### Example' blocks instead",
            )


def _validate_single_chapter(
    chap_path: Path, root_dir: Path, file_cache: dict[Path, list[str]], errors: list[str]
) -> int:
    """Validate one textbook chapter file and return verified anchor count."""
    resolved_chap, resolved_root = chap_path.resolve(), root_dir.resolve()
    rel_chap = resolved_chap.relative_to(resolved_root)
    orig_text = _load_checked_chapter_text(resolved_chap, resolved_root, rel_chap, errors)
    lines = orig_text.splitlines()
    state = _ChapterScanState()

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        prev_fence = state.active_fence
        state.active_fence, toggled = update_fence_state(stripped, state.active_fence)
        if toggled:
            _flush_unused_anchor(rel_chap, state.pending_anchor, errors)
            state.pending_anchor = None
            state.pending_heading = _check_heading_opening(
                rel_chap, state.pending_heading, stripped, opened_fence=(prev_fence is None), errors=errors
            )
            state.fence_meta = _handle_fence_transition(
                rel_chap, idx, stripped, prev_fence, state.fence_meta, state.pending_gates, errors
            )
            continue
        if state.active_fence is not None and state.fence_meta is not None:
            state.fence_meta.lines.append((idx, raw_line))
            continue
        if stripped == "$$":
            state.pending_heading = _check_heading_opening(rel_chap, state.pending_heading, stripped, False, errors)
            state.in_math = not state.in_math
            continue
        if _process_chapter_directive(rel_chap, idx, stripped, state, errors):
            continue

        allow_slice = "allow-long-slice" in state.pending_gates
        allow_wide = "allow-wide-fence" in state.pending_gates
        if _validate_transclusion(
            raw_line,
            idx,
            rel_chap,
            resolved_chap,
            resolved_root,
            state.pending_anchor,
            allow_slice,
            allow_wide,
            file_cache,
            errors,
        ):
            state.pending_heading = _check_heading_opening(rel_chap, state.pending_heading, stripped, False, errors)
            state.anchor_count += 1
            state.pending_anchor = None
            state.pending_gates.pop("allow-long-slice", None)
            state.pending_gates.pop("allow-wide-fence", None)
            _flush_unused_gates(rel_chap, state.pending_gates, keep_slice=False, errors=errors)
            continue

        if state.pending_anchor is not None and stripped:
            _flush_unused_anchor(rel_chap, state.pending_anchor, errors)
            state.pending_anchor = None
        if state.in_math:
            if stripped:
                _flush_unused_gates(rel_chap, state.pending_gates, keep_slice=False, errors=errors)
            continue
        _validate_prose_line(
            raw_line, stripped, idx, rel_chap, resolved_chap, resolved_root, state, file_cache, errors
        )

    _flush_unused_anchor(rel_chap, state.pending_anchor, errors)
    _flush_unused_gates(rel_chap, state.pending_gates, keep_slice=False, errors=errors)
    if state.active_fence is not None:
        _append_unique(errors, f"[{rel_chap}] Unclosed fenced code block at end of file")
    if state.in_math:
        _append_unique(errors, f"[{rel_chap}] Unclosed '$$' math block at end of file")
    _validate_midchapter_details(lines, rel_chap, errors)
    return state.anchor_count


def validate_chapters(root_dir: Path | None = None) -> ChapterValidationResult:
    """Return `ChapterValidationResult` across all `systems/*/chapters/*.md`."""
    resolved_root = (root_dir or ROOT_DIR).resolve()
    errors: list[str] = []
    file_cache: dict[Path, list[str]] = {}
    chapter_paths = sorted(resolved_root.glob("systems/*/chapters/*.md"))
    anchor_count = sum(
        _validate_single_chapter(chap_path, resolved_root, file_cache, errors)
        for chap_path in chapter_paths
    )
    return ChapterValidationResult(errors=errors, chapter_count=len(chapter_paths), anchor_count=anchor_count)


def validate_widgets(root_dir: Path | None = None) -> list[str]:
    """Scan interactive Vue widgets for cryptic datasheet bit-slice shorthand (`imm[12|10:5]`)."""
    resolved_root = (root_dir or ROOT_DIR).resolve()
    comp_dir = resolved_root / "book" / ".vitepress" / "theme" / "components"
    if not comp_dir.is_dir():
        return []
    errors: list[str] = []
    for vue_path in sorted(comp_dir.rglob("*.vue")):
        rel_vue = vue_path.relative_to(resolved_root)
        for idx, line in enumerate(vue_path.read_text(encoding="utf-8").splitlines(), start=1):
            if m := DATASHEET_SHORTHAND_RE.search(line):
                _append_unique(
                    errors,
                    f"[{rel_vue}:{idx}] Cryptic bit-slice shorthand '{m.group(0)}'; use explicit 'Bits A..B' labels",
                )
    return errors


def _validate_skill_bullets(lines: list[str], rel_path: str, errors: list[str]) -> None:
    """Enforce `<= MAX_SKILL_BULLET_WORDS` per bullet outside fenced code blocks."""
    in_fence = False
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if m := SKILL_BULLET_RE.match(line):
            words = len(m.group(1).split())
            if words > MAX_SKILL_BULLET_WORDS:
                errors.append(
                    f"[{rel_path}:{idx}] Bullet has {words} words (limit {MAX_SKILL_BULLET_WORDS}); "
                    "split monolithic rules into atomic bullets"
                )


def _validate_skill_rubrics(sdir: Path, rel_dir: Path, errors: list[str]) -> None:
    """Validate `references/rubric_*.md` line budgets and atomic bullet lengths."""
    refs_dir = sdir / "references"
    if not refs_dir.is_dir():
        return
    for rubric in sorted(refs_dir.glob("rubric_*.md")):
        r_lines = rubric.read_text(encoding="utf-8").splitlines()
        rel_rubric = f"{rel_dir}/references/{rubric.name}"
        if len(r_lines) > MAX_RUBRIC_LINES:
            errors.append(
                f"[{rel_rubric}] Exceeds {MAX_RUBRIC_LINES}-line rubric budget ({len(r_lines)} lines)"
            )
        _validate_skill_bullets(r_lines, rel_rubric, errors)


def validate_skills(root_dir: Path | None = None) -> tuple[list[str], int]:
    """Enforce frontmatter, `<= 120`-line prompt budget, bullet caps, and calibration isolation."""
    resolved_root = (root_dir or ROOT_DIR).resolve()
    skills_dir = resolved_root / ".agents" / "skills"
    if not skills_dir.is_dir():
        return [], 0

    errors: list[str] = []
    skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    for sdir in skill_dirs:
        rel_dir = sdir.relative_to(resolved_root)
        for leaked in sorted(sdir.rglob("*calibration_log*")):
            rel_leak = leaked.relative_to(resolved_root)
            errors.append(
                f"[{rel_leak}] Calibration logs must live in docs/calibration/<skill>.md, "
                "never inside .agents/skills/ (prevents registry leakage into clean-room reviewers)"
            )
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
            if "calibration_log" in fm_body:
                errors.append(
                    f"[{rel_dir}/SKILL.md:1] YAML frontmatter must not expose calibration_log.md to reviewers"
                )
        if len(lines) > MAX_SKILL_LINES:
            errors.append(
                f"[{rel_dir}/SKILL.md] Exceeds {MAX_SKILL_LINES}-line prompt budget ({len(lines)} lines); "
                "move history into docs/calibration/ or deterministic scripts"
            )
        _validate_skill_bullets(lines, f"{rel_dir}/SKILL.md", errors)
        _validate_skill_rubrics(sdir, rel_dir, errors)
        if sdir.name in REQUIRED_CALIBRATED_SKILLS:
            cal_log = resolved_root / "docs" / "calibration" / f"{sdir.name}.md"
            if not cal_log.is_file() or not cal_log.read_text(encoding="utf-8").strip():
                errors.append(f"[{rel_dir}] Missing non-empty docs/calibration/{sdir.name}.md ledger")
    return errors, len(skill_dirs)


def validate_gemini_rules(root_dir: Path | None = None) -> list[str]:
    """Enforce `<= MAX_SKILL_BULLET_WORDS` atomic bullets inside `GEMINI.md` when present."""
    resolved_root = (root_dir or ROOT_DIR).resolve()
    gemini_path = resolved_root / "GEMINI.md"
    if not gemini_path.is_file():
        return []
    errors: list[str] = []
    lines = gemini_path.read_text(encoding="utf-8").splitlines()
    _validate_skill_bullets(lines, "GEMINI.md", errors)
    return errors


def main() -> int:
    """CLI entry point for textbook, widget, skill, and GEMINI rule validation."""
    result = validate_chapters(ROOT_DIR)
    errors = list(result.errors)
    errors.extend(validate_widgets(ROOT_DIR))
    skill_errors, skill_count = validate_skills(ROOT_DIR)
    errors.extend(skill_errors)
    errors.extend(validate_gemini_rules(ROOT_DIR))
    if errors:
        print("Textbook validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(
        f"OK: Validated {result.chapter_count} textbook chapter(s), {result.anchor_count} code/file anchor(s), "
        f"and {skill_count} skill(s) with zero drift."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
