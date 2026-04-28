#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Shared Playwright / Chrome helpers for browser automation."""

from __future__ import annotations

import ctypes
import random
import subprocess
import time
import urllib.request

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .config import get_settings


_settings = get_settings()
DEBUG_PORT = _settings.debug_port
USER_DATA_DIR = _settings.user_data_dir
CHROME_PATH = _settings.chrome_path
DEFAULT_TIMEOUT_MS = _settings.default_timeout_ms
KEEP_BROWSER_OPEN_ON_ERROR = _settings.keep_browser_open_on_error


def random_sleep(min_sec=0.2, max_sec=0.6):
    """Sleep for a short random duration to reduce flaky UI timing."""
    time.sleep(random.uniform(min_sec, max_sec))


def is_debug_browser_ready(port=DEBUG_PORT):
    """Return whether a Chrome instance is listening on the debug port."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1.5) as response:
            return response.status == 200
    except Exception:
        return False


def start_debug_chrome(port=DEBUG_PORT, user_data_dir=USER_DATA_DIR):
    """Start Chrome with a remote debugging port for Playwright CDP connection."""
    proc = subprocess.Popen(
        [
            CHROME_PATH,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
        ],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )
    time.sleep(2)
    return proc


def ensure_debug_chrome(port=DEBUG_PORT, user_data_dir=USER_DATA_DIR):
    """Reuse an existing debug Chrome, or start a new one if none is ready."""
    if is_debug_browser_ready(port):
        print(f"Detected Chrome on debug port {port}, reusing the existing instance.")
        return None

    print(f"No Chrome detected on debug port {port}, starting a new instance.")
    proc = start_debug_chrome(port=port, user_data_dir=user_data_dir)
    for _ in range(10):
        if is_debug_browser_ready(port):
            return proc
        time.sleep(0.5)
    raise RuntimeError(f"Chrome started but the debug port is still unavailable: {port}")


def find_debug_chrome_pid(port=DEBUG_PORT):
    """Find the Chrome process ID for the configured remote debugging port."""
    try:
        result = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_Process -Filter \"name='chrome.exe'\" | "
                    f"Where-Object {{ $_.CommandLine -match '--remote-debugging-port={port}' }} | "
                    "Select-Object -First 1 -ExpandProperty ProcessId"
                ),
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return int(result) if result else None
    except Exception:
        return None


def activate_browser_window_by_pid(pid):
    """Bring the Chrome window for the given PID to the foreground."""
    if not pid:
        return False

    user32 = ctypes.windll.user32
    target_hwnd = None

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_windows_proc(hwnd, _):
        nonlocal target_hwnd
        window_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if window_pid.value != pid:
            return True
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindow(hwnd, 4):
            return True
        target_hwnd = hwnd
        return False

    user32.EnumWindows(enum_windows_proc, 0)
    if not target_hwnd:
        return False

    user32.ShowWindow(target_hwnd, 9)
    user32.ShowWindow(target_hwnd, 3)
    user32.SetForegroundWindow(target_hwnd)
    return True


def activate_debug_browser(chrome_proc=None, port=DEBUG_PORT):
    """Bring the debug Chrome window to the foreground for visual inspection."""
    pid = chrome_proc.pid if chrome_proc else find_debug_chrome_pid(port)
    if not pid:
        print("No Chrome process found to activate; skipping window activation")
        return
    if activate_browser_window_by_pid(pid):
        print("Activated the Chrome window")
        time.sleep(0.8)
    else:
        print("Failed to activate the Chrome window; continuing")


def connect_browser(playwright, port=DEBUG_PORT):
    """Connect Playwright to Chrome over CDP and return browser/context."""
    browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    return browser, context


def open_browser_page(playwright, url, wait_until="domcontentloaded", sleep_range=(1.0, 1.8)):
    """Open a new page in the debug Chrome instance and navigate to the target URL."""
    chrome_proc = ensure_debug_chrome()
    activate_debug_browser(chrome_proc=chrome_proc)
    browser, context = connect_browser(playwright)
    page = context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT_MS)
    page.bring_to_front()
    page.goto(url, wait_until=wait_until)
    random_sleep(*sleep_range)
    return chrome_proc, browser, context, page


def close_page(page=None, browser=None, chrome_proc=None, force_close_browser=False, port=DEBUG_PORT):
    """Close the current page, and optionally force close the entire debug browser."""
    if page:
        try:
            if not page.is_closed():
                page.close(run_before_unload=True)
                print("Closed the current tab.")
        except Exception as exc:
            print(f"关闭当前标签页失败: {exc}")

    if not force_close_browser:
        return

    if browser:
        try:
            browser.close()
        except Exception:
            pass

    pid = chrome_proc.pid if chrome_proc else find_debug_chrome_pid(port)
    if not pid:
        print("No Chrome process found to close.")
        return

    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        print(f"Force closed Chrome, PID: {pid}")
    except Exception as exc:
        print(f"Failed to force close Chrome: {exc}")


def goto_with_wait(page, url, desc, timeout_ms=DEFAULT_TIMEOUT_MS):
    """Navigate to a page and wait for basic load completion."""
    print(f"{desc}: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    random_sleep(1.0, 1.6)
    try:
        page.wait_for_load_state("networkidle", timeout=3000)
    except Exception:
        print(f"{desc}: networkidle was not reached; continuing.")


def wait_for_any_selector(page, selectors, desc, timeout_ms=DEFAULT_TIMEOUT_MS):
    """Wait until any selector in the list becomes visible."""
    last_error = None
    for selector in selectors:
        try:
            page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
            return selector
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"{desc}失败: {selectors}") from last_error


def has_visible_element(page, selectors):
    """Return whether any selector in the list is currently visible."""
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0 and locator.is_visible():
                return True
        except Exception:
            continue
    return False


def click_or_raise(page, selector, desc, timeout_ms=DEFAULT_TIMEOUT_MS):
    """
    Click a target element with a fast-fail selector check.

    This avoids hanging for the full default timeout when the selector is invalid
    or the element does not exist. A short selector wait is used first, then the
    remaining timeout is used for the actual click attempt.
    """
    start_time = time.time()
    find_timeout_ms = min(timeout_ms, 5000)
    locator = page.locator(selector).first

    def remaining_timeout_ms():
        elapsed_ms = int((time.time() - start_time) * 1000)
        return max(500, timeout_ms - elapsed_ms)

    try:
        page.wait_for_selector(selector, state="visible", timeout=find_timeout_ms)
        locator.scroll_into_view_if_needed(timeout=remaining_timeout_ms())
        random_sleep(0.2, 0.4)
        locator.click(force=True, timeout=remaining_timeout_ms())
    except PlaywrightTimeoutError as exc:
        raise RuntimeError(
            f"{desc}失败: 未在 {find_timeout_ms}ms 内找到可点击元素 {selector}"
        ) from exc
    except Exception as first_exc:
        try:
            handle = locator.element_handle(timeout=500)
            if handle is None:
                raise RuntimeError("未获取到元素句柄")
            page.evaluate("(el) => el.click()", handle)
        except Exception as exc:
            raise RuntimeError(
                f"{desc}失败: 点击元素 {selector} 时出错，原始错误: {first_exc}"
            ) from exc


def click_first_visible(page, selectors, desc, timeout_ms=DEFAULT_TIMEOUT_MS):
    """Find and click the first visible element among multiple selectors."""
    deadline = time.time() + timeout_ms / 1000
    last_selector = selectors[0]
    while time.time() < deadline:
        for selector in selectors:
            locator = page.locator(selector)
            for index in range(locator.count()):
                item = locator.nth(index)
                try:
                    if not item.is_visible():
                        continue
                    item.scroll_into_view_if_needed(timeout=timeout_ms)
                    random_sleep(0.2, 0.4)
                    item.click(force=True, timeout=timeout_ms)
                    return item
                except Exception:
                    last_selector = selector
                    continue
        time.sleep(0.2)
    raise RuntimeError(f"{desc}失败: {last_selector}")


def hover_or_raise(page, selector, desc, timeout_ms=DEFAULT_TIMEOUT_MS):
    """Hover over an element, with a mouse-move fallback."""
    locator = page.locator(selector).first
    try:
        page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
        locator.scroll_into_view_if_needed(timeout=timeout_ms)
        random_sleep(0.2, 0.4)
        locator.hover(force=True, timeout=timeout_ms)
    except PlaywrightTimeoutError as exc:
        raise RuntimeError(f"{desc}失败: {selector}") from exc
    except Exception:
        try:
            box = locator.bounding_box()
            if not box:
                raise RuntimeError("未获取到元素位置")
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        except Exception as exc:
            raise RuntimeError(f"{desc}失败: {selector}") from exc


def fill_first_visible_input(page, selectors, value, desc, timeout_ms=DEFAULT_TIMEOUT_MS):
    """Fill the first visible and enabled input among multiple selectors."""
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        for selector in selectors:
            locator = page.locator(selector)
            for index in range(locator.count()):
                item = locator.nth(index)
                try:
                    if item.is_visible() and item.is_enabled():
                        item.scroll_into_view_if_needed(timeout=timeout_ms)
                        item.click(force=True, timeout=timeout_ms)
                        item.fill(str(value).strip())
                        return item
                except Exception:
                    continue
        time.sleep(0.2)
    raise RuntimeError(f"{desc}失败: 未找到可输入控件")


def get_first_visible_locator(page, selector, desc, timeout_ms=DEFAULT_TIMEOUT_MS):
    """Return the first visible locator matched by the selector."""
    deadline = time.time() + timeout_ms / 1000
    last_count = 0
    while time.time() < deadline:
        locator = page.locator(selector)
        last_count = locator.count()
        for index in range(last_count):
            item = locator.nth(index)
            try:
                if item.is_visible():
                    return item
            except Exception:
                continue
        time.sleep(0.2)
    raise RuntimeError(f"{desc}失败: 未找到可见元素，匹配数量 {last_count}")
