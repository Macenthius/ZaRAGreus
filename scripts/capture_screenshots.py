"""Capture the report screenshots from the running app and the real evaluation log.

Dev-only tool: needs Playwright, which is NOT in requirements.txt:
    pip install playwright
    python -m playwright install chromium

Prerequisites: Ollama running with qwen2.5:0.5b, and the app started with
    streamlit run app/streamlit_app.py --server.headless true --server.port 8599

Usage:  python scripts/capture_screenshots.py [--url http://localhost:8599] [--scale 2]
Writes report_assets/screenshots/fig3..fig6 PNGs. Nothing is edited or faked: fig3-5 are the
live app, fig6 renders the last lines of results/eval_run_qwen2.5-0.5b.log verbatim.
"""
from __future__ import annotations

import argparse
import html
import logging
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report_assets" / "screenshots"
OWNERSHIP_Q = "What are the three rules of ownership?"
REFUSAL_Q = "What is the capital of France?"
LOG_LINES = 35

log = logging.getLogger("capture_screenshots")


def open_app(page: Page, url: str) -> None:
    """Load the app fresh and wait until the question box is ready."""
    page.goto(url, wait_until="networkidle")
    page.get_by_label("Your question").wait_for(timeout=120_000)


def ask(page: Page, question: str) -> None:
    box = page.get_by_label("Your question")
    box.fill(question)
    box.press("Enter")


def wait_idle(page: Page, timeout: int = 180_000) -> None:
    """Wait until Streamlit's 'Running...' status widget has disappeared."""
    page.wait_for_function(
        "() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=timeout)
    page.wait_for_timeout(800)


def fit_viewport(page: Page, width: int) -> None:
    """Streamlit scrolls inside its main container, so grow the viewport to the content height."""
    height = page.evaluate(
        """() => {
            const els = [document.querySelector('[data-testid="stMain"]'),
                         document.querySelector('[data-testid="stAppViewContainer"]'),
                         document.querySelector('section.main'), document.body];
            return Math.max(...els.filter(Boolean).map(e => e.scrollHeight));
        }""")
    page.set_viewport_size({"width": width, "height": max(1000, int(height) + 40)})
    page.wait_for_timeout(600)


def shot_main_answer(page: Page, url: str, width: int) -> Path:
    open_app(page, url)
    ask(page, OWNERSHIP_Q)
    page.get_by_text("Retrieve:", exact=False).first.wait_for(timeout=180_000)
    wait_idle(page)
    page.locator('[data-testid="stExpander"] summary').first.click()
    page.wait_for_timeout(800)
    fit_viewport(page, width)
    path = OUT / "fig3_main_answer_sources.png"
    page.screenshot(path=str(path), full_page=True)
    return path


def shot_refusal(page: Page, url: str, width: int) -> Path:
    page.set_viewport_size({"width": width, "height": 1000})
    open_app(page, url)
    ask(page, REFUSAL_Q)
    page.get_by_text("Best match similarity", exact=False).first.wait_for(timeout=120_000)
    wait_idle(page)
    fit_viewport(page, width)
    path = OUT / "fig4_refusal.png"
    page.screenshot(path=str(path), full_page=True)
    return path


def shot_sidebar(page: Page, url: str, width: int) -> Path:
    page.set_viewport_size({"width": width, "height": 1000})
    open_app(page, url)
    ask(page, OWNERSHIP_Q)
    page.get_by_text("Retrieve:", exact=False).first.wait_for(timeout=180_000)
    wait_idle(page)
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.get_by_text("Ollama OK", exact=False).wait_for(timeout=30_000)
    path = OUT / "fig5_sidebar_status.png"
    # If the sidebar content is taller than its visible box it would be clipped: fall back to full page.
    clipped = page.evaluate(
        """() => { const c = document.querySelector('[data-testid="stSidebarContent"]')
                     || document.querySelector('[data-testid="stSidebar"]');
                   return c.scrollHeight > c.clientHeight + 2; }""")
    if clipped:
        log.warning("Sidebar content is clipped; taking a full-page screenshot instead.")
        fit_viewport(page, width)
        page.screenshot(path=str(path), full_page=True)
    else:
        sidebar.screenshot(path=str(path))
    return path


def shot_eval_terminal(page: Page, width: int) -> Path:
    candidates = [ROOT / "results" / "eval_run_qwen2.5-0.5b.log"] + sorted(
        (ROOT / "results").glob("eval_run_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    log_path = next((p for p in candidates if p.exists()), None)
    if log_path is None:
        sys.exit("No results/eval_run_*.log found - run scripts/evaluate.py and save its output first.")
    lines = log_path.read_text(encoding="utf-8").splitlines()[-LOG_LINES:]
    body = html.escape("\n".join(lines))  # verbatim: escaped for HTML only, never edited
    page_html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
      body {{ margin: 0; background: #1e1e1e; font-family: Consolas, 'Cascadia Mono', monospace; }}
      .win {{ margin: 16px; border: 1px solid #3c3c3c; border-radius: 6px; overflow: hidden; }}
      .bar {{ background: #2d2d30; color: #cccccc; padding: 8px 14px; font: 13px 'Segoe UI', sans-serif; }}
      pre {{ margin: 0; padding: 14px 16px; background: #0c0c0c; color: #e6e6e6; font-size: 13px;
             line-height: 1.45; white-space: pre-wrap; word-break: break-word; }}
      .src {{ background: #252526; color: #9d9d9d; padding: 5px 14px; font: 12px 'Segoe UI', sans-serif; }}
    </style></head><body><div class="win" id="term">
      <div class="bar">PowerShell - python scripts/evaluate.py</div>
      <div class="src">Recorded output: last {len(lines)} lines of {log_path.relative_to(ROOT).as_posix()}, shown verbatim</div>
      <pre>{body}</pre></div></body></html>"""
    page.set_viewport_size({"width": width, "height": 1000})
    page.set_content(page_html)
    path = OUT / "fig6_eval_terminal.png"
    page.locator("#term").screenshot(path=str(path))
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://localhost:8599")
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--only", nargs="*", help="subset of: main refusal sidebar terminal")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    width = 1400
    todo = set(args.only or ["main", "refusal", "sidebar", "terminal"])
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, fn in [("main", lambda pg: shot_main_answer(pg, args.url, width)),
                         ("refusal", lambda pg: shot_refusal(pg, args.url, width)),
                         ("sidebar", lambda pg: shot_sidebar(pg, args.url, width)),
                         ("terminal", lambda pg: shot_eval_terminal(pg, width))]:
            if name not in todo:
                continue
            # a fresh browser context per shot = a fresh Streamlit session
            ctx = browser.new_context(viewport={"width": width, "height": 1000},
                                      device_scale_factor=args.scale)
            path = fn(ctx.new_page())
            log.info("wrote %s (%.2f MB)", path.relative_to(ROOT), path.stat().st_size / 1e6)
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
