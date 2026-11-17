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
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_book  # noqa: E402 — repo test runner imports standalone scripts without package install
import check_code  # noqa: E402 — repo test runner imports standalone scripts without package install
import check_visuals  # noqa: E402 — repo test runner imports standalone scripts without package install
import harvest_feedback  # noqa: E402 — repo test runner imports standalone scripts without package install

_REAL_IMPORT = builtins.__import__


def _write(path: Path, text: str) -> Path:
    """Create parent dirs, write UTF-8 `text`, and return `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _fake_import_no_playwright(name: str, *args: object, **kwargs: object) -> object:
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
        "### Exercise 1: Warmup\n"
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
    ):
        assert expected in chap_errs
    assert "Graded Engineering Exercises" not in chap_errs
    assert "Exercise 1" not in chap_errs
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
    """Verify validate_skills rejects missing SKILL.md, bad frontmatter, >120 lines, and missing logs."""
    (tmp_path / ".agents" / "skills" / "empty-skill").mkdir(parents=True)
    _write(tmp_path / ".agents" / "skills" / "bad-fm" / "SKILL.md", "# No frontmatter\n")
    _write(tmp_path / ".agents" / "skills" / "missing-fields" / "SKILL.md", "---\ntitle: x\n---\nbody\n")
    long_skill = "---\nname: apex-couch-mentor\ndescription: demo\n---\n" + "\n".join(
        f"- rule {i}" for i in range(122)
    )
    _write(tmp_path / ".agents" / "skills" / "apex-couch-mentor" / "SKILL.md", long_skill)

    errs, count = check_book.validate_skills(tmp_path)
    joined = "\n".join(errs)
    assert count == 4
    assert "Missing SKILL.md" in joined
    assert "Missing valid YAML frontmatter" in joined
    assert "requires non-empty 'name' and 'description'" in joined
    assert "Exceeds 120-line prompt budget" in joined
    assert "Missing non-empty references/calibration_log.md" in joined

    # Clean skill passes validation
    clean_root = tmp_path / "clean"
    _write(
        clean_root / ".agents" / "skills" / "apex-couch-mentor" / "SKILL.md",
        "---\nname: apex-couch-mentor\ndescription: clean demo\n---\n# Clean\n",
    )
    _write(
        clean_root / ".agents" / "skills" / "apex-couch-mentor" / "references" / "calibration_log.md",
        "# Log\n\nEntry 1.\n",
    )
    errs_ok, count_ok = check_book.validate_skills(clean_root)
    assert count_ok == 1
    assert errs_ok == []


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
    assert (shots / "clean" / "mermaid_0_mobile.png").is_file()
    assert (shots / "clean" / "widget_0.png").is_file()
    assert (shots / "clean" / "widget_0_mobile.png").is_file()

    # Broken HTML hitting overflow, shrunken SVG, clipped foreignObject, dark contrast, post-click error, and 404
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

    monkeypatch.setattr(harvest_feedback.shutil, "which", lambda _n: "/bin/gh")
    page1 = json.dumps([
        {"id": 1, "path": "ch1.md", "line": 19, "body": "Cut off text", "user": {"login": "Ethanex8", "type": "User"}},
    ])
    page2 = json.dumps([
        {"id": 2, "path": "ch1.md", "line": 20, "body": "   ", "user": {"login": "Ethanex8", "type": "User"}},
    ])
    responses = {
        "pulls/3/comments": f"{page1}\n{page2}",
        "pulls/3/reviews": json.dumps([
            {"id": 3, "body": "Overall nice", "user": {"login": "Ethanex8", "type": "User"}},
        ]),
        "issues/3/comments": json.dumps([
            {"id": 4, "body": "bot noise", "user": {"login": "vercel[bot]", "type": "Bot"}},
        ]),
        "empty": "",
        "dictpayload": json.dumps({"message": "unexpected object"}),
    }

    monkeypatch.setattr(harvest_feedback.subprocess, "run", _FakeGhRunner(responses))
    out_json = tmp_path / "pr3.json"
    assert harvest_feedback.main(["--pr", "3", "--out", str(out_json)]) == 0
    saved = json.loads(out_json.read_text(encoding="utf-8"))
    assert len(saved["items"]) == 2
    assert saved["items"][0]["body"] == "Cut off text"
    assert harvest_feedback.main(["--pr", "3", "--include-bots"]) == 0
    assert "No human feedback" in harvest_feedback.format_feedback_markdown(9, [])
    assert harvest_feedback.fetch_gh_json("repos/Ethanex8/apex/empty") == []
    with pytest.raises(RuntimeError, match="Unexpected non-list JSON"):
        harvest_feedback.fetch_gh_json("repos/Ethanex8/apex/dictpayload")

    with pytest.raises(RuntimeError):
        harvest_feedback.fetch_gh_json("repos/Ethanex8/apex/bad/endpoint")
    monkeypatch.setattr(harvest_feedback.subprocess, "run", _FakeGhRunner({}))
    assert harvest_feedback.main(["--pr", "3"]) == 1
