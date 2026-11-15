#!/usr/bin/env python3
"""AST- and parser-driven source symbol & statement-span resolver for Apex.

Purpose:
  Resolve exact 1-indexed `(start_line, end_line)` spans inside Python, SystemVerilog,
  C/Header/Assembly, and Shell source files without polluting source code with
  `#region` markers. Powers `scripts/sync_book.py` and `scripts/check_book.py`.

Usage:
  from code_anchors import AnchorError, extract_symbols, resolve_anchor
  start, end = resolve_anchor(Path("systems/brain/sim/oracle.py"), "RV32Oracle.step")

Invariants:
  - Returned line numbers are always 1-indexed and inclusive (`1 <= start <= end`).
  - Ambiguous or missing symbols/statement patterns raise `AnchorError` with context.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path


class AnchorError(ValueError):
    """Raised when an anchor spec is malformed, missing, or matches zero/multiple spans."""


_SPAN_SPEC_RE = re.compile(
    r'^(?P<scope>[^\[\]]*?)\[\s*(?:(?P<q1>["\'])(?P<p1>(?:\\.|(?!(?P=q1)).)*)(?P=q1))\s*'
    r'(?:\.\.\s*(?:(?P<q2>["\'])(?P<p2>(?:\\.|(?!(?P=q2)).)*)(?P=q2))\s*)?\]$'
)


def _unescape_quoted(raw: str) -> str:
    """Decode backslash escapes inside bracketed statement-slice patterns."""
    return re.sub(r"\\(.)", r"\1", raw)


def _extract_python_symbols(text: str) -> dict[str, tuple[int, int]]:
    """Extract 1-indexed `(start, end)` line spans from Python source using `ast`."""
    tree = ast.parse(text)
    symbols: dict[str, tuple[int, int]] = {}
    method_counts: Counter[str] = Counter()
    unqualified_methods: dict[str, tuple[int, int]] = {}

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decs = [d.lineno for d in node.decorator_list]
            start = min(decs + [node.lineno])
            end = node.end_lineno or node.lineno
            symbols[node.name] = (start, end)
        elif isinstance(node, ast.ClassDef):
            decs = [d.lineno for d in node.decorator_list]
            start = min(decs + [node.lineno])
            end = node.end_lineno or node.lineno
            symbols[node.name] = (start, end)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    m_decs = [d.lineno for d in item.decorator_list]
                    m_start = min(m_decs + [item.lineno])
                    m_end = item.end_lineno or item.lineno
                    symbols[f"{node.name}.{item.name}"] = (m_start, m_end)
                    method_counts[item.name] += 1
                    unqualified_methods[item.name] = (m_start, m_end)
        elif isinstance(node, ast.Assign):
            end = node.end_lineno or node.lineno
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    symbols.setdefault(tgt.id, (node.lineno, end))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            end = node.end_lineno or node.lineno
            symbols.setdefault(node.target.id, (node.lineno, end))

    for m_name, count in method_counts.items():
        if count == 1 and m_name not in symbols:
            symbols[m_name] = unqualified_methods[m_name]
    return symbols


def _find_matching_brace_end(lines: list[str], open_idx: int, label: str = "<source>") -> int:
    """Scan forward from 0-indexed `open_idx` counting `{`/`}` to locate block end."""
    depth = 0
    saw_open = False
    for idx in range(open_idx, len(lines)):
        clean = re.sub(
            r'/\*.*?\*/|//.*$|(?:^|(?<=[\s;|&(]))#(?![!{]).*$|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
            "",
            lines[idx],
        )
        for ch in clean:
            if ch == "{":
                depth += 1
                saw_open = True
            elif ch == "}":
                depth -= 1
                if saw_open and depth <= 0:
                    return idx + 1
    raise AnchorError(f"Unclosed '{{' brace block starting at {label}:{open_idx + 1}")


def _extract_sv_symbols(text: str) -> dict[str, tuple[int, int]]:
    """Extract module, function, task, param, and labeled block spans from SystemVerilog."""
    lines = text.splitlines()
    symbols: dict[str, tuple[int, int]] = {}
    mod_re = re.compile(r"^\s*module\s+([A-Za-z_]\w*)\b")
    fn_re = re.compile(r"^\s*(?:automatic\s+)?(function|task)\b.*?\b([A-Za-z_]\w*)\s*(?:\(|;)")
    param_re = re.compile(r"^\s*(?:localparam|parameter)\b[^=]*?\b([A-Za-z_]\w*)\s*=")
    begin_re = re.compile(r"\bbegin\s*:\s*([A-Za-z_]\w*)")

    for i, line in enumerate(lines):
        if m := mod_re.match(line):
            name = m.group(1)
            for j in range(i, len(lines)):
                if re.match(r"^\s*endmodule\b", lines[j]):
                    symbols[name] = (i + 1, j + 1)
                    break
        elif m := fn_re.match(line):
            kw, name = m.groups()
            end_kw = f"end{kw}"
            for j in range(i, len(lines)):
                if re.search(rf"\b{end_kw}\b", lines[j]):
                    symbols[name] = (i + 1, j + 1)
                    break
        elif m := param_re.match(line):
            symbols.setdefault(m.group(1), (i + 1, i + 1))
        elif m := begin_re.search(re.sub(r"/\*.*?\*/|//.*$", "", line)):
            label = m.group(1)
            depth = 0
            for j in range(i, len(lines)):
                code_part = re.sub(r"/\*.*?\*/|//.*$", "", lines[j])
                depth += len(re.findall(r"\bbegin\b", code_part))
                depth -= len(re.findall(r"\bend\b", code_part))
                if depth <= 0:
                    symbols[label] = (i + 1, j + 1)
                    break
    return symbols


def _extract_c_or_asm_symbols(text: str, label: str = "<source>") -> dict[str, tuple[int, int]]:
    """Extract C/Header `#define` macros and functions, plus assembly labels."""
    lines = text.splitlines()
    symbols: dict[str, tuple[int, int]] = {}
    def_re = re.compile(r"^\s*#define\s+([A-Za-z_]\w*)")
    fn_re = re.compile(r"^(?:[A-Za-z_][\w\s\*]*?[\s\*])([A-Za-z_]\w*)\s*\([^;]*\)\s*(?:\{|$)")
    asm_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s*(?://|#|/\*|$))")

    for i, line in enumerate(lines):
        if m := def_re.match(line):
            end = i + 1
            while end < len(lines) and lines[end - 1].rstrip().endswith("\\"):
                end += 1
            symbols.setdefault(m.group(1), (i + 1, end))
        elif m := fn_re.match(line):
            name = m.group(1)
            if name not in {"if", "for", "while", "switch"} and "{" in "".join(lines[i : i + 3]):
                symbols[name] = (i + 1, _find_matching_brace_end(lines, i, label))
        elif m := asm_re.match(line):
            name = m.group(1)
            end = i + 1
            for j in range(i + 1, len(lines)):
                if asm_re.match(lines[j]):
                    end = j
                    break
                end = j + 1
            symbols.setdefault(name, (i + 1, end))
    return symbols


def _extract_shell_symbols(text: str, label: str = "<source>") -> dict[str, tuple[int, int]]:
    """Extract Bash function definitions and top-level variable assignments."""
    lines = text.splitlines()
    symbols: dict[str, tuple[int, int]] = {}
    fn_re = re.compile(r"^\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\s*\)\s*\{?")
    var_re = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=")

    for i, line in enumerate(lines):
        if m := fn_re.match(line):
            name = m.group(1)
            symbols[name] = (i + 1, _find_matching_brace_end(lines, i, label))
        elif m := var_re.match(line):
            symbols.setdefault(m.group(1), (i + 1, i + 1))
    return symbols


def extract_symbols(file_path: Path) -> dict[str, tuple[int, int]]:
    """Return a mapping of symbol names to inclusive `(start_line, end_line)` spans."""
    text = file_path.read_text(encoding="utf-8")
    suffix = file_path.suffix.lower()
    if suffix == ".py":
        return _extract_python_symbols(text)
    if suffix in {".sv", ".v", ".svh"}:
        return _extract_sv_symbols(text)
    if suffix in {".c", ".h", ".s"}:
        return _extract_c_or_asm_symbols(text, file_path.name)
    if suffix == ".sh":
        return _extract_shell_symbols(text, file_path.name)
    return {}


def _resolve_symbol_name(
    symbols: dict[str, tuple[int, int]], name: str, file_path: Path
) -> tuple[int, int]:
    """Look up a single symbol identifier, raising `AnchorError` if missing."""
    clean = name.strip().removesuffix("()")
    if clean not in symbols:
        raise AnchorError(f"Symbol '{clean}' not found in '{file_path}'")
    return symbols[clean]


def _resolve_bracketed_slice(
    file_path: Path,
    lines: list[str],
    symbols: dict[str, tuple[int, int]],
    scope: str,
    pat1_raw: str,
    pat2_raw: str | None,
) -> tuple[int, int]:
    """Resolve `Scope["pat1"]` or `Scope["pat1".."pat2"]` to unique line bounds."""
    scope_clean = scope.strip()
    if scope_clean:
        search_start, search_end = _resolve_symbol_name(symbols, scope_clean, file_path)
    else:
        search_start, search_end = 1, len(lines)

    pat1 = _unescape_quoted(pat1_raw)
    matches1 = [
        ln for ln in range(search_start, search_end + 1) if pat1 in lines[ln - 1]
    ]
    if len(matches1) != 1:
        raise AnchorError(
            f"Pattern '{pat1}' inside '{scope_clean or file_path.name}' in '{file_path}' "
            f"matched {len(matches1)} lines (expected exactly 1)"
        )
    s_ln = matches1[0]
    if pat2_raw is None:
        return (s_ln, s_ln)

    pat2 = _unescape_quoted(pat2_raw)
    matches2 = [
        ln for ln in range(s_ln, search_end + 1) if pat2 in lines[ln - 1]
    ]
    if len(matches2) != 1:
        raise AnchorError(
            f"End pattern '{pat2}' after line {s_ln} inside '{scope_clean or file_path.name}' "
            f"in '{file_path}' matched {len(matches2)} lines (expected exactly 1)"
        )
    return (s_ln, matches2[0])


def resolve_anchor(file_path: Path, spec: str) -> tuple[int, int]:
    """Resolve an anchor specification (`sym`, `a..b`, or `Scope["p1".."p2"]`) to 1-indexed lines."""
    clean_spec = spec.strip()
    if not clean_spec:
        raise AnchorError(f"Empty anchor specification for '{file_path}'")

    symbols = extract_symbols(file_path)
    if "[" in clean_spec:
        m = _SPAN_SPEC_RE.match(clean_spec)
        if not m or m.group("p1") is None:
            raise AnchorError(f"Malformed statement-slice anchor '{clean_spec}' for '{file_path}'")
        lines = file_path.read_text(encoding="utf-8").splitlines()
        return _resolve_bracketed_slice(
            file_path,
            lines,
            symbols,
            m.group("scope") or "",
            m.group("p1"),
            m.group("p2"),
        )

    if ".." in clean_spec:
        parts = clean_spec.split("..")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            raise AnchorError(f"Malformed symbol-span anchor '{clean_spec}' for '{file_path}'")
        s1, _ = _resolve_symbol_name(symbols, parts[0], file_path)
        _, e2 = _resolve_symbol_name(symbols, parts[1], file_path)
        if s1 > e2:
            raise AnchorError(
                f"Reversed symbol span '{clean_spec}' in '{file_path}' ({s1} > {e2})"
            )
        return (s1, e2)

    return _resolve_symbol_name(symbols, clean_spec, file_path)
