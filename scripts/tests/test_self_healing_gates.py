#!/usr/bin/env python3
"""Unit and headless-Chromium tests for Apex self-healing quality gates.

Purpose:
  Verify every new branch added across:
    - `scripts/check_book.py` (`<= 25`-line slices, fence widths, Mermaid limits, skill budgets)
    - `scripts/check_visuals.py` (overflow, SVG scale, foreignObject clip, WCAG contrast, 404s)
    - `scripts/harvest_feedback.py` (`gh api` normalization, bot filtering, CLI JSON/Markdown output)

Usage:
  PYTHONPATH=scripts uv run --with pytest --with pytest-cov --with pyyaml --with playwright pytest -v \\
    scripts/tests/test_self_healing_gates.py

Invariants:
  - Executes strictly inside `tmp_path` without mutating repository chapters or skills.
  - Every test function stays `<= 80` lines with clear architectural docstrings.
"""

from __future__ import annotations

import builtins
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_review_plan  # noqa: E402 — repo test runner imports standalone scripts without package install
import chapter_index  # noqa: E402 — repo test runner imports standalone scripts without package install
import check_book  # noqa: E402 — repo test runner imports standalone scripts without package install
import check_code  # noqa: E402 — repo test runner imports standalone scripts without package install
import check_visuals  # noqa: E402 — repo test runner imports standalone scripts without package install
import code_anchors  # noqa: E402 — repo test runner imports standalone scripts without package install
import harvest_feedback  # noqa: E402 — repo test runner imports standalone scripts without package install

_REAL_IMPORT = builtins.__import__


def _write(path: Path, text: str) -> Path:
    """Create parent dirs, write UTF-8 `text`, and return `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _fake_import_no_playwright(name: str, *args: Any, **kwargs: Any) -> Any:
    """Simulate a Python environment lacking the `playwright` package."""
    if name.startswith("playwright"):
        raise ImportError("no playwright")
    return _REAL_IMPORT(name, *args, **kwargs)


class _FakeGhRunner:
    """Callable `subprocess.run` stub serving canned `gh` CLI JSON payloads."""

    def __init__(self, responses: dict[str, str]) -> None:
        """Store canned endpoint suffix -> stdout JSON payload mapping."""
        self.responses = responses

    def __call__(self, cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        """Return synthetic `gh repo view` or `gh api` CompletedProcess response."""
        if "repo" in cmd and "view" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "Ethanex8/apex\n", "")
        ep = cmd[-1]
        for key, payload in self.responses.items():
            if ep.endswith(key):
                return subprocess.CompletedProcess(cmd, 0, payload, "")
        return subprocess.CompletedProcess(cmd, 1, "", "API 404")


def test_check_book_slices_fences_and_mermaid_gates(tmp_path: Path) -> None:
    """Verify check_book enforces excerpt caps, fence column widths, Mermaid guards, and exemptions."""
    src_lines = "\n".join(f"    x += {i}" for i in range(28))
    wide_comment = "# " + "w" * 102
    _write(
        tmp_path / "systems" / "demo" / "sim" / "big.py",
        f"def big() -> int:\n    {wide_comment}\n    x = 0\n{src_lines}\n    return x\n",
    )
    wide_ascii = "A" * 85
    wide_code = "x = " + "1" * 102

    bad_chap = _write(
        tmp_path / "systems" / "demo" / "chapters" / "01.md",
        "# Ch1\n\n"
        "<!-- book-gate: allow-wide-fence (   ) -->\n"
        "<!-- book-gate: allow-wide-mermaid (unused) -->\n"
        "Unrelated paragraph\n"
        "<!-- book-sync: big -->\n"
        "<<< @/systems/demo/sim/big.py#L1-L32\n\n"
        f"```text\n{wide_ascii}\n```\n\n"
        f"```python\n{wide_code}\n```\n\n"
        "```mermaid\n---\ntitle: Wide\n---\n%% comment\nflowchart LR\n  A-->B-->C-->D-->E\n```\n\n"
        "```mermaid\n%% seq comment\nsequenceDiagram\n  A->>B: Save x; y\n```\n\n"
        "<!-- book-sync: unused_before_sync -->\n"
        "<!-- book-sync: unused_before_fence -->\n"
        "```text\nok\n```\n"
        "<!-- book-sync: unused_eof -->\n",
    )
    errs, _, _ = check_book.validate_chapters(tmp_path)
    joined = "\n".join(errs)
    for needle in (
        "Empty reason inside book-gate directive",
        "Unused book-gate directive 'allow-wide-mermaid'",
        "spans 32 lines (limit 25)",
        "Transcluded line big.py:2 is 108 chars (limit 100)",
        "Raw ASCII/text diagram fence ('text') banned",
        "Fenced line is 85 chars (limit 80 for 'text')",
        "Fenced line is 106 chars (limit 100 for 'python')",
        "Wide horizontal Mermaid diagram (4 edges)",
        "Semicolon ';' inside Mermaid sequenceDiagram",
        "Unused book-sync directive 'unused_before_sync'",
        "Unused book-sync directive 'unused_before_fence'",
        "Unused book-sync directive 'unused_eof'",
    ):
        assert needle in joined

    # Now apply valid exemptions, sequenceDiagram HTML entities & comments, and confirm zero errors
    bad_chap.write_text(
        "# Ch1\n\n"
        "<!-- book-gate: allow-long-slice (full dispatcher contrast) -->\n"
        "<!-- book-gate: allow-wide-fence (verbatim wide comment fixture) -->\n"
        "<!-- book-sync: big -->\n"
        "<<< @/systems/demo/sim/big.py#L1-L32\n\n"
        "<!-- book-gate: allow-ascii-fence (verbatim hardware bus printout) -->\n"
        f"<!-- book-gate: allow-wide-fence (exact hardware bus table) -->\n```text\n{wide_ascii}\n```\n\n"
        "<!-- book-gate: allow-wide-mermaid (4-node comparison layout) -->\n"
        "```mermaid\nflowchart LR\n  A-->B-->C-->D-->E\n```\n\n"
        "```mermaid\nsequenceDiagram\n  %% A->>B: ignored; semicolon\n  A->>B: A &lt; B ok\n```\n",
        encoding="utf-8",
    )
    errs2, _, _ = check_book.validate_chapters(tmp_path)
    assert errs2 == []


def test_check_book_pedagogy_gates_and_widget_shorthand(tmp_path: Path) -> None:
    """Verify check_book rejects abrupt heading openings, crutches, and cryptic bit-slice shorthand."""
    _write(tmp_path / "systems" / "demo" / "sim" / "a.py", "X = 1\n")
    _write(
        tmp_path / "systems" / "demo" / "chapters" / "01.md",
        "# Ch1\n\n"
        "## Jump Fence\n"
        "```python\nx = 1\n```\n\n"
        "## Jump Widget\n"
        "<DemoWidget />\n\n"
        "## Jump Transclude\n"
        "<!-- book-sync: X -->\n"
        "<<< @/systems/demo/sim/a.py#L1\n\n"
        "## Jump List\n"
        "- item\n\n"
        "## Jump Imperative\n"
        "Trace the four signals below.\n\n"
        "## Calm Heading\n"
        "Here we explain why constants split across bitfields.\n"
        "Wait: why does the decoder shift imm[12|10:5]?\n"
        "```python\n# bits [30..25|10..5]\n```\n\n"
        "## Graded Engineering Exercises\n"
        "### Problem 1: Warmup\n"
        "- Step 1.\n\n"
        "#### Exercise 2.1: Quick Substitution\n"
        "- Step 1.\n",
    )
    _write(
        tmp_path / "book" / ".vitepress" / "theme" / "components" / "bad.vue",
        "<template><span>imm[12|10:5]</span></template>\n",
    )
    chap_errs = "\n".join(check_book.validate_chapters(tmp_path).errors)
    for expected in (
        "Chapter jumps straight from H1 into 'Jump Fence' without introductory prose",
        "jumps straight into a code/diagram block",
        "jumps straight into a Vue widget",
        "jumps straight into a code transclusion",
        "jumps straight into a list/table/equation",
        "opens abruptly with 'Trace...'",
        "Conversational crutch 'Wait: why'",
        "Cryptic bit-slice shorthand 'imm[12|10:5]'",
        "Cryptic bit-slice shorthand '[30..25|10..5]'",
        "Problem/exercise closing heading 'Graded Engineering Exercises' should simply be 'Problems'",
    ):
        assert expected in chap_errs
    assert "Problem 1" not in chap_errs
    assert "Exercise 2.1" not in chap_errs
    widget_errs = "\n".join(check_book.validate_widgets(tmp_path))
    assert "Cryptic bit-slice shorthand 'imm[12|10:5]'" in widget_errs


def test_check_book_editorial_typography_and_line_break_gates(tmp_path: Path) -> None:
    """Verify H1/H2 conciseness, banner bans, code-only backticks, term adjacency, bold caps, and 1-sentence lines."""
    chap = _write(
        tmp_path / "systems" / "demo" / "chapters" / "01.md",
        "# Chapter 1: Instruction Set Architecture & Fixed-Width Binary Arithmetic\n\n"
        "> **Part I: Custom Silicon · Reading Time**: 35 minutes\n\n"
        "Primary Modules and Interactive Figures live below.\n\n"
        "<!-- book-gate: allow-multi-sentence-line (unused before heading) -->\n"
        "## 1. Why Software First: The Golden Model & `ISA` (RV32I) For Real Chips Today\n\n"
        "Hardware uses `HDL` in `SystemVerilog` with `32`-bit words, `50 MHz` clocks, `4,096` slots, and `32` wires.\n"
        "Math in code like `Z_{2^N}` fails while f-strings like `f\"x_{i}\"` stay allowed.\n"
        "Selectors—the circuit equivalent of `a ? b : c` (**multiplexers**)—route signals.\n"
        "Every wire updates **simultaneously on every tick of a fast clock**.\n"
        "First sentence ends here. Second sentence shares the same line!  \n"
        "$$\n"
        "<!-- book-gate: allow-multi-sentence-line (unused in math) -->\n"
        "x = 1\n"
        "$$\n",
    )
    errs = "\n".join(check_book.validate_chapters(tmp_path).errors)
    for expected in (
        "Chapter H1 title 'Instruction Set Architecture & Fixed-Width Binary Arithmetic' must be concise",
        "Front-matter blockquote banner before first '##'",
        "Front-matter metadata/TOC/figure inventory",
        "Unused book-gate directive 'allow-multi-sentence-line'",
        "contains ':'",
        "uses '&'",
        "contains parenthetical clutter",
        "wraps words in backticks",
        "exceeds 8 words",
        "Non-code acronym or proper noun '`HDL`'",
        "Prose number/measurement '`32`-bit'",
        "Prose number/measurement '`50 MHz`'",
        "Comma-formatted prose number '4,096'",
        "Prose number/measurement '`32` wires'",
        "Raw LaTeX subscript/superscript inside backticks '`Z_{2^N}`'",
        "Detached term definition",
        "Overlong bold phrase '**simultaneously on every tick of a fast clock**'",
        "Multiple sentences on one Markdown line",
        "Trailing two-space hard '<br>' break",
    ):
        assert expected in errs
    assert "f\"x_{i}\"" not in errs

    chap.write_text(
        "# Chapter 1: Instruction Set Architecture\n\n"
        "Every processor begins with an instruction contract.\n\n"
        "## 1. Why Chip Design Starts in Software\n\n"
        "Hardware selector switches (**multiplexers**) choose one input wire, e.g. `x0`.\n"
        "- **Hardware Cost**: Every 32-bit adder runs in parallel.\n"
        "| Col | Val |\n"
        "| --- | --- |\n"
        "| **Very Long Bold Cell Inside Table Row Is Allowed** | ok |\n"
        "<!-- book-gate: allow-multi-sentence-line (quoted dual-sentence motto) -->\n"
        "First sentence. Second sentence with explicit exemption.\n",
        encoding="utf-8",
    )
    assert check_book.validate_chapters(tmp_path).errors == []


def test_check_book_coordinate_prose_wall_and_table_exemption(tmp_path: Path) -> None:
    """Verify check_book rejects coordinate-recitation prose walls while allowing tables and gated prose."""
    chap = _write(
        tmp_path / "systems" / "demo" / "chapters" / "01.md",
        "# Instruction Encoding\n\n"
        "Every 32-bit instruction places fields at fixed bit positions.\n\n"
        "## Bitfield Layouts\n\n"
        "We group immediate wires cleanly across instruction types.\n"
        "Specifically, B-type puts Bit 12 at Bit 31, Bits 10..5 in Bits 30..25, Bits 4..1 in Bits 11..8, and Bit 11 at Bit 7.\n",
    )
    errs = "\n".join(check_book.validate_chapters(tmp_path).errors)
    assert "Coordinate-recitation prose wall" in errs

    chap.write_text(
        "# Instruction Encoding\n\n"
        "Every 32-bit instruction places fields at fixed bit positions.\n\n"
        "## Bitfield Layouts\n\n"
        "We group immediate wires cleanly across instruction types.\n"
        "| Format | Constant Bit Mapping |\n"
        "| --- | --- |\n"
        "| B-type | Bit 12 at Bit 31, Bits 10..5 in Bits 30..25, Bits 4..1 in Bits 11..8, Bit 11 at Bit 7 |\n"
        "<!-- book-gate: allow-enumerative-prose (explicit prose walk-through fixture) -->\n"
        "Explicitly, Bit 12 at Bit 31, Bits 10..5 in Bits 30..25, Bits 4..1 in Bits 11..8, and Bit 11 at Bit 7.\n",
        encoding="utf-8",
    )
    assert check_book.validate_chapters(tmp_path).errors == []


def test_check_book_per_question_exercise_reveals(tmp_path: Path) -> None:
    """Verify check_book rejects monolithic bottom solution dumps and requires per-question/subpart reveals."""
    chap = _write(
        tmp_path / "systems" / "demo" / "chapters" / "01.md",
        "# Modular Arithmetic\n\nEvery register wraps cleanly.\n\n"
        "## 1. Core Rings\n\nRings wrap around a fixed modulus.\n\n"
        "#### Exercise 1.1: Monolithic Dump\n\n"
        "Practice ring wrapping.\n\n"
        "1. First prompt.\n"
        "2. Second prompt.\n"
        "   - **(a)** Sub-part one.\n"
        "   - **(b)** Sub-part two.\n\n"
        "<details><summary>Solution</summary>\n\n1. One.\n2. Two.\n\n</details>\n\n"
        "---\n\n"
        "## 2. Next Section\n\nNext prose line.\n",
    )
    errs = "\n".join(check_book.validate_chapters(tmp_path).errors)
    assert "Exercise 'Exercise 1.1: Monolithic Dump' has 3 question/sub-part(s) but only 1 '<details>' reveal(s)" in errs

    chap.write_text(
        "# Modular Arithmetic\n\nEvery register wraps cleanly.\n\n"
        "## 1. Core Rings\n\nRings wrap around a fixed modulus.\n\n"
        "#### Exercise 1.1: Inline Reveals\n\n"
        "Practice ring wrapping.\n\n"
        "1. First prompt.\n"
        "   <details><summary>Solution</summary>One.</details>\n"
        "2. Second prompt.\n"
        "   - **(a)** Sub-part one.\n"
        "     <details><summary>Solution</summary>Two A.</details>\n"
        "   - **(b)** Sub-part two.\n"
        "     <details><summary>Solution</summary>Two B.</details>\n",
        encoding="utf-8",
    )
    assert check_book.validate_chapters(tmp_path).errors == []



def test_check_code_tuple_import_and_assert_gates(tmp_path: Path) -> None:
    """Verify check_code flags >2-item tuple returns, local imports, and compound pytest asserts."""
    bad_mod = _write(
        tmp_path / "scripts" / "readability_bad.py",
        '"""Bad readability demo."""\n\n'
        "def bad_ret() -> tuple[int, int, bool]:\n"
        '    """Return opaque 3-tuple."""\n'
        "    import json\n"
        "    return 1, len(json.dumps({})), True\n\n"
        "# code-gate: allow-tuple-return (explicit test exemption)\n"
        "def ok_ret() -> tuple[int, int, int]:\n"
        '    """Exempted 3-tuple."""\n'
        "    # code-gate: allow-local-import (optional runtime dep)\n"
        "    import math\n"
        "    return 1, 2, int(math.pi)\n",
    )
    bad_test = _write(
        tmp_path / "scripts" / "test_readability_bad.py",
        '"""Bad test assert demo."""\n\n'
        "def test_demo() -> None:\n"
        '    """Check compound vs exempt asserts."""\n'
        "    a, b = 1, 2\n"
        "    assert a == 1 and b == 2\n"
        "    # code-gate: allow-compound-assert (explicit test exemption)\n"
        "    assert a < b and b > 0\n",
    )
    mod_errs = "\n".join(check_code.check_python_file(bad_mod, tmp_path))
    assert "returns a 3-item positional tuple" in mod_errs
    assert "Local import inside function" in mod_errs
    assert "ok_ret" not in mod_errs

    test_errs = check_code.check_python_file(bad_test, tmp_path)
    assert len(test_errs) == 1
    assert "Compound 'assert ... and ...'" in test_errs[0]


def test_check_book_skill_budgets_and_calibration_logs(tmp_path: Path) -> None:
    """Verify validate_skills enforces docs/calibration/ relocation, zero skill leaks, and GEMINI bullets."""
    (tmp_path / ".agents" / "skills" / "empty-skill").mkdir(parents=True)
    _write(tmp_path / ".agents" / "skills" / "bad-fm" / "SKILL.md", "# No frontmatter\n")
    _write(tmp_path / ".agents" / "skills" / "missing-fields" / "SKILL.md", "---\ntitle: x\n---\nbody\n")
    long_skill = "---\nname: apex-couch-mentor\ndescription: demo\n---\n" + "\n".join(
        f"- rule {i}" for i in range(122)
    )
    _write(tmp_path / ".agents" / "skills" / "apex-couch-mentor" / "SKILL.md", long_skill)
    _write(
        tmp_path / ".agents" / "skills" / "apex-couch-mentor" / "references" / "calibration_log.md",
        "# Leaked log\n",
    )

    errs, count = check_book.validate_skills(tmp_path)
    joined = "\n".join(errs)
    assert count == 4
    assert "Missing SKILL.md" in joined
    assert "Missing valid YAML frontmatter" in joined
    assert "requires non-empty 'name' and 'description'" in joined
    assert "Exceeds 120-line prompt budget" in joined
    assert "Calibration logs must live in docs/calibration/" in joined
    assert "Missing non-empty docs/calibration/apex-couch-mentor.md" in joined

    # Clean skill passes validation and GEMINI bullet check enforces 50-word cap
    clean_root = tmp_path / "clean"
    _write(
        clean_root / ".agents" / "skills" / "apex-couch-mentor" / "SKILL.md",
        "---\nname: apex-couch-mentor\ndescription: clean demo\n---\n# Clean\n",
    )
    _write(clean_root / "docs" / "calibration" / "apex-couch-mentor.md", "# Log\n\nEntry 1.\n")
    errs_ok, count_ok = check_book.validate_skills(clean_root)
    assert count_ok == 1
    assert errs_ok == []

    _write(clean_root / "GEMINI.md", "- " + " ".join(f"w{i}" for i in range(55)) + "\n")
    assert "split monolithic rules into atomic bullets" in "\n".join(check_book.validate_gemini_rules(clean_root))
    _write(clean_root / "GEMINI.md", "- Short clean invariant.\n")
    assert check_book.validate_gemini_rules(clean_root) == []


def test_check_visuals_routes_server_and_error_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify route discovery, static serving/base checks, Chromium lookup, and missing deps."""
    _write(tmp_path / "systems" / "brain" / "README.md", "# Brain\n")
    _write(tmp_path / "systems" / "brain" / "chapters" / "01_isa.md", "# Ch1\n")
    assert check_visuals.discover_routes(tmp_path) == ["/", "/vision", "/brain/", "/brain/01_isa"]
    assert check_visuals.discover_routes(tmp_path / "no_systems") == ["/", "/vision"]
    assert check_visuals.normalize_base("/apex/") == "/apex"
    assert check_visuals.normalize_base("/") == ""

    fake_bin = _write(tmp_path / "fake_chrome", "")
    pw_bin = _write(tmp_path / "pw_chrome", "")
    monkeypatch.setenv("CHROMIUM_PATH", str(fake_bin))
    assert check_visuals.resolve_chromium_executable(str(pw_bin)) == str(fake_bin)
    monkeypatch.delenv("CHROMIUM_PATH", raising=False)
    assert check_visuals.resolve_chromium_executable(str(pw_bin)) is None
    monkeypatch.setattr(check_visuals.shutil, "which", lambda name: "/usr/bin/chrome" if name == "chromium" else None)
    assert check_visuals.resolve_chromium_executable(None) == "/usr/bin/chrome"

    # Missing dist dir and missing playwright diagnostic branches
    assert "Built dist directory missing" in check_visuals.audit_pages(tmp_path / "nodist", "/apex/", ["/"])[0]
    dist = tmp_path / "dist"
    _write(dist / "index.html", "<!doctype html><html><body>ok</body></html>")
    _write(dist / "vision.html", "<!doctype html><html><body>vision</body></html>")
    _write(dist / "dir%20with%20space" / "index.html", "<!doctype html><html><body>dir</body></html>")
    _write(dist / "my dir" / "index.html", "<!doctype html><html><body>unquoted</body></html>")

    httpd, port = check_visuals.start_dist_server(dist, "/apex/")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/favicon.ico") as resp:
            assert resp.status == 204
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/apex/vision") as resp:
            assert b"vision" in resp.read()
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/apex/my%20dir/") as resp:
            assert b"unquoted" in resp.read()
        handler = check_visuals._make_handler(dist, "/apex")
        probe = object.__new__(handler)
        assert "__invalid_escape__" in probe.translate_path("/apex/../../etc/passwd")
        assert "__invalid_base__" in probe.translate_path("/assets/app.js")
    finally:
        httpd.shutdown()
        httpd.server_close()

    monkeypatch.setattr(builtins, "__import__", _fake_import_no_playwright)
    errs = check_visuals.audit_pages(dist, "/apex/", ["/"])
    assert errs
    assert "Missing required dependency 'playwright'" in errs[0]


def test_check_visuals_chromium_clean_and_defect_detection(tmp_path: Path) -> None:
    """Run headless Chromium against synthetic HTML fixtures proving clean pass and all visual failures."""
    dist = tmp_path / "dist"
    shots = tmp_path / "shots"
    _write(
        dist / "clean.html",
        "<!doctype html><html><body style='margin:0;background:#fff;'>"
        "<div class='mermaid-book-figure' style='width:320px;'>"
        "  <div class='mermaid-svg-wrap'>"
        "    <svg viewBox='0 0 300 100' width='300' height='100'>"
        "      <foreignObject x='10' y='10' width='120' height='40'>"
        "        <div xmlns='http://www.w3.org/1999/xhtml' style='font-size:13px;'>OK Node</div>"
        "      </foreignObject>"
        "    </svg>"
        "  </div>"
        "</div>"
        "<details><summary>Hidden</summary>"
        "  <div class='mermaid-book-figure'><svg viewBox='0 0 500 100'><foreignObject width='10' height='10'>"
        "    <div>Hidden Box</div></foreignObject></svg></div>"
        "</details>"
        "<div class='hw-widget' style='width:320px;'>"
        "  <button class='hw-btn' style='display:none;'>HiddenBtn</button>"
        "  <button class='hw-btn' style='color:#fff;background:rgb(37 99 235 / 1);' "
        "    onclick=\"this.classList.add('active');\">Preset</button>"
        "</div></body></html>",
    )
    assert check_visuals.main(["--dist", str(dist), "--base", "/apex/", "--screenshot-dir", str(shots), "clean"]) == 0
    assert (shots / "clean" / "mermaid_0.png").is_file()
    assert (shots / "clean" / "mermaid_0_dark.png").is_file()
    assert (shots / "clean" / "mermaid_0_mobile.png").is_file()
    assert (shots / "clean" / "widget_0.png").is_file()
    assert (shots / "clean" / "widget_0_dark.png").is_file()
    assert (shots / "clean" / "widget_0_mobile.png").is_file()

    # Broken HTML hitting overflow, shrunken SVG, clipped foreignObject, dark contrast, and post-click error
    _write(
        dist / "broken.html",
        "<!doctype html><html><style>"
        ".bad{color:#2563eb;background:#2563eb;} html.dark .bad-dark{color:#1b1b1f;background:#1b1b1f;}"
        "</style><body style='margin:0;background:#fff;'>"
        "<div style='width:900px;height:10px;'>wide</div>"
        "<div class='mermaid-book-figure'><div class='mermaid-error'>Syntax err</div></div>"
        "<div class='mermaid-book-figure' style='width:300px;'>"
        "  <div class='mermaid-svg-wrap'>"
        "    <svg viewBox='0 0 1200 100' style='width:300px;height:25px;'>"
        "      <foreignObject x='0' y='0' width='20' height='12'>"
        "        <div xmlns='http://www.w3.org/1999/xhtml' style='white-space:nowrap;'>Very Long Clipped Label</div>"
        "      </foreignObject>"
        "    </svg>"
        "  </div>"
        "</div>"
        "<div class='hw-widget' style='width:300px;'>"
        "  <div style='width:500px;height:5px;'>widget wide</div>"
        "  <button class='hw-btn bad bad-dark' onclick=\"throw new Error('clickboom');\">BlueOnBlue</button>"
        "</div>"
        "<a href='#missing-part-slug'>BadHash</a>"
        "<img src='/apex/missing_asset.png'/>"
        "<script>console.error('boom');</script>"
        "</body></html>",
    )
    errs = "\n".join(check_visuals.audit_pages(dist, "/apex/", ["/broken"]))
    for expected in (
        "Document horizontal overflow",
        "overflows by",
        "Mermaid render error",
        "[/broken:desktop] Mermaid[0] scaled down to 25% (< 48%)",
        "[/broken:mobile] Mermaid[0] scaled down to 25% (< 52%)",
        "clips foreignObject box",
        "Broken hash anchor '#missing-part-slug'",
        "Low idle contrast",
        "Low active/hover contrast",
        "Low dark-idle contrast",
        "Low dark-active/hover contrast",
        "clickboom",
        "console.error: boom",
        "HTTP 404:",
    ):
        assert expected in errs
    assert check_visuals.main(["--dist", str(dist), "--base", "/apex/", "/broken"]) == 1


def test_check_visuals_math_layout_detection(tmp_path: Path) -> None:
    """Verify MATH_AUDIT_JS, prose_math_desktop.png, and display_math_desktop.png catch math issues."""
    dist = tmp_path / "dist"
    shots = tmp_path / "shots"
    _write(
        dist / "clean-math.html",
        "<!doctype html><html><body style='margin:0;background:#fff;'>"
        "<div class='vp-doc' style='max-width:600px;width:100%;'><h3>Clean Math</h3>"
        "<p>Value <mjx-container style='display:inline;overflow:visible;'>x</mjx-container></p>"
        "<mjx-container display='true' style='display:block;overflow-x:auto;overflow-y:visible;'>"
        "<span style='display:inline-block;width:200px;height:20px;'>eq</span></mjx-container>"
        "</div></body></html>",
    )
    assert check_visuals.main(["--dist", str(dist), "--base", "/apex/", "--screenshot-dir", str(shots), "clean-math"]) == 0
    assert (shots / "clean-math" / "prose_math_desktop.png").is_file()
    assert (shots / "clean-math" / "display_math_desktop.png").is_file()

    _write(
        dist / "bad-math.html",
        "<!doctype html><html><body style='margin:0;background:#fff;'><div class='vp-doc' style='max-width:400px;width:100%;'>"
        "<mjx-container style='display:inline-block;overflow-x:auto;overflow-y:hidden;vertical-align:middle;'>bad</mjx-container>"
        "<mjx-container display='true' style='display:block;width:300px;height:16px;overflow-x:auto;overflow-y:hidden;'>"
        "<div style='width:500px;height:40px;'>wide_eq</div></mjx-container>"
        "</div></body></html>",
    )
    errs = "\n".join(check_visuals.audit_pages(dist, "/apex/", ["/bad-math"]))
    for expected in (
        "Inline math breaks baseline/overflow",
        "Display math clips vertically",
        "Display math overflows desktop column",
    ):
        assert expected in errs


def test_harvest_feedback_pr_normalization_and_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify GitHub PR comment harvesting, pagination, bot filtering, markdown rendering, and CLI errors."""
    for bad_slug in ("invalid_repo_no_slash", "a/", "/b", "a/b/c"):
        with pytest.raises(ValueError):
            harvest_feedback.resolve_repo_slug(bad_slug)
    assert harvest_feedback.resolve_repo_slug("Ethanex8/apex") == "Ethanex8/apex"

    monkeypatch.setattr(harvest_feedback.shutil, "which", lambda _n: None)
    with pytest.raises(RuntimeError):
        harvest_feedback.resolve_repo_slug()
    with pytest.raises(RuntimeError):
        harvest_feedback.fetch_gh_json("repos/a/b/issues/1/comments")
    with pytest.raises(RuntimeError):
        harvest_feedback.fetch_review_thread_states("Ethanex8/apex", 3)

    monkeypatch.setattr(harvest_feedback.shutil, "which", lambda _n: "/bin/gh")
    page1 = json.dumps([
        {"id": 1, "path": "ch1.md", "line": 19, "body": "Cut off text", "user": {"login": "Ethanex8", "type": "User"}},
    ])
    page2 = json.dumps([
        {"id": 2, "path": "ch1.md", "line": 20, "body": "   ", "user": {"login": "Ethanex8", "type": "User"}},
    ])
    graphql_payload = json.dumps({
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {"id": "PRRT_1", "isResolved": False, "isOutdated": False, "comments": {"nodes": [{"databaseId": 1}]}},
                        ],
                    }
                }
            }
        }
    })
    responses = {
        "graphql": graphql_payload,
        "pulls/3/comments": f"{page1}\n{page2}",
        "pulls/3/reviews": json.dumps([
            {"id": 3, "body": "Overall nice", "user": {"login": "Ethanex8", "type": "User"}},
        ]),
        "issues/3/comments": json.dumps([
            {"id": 4, "body": "bot noise", "user": {"login": "vercel[bot]", "type": "Bot"}},
            {"id": 5, "body": f"{harvest_feedback.PREVIEW_COMMENT_MARKER}\nPreview link", "user": {"login": "Ethanex8", "type": "User"}},
        ]),
        "empty": "",
        "dictpayload": json.dumps({"message": "unexpected object"}),
    }

    def _run_gh(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        """Stub gh REST, repo view, and GraphQL queries."""
        if "graphql" in cmd:
            return subprocess.CompletedProcess(cmd, 0, responses["graphql"], "")
        return _FakeGhRunner(responses)(cmd)

    monkeypatch.setattr(harvest_feedback.subprocess, "run", _run_gh)
    out_json = tmp_path / "pr3.json"
    assert harvest_feedback.main(["--pr", "3", "--out", str(out_json)]) == 0
    saved = json.loads(out_json.read_text(encoding="utf-8"))
    assert len(saved["items"]) == 2
    assert saved["items"][0]["body"] == "Cut off text"
    assert saved["items"][0]["thread_id"] == "PRRT_1"
    assert saved["items"][0]["is_resolved"] is False
    assert harvest_feedback.main(["--pr", "3", "--include-bots"]) == 0
    assert "No human feedback" in harvest_feedback.format_feedback_markdown(9, [])
    assert harvest_feedback.fetch_gh_json("repos/Ethanex8/apex/empty") == []
    with pytest.raises(RuntimeError, match="Unexpected non-list JSON"):
        harvest_feedback.fetch_gh_json("repos/Ethanex8/apex/dictpayload")

    with pytest.raises(RuntimeError):
        harvest_feedback.fetch_gh_json("repos/Ethanex8/apex/bad/endpoint")
    monkeypatch.setattr(harvest_feedback.subprocess, "run", _FakeGhRunner({}))
    assert harvest_feedback.main(["--pr", "3"]) == 1


def test_harvest_feedback_thread_filtering_and_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify GraphQL reviewThreads pagination, resolved thread filtering, --include-resolved, and errors."""
    monkeypatch.setattr(harvest_feedback.shutil, "which", lambda _n: "/bin/gh")
    page1 = json.dumps({
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": True, "endCursor": "CUR1"},
                        "nodes": [
                            {"id": "T_OPEN", "isResolved": False, "isOutdated": False, "comments": {"nodes": [{"databaseId": 10}]}},
                        ],
                    }
                }
            }
        }
    })
    page2 = json.dumps({
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {"id": "T_DONE", "isResolved": True, "isOutdated": True, "comments": {"nodes": [{"databaseId": 20}]}},
                        ],
                    }
                }
            }
        }
    })
    rest_comments = json.dumps([
        {"id": 10, "path": "ch1.md", "line": 5, "body": "Open comment", "user": {"login": "Ethanex8", "type": "User"}},
        {"id": 20, "path": "ch1.md", "line": 9, "body": "Old resolved", "user": {"login": "Ethanex8", "type": "User"}},
    ])

    def _run_paged(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        """Stub multi-page GraphQL reviewThreads and REST PR comment endpoints."""
        if "graphql" in cmd:
            return subprocess.CompletedProcess(cmd, 0, page2 if "after=CUR1" in cmd else page1, "")
        if cmd[-1].endswith("pulls/7/comments"):
            return subprocess.CompletedProcess(cmd, 0, rest_comments, "")
        return subprocess.CompletedProcess(cmd, 0, "[]", "")

    monkeypatch.setattr(harvest_feedback.subprocess, "run", _run_paged)
    unresolved = harvest_feedback.normalize_pr_feedback("Ethanex8/apex", 7)
    assert len(unresolved) == 1
    assert unresolved[0]["thread_id"] == "T_OPEN"

    all_items = harvest_feedback.normalize_pr_feedback("Ethanex8/apex", 7, include_resolved=True)
    assert len(all_items) == 2
    assert all_items[1]["is_resolved"] is True
    assert "(resolved; outdated)" in harvest_feedback.format_feedback_markdown(7, all_items)

    monkeypatch.setattr(
        harvest_feedback.subprocess,
        "run",
        lambda cmd, **_kw: subprocess.CompletedProcess(cmd, 0, "[]", ""),
    )
    with pytest.raises(RuntimeError, match="Unexpected GraphQL payload"):
        harvest_feedback.fetch_review_thread_states("Ethanex8/apex", 7)

    monkeypatch.setattr(
        harvest_feedback.subprocess,
        "run",
        lambda cmd, **_kw: subprocess.CompletedProcess(cmd, 0, json.dumps({"errors": [{"message": "bad"}]}), ""),
    )
    with pytest.raises(RuntimeError, match="graphql returned errors"):
        harvest_feedback.fetch_review_thread_states("Ethanex8/apex", 7)


def test_harvest_feedback_thread_grouping_and_since_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify inline thread reply grouping, outdated flags, and --since / --after-review-id filtering."""
    monkeypatch.setattr(harvest_feedback.shutil, "which", lambda _n: "/bin/gh")
    gql = json.dumps({
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "id": "T_GRP",
                                "isResolved": False,
                                "isOutdated": True,
                                "comments": {"nodes": [{"databaseId": 100}, {"databaseId": 101}]},
                            }
                        ],
                    }
                }
            }
        }
    })
    inline = json.dumps([
        {
            "id": 101,
            "in_reply_to_id": 100,
            "path": "ch1.md",
            "line": 12,
            "created_at": "2026-11-24T02:00:00Z",
            "body": "Fixed in commit abc",
            "user": {"login": "Ethanex8", "type": "User"},
        },
        {
            "id": 100,
            "path": "ch1.md",
            "line": 12,
            "created_at": "2026-11-24T01:00:00Z",
            "body": "Original human critique",
            "user": {"login": "reviewer", "type": "User"},
        },
    ])
    reviews = json.dumps([
        {"id": 50, "submitted_at": "2026-11-24T00:30:00Z", "body": "Old review", "user": {"login": "reviewer", "type": "User"}},
        {"id": 55, "submitted_at": "2026-11-24T02:30:00Z", "body": "New review", "user": {"login": "reviewer", "type": "User"}},
    ])

    def _run_stub(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        """Serve GraphQL thread state, inline replies, and timestamped review summaries."""
        if "graphql" in cmd:
            return subprocess.CompletedProcess(cmd, 0, gql, "")
        if cmd[-1].endswith("pulls/9/comments"):
            return subprocess.CompletedProcess(cmd, 0, inline, "")
        if cmd[-1].endswith("pulls/9/reviews"):
            return subprocess.CompletedProcess(cmd, 0, reviews, "")
        return subprocess.CompletedProcess(cmd, 0, "[]", "")

    monkeypatch.setattr(harvest_feedback.subprocess, "run", _run_stub)
    items = harvest_feedback.normalize_pr_feedback(
        "Ethanex8/apex", 9, since="2026-11-24T01:30:00Z", after_review_id=50
    )
    assert len(items) == 2
    assert items[0]["id"] == 100
    assert items[0]["reply_count"] == 1
    assert items[0]["last_author"] == "Ethanex8"
    assert items[0]["is_outdated"] is True
    assert items[1]["id"] == 55
    md = harvest_feedback.format_feedback_markdown(9, items)
    assert "outdated; 1 reply, last: @Ethanex8" in md
    assert "[thread=T_GRP root=100]" in md
    with pytest.raises(ValueError):
        harvest_feedback.parse_iso_timestamp("   ")


def test_review_process_doc_and_repo_skills() -> None:
    """Verify docs/REVIEW_PROCESS.md Mermaid flowchart, repo SKILL.md files, and GEMINI.md pass."""
    repo_root = Path(__file__).resolve().parents[2]
    doc = repo_root / "docs" / "REVIEW_PROCESS.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "```mermaid\nflowchart TD" in text
    mermaid_block = text.split("```mermaid\n", 1)[1].split("```", 1)[0]
    assert "<br" not in mermaid_block.lower()
    for line in mermaid_block.splitlines():
        if "[" in line and "(" in line and '"' not in line:
            raise AssertionError(f"Unquoted special chars in Mermaid node: {line}")

    errs, count = check_book.validate_skills(repo_root)
    assert count == 4
    assert errs == []
    assert check_book.validate_gemini_rules(repo_root) == []


def test_build_review_plan_sharding_ledgers_and_seams(tmp_path: Path) -> None:
    """Verify overlapping section shards, Prior-Section Ledgers, widget/slice seams, and diff guardian."""
    _write(tmp_path / "book" / ".vitepress" / "theme" / "components" / "WidgetA.vue", "<template></template>\n")
    _write(tmp_path / "systems" / "demo" / "sim" / "core.py", "def add(x: int) -> int:\n    return x + 1\n")
    chap = _write(
        tmp_path / "systems" / "demo" / "chapters" / "01_intro.md",
        "# Intro Chapter\n\nOpening **Alpha Term** with `op_a` and $U_N(x) = \\lfloor x \\rfloor$.\n"
        "```markdown\n## Fake Heading Inside Fence\n<IgnoredWidget />\n```\n"
        "## 1. Base Concepts\n### First Topic\n"
        "Introduce **Beta Term** and `op_b`.\n"
        "#### Exercise 1.1: Quick Check\n1. Evaluate `op_a`.\n\n"
        "### Second Topic\n"
        "<WidgetA />\n"
        "<<< @/systems/demo/sim/core.py#L1-L2\n"
        + ("Filler line for section splitting.\n" * 12)
        + "## 2. Advanced System\n"
        "### Deep Dive\n"
        "<MissingWidget />\n"
        "<<< ../sim/core.py#L1-L2\n"
        "<<< /outside/root/external.py#L1-L3\n",
    )
    plan = build_review_plan.build_review_plan(
        chap, root_dir=tmp_path, target_lines=12, overlap_lines=4, base_ref="HEAD~1"
    )
    assert len(plan.shards) >= 3
    assert plan.shards[0].overlap_prev is None
    assert plan.shards[0].overlap_next is not None
    assert plan.shards[1].overlap_prev is not None
    assert "WidgetA.vue" in plan.shards[1].widgets[0]
    assert "systems/demo/sim/core.py#L1-L2" in plan.shards[1].transclusions[0]
    assert any("Alpha Term" in t.prompt and "`op_a`" in t.prompt for t in plan.tasks if "Shard 2" in t.role)
    assert any("U_N" in t.prompt and "\\lfloor" in t.prompt for t in plan.tasks if "Shard 2" in t.role)
    assert any("Exercise 1.1" in t.prompt for t in plan.tasks if "Shard 3" in t.role)
    assert any("<unresolved:MissingWidget.vue>" in w for w in plan.shards[-1].widgets)
    vis_task = next(t for t in plan.tasks if t.role == "Visual Pedagogy Critic")
    assert "WidgetA.vue" in vis_task.prompt
    assert "book/.vitepress/theme/components/WidgetA.vue" in vis_task.allowed_files
    diff_task = next(t for t in plan.tasks if t.role == "Diff & Flow Regression Guardian")
    assert diff_task.type_name == "research"
    assert ".cache/review-diff/01_intro.patch" in diff_task.allowed_files
    assert (tmp_path / ".cache" / "review-diff" / "01_intro.patch").is_file()


def test_build_review_plan_diff_patch_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify git-backed pre-generated unified diff patch creation, untracked files, and PNG freshness."""
    chap = _write(tmp_path / "systems" / "demo" / "chapters" / "01_git.md", "# Git\n\nBaseline prose.\n")
    untracked_vue = _write(
        tmp_path / "book" / ".vitepress" / "theme" / "components" / "NewWidget.vue",
        "<template><svg /></template>\n",
    )
    (tmp_path / ".git").mkdir()

    def _fake_git_diff(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        """Simulate git diff, untracked ls-files, and bad-ref errors."""
        if "bad-ref" in cmd:
            return subprocess.CompletedProcess(cmd, 128, "", "fatal: bad revision")
        if "ls-files" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "book/.vitepress/theme/components/NewWidget.vue\n", "")
        return subprocess.CompletedProcess(cmd, 0, "+Updated prose.\n", "")

    monkeypatch.setattr(build_review_plan.subprocess, "run", _fake_git_diff)
    plan = build_review_plan.build_review_plan(chap, root_dir=tmp_path, base_ref="HEAD~1")
    patch_txt = (tmp_path / ".cache" / "review-diff" / "01_git.patch").read_text(encoding="utf-8")
    assert "+Updated prose." in patch_txt
    assert "+++ b/book/.vitepress/theme/components/NewWidget.vue" in patch_txt
    macro_task = next(t for t in plan.tasks if t.role == "Global Macro & Dependency Critic")
    assert "opening theory" not in macro_task.prompt.lower()
    vis_task = next(t for t in plan.tasks if t.role == "Visual Pedagogy Critic")
    assert "MISSING" in vis_task.prompt
    shot_dir = _write(tmp_path / ".cache" / "visual-audit" / "demo__01_git" / "widget_0.png", "png").parent
    _write(shot_dir / "widget_0_dark.png", "png_dark")
    _write(tmp_path / "book" / ".vitepress" / "theme" / "custom.css", "body{}")
    old_t = shot_dir.joinpath("widget_0.png").stat().st_mtime - 50
    for item in (tmp_path / "book" / ".vitepress" / "theme" / "custom.css", untracked_vue, chap):
        os.utime(item, (old_t, old_t))
    fresh_plan = build_review_plan.build_review_plan(chap, root_dir=tmp_path)
    assert "FRESH (2 PNGs, 1 dark)" in next(t for t in fresh_plan.tasks if t.role == "Visual Pedagogy Critic").prompt
    os.utime(chap, (old_t + 100, old_t + 100))
    stale_plan = build_review_plan.build_review_plan(chap, root_dir=tmp_path)
    assert "STALE" in next(t for t in stale_plan.tasks if t.role == "Visual Pedagogy Critic").prompt
    assert build_review_plan.main(["--chapter", str(chap), "--base-ref", "bad-ref"]) == 1


def test_build_review_plan_code_sharding_and_freshness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify --code AST/SV/C/Vue sharding, CHAPTER_INDEX staleness guard, and ledger overflow markers."""
    _write(tmp_path / "systems" / "demo" / "README.md", "# Demo Spec\n")
    big_py = _write(
        tmp_path / "systems" / "demo" / "sim" / "engine.py",
        '"""Engine."""\nCONST = 1\n\ndef f1() -> int:\n    return 1\n\n'
        "def f2() -> int:\n    x = 1\n    y = 2\n    return x + y\n",
    )
    _write(tmp_path / "systems" / "demo" / "tb" / "test_engine.py", "def test_ok() -> None:\n    assert True\n")
    sv_file = _write(tmp_path / "systems" / "demo" / "rtl" / "alu.sv", "module a; endmodule\nmodule b; endmodule\n")
    vue_file = _write(tmp_path / "book" / "W.vue", "<script setup>\nconst x = 1\n</script>\n<template><div /></template>\n")

    code_plan = build_review_plan.build_review_plan(
        code_paths=[big_py, sv_file, vue_file], root_dir=tmp_path, target_lines=5
    )
    assert code_plan.chapter is None
    assert code_plan.slug == "code_engine"
    assert any("Architecture & Spec-Correctness Auditor" in t.role for t in code_plan.tasks)
    assert any("systems/demo/README.md" in t.allowed_files for t in code_plan.tasks)
    assert any("systems/demo/tb/test_engine.py" in t.allowed_files for t in code_plan.tasks)

    # Stale CHAPTER_INDEX.md raises unless --allow-stale-index is supplied
    chap = _write(tmp_path / "systems" / "demo" / "chapters" / "01_c.md", "# Demo\n\n" + "\n".join(f"**T{i}** `c{i}`" for i in range(12)))
    _write(tmp_path / "docs" / "CHAPTER_INDEX.md", "# Stale\n")
    with pytest.raises(RuntimeError, match="CHAPTER_INDEX.md is missing or stale"):
        build_review_plan.build_review_plan(chap, root_dir=tmp_path)

    monkeypatch.setattr(build_review_plan, "MAX_LEDGER_ITEMS", 3)
    chap.write_text(
        "# Demo\n\n## First\n" + "\n".join(f"**T{i}** `c{i}`" for i in range(6)) + "\n## Next\nBody.\n",
        encoding="utf-8",
    )
    ov_plan = build_review_plan.build_review_plan(chap, root_dir=tmp_path, target_lines=5, allow_stale_index=True)
    assert any("(+3 more)" in t.prompt for t in ov_plan.tasks if "Shard 2" in t.role)
    assert build_review_plan.main(["--code", str(big_py), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["slug"] == "code_engine"
    assert build_review_plan.main([]) == 1


def test_build_review_plan_scoped_round_r_plus_1(tmp_path: Path) -> None:
    """Verify --changed-since narrows local prose fixes while cascading structural/visual changes."""
    chap = _write(
        tmp_path / "systems" / "demo" / "chapters" / "01_scope.md",
        "# Scope\n\nIntro **RootTerm**.\n\n"
        "## 1. One\nLine A.\nLine B.\nLine C.\n\n"
        "## 2. Two\nLine D.\nLine E.\nLine F.\n\n"
        "## 3. Three\nLine G.\nLine H.\n",
    )
    py_mod = _write(tmp_path / "systems" / "demo" / "sim" / "m.py", "def a() -> int:\n    return 1\n\ndef b() -> int:\n    return 2\n")
    for cmd in (
        ["git", "init"],
        ["git", "config", "user.name", "Apex"],
        ["git", "config", "user.email", "apex@example.com"],
        ["git", "add", "."],
        ["git", "commit", "-m", "base"],
    ):
        subprocess.run(cmd, cwd=tmp_path, check=True, capture_output=True)
    base_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()

    # 1. Local prose-only edit in Section 2 selects Shard 2 + Diff Guardian (no Macro/Visual)
    chap.write_text(chap.read_text(encoding="utf-8").replace("Line E.", "Line E polished."), encoding="utf-8")
    p_local = build_review_plan.build_review_plan(
        chap, code_paths=[py_mod, py_mod], root_dir=tmp_path, target_lines=5, overlap_lines=0, base_ref=base_sha, changed_since=base_sha
    )
    assert p_local.shards[1].overlap_prev is None
    assert p_local.shards[1].overlap_next is None
    assert len(p_local.code_files) == 1
    roles_local = [t.role for t in p_local.tasks]
    assert "Cold-Reader (Shard 2/3)" in roles_local
    assert "Cold-Reader (Shard 1/3)" not in roles_local
    assert "Global Macro & Dependency Critic" not in roles_local
    assert "Diff & Flow Regression Guardian" in roles_local

    # 2. Structural bold/heading change in Section 1 cascades to Shards 1..3 + Macro Critic
    chap.write_text(chap.read_text(encoding="utf-8").replace("Line A.", "Define **NewTerm**."), encoding="utf-8")
    p_struct = build_review_plan.build_review_plan(
        chap, root_dir=tmp_path, target_lines=5, overlap_lines=0, base_ref=base_sha, changed_since=base_sha
    )
    roles_struct = [t.role for t in p_struct.tasks]
    assert "Cold-Reader (Shard 3/3)" in roles_struct
    assert "Global Macro & Dependency Critic" in roles_struct
    with pytest.raises(ValueError, match="--target-lines"):
        build_review_plan.build_review_plan(chap, root_dir=tmp_path, target_lines=0)
    with pytest.raises(ValueError, match="--overlap-lines"):
        build_review_plan.build_review_plan(chap, root_dir=tmp_path, overlap_lines=-1)


def test_build_review_plan_edge_cases_and_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify no-H2 chapters, oversized H2 without H3, JSON/Markdown CLI, and missing files."""
    chap = _write(
        tmp_path / "chap.md",
        "Intro without headings.\n"
        "## Giant Unsplit\n"
        "```python\n### ignored fence\n**Ignored** `ignored`\n```\n"
        + "\n".join(f"**Term{i}** and `tok_{i}`" for i in range(20))
        + "\n## Tail\nDone.\n",
    )
    no_h2 = _write(tmp_path / "plain.md", "Just lines.\nZero H2.\n")
    plain_plan = build_review_plan.build_review_plan(no_h2, root_dir=tmp_path)
    assert len(plain_plan.shards) == 1
    assert "Prior-Section Ledger: (none" in plain_plan.tasks[0].prompt

    giant_plan = build_review_plan.build_review_plan(chap, root_dir=tmp_path, target_lines=10)
    assert len(giant_plan.shards) == 2
    assert build_review_plan.main(["--chapter", str(chap), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["slug"] == "chap"
    assert build_review_plan.main(["--chapter", str(chap)]) == 0
    assert "## Frozen Subagent Prompts" in capsys.readouterr().out
    assert build_review_plan.main(["--chapter", str(tmp_path / "missing.md")]) == 1


def test_check_code_mypy_rtl_c_and_tautology(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify mypy runner, tautological asserts, multi-module Verilator flags, C/H/ASM gates, and multiline C anchors."""
    taut_test = _write(
        tmp_path / "scripts" / "test_taut.py",
        '"""Taut."""\n\ndef test_bad() -> None:\n    """Check."""\n    assert True\n    assert 1 == 1\n'
        "    # code-gate: allow-tautology (fixture)\n    assert True\n",
    )
    py_errs = "\n".join(check_code.check_python_file(taut_test, tmp_path))
    assert py_errs.count("Tautological constant assert") == 2

    with monkeypatch.context() as mp:
        mp.setattr(check_code.shutil, "which", lambda _n: None)
        assert "Missing required type-checker 'mypy'" in "\n".join(check_code._run_mypy([taut_test], tmp_path))
        mp.setattr(check_code.shutil, "which", lambda n: "/bin/mypy" if n == "mypy" else None)
        mp.setattr(check_code.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess([], 1, "bad type", ""))
        assert "mypy type check failed" in "\n".join(check_code._run_mypy([taut_test], tmp_path))

    # Multi-module SV + long always block + missing Ports contract + .svh skip
    long_sv = "\n".join("      q <= q + 1;" for _ in range(82))
    bad_sv = _write(
        tmp_path / "systems" / "demo" / "rtl" / "sub" / "top.sv",
        f"// Purpose: top\nmodule top(input logic clk);\n  always_ff @(posedge clk) begin\n{long_sv}\n  end\nendmodule\n",
    )
    _write(tmp_path / "systems" / "demo" / "rtl" / "defs.svh", "// Purpose: defs\n`define W 32\n")
    seen_cmds: list[list[str]] = []

    def _fake_tool_run(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        """Record invoked tool CLI arguments and succeed."""
        seen_cmds.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    with monkeypatch.context() as mp:
        mp.setattr(check_code.shutil, "which", lambda n: f"/bin/{n}" if n in {"verilator", "gcc"} else None)
        mp.setattr(check_code.subprocess, "run", _fake_tool_run)
        sv_errs = "\n".join(check_code.check_rtl_or_c_file(bad_sv, tmp_path))
        assert "missing 'Ports:' or 'Clock Domain'" in sv_errs
        assert "SystemVerilog 'always_ff' block is" in sv_errs
        assert any("-y" in c and any("rtl" in arg for arg in c) for c in seen_cmds)
        assert check_code.check_rtl_or_c_file(tmp_path / "systems" / "demo" / "rtl" / "defs.svh", tmp_path) == []

    # C header guard, multiline C anchor, >80-line C func, target-compiler exemption, and .S contract
    bad_h = _write(tmp_path / "systems" / "demo" / "fw" / "bad.h", "// Purpose: hdr\ntypedef int word_t;\n")
    assert "missing include guard" in "\n".join(check_code.check_rtl_or_c_file(bad_h, tmp_path))
    long_c = "\n".join("  x += 1;" for _ in range(82))
    c_file = _write(
        tmp_path / "systems" / "demo" / "fw" / "isr.c",
        "// Purpose: ISR\n// code-gate: allow-target-compiler (RISC-V CSR intrinsics)\n"
        f"static inline int\nhandle_irq(int a,\n           int b) {{\n  int c = '{{';\n  int x = a + b + c;\n{long_c}\n  return x;\n}}\n",
    )
    c_errs = check_code.check_rtl_or_c_file(c_file, tmp_path)
    assert len(c_errs) == 1
    assert "C function 'handle_irq' is" in c_errs[0]
    assert code_anchors.resolve_anchor(c_file, "handle_irq")[0] == 3
    bad_exempt_c = _write(
        tmp_path / "systems" / "demo" / "fw" / "bad_ex.c",
        "// Purpose: bad\n// code-gate: allow-target-compiler ()\nint ok(void) { return '{'; }\n",
    )
    with monkeypatch.context() as mp:
        mp.setattr(check_code.shutil, "which", lambda _n: None)
        assert "Missing required C compiler" in "\n".join(check_code.check_rtl_or_c_file(bad_exempt_c, tmp_path))
    asm_file = _write(tmp_path / "systems" / "demo" / "fw" / "boot.S", "reset:\n  nop\n")
    assert "Missing top contract header" in "\n".join(check_code.check_rtl_or_c_file(asm_file, tmp_path))


def test_check_book_skill_bullet_and_leak_gates(tmp_path: Path) -> None:
    """Verify check_book rejects calibration_log frontmatter exposure, >50-word bullets, and >100-line rubrics."""
    long_bullet = "- " + " ".join(f"word{i}" for i in range(70))
    _write(
        tmp_path / ".agents" / "skills" / "demo-skill" / "SKILL.md",
        "---\nname: demo-skill\ndescription: demo\nfile_names:\n  - references/calibration_log.md\n---\n"
        f"{long_bullet}\n```markdown\n{long_bullet}\n```\n",
    )
    _write(
        tmp_path / ".agents" / "skills" / "demo-skill" / "references" / "rubric_demo.md",
        "# Rubric\n" + f"{long_bullet}\n" + ("\n" * 102),
    )
    errs, count = check_book.validate_skills(tmp_path)
    joined = "\n".join(errs)
    assert count == 1
    assert "must not expose calibration_log.md" in joined
    assert "Exceeds 100-line rubric budget" in joined
    assert joined.count("split monolithic rules into atomic bullets") == 2


def test_chapter_index_generation_and_consumers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify chapter_index renders compact section budgets, novel symbols, drills, widgets, and consumers."""
    assert "No textbook chapters authored yet" in chapter_index.render_chapter_index_md(tmp_path)

    _write(
        tmp_path / "systems" / "demo" / "chapters" / "01_demo.md",
        "# Demo Systems Chapter\n\n"
        "## 1. Core Foundations\n"
        "### First Mechanics\n"
        "```python\n## fake\n```\n"
        "Introduce **First Concept** and [`helper_alpha`](../sim/mod.py#L1-L4).\n"
        "<WidgetAlpha />\n"
        "#### Exercise 1.1: Core Drill\n1. Part A.\n2. Part B.\n"
        "<details><summary>Solution</summary>\n1. Ans.\n</details>\n"
        "#### Exercise 1.2: Follow Drill\n1. Part C.\n"
        "### Second Layer\n"
        "Pure prose sentence with `val` only.\n"
        "## 2. Standalone Hardware\n"
        "Uses `helper_alpha` and **First Concept** plus `novel_beta`.\n",
    )
    rendered = chapter_index.render_chapter_index_md(tmp_path)
    assert "**Sec 1: 1. Core Foundations**" in rendered
    assert "Exercise 1.1 (2 pts), Exercise 1.2 (1 pts)" in rendered
    assert "<WidgetAlpha />" in rendered
    assert "`helper_alpha`" in rendered
    assert "`novel_beta`" in rendered
    assert "Sec 2" in rendered
    assert chapter_index._format_cell(["a|b"]) == "a\\|b"

    out_idx = tmp_path / "docs" / "CHAPTER_INDEX.md"
    monkeypatch.setattr(chapter_index, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(chapter_index, "CHAPTER_INDEX_MD_PATH", out_idx)
    assert chapter_index.main() == 0
    assert out_idx.is_file()


def test_harvest_feedback_preview_loc_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify harvest_feedback populates missing path/line from apex-preview-loc markers."""
    monkeypatch.setattr(harvest_feedback.shutil, "which", lambda _n: "/bin/gh")
    gql = json.dumps({
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "id": "T_FILE",
                                "isResolved": False,
                                "isOutdated": False,
                                "comments": {"nodes": [{"databaseId": 301}]},
                            }
                        ],
                    }
                }
            }
        }
    })
    inline = json.dumps([
        {
            "id": 301,
            "path": "systems/brain/chapters/01_isa_and_binary_arithmetic.md",
            "line": None,
            "body": "Clarify bit range.\n\n<!-- apex-preview-loc: path=systems/brain/chapters/01_isa_and_binary_arithmetic.md line=42-43 -->",
            "user": {"login": "Ethanex8", "type": "User"},
        }
    ])
    issue_comments = json.dumps([
        {
            "id": 302,
            "body": "Check figure.\n<!-- apex-preview-loc: path=VISION.md line=15 -->",
            "user": {"login": "Ethanex8", "type": "User"},
        },
        {
            "id": 303,
            "body": "Already fixed.\n<!-- apex-preview-resolved: 1 -->",
            "user": {"login": "Ethanex8", "type": "User"},
        },
    ])

    def _run_stub(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
        """Serve GraphQL thread state, file-level inline thread, and issue comment fallback."""
        if "graphql" in cmd:
            return subprocess.CompletedProcess(cmd, 0, gql, "")
        if cmd[-1].endswith("pulls/11/comments"):
            return subprocess.CompletedProcess(cmd, 0, inline, "")
        if cmd[-1].endswith("issues/11/comments"):
            return subprocess.CompletedProcess(cmd, 0, issue_comments, "")
        return subprocess.CompletedProcess(cmd, 0, "[]", "")

    monkeypatch.setattr(harvest_feedback.subprocess, "run", _run_stub)
    items = harvest_feedback.normalize_pr_feedback("Ethanex8/apex", 11)
    assert len(items) == 2
    assert items[0]["line"] == 42
    assert items[0]["body"] == "Clarify bit range."
    assert items[1]["path"] == "VISION.md"
    assert items[1]["line"] == 15
    assert items[1]["body"] == "Check figure."
    all_items = harvest_feedback.normalize_pr_feedback("Ethanex8/apex", 11, include_resolved=True)
    assert len(all_items) == 3
    assert all_items[2]["is_resolved"] is True
    assert all_items[2]["body"] == "Already fixed."
    assert harvest_feedback._extract_preview_location("plain text") == (None, None)



