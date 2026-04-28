"""Command-line entrypoint for basic browser automation tasks."""

from __future__ import annotations

import argparse

from playwright.sync_api import sync_playwright

from .browser import close_page, open_browser_page


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a basic Playwright browser session.")
    parser.add_argument("--url", required=True, help="URL to open in the browser")
    parser.add_argument(
        "--close-browser",
        action="store_true",
        help="Force close the debug Chrome process after the run",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    chrome_proc = None
    browser = None
    page = None

    with sync_playwright() as playwright:
        try:
            chrome_proc, browser, _context, page = open_browser_page(playwright, args.url)
            print(f"Opened: {args.url}")
        finally:
            close_page(
                page=page,
                browser=browser,
                chrome_proc=chrome_proc,
                force_close_browser=args.close_browser,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
