#!/usr/bin/env python3
"""Unit tests for Apex code-sync, textbook-gate, and artifact quality tooling.

Purpose:
  Verify every parser branch, sync rewrite rule, git prose-impact detector,
  book hygiene validator, and AST/Shell/RTL/Ruff quality gate across:
    - `scripts/code_anchors.py`
    - `scripts/sync_book.py`
    - `scripts/check_book.py`
    - `scripts/check_code.py`

Usage:
  PYTHONPATH=scripts uv run --with pytest --with pytest-cov --with pyyaml pytest -v \\
    --cov=code_anchors --cov=sync_book --cov=check_book --cov=check_code \\
    --cov-fail-under=95 scripts/tests/test_repo_tooling.py

Invariants:
  - Runs strictly in `tmp_path` without mutating repository chapters or scripts.
  - Maintains >=95% line coverage across all code-sync and quality-gate tooling.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_book  # noqa: E402 — repo test runner imports standalone scripts without package install
import check_code  # noqa: E402 — repo test runner imports standalone scripts without package install
import code_anchors  # noqa: E402 — repo test runner imports standalone scripts without package install
import sync_book  # noqa: E402 — repo test runner imports standalone scripts without package install


def _write_text(path: Path, text: str) -> Path:
    """Create parent directories and write UTF-8 text to `path`, returning `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _make_git_book_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Create an initialized git repo with one Python module and one synced chapter."""
    src = _write_text(
        tmp_path / "systems" / "demo" / "sim" / "alu.py",
        '"""ALU module."""\n'
        "\n"
        "MASK = 0xFF\n"
        "\n"
        "def add(a: int, b: int) -> int:\n"
        '    """Add two ints."""\n'
        "    return (a + b) & MASK\n",
    )
    chap = _write_text(
        tmp_path / "systems" / "demo" / "chapters" / "01_alu.md",
        "# Chapter 1\n\n"
        "## Section One: Adder\n\n"
        "See [`add`](../sim/alu.py#L1) in [`alu.py`](../sim/alu.py) (`1` lines).\n\n"
        "<!-- book-sync: add -->\n"
        "<<< @/systems/demo/sim/alu.py#L1\n",
    )
    for cmd in (
        ["git", "init"],
        ["git", "config", "user.name", "Apex Test"],
        ["git", "config", "user.email", "test@example.com"],
        ["git", "add", "."],
        ["git", "commit", "-m", "initial"],
    ):
        subprocess.run(cmd, cwd=tmp_path, check=True, capture_output=True)
    return src, chap


def test_code_anchors_python_symbols_and_slices(tmp_path: Path) -> None:
    """Verify Python AST extraction, unique vs. ambiguous methods, constants, and bracket slices."""
    py_file = _write_text(
        tmp_path / "mod.py",
        "CONST_A = 1\n"
        "CONST_B: int = 2\n"
        "\n"
        "@staticmethod\n"
        "def helper(x: int) -> int:\n"
        "    y = x + 1\n"
        "    return y\n"
        "\n"
        "class Alpha:\n"
        "    def unique_m(self) -> int:\n"
        "        return 10\n"
        "    def shared(self) -> int:\n"
        "        return 20\n"
        "\n"
        "class Beta:\n"
        "    def shared(self) -> int:\n"
        "        return 30\n",
    )
    syms = code_anchors.extract_symbols(py_file)
    assert syms["CONST_A"] == (1, 1)
    assert syms["CONST_B"] == (2, 2)
    assert code_anchors.resolve_anchor(py_file, "helper()") == (4, 7)
    assert code_anchors.resolve_anchor(py_file, "unique_m") == (10, 11)
    assert code_anchors.resolve_anchor(py_file, "Beta.shared") == (16, 17)
    assert "shared" not in syms  # Ambiguous across Alpha and Beta
    assert code_anchors.resolve_anchor(py_file, "CONST_A..helper") == (1, 7)
    assert code_anchors.resolve_anchor(py_file, "Alpha.shared['return 20']") == (13, 13)
    assert code_anchors.resolve_anchor(py_file, '["y = x + 1".."return y"]') == (6, 7)


def test_code_anchors_sv_c_asm_shell_and_errors(tmp_path: Path) -> None:
    """Verify SystemVerilog, C/Assembly, and Shell parsers plus AnchorError diagnostics."""
    sv = _write_text(
        tmp_path / "core.sv",
        "module core;\n"
        "  localparam WIDTH = 32;\n"
        "  function automatic int add1(int x);\n"
        "    return x + 1;\n"
        "  endfunction\n"
        "  always_comb begin : decode_blk\n"
        "    int z = 0;\n"
        "  end\n"
        "endmodule\n",
    )
    c_src = _write_text(
        tmp_path / "boot.c",
        "#define SUM(a, b) \\\n  ((a) + (b))\n"
        "int main(void) {\n"
        "  if (1) { return 0; }\n"
        "}\n",
    )
    asm_src = _write_text(tmp_path / "start.S", "reset_vec:\n  nop\nhalt:\n  j halt\n")
    sh_src = _write_text(
        tmp_path / "run.sh",
        "FOO=bar\n"
        "helper() {\n"
        '  if [ -n "$FOO" ]; then echo "{ok}"; fi\n'
        "}\n",
    )
    txt = _write_text(tmp_path / "notes.txt", "plain text\n")

    assert code_anchors.resolve_anchor(sv, "core") == (1, 9)
    assert code_anchors.resolve_anchor(sv, "WIDTH") == (2, 2)
    assert code_anchors.resolve_anchor(sv, "add1") == (3, 5)
    assert code_anchors.resolve_anchor(sv, "decode_blk") == (6, 8)
    assert code_anchors.resolve_anchor(c_src, "SUM") == (1, 2)
    assert code_anchors.resolve_anchor(c_src, "main") == (3, 5)
    assert code_anchors.resolve_anchor(asm_src, "reset_vec") == (1, 2)
    assert code_anchors.resolve_anchor(asm_src, "halt") == (3, 4)
    assert code_anchors.resolve_anchor(sh_src, "FOO") == (1, 1)
    assert code_anchors.resolve_anchor(sh_src, "helper") == (2, 4)
    assert code_anchors.extract_symbols(txt) == {}

    for bad in ("", "missing", "a..b..c", "add1..WIDTH", "core[unquoted]", '["nope"]', '["return 0".."nope"]'):
        target = sv if bad != '["return 0".."nope"]' else c_src
        with pytest.raises(code_anchors.AnchorError):
            code_anchors.resolve_anchor(target, bad)


def test_sync_book_rewrites_and_fences(tmp_path: Path) -> None:
    """Verify sync_book rewrites transclusions, links, labels, and badges while ignoring fences."""
    src = _write_text(
        tmp_path / "systems" / "demo" / "sim" / "alu.py",
        "PAD = 0\n"
        "PAD2 = 1\n"
        "def compute(x: int) -> int:\n"
        "    val = x * 2\n"
        "    return val + 1\n",
    )
    chap = _write_text(
        tmp_path / "systems" / "demo" / "chapters" / "01.md",
        "# Ch 1\n\n"
        "Call [`compute(x)`](../sim/alu.py#L1) or [body lines 1–1](../sim/alu.py#L1 \"anchor: compute['val = x * 2'..'return val + 1']\").\n"
        "File [`alu.py`](../sim/alu.py) (`1` lines), [external](https://example.com#L1), inline `[compute](alu.py#L1)`, [miss](nope.py#L1).\n\n"
        "<!-- book-sync: compute -->\n"
        "<<< @/systems/demo/sim/alu.py#L1\n\n"
        "```md\n"
        "<!-- book-sync: fake -->\n"
        "<<< @/systems/demo/sim/alu.py#L1\n"
        "```\n"
        "$$\n"
        "x = 1\n"
        "$$\n",
    )
    changed, errors = sync_book.sync_all_chapters(tmp_path, check_only=True)
    assert errors == [] and changed == [chap]
    assert "#L1" in chap.read_text(encoding="utf-8")

    changed2, errors2 = sync_book.sync_all_chapters(tmp_path, check_only=False)
    assert errors2 == [] and changed2 == [chap]
    updated = chap.read_text(encoding="utf-8")
    assert "[`compute(x)`](../sim/alu.py#L3-L5)" in updated
    assert '[body lines 4–5](../sim/alu.py#L4-L5 "anchor: compute[\'val = x * 2\'..\'return val + 1\']")' in updated
    assert f"(`{len(src.read_text().splitlines())}` lines)" in updated
    assert "<<< @/systems/demo/sim/alu.py#L3-L5" in updated
    # Fenced example must stay untouched
    assert "<<< @/systems/demo/sim/alu.py#L1" in updated


def test_sync_book_prose_impact_and_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify git diff prose-impact distinguishes line shifts from edits inside transcluded spans."""
    src, chap = _make_git_book_repo(tmp_path)
    # Edit above `add`: shifts line numbers only, should report zero prose impact on `add`
    src.write_text(
        '"""ALU module."""\n'
        "\n"
        "HEADER_COMMENT = 1\n"
        "MASK = 0xFF\n\n"
        "def add(a: int, b: int) -> int:\n"
        '    """Add two ints."""\n'
        "    return (a + b) & MASK\n",
        encoding="utf-8",
    )
    assert sync_book.detect_prose_impact("HEAD", tmp_path) == []

    # Edit inside `add`: triggers prose impact warning pointing at Section One
    src.write_text(
        src.read_text(encoding="utf-8").replace("return (a + b) & MASK", "return (a + b + 0) & MASK"),
        encoding="utf-8",
    )
    impacts = sync_book.detect_prose_impact("HEAD", tmp_path)
    assert len(impacts) == 1 and "Section One: Adder" in impacts[0] and "(add)" in impacts[0]

    monkeypatch.setattr(sync_book, "ROOT_DIR", tmp_path)
    assert sync_book.main(["--check"]) == 1  # Drift before sync
    assert sync_book.main([]) == 0           # Auto-sync fixes drift
    assert sync_book.main(["--check"]) == 0  # Clean now
    assert sync_book.main(["--prose-impact", "HEAD"]) == 0
    with pytest.raises(RuntimeError):
        sync_book.detect_prose_impact("nonexistent_ref_xyz", tmp_path)

    chap.write_text(chap.read_text(encoding="utf-8").replace("book-sync: add", "book-sync: missing_fn"), encoding="utf-8")
    assert sync_book.main(["--check"]) == 1


def test_check_book_detects_all_violations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify check_book catches legacy directives, unanchored links, bare lines, tildes, and open math."""
    _write_text(tmp_path / "systems" / "demo" / "sim" / "a.py", "def f() -> int:\n    return 1\n")
    chap = _write_text(
        tmp_path / "systems" / "demo" / "chapters" / "01.md",
        "<!-- expect-symbol: f -->\n"
        "<!-- book-sync: f -->\n"
        "no transclude here\n"
        "<<< @/systems/demo/sim/a.py#L1-L99\n"
        "<<< @/systems/demo/sim/missing.py#L1\n"
        "<<< @/systems/demo/sim/a.py#L1-L2\n"
        "[bad](../sim/missing.py#L1) [oob](../sim/a.py#L9) [unanchored](../sim/a.py#L1) [drift](../sim/a.py#L1 \"anchor: f\")\n"
        "Roughly ~5 ms~ strike, see line 42.\n"
        "$$\nx = 1\n",
    )
    errs, chaps, _ = check_book.validate_chapters(tmp_path)
    assert chaps == 1
    joined = "\n".join(errs)
    for expected_msg in (
        "Legacy '<!-- expect-symbol:",
        "Unused book-sync directive",
        "Out-of-bounds transclusion",
        "Transcluded file does not exist",
        "Missing '<!-- book-sync:",
        "Broken relative link target",
        "Out-of-bounds line citation",
        "Unanchored #L link",
        "Line link drift",
        "GFM strikethrough",
        "Unanchored prose line number",
        "Unclosed '$$' math block",
    ):
        assert expected_msg in joined

    monkeypatch.setattr(check_book, "ROOT_DIR", tmp_path)
    assert check_book.main() == 1

    # Now replace with clean synced chapter and verify exit 0
    chap.write_text(
        "# Clean\n\nSee [`f`](../sim/a.py#L1-L2) in [`a.py`](../sim/a.py) (`2` lines).\n\n"
        "<!-- book-sync: f -->\n"
        "<<< @/systems/demo/sim/a.py#L1-L2\n",
        encoding="utf-8",
    )
    assert check_book.main() == 0


def test_check_code_python_shell_rtl_and_ruff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify check_code flags missing docstrings, >80L funcs, unexplained pragmas, and shell/RTL defects."""
    long_body = "\n".join("    x += 1" for _ in range(82))
    bad_py = _write_text(
        tmp_path / "scripts" / "bad.py",
        "import os  # noqa: F401\n"
        "def nodoc(x: int) -> int:\n"
        f"{long_body}\n"
        "    return x\n",
    )
    exempt_py = _write_text(
        tmp_path / "scripts" / "exempt.py",
        '"""Exempt module."""\n\n'
        "# code-gate: allow-long-dispatch (test exemption)\n"
        "def ok_long() -> int:\n"
        '    """Exempted dispatcher."""\n'
        "    x = 0\n"
        f"{long_body}\n"
        "    return x\n",
    )
    bad_sh = _write_text(
        tmp_path / "scripts" / "bad.sh",
        "#!/usr/bin/env bash\n"
        "# shellcheck disable=SC2034\n"
        "helper() {\n"
        "  source .tools/env.sh\n"
        "  if [ $foo ; then echo hi\n"
        "}\n",
    )
    bad_sv = _write_text(
        tmp_path / "systems" / "demo" / "rtl" / "bad.sv",
        "// verilator lint_off WIDTH\nmodule m; endmodule\n",
    )
    monkeypatch.setattr(check_code, "_run_ruff", lambda _py, _root: [])

    py_errs = "\n".join(check_code.check_python_file(bad_py, tmp_path))
    assert "Missing module docstring" in py_errs
    assert "Missing docstring on function 'nodoc'" in py_errs
    assert "exceeds" not in py_errs and "limit 80" in py_errs
    assert "Unexplained '# noqa'" in py_errs
    assert check_code.check_python_file(exempt_py, tmp_path) == []

    sh_errs = "\n".join(check_code.check_shell_file(bad_sh, tmp_path))
    assert "Missing 'set -euo pipefail'" in sh_errs
    assert "Missing top contract header" in sh_errs
    assert "Missing doc comment immediately above shell function 'helper'" in sh_errs
    assert "Unexplained '# shellcheck'" in sh_errs
    assert "CWD-fragile" in sh_errs
    assert "bash -n failed" in sh_errs

    sv_errs = "\n".join(check_code.check_rtl_or_c_file(bad_sv, tmp_path))
    assert "Missing top contract header" in sv_errs
    assert "Unexplained 'verilator lint_off'" in sv_errs

    monkeypatch.setattr(check_code, "ROOT_DIR", tmp_path)
    assert check_code.main([]) == 1

    # Clean workspace + blank-line comment separation + __pycache__ ignored
    shutil.rmtree(tmp_path / "systems")
    bad_py.unlink()
    bad_sh.unlink()
    _write_text(tmp_path / "scripts" / "__pycache__" / "ignored.py", "def bad(): pass\n")
    _write_text(
        tmp_path / "scripts" / "good.sh",
        "#!/usr/bin/env bash\n"
        "# Purpose: Clean helper.\n"
        "# Usage: bash good.sh\n"
        "set -euo pipefail\n"
        "# Print status banner.\n\n"
        "say_ok() {\n"
        '  echo "ok"\n'
        "}\n",
    )
    assert check_code.main([]) == 0


def test_tooling_edge_cases_and_wrappers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover SyntaxError, Ruff/Verilator wrappers, check_book fences/links, and sync_book single-line labels."""
    # 1. check_code: SyntaxError, explicit path filter, _run_ruff, and mocked Verilator lint
    syn_err = _write_text(tmp_path / "scripts" / "broken.py", "def oops(:\n")
    assert "Python syntax error" in "\n".join(check_code.check_python_file(syn_err, tmp_path))
    assert check_code.collect_target_files(tmp_path, [str(syn_err)]) == ([syn_err.resolve()], [])

    fake_proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="err", stderr="")
    with monkeypatch.context() as mp:
        mp.setattr(check_code.subprocess, "run", lambda *a, **kw: fake_proc)
        mp.setattr(
            check_code.shutil, "which", lambda name: f"/bin/{name}" if name in {"ruff", "verilator"} else None
        )
        assert "ruff check failed" in "\n".join(check_code._run_ruff([syn_err], tmp_path))
        sv = _write_text(tmp_path / "systems" / "demo" / "rtl" / "c.sv", "// Purpose: demo\nmodule c; endmodule\n")
        assert "verilator --lint-only failed" in "\n".join(check_code.check_rtl_or_c_file(sv, tmp_path))
        mp.setattr(check_code.shutil, "which", lambda name: "/bin/uv" if name == "uv" else None)
        assert "ruff check failed" in "\n".join(check_code._run_ruff([syn_err], tmp_path))

    # 2. check_book: fences, inline backticks, #frag/https links, transclusion drift & bad link anchor
    _write_text(tmp_path / "systems" / "demo" / "sim" / "a.py", "CONST = 1\ndef f() -> int:\n    return 1\n")
    chap = _write_text(
        tmp_path / "systems" / "demo" / "chapters" / "01.md",
        "# T\n\n"
        "```python\n<<< @/systems/demo/sim/a.py#L1\n```\n"
        "`[f](a.py#L1)` [ext](https://x.test) [sec](#top) [frag](../sim/a.py#hdr) [`a + b`](../sim/a.py#L1)\n"
        "[miss](../sim/a.py#L1 \"anchor: nope\")\n"
        "<!-- book-sync: f -->\n<<< @/systems/demo/sim/a.py#L1\n"
        "<!-- book-sync: missing_sym -->\n<<< @/systems/demo/sim/a.py#L1\n",
    )
    errs, _, _ = check_book.validate_chapters(tmp_path)
    joined = "\n".join(errs)
    assert "Transclusion drift for 'f'" in joined
    assert "Symbol 'missing_sym' not found" in joined
    assert "Symbol 'nope' not found" in joined

    # 3. sync_book: single-line label rewrite + clean prose-impact CLI path
    chap.write_text(
        '## Sec\n\nSee [line 99](../sim/a.py#L99 "anchor: CONST") and [`a + b`](../sim/a.py#L1) [#sec](#sec).\n\n'
        "<!-- book-sync: missing_sym -->\n<<< @/systems/demo/sim/a.py#L1\n",
        encoding="utf-8",
    )
    assert "[line 1](../sim/a.py#L1" in sync_book.sync_chapter_text(chap, tmp_path)[0]
    _make_git_book_repo(tmp_path / "repo2")
    monkeypatch.setattr(sync_book, "ROOT_DIR", tmp_path / "repo2")
    assert sync_book.main(["--prose-impact", "HEAD"]) == 0
    _write_text(tmp_path / "repo2" / "systems" / "demo" / "sim" / "alu.py", "MASK = 1\n")
    c2 = tmp_path / "repo2" / "systems" / "demo" / "chapters" / "01_alu.md"
    c2.write_text(c2.read_text(encoding="utf-8").replace("book-sync: add", "book-sync: nope"), encoding="utf-8")
    assert sync_book.detect_prose_impact("HEAD", tmp_path / "repo2") == []


def test_hardened_sync_and_anchor_edge_cases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover binary links, path escapes, 4-tick fences, shell/SV comments, EOF macros, and bad git refs."""
    # code_anchors: unclosed brace, ${#var}, SV comments around begin/end, and EOF backslash macro
    unclosed_c = _write_text(tmp_path / "unclosed.c", "int f(void) {\n  return 1;\n")
    with pytest.raises(code_anchors.AnchorError):
        code_anchors.extract_symbols(unclosed_c)
    sh_len = _write_text(tmp_path / "len.sh", "fn() {\n  echo ${#HOME}\n}\n")
    assert code_anchors.resolve_anchor(sh_len, "fn") == (1, 3)
    sv_cmt = _write_text(
        tmp_path / "sv_cmt.sv",
        "module m;\n  always_comb begin : blk\n    // end fake\n    /* begin fake */\n  end\nendmodule\n",
    )
    assert code_anchors.resolve_anchor(sv_cmt, "blk") == (2, 5)
    eof_macro = _write_text(tmp_path / "eof.h", "#define M(x) \\")
    assert code_anchors.resolve_anchor(eof_macro, "M") == (1, 1)

    # sync_book: binary relative links, path traversal, 4-backtick fences, missing transclusions, CLI bad ref
    (tmp_path / "systems" / "demo" / "sim").mkdir(parents=True, exist_ok=True)
    (tmp_path / "systems" / "demo" / "sim" / "blob.bin").write_bytes(b"\x80\xff\x00\xfe")
    _write_text(tmp_path / "systems" / "demo" / "sim" / "alu.py", "def f() -> int:\n    return 1\n")
    _write_text(tmp_path.parent / "outside.py", "X = 1\n")
    chap = _write_text(
        tmp_path / "systems" / "demo" / "chapters" / "01.md",
        "# H\n\n"
        "[bin](../sim/blob.bin) [esc](../../../../outside.py#L1) "
        "`\\`[f](../sim/alu.py#L1)` ``[f](../sim/alu.py#L1)``\n"
        "````md\n```python\n<<< @/systems/demo/sim/alu.py#L1\n```\nnot_closing ``` still_in_fence\n````\n"
        "<!-- book-sync: f -->\n<<< @/systems/demo/sim/missing.py#L1\n"
        "<!-- book-sync: f -->\n<<< @/../../outside.py#L1\n",
    )
    synced, errs = sync_book.sync_chapter_text(chap, tmp_path)
    joined = "\n".join(errs)
    assert "Path escapes repository root" in joined
    assert "Transcluded file does not exist" in joined
    assert "Transclusion escapes repository root" in joined
    assert "```python\n<<< @/systems/demo/sim/alu.py#L1" in synced

    _make_git_book_repo(tmp_path / "g")
    monkeypatch.setattr(sync_book, "ROOT_DIR", tmp_path / "g")
    assert sync_book.main(["--prose-impact", "nonexistent_ref_999"]) == 1


def test_hardened_check_gates_and_linters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover unclosed fences, currency ~, missing linters, dot-sourcing, ruff: noqa, and CLI errors."""
    _write_text(tmp_path / "systems" / "demo" / "sim" / "a.py", "def f() -> int:\n    return 1\n")
    _write_text(
        tmp_path / "systems" / "demo" / "chapters" / "01.md",
        "# H\n\nCost \\$10 and ~5 ms~ (`~tilde~`). [esc](../../../../outside.py#L1)\n"
        "<<< @/../../outside.py#L1\n"
        "````md\n<!-- still open fence\n",
    )
    errs, _, _ = check_book.validate_chapters(tmp_path)
    joined = "\n".join(errs)
    assert "Unclosed fenced code block" in joined
    assert "GFM strikethrough" in joined
    assert "escapes repository root" in joined

    # check_code: missing files, unsupported extensions, missing linters, dot-sourcing, empty pragma, ruff: noqa
    paths, path_errs = check_code.collect_target_files(
        tmp_path, [str(tmp_path / "nope.py"), str(tmp_path / "systems" / "demo" / "chapters" / "01.md")]
    )
    assert paths == [] and len(path_errs) == 2

    bad_sh = _write_text(
        tmp_path / "scripts" / "dot.sh",
        "#!/usr/bin/env bash\n# Purpose: p\n# Usage: u\nset -euo pipefail\n"
        "# shellcheck disable=SC2034 #\n"
        "  . .tools/env.sh\n",
    )
    bad_py = _write_text(tmp_path / "scripts" / "rnoqa.py", '"""Doc."""\n# ruff: noqa: F401\nX = 1\n')
    assert "Unexplained '# noqa'" in "\n".join(check_code.check_python_file(bad_py, tmp_path))
    assert "CWD-fragile" in "\n".join(check_code.check_shell_file(bad_sh, tmp_path))

    sv = _write_text(tmp_path / "systems" / "demo" / "rtl" / "m.sv", "// Purpose: p\nmodule m; endmodule\n")
    with monkeypatch.context() as mp:
        mp.setattr(check_code.shutil, "which", lambda _name: None)
        assert "Missing required linter 'ruff'" in "\n".join(check_code._run_ruff([bad_py], tmp_path))
        assert "Missing required linter 'shellcheck'" in "\n".join(check_code.check_shell_file(bad_sh, tmp_path))
        assert "Missing required RTL linter 'verilator'" in "\n".join(check_code.check_rtl_or_c_file(sv, tmp_path))
