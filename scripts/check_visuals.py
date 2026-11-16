#!/usr/bin/env python3
"""Headless Chromium visual, layout, Mermaid SVG, and WCAG contrast gate.

Purpose:
  Serve the built VitePress site (`book/.vitepress/dist`) under its configured
  base path and verify rendered pages in headless Chromium across desktop
  (`1280x900`) and mobile (`390x844`) viewports:
    - Zero JS `pageerror`, `console.error`, HTTP `>= 400`, or `.mermaid-error`.
    - Zero card/article horizontal overflow (`scrollWidth <= clientWidth + 2`).
    - Legible Mermaid scale (`renderedWidth / viewBoxWidth >= 0.48` desktop) and
      zero clipped `<foreignObject>` SVG text labels.
    - Interactive `.hw-widget` button click/hover stability and `>= 3.5:1` WCAG
      text contrast (catching active-hover color-on-color regressions).

Usage:
  uv run --with playwright python3 scripts/check_visuals.py
  uv run --with playwright python3 scripts/check_visuals.py --screenshot-dir .cache/visual-audit /brain/01_isa_and_binary_arithmetic

Outputs:
  Writes optional PNG snapshots to `--screenshot-dir`; exits 0 on pass or 1 with
  per-route visual violation diagnostics on failure.
"""

from __future__ import annotations

import argparse
import http.server
import math
import os
import shutil
import sys
import threading
from pathlib import Path
from urllib.parse import unquote

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DIST = ROOT_DIR / "book" / ".vitepress" / "dist"
DEFAULT_BASE = "/apex/"
VIEWPORTS: tuple[tuple[str, int, int], ...] = (("desktop", 1280, 900), ("mobile", 390, 844))
MIN_MERMAID_SCALE = 0.48
MIN_BTN_CONTRAST = 3.5

# Evaluated per route+viewport to detect container overflow, tiny Mermaid SVGs, and clipped SVG HTML labels.
LAYOUT_AUDIT_JS = """(minScale) => {
  const issues = [];
  const docOverflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
  if (docOverflow > 2) issues.push(`Document horizontal overflow by ${docOverflow}px`);

  document.querySelectorAll('.hw-widget, .mermaid-book-figure').forEach((el, idx) => {
    const diff = el.scrollWidth - el.clientWidth;
    if (diff > 2) issues.push(`Container[${idx}] (${el.className}) overflows by ${diff}px`);
  });

  document.querySelectorAll('.mermaid-error').forEach((el, idx) => {
    issues.push(`Mermaid render error[${idx}]: ${el.textContent?.trim()}`);
  });

  document.querySelectorAll('.mermaid-book-figure svg').forEach((svg, idx) => {
    const vb = (svg.getAttribute('viewBox') || '').trim().split(/\\s+/).map(Number);
    const rect = svg.getBoundingClientRect();
    const hidden =
      rect.width <= 0 ||
      rect.height <= 0 ||
      Boolean(svg.closest('details:not([open])')) ||
      (typeof svg.checkVisibility === 'function' && !svg.checkVisibility());
    if (hidden) return;
    if (vb.length === 4 && vb[2] > 0 && window.innerWidth >= 900) {
      const scale = rect.width / vb[2];
      if (scale < minScale) {
        issues.push(`Mermaid[${idx}] scaled down to ${(scale * 100).toFixed(0)}% (< ${(minScale * 100).toFixed(0)}%)`);
      }
    }
    svg.querySelectorAll('foreignObject').forEach((fo, fIdx) => {
      const fr = fo.getBoundingClientRect();
      if (fr.width <= 0 || fr.height <= 0) return;
      fo.querySelectorAll('div, p, span').forEach((node) => {
        const nr = node.getBoundingClientRect();
        if (nr.width <= 0 || nr.height <= 0) return;
        const clippedBox = nr.right > fr.right + 2 || nr.bottom > fr.bottom + 2;
        const clippedScroll =
          (node.clientWidth > 0 && node.scrollWidth > node.clientWidth + 2) ||
          (node.clientHeight > 0 && node.scrollHeight > node.clientHeight + 2);
        if (clippedBox || clippedScroll) {
          issues.push(`Mermaid[${idx}] label[${fIdx}] ('${node.textContent?.trim().slice(0, 24)}') clips foreignObject box`);
        }
      });
    });
  });
  return issues;
}"""

# Computes effective composite background and WCAG 2.1 contrast ratio for a visible button element.
BUTTON_CONTRAST_JS = """(btn) => {
  const parseRgba = (s) => {
    const m = s.match(/rgba?\\(([^)]+)\\)/);
    if (!m) return [255, 255, 255, 0];
    const tokens = m[1].trim().split(/[\\s,/]+/).filter(Boolean);
    const parts = tokens.map((v, i) =>
      v.endsWith('%') ? Number.parseFloat(v) * (i < 3 ? 2.55 : 0.01) : Number.parseFloat(v)
    );
    const a = parts.length > 3 && !Number.isNaN(parts[3]) ? parts[3] : 1;
    return [parts[0] || 0, parts[1] || 0, parts[2] || 0, a];
  };
  const blend = (fg, bg) => {
    const a = fg[3] + bg[3] * (1 - fg[3]);
    if (a <= 0) return bg.slice(0, 3).concat([1]);
    return [
      (fg[0] * fg[3] + bg[0] * bg[3] * (1 - fg[3])) / a,
      (fg[1] * fg[3] + bg[1] * bg[3] * (1 - fg[3])) / a,
      (fg[2] * fg[3] + bg[2] * bg[3] * (1 - fg[3])) / a,
      a,
    ];
  };
  const layers = [];
  for (let cur = btn; cur; cur = cur.parentElement) {
    const cs = getComputedStyle(cur);
    const c = parseRgba(cs.backgroundColor);
    const op = Number.parseFloat(cs.opacity);
    if (!Number.isNaN(op)) c[3] *= op;
    layers.unshift(c);
  }
  const isDark = document.documentElement.classList.contains('dark');
  let bg = isDark ? [27, 27, 31, 1] : [255, 255, 255, 1];
  for (const layer of layers) bg = blend(layer, bg);
  const fgStyle = getComputedStyle(btn);
  const fg = parseRgba(fgStyle.color);
  const fgOp = Number.parseFloat(fgStyle.opacity);
  if (!Number.isNaN(fgOp)) fg[3] *= fgOp;
  const effFg = blend(fg, bg);
  const lum = (rgb) => {
    const ch = rgb.slice(0, 3).map((v) => {
      const s = v / 255;
      return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
  };
  const l1 = lum(effFg), l2 = lum(bg);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}"""


def discover_routes(root_dir: Path) -> list[str]:
    """Return built VitePress routes for home, vision, system READMEs, and chapters."""
    routes = ["/", "/vision"]
    systems_dir = root_dir / "systems"
    if not systems_dir.is_dir():
        return routes
    for readme in sorted(systems_dir.glob("*/README.md")):
        routes.append(f"/{readme.parent.name}/")
    for chap in sorted(systems_dir.glob("*/chapters/*.md")):
        routes.append(f"/{chap.parent.parent.name}/{chap.stem}")
    return routes


def normalize_base(base_path: str) -> str:
    """Normalize VitePress `--base` prefix to `'/subpath'` or `''` for root."""
    clean = "/" + base_path.strip("/") if base_path.strip("/") else ""
    return clean


class DistHandler(http.server.SimpleHTTPRequestHandler):
    """Static HTTP handler matching VitePress cleanUrls, base prefix, and path-escape guards."""

    dist_root: Path = DEFAULT_DIST
    base_prefix: str = ""

    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler dispatch requires exact method name
        """Return 204 for missing favicon requests to avoid false console noise."""
        clean = self.path.split("?", 1)[0].split("#", 1)[0]
        if clean == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()

    def translate_path(self, path: str) -> str:
        """Strip configured base prefix and resolve cleanUrls safely inside `dist_root`."""
        clean = unquote(path.split("?", 1)[0].split("#", 1)[0])
        if self.base_prefix:
            if not (clean == self.base_prefix or clean.startswith(self.base_prefix + "/")):
                return str(self.dist_root / "__invalid_base__")
            clean = clean[len(self.base_prefix) :] or "/"
        rel = clean.lstrip("/")
        candidate = (self.dist_root / rel).resolve()
        if not candidate.is_relative_to(self.dist_root):
            return str(self.dist_root / "__invalid_escape__")
        if candidate.is_dir():
            return str(candidate / "index.html")
        if not candidate.exists() and (self.dist_root / f"{rel}.html").is_file():
            return str(self.dist_root / f"{rel}.html")
        return str(candidate)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 — stdlib BaseHTTPRequestHandler signature
        """Suppress HTTP request logs during automated test runs."""
        return


def _make_handler(dist_dir: Path, base_prefix: str) -> type[http.server.SimpleHTTPRequestHandler]:
    """Bind `dist_dir` and `base_prefix` onto a fresh top-level `DistHandler` subclass."""
    return type("BoundDistHandler", (DistHandler,), {"dist_root": dist_dir.resolve(), "base_prefix": base_prefix})


def start_dist_server(dist_dir: Path, base_path: str) -> tuple[http.server.ThreadingHTTPServer, int]:
    """Start background static HTTP server for `dist_dir` and return `(server, port)`."""
    handler_cls = _make_handler(dist_dir, normalize_base(base_path))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, int(httpd.server_address[1])


def resolve_chromium_executable(pw_executable: str | None = None) -> str | None:
    """Resolve explicit Chromium binary if set, else prefer Playwright's binary over system Chrome."""
    env_path = os.environ.get("CHROMIUM_PATH")
    if env_path and Path(env_path).is_file():
        return env_path
    if pw_executable and Path(pw_executable).is_file():
        return None
    for candidate in ("chromium", "chromium-browser", "google-chrome"):
        if found := shutil.which(candidate):
            return found
    sys_chromium = Path("/usr/bin/chromium")
    return str(sys_chromium) if sys_chromium.is_file() else None


def _check_button_contrast(btn: object, idx: int, label: str, route: str, errors: list[str]) -> None:
    """Evaluate `BUTTON_CONTRAST_JS` on `btn` and record finite non-compliant contrast ratios."""
    ratio = float(btn.evaluate(BUTTON_CONTRAST_JS))
    if not math.isfinite(ratio) or ratio < MIN_BTN_CONTRAST:
        errors.append(f"[{route}:desktop] Low {label} contrast ({ratio:.2f}:1) on button[{idx}]")


def _audit_widget_buttons(page: object, route: str, errors: list[str]) -> None:
    """Audit widget buttons before clicking (light & dark idle) and after click/hover across themes."""
    # Capture concrete ElementHandles up front so dynamic enable/disable state changes never shift indices.
    handles = page.locator(".hw-widget .hw-btn").element_handles()
    for idx, btn in enumerate(handles):
        if btn.is_visible() and btn.is_enabled():
            btn.scroll_into_view_if_needed()
            _check_button_contrast(btn, idx, "idle", route, errors)

    # Sample true pre-click idle contrast under VitePress `.dark` before click mutations run.
    page.evaluate("document.documentElement.classList.add('dark')")
    page.wait_for_timeout(160)
    try:
        for idx, btn in enumerate(handles):
            if btn.is_visible() and btn.is_enabled():
                _check_button_contrast(btn, idx, "dark-idle", route, errors)
    finally:
        page.evaluate("document.documentElement.classList.remove('dark')")
        page.wait_for_timeout(160)

    for idx, btn in enumerate(handles):
        if not btn.is_visible() or not btn.is_enabled():
            continue
        btn.scroll_into_view_if_needed()
        btn.click()
        btn.hover()
        # Wait past `.hw-btn`'s 0.15s CSS color/background transition before sampling final styles.
        page.wait_for_timeout(200)
        if btn.is_visible() and btn.is_enabled():
            _check_button_contrast(btn, idx, "active/hover", route, errors)

    page.evaluate("document.documentElement.classList.add('dark')")
    page.wait_for_timeout(160)
    try:
        for idx, btn in enumerate(handles):
            if btn.is_visible() and btn.is_enabled():
                _check_button_contrast(btn, idx, "dark-active/hover", route, errors)
    finally:
        page.evaluate("document.documentElement.classList.remove('dark')")


def _capture_route_screenshots(page: object, route: str, shot_root: Path) -> None:
    """Save visible Mermaid SVG and Vue widget PNG snapshots for visual subagent inspection."""
    slug = route.strip("/").replace("/", "__") or "index"
    out_dir = shot_root / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    mermaids = page.locator(".mermaid-book-figure")
    for idx in range(mermaids.count()):
        item = mermaids.nth(idx)
        if item.is_visible():
            item.screenshot(path=str(out_dir / f"mermaid_{idx}.png"))
    widgets = page.locator(".hw-widget")
    for idx in range(widgets.count()):
        item = widgets.nth(idx)
        if item.is_visible():
            item.screenshot(path=str(out_dir / f"widget_{idx}.png"))


def _drain_page_errors(page_errs: list[str], route: str, vp_name: str, errors: list[str]) -> None:
    """Flush accumulated browser runtime/network errors into `errors` and clear `page_errs`."""
    for msg in page_errs:
        errors.append(f"[{route}:{vp_name}] {msg}")
    page_errs.clear()


def _run_browser_audit(
    pw: object,
    port: int,
    base_prefix: str,
    routes: list[str],
    exe_path: str | None,
    screenshot_dir: Path | None,
    errors: list[str],
) -> None:
    """Launch headless Chromium inside Playwright and audit every route across desktop and mobile."""
    launch_opts: dict[str, object] = {"headless": True}
    if exe_path:
        launch_opts["executable_path"] = exe_path
    browser = pw.chromium.launch(**launch_opts)
    try:
        for vp_name, width, height in VIEWPORTS:
            page = browser.new_page(viewport={"width": width, "height": height})
            try:
                page_errs: list[str] = []
                page.on("pageerror", lambda exc, pe=page_errs: pe.append(f"JS exception: {exc}"))
                page.on(
                    "console",
                    lambda msg, pe=page_errs: pe.append(f"console.error: {msg.text}") if msg.type == "error" else None,
                )
                page.on(
                    "response",
                    lambda resp, pe=page_errs: pe.append(f"HTTP {resp.status}: {resp.url}") if resp.status >= 400 else None,
                )
                for route in routes:
                    page_errs.clear()
                    norm_route = "/" + route.lstrip("/")
                    full_url = f"http://127.0.0.1:{port}{base_prefix}{norm_route}"
                    page.goto(full_url, wait_until="networkidle")
                    page.wait_for_timeout(450)
                    _drain_page_errors(page_errs, route, vp_name, errors)
                    for issue in page.evaluate(LAYOUT_AUDIT_JS, MIN_MERMAID_SCALE):
                        errors.append(f"[{route}:{vp_name}] {issue}")
                    if vp_name == "desktop":
                        _audit_widget_buttons(page, route, errors)
                        _drain_page_errors(page_errs, route, vp_name, errors)
                        if screenshot_dir is not None:
                            _capture_route_screenshots(page, route, screenshot_dir)
            finally:
                page.close()
    finally:
        browser.close()


def audit_pages(
    dist_dir: Path,
    base_path: str,
    routes: list[str],
    screenshot_dir: Path | None = None,
) -> list[str]:
    """Run headless Chromium visual checks across `routes` and return diagnostic errors."""
    if not dist_dir.is_dir():
        return [f"Built dist directory missing: '{dist_dir}' (run 'npm --prefix book run build' first)"]
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return ["Missing required dependency 'playwright'; invoke via 'uv run --with playwright python3 scripts/check_visuals.py'"]

    errors: list[str] = []
    httpd, port = start_dist_server(dist_dir, base_path)
    base_prefix = normalize_base(base_path)
    try:
        with sync_playwright() as pw:
            pw_exe = getattr(pw.chromium, "executable_path", None)
            exe_path = resolve_chromium_executable(pw_exe)
            _run_browser_audit(pw, port, base_prefix, routes, exe_path, screenshot_dir, errors)
    finally:
        httpd.shutdown()
        httpd.server_close()
    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for headless Chromium VitePress visual verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST, help="Path to built VitePress dist directory.")
    parser.add_argument("--base", default=DEFAULT_BASE, help="VitePress base path prefix (default: /apex/).")
    parser.add_argument("--screenshot-dir", type=Path, default=None, help="Optional directory to save desktop PNGs.")
    parser.add_argument("routes", nargs="*", help="Optional explicit routes (defaults to auto-discovered site routes).")
    args = parser.parse_args(argv)

    routes = args.routes or discover_routes(ROOT_DIR)
    errors = audit_pages(args.dist, args.base, routes, args.screenshot_dir)
    if errors:
        print("Visual verification FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"OK: Verified {len(routes)} page(s) across desktop/mobile viewports with zero layout, SVG, or contrast defects.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
