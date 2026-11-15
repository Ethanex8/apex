#!/usr/bin/env python3
"""Static AST, Ruff, ShellCheck, and RTL/C quality gate for all Apex artifacts.

Purpose:
  Enforce the Pass-2 and Pass-4 standards from `apex-artifact-author` across all
  Python, Shell, SystemVerilog, and C/Header files under `scripts/` and `systems/`:
    - Python: module + 100% class/function/test docstrings, `<= 80`-line functions
      (unless justified by `# code-gate: allow-long-dispatch (<reason>)`),
      explained `# noqa` / `# ruff: noqa` / `# type: ignore` pragmas, and `ruff check`.
    - Shell: `bash -n`, `shellcheck -x`, `set -euo pipefail`, `Purpose:`/`Usage:`
      header, function doc comments, explained `# shellcheck` directives, and
      CWD-safe sourcing/paths.
    - SystemVerilog / C: contract headers, explained `verilator lint_off`, and
      `verilator --lint-only -Wall` (fail-fast if a required linter is missing).

Usage:
  python3 scripts/check_code.py
  python3 scripts/check_code.py path/to/file1.py path/to/file2.sh

Outputs:
  Prints validated file counts and exits 0 cleanly, or prints every violation and exits 1.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import shutil
import subprocess
import sys
import tokenize
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
IGNORED_PARTS = {".git", ".tools", ".venv", "__pycache__", "node_modules", "dist"}
SUPPORTED_EXTS = {".py", ".sh", ".sv", ".v", ".c", ".h"}
MAX_PY_FUNC_LINES = 80

EXEMPTION_RE = re.compile(r"#\s*code-gate:\s*allow-long-dispatch\s*\(([^)]+)\)")
PRAGMA_RE = re.compile(r"#\s*(?:ruff:\s*noqa|noqa|type:\s*ignore)\b")
NOQA_EXPLAINED_RE = re.compile(r"#\s*(?:ruff:\s*noqa|noqa|type:\s*ignore)\b[^\n]*?(?:—|--|-)\s+\S+")
SH_FUNC_RE = re.compile(r"^\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\s*\)\s*\{")
SHELLCHECK_RE = re.compile(r"#\s*shellcheck\s+([^\n]+)")
CWD_SOURCE_RE = re.compile(r"(?:(?:^|[;&|])\s*)(?:source|\.)\s+\.(?!\.)")


def collect_target_files(
    root_dir: Path, explicit: list[str] | None = None
) -> tuple[list[Path], list[str]]:
    """Return `(valid_paths, errors)` under `scripts/` and `systems/` or explicit CLI paths."""
    if explicit:
        paths: list[Path] = []
        errors: list[str] = []
        for raw in explicit:
            p = Path(raw).resolve()
            if not p.is_file():
                errors.append(f"Target file does not exist: '{raw}'")
            elif p.suffix.lower() not in SUPPORTED_EXTS:
                errors.append(f"Unsupported file extension '{p.suffix}' for '{raw}'")
            else:
                paths.append(p)
        return paths, errors

    candidates: list[Path] = []
    for folder in ("scripts", "systems"):
        base = root_dir / folder
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTS:
                continue
            if any(part in IGNORED_PARTS for part in path.parts):
                continue
            candidates.append(path.resolve())
    return sorted(candidates), []


def _has_long_dispatch_exemption(
    lines: list[str], node: ast.FunctionDef | ast.AsyncFunctionDef
) -> bool:
    """Return True if a `# code-gate: allow-long-dispatch (<reason>)` precedes `node`."""
    first_ln = min([d.lineno for d in node.decorator_list] + [node.lineno])
    idx = first_ln - 2
    while idx >= 0 and not lines[idx].strip():
        idx -= 1
    while idx >= 0 and lines[idx].lstrip().startswith("#"):
        if (m := EXEMPTION_RE.search(lines[idx])) and m.group(1).strip():
            return True
        idx -= 1
    return False


def _has_preceding_comment(lines: list[str], zero_idx: int) -> bool:
    """Return True if a non-shebang, non-pragma `#`/`//` doc comment precedes `zero_idx`."""
    idx = zero_idx - 1
    while idx >= 0 and not lines[idx].strip():
        idx -= 1
    if idx < 0:
        return False
    stripped = lines[idx].lstrip()
    if (
        stripped.startswith("#!")
        or PRAGMA_RE.match(stripped)
        or SHELLCHECK_RE.match(stripped)
        or "verilator lint_off" in stripped
    ):
        return False
    return stripped.startswith(("#", "//"))


def _check_python_pragmas(text: str, lines: list[str], rel: Path) -> list[str]:
    """Scan Python `COMMENT` tokens so unexplained `# noqa` / `# type: ignore` fail fast."""
    errors: list[str] = []
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type != tokenize.COMMENT:
            continue
        ln_num = tok.start[0]
        if (
            PRAGMA_RE.search(tok.string)
            and not NOQA_EXPLAINED_RE.search(tok.string)
            and not _has_preceding_comment(lines, ln_num - 1)
        ):
            errors.append(
                f"[{rel}:{ln_num}] Unexplained '# noqa'/'# type: ignore' pragma; add '— <reason>'"
            )
    return errors


def check_python_file(path: Path, root_dir: Path) -> list[str]:
    """Validate AST docstrings, function lengths, and explained suppressions on one `.py` file."""
    rel = path.relative_to(root_dir) if path.is_relative_to(root_dir) else path
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    errors: list[str] = []

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [f"[{rel}:{exc.lineno}] Python syntax error: {exc.msg}"]

    if not ast.get_docstring(tree):
        errors.append(f"[{rel}:1] Missing module docstring")

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not ast.get_docstring(node):
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            errors.append(f"[{rel}:{node.lineno}] Missing docstring on {kind} '{node.name}'")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_ln = node.end_lineno or node.lineno
            length = end_ln - node.lineno + 1
            if length > MAX_PY_FUNC_LINES and not _has_long_dispatch_exemption(lines, node):
                errors.append(
                    f"[{rel}:{node.lineno}] Function '{node.name}' is {length} lines "
                    f"(limit {MAX_PY_FUNC_LINES}; split or add '# code-gate: allow-long-dispatch (<reason>)')"
                )

    errors.extend(_check_python_pragmas(text, lines, rel))
    return errors


def check_shell_file(path: Path, root_dir: Path) -> list[str]:
    """Validate syntax, `shellcheck -x`, strict mode, headers, and CWD safety on one `.sh` file."""
    rel = path.relative_to(root_dir) if path.is_relative_to(root_dir) else path
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    errors: list[str] = []

    head = "\n".join(lines[:40])
    if "set -euo pipefail" not in head:
        errors.append(f"[{rel}:1] Missing 'set -euo pipefail' strict safety header")
    if "Purpose:" not in head or "Usage:" not in head:
        errors.append(f"[{rel}:1] Missing top contract header containing 'Purpose:' and 'Usage:'")

    for idx, line in enumerate(lines, start=1):
        if (m := SH_FUNC_RE.match(line)) and not _has_preceding_comment(lines, idx - 1):
            errors.append(f"[{rel}:{idx}] Missing doc comment immediately above shell function '{m.group(1)}'")
        if sc_m := SHELLCHECK_RE.search(line):
            _, _, inline_reason = sc_m.group(1).partition("#")
            if not inline_reason.strip() and not _has_preceding_comment(lines, idx - 1):
                errors.append(f"[{rel}:{idx}] Unexplained '# shellcheck' directive; document why above it")
        if CWD_SOURCE_RE.search(line) and "ENV_FILE" not in line and not line.lstrip().startswith("#"):
            errors.append(f"[{rel}:{idx}] CWD-fragile 'source .' hint/command; resolve path from BASH_SOURCE[0]")

    bash_chk = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True, check=False)
    if bash_chk.returncode != 0:
        errors.append(f"[{rel}] bash -n failed: {bash_chk.stderr.strip()}")

    sc_bin = shutil.which("shellcheck")
    if not sc_bin:
        errors.append(f"[{rel}] Missing required linter 'shellcheck' on PATH")
    else:
        sc = subprocess.run([sc_bin, "-x", str(path)], capture_output=True, text=True, check=False)
        if sc.returncode != 0:
            errors.append(f"[{rel}] shellcheck -x failed:\n{sc.stdout.strip() or sc.stderr.strip()}")
    return errors


def check_rtl_or_c_file(path: Path, root_dir: Path) -> list[str]:
    """Validate contract headers and explained lint suppressions on `.sv`/`.v`/`.c`/`.h` files."""
    rel = path.relative_to(root_dir) if path.is_relative_to(root_dir) else path
    lines = path.read_text(encoding="utf-8").splitlines()
    errors: list[str] = []
    head = "\n".join(lines[:45])
    if "Purpose:" not in head:
        errors.append(f"[{rel}:1] Missing top contract header containing 'Purpose:'")

    for idx, line in enumerate(lines, start=1):
        if "verilator lint_off" in line and not _has_preceding_comment(lines, idx - 1):
            errors.append(f"[{rel}:{idx}] Unexplained 'verilator lint_off'; add comment explaining why")

    if path.suffix.lower() in {".sv", ".v"}:
        verilator_bin = shutil.which("verilator") or (
            str(p)
            if (p := root_dir / ".tools" / "oss-cad-suite" / "bin" / "verilator").is_file()
            else None
        )
        if not verilator_bin:
            errors.append(f"[{rel}] Missing required RTL linter 'verilator' on PATH or .tools/oss-cad-suite/bin")
        else:
            proc = subprocess.run(
                [verilator_bin, "--lint-only", "-Wall", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                errors.append(f"[{rel}] verilator --lint-only failed:\n{proc.stderr.strip()}")
    return errors


def _run_ruff(py_files: list[Path], root_dir: Path) -> list[str]:
    """Run `ruff check` across `py_files`, using direct binary or `uv run --with ruff`."""
    if not py_files:
        return []
    targets = [str(p) for p in py_files]
    ruff_bin = shutil.which("ruff")
    if ruff_bin:
        cmd = [ruff_bin, "check", *targets]
    elif uv_bin := shutil.which("uv"):
        cmd = [uv_bin, "run", "--with", "ruff", "ruff", "check", *targets]
    else:
        return ["Missing required linter 'ruff' (or 'uv') on PATH"]

    proc = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        msg = (proc.stdout + "\n" + proc.stderr).strip()
        return [f"ruff check failed:\n{msg}"]
    return []


def run_checks(root_dir: Path | None = None, explicit: list[str] | None = None) -> tuple[list[str], int]:
    """Run all language quality checks and return `(errors, file_count)`."""
    resolved_root = (root_dir or ROOT_DIR).resolve()
    files, errors = collect_target_files(resolved_root, explicit)
    py_files: list[Path] = []

    for path in files:
        suf = path.suffix.lower()
        if suf == ".py":
            py_files.append(path)
            errors.extend(check_python_file(path, resolved_root))
        elif suf == ".sh":
            errors.extend(check_shell_file(path, resolved_root))
        elif suf in {".sv", ".v", ".c", ".h"}:
            errors.extend(check_rtl_or_c_file(path, resolved_root))

    errors.extend(_run_ruff(py_files, resolved_root))
    return errors, len(files)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for repo-wide static code quality verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="Optional explicit source files to check.")
    args = parser.parse_args(argv if argv is not None else [])
    errors, count = run_checks(ROOT_DIR, args.files or None)
    if errors:
        print("Code quality gate FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"OK: Verified {count} code/script file(s) with 100% docstring, modularity, and lint compliance.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
