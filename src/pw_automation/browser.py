#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
浏览器自动化公共模板。

这个文件专门放所有高频、可复用的 Playwright / Chrome 操作，避免
`lx_OMS.py` 和 `lingxing.py` 重复维护同一套浏览器逻辑。
"""

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
    """统一的随机等待，降低页面未完全渲染时直接操作导致的失败概率。"""
    time.sleep(random.uniform(min_sec, max_sec))


def is_debug_browser_ready(port=DEBUG_PORT):
    """检查调试端口上是否已经有可被 Playwright 接管的 Chrome。"""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1.5) as response:
            return response.status == 200
    except Exception:
        return False


def start_debug_chrome(port=DEBUG_PORT, user_data_dir=USER_DATA_DIR):
    """启动带远程调试端口的 Chrome，供 Playwright 直接接管。"""
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
    """
    优先复用已有调试浏览器。
    只有端口不存在浏览器时，才启动新的 Chrome 实例。
    """
    if is_debug_browser_ready(port):
        print(f"检测到调试端口 {port} 已有浏览器，直接复用现有实例。")
        return None

    print(f"调试端口 {port} 未发现浏览器，启动新的 Chrome 实例。")
    proc = start_debug_chrome(port=port, user_data_dir=user_data_dir)
    for _ in range(10):
        if is_debug_browser_ready(port):
            return proc
        time.sleep(0.5)
    raise RuntimeError(f"Chrome 启动后仍无法连接调试端口: {port}")


def find_debug_chrome_pid(port=DEBUG_PORT):
    """根据远程调试端口，找到对应的 Chrome 进程 PID。"""
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
    """将指定 PID 对应的浏览器窗口置前并最大化。"""
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
    """把调试浏览器切到前台，便于观察自动化执行过程。"""
    pid = chrome_proc.pid if chrome_proc else find_debug_chrome_pid(port)
    if not pid:
        print("未找到可激活的 Chrome 进程，跳过窗口置前。")
        return
    if activate_browser_window_by_pid(pid):
        print("已激活 Chrome 浏览器窗口。")
        time.sleep(0.8)
    else:
        print("Chrome 浏览器窗口激活失败，继续执行。")


def connect_browser(playwright, port=DEBUG_PORT):
    """连接到已开启远程调试端口的 Chrome，并返回 browser/context。"""
    browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    return browser, context



def open_browser_page(playwright, url, wait_until="domcontentloaded", sleep_range=(1.0, 1.8)):
    """
    统一页面打开入口：
    1. 确保调试 Chrome 已经存在
    2. 激活浏览器窗口
    3. 连接浏览器并创建标签页
    4. 打开目标页面
    """
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
    """
    默认只关闭当前标签页。
    需要时可额外强制关闭整个调试浏览器。
    """
    if page:
        try:
            if not page.is_closed():
                page.close(run_before_unload=True)
                print("当前标签页已关闭。")
        except Exception as exc:
            print(f"关闭标签页失败: {exc}")

    if not force_close_browser:
        return

    if browser:
        try:
            browser.close()
        except Exception:
            pass

    pid = chrome_proc.pid if chrome_proc else find_debug_chrome_pid(port)
    if not pid:
        print("未找到可关闭的 Chrome 进程。")
        return

    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        print(f"Chrome 浏览器已强制关闭，PID: {pid}")
    except Exception as exc:
        print(f"强制关闭 Chrome 浏览器失败: {exc}")


def goto_with_wait(page, url, desc, timeout_ms=DEFAULT_TIMEOUT_MS):
    """页面跳转公共方法，优先等 DOM 加载，再尽量等 networkidle。"""
    print(f"{desc}: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    random_sleep(1.0, 1.6)
    try:
        page.wait_for_load_state("networkidle", timeout=3000)
    except Exception:
        print(f"{desc} 时 networkidle 未稳定，继续执行。")


def wait_for_any_selector(page, selectors, desc, timeout_ms=DEFAULT_TIMEOUT_MS):
    """多个候选元素里，只要任意一个出现就算加载完成。"""
    last_error = None
    for selector in selectors:
        try:
            page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
            return selector
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"{desc}失败: {selectors}") from last_error


def has_visible_element(page, selectors):
    """判断多个候选 selector 中，是否至少有一个当前可见。"""
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
    通用点击：
    先等待元素可见，再滚动到可视区域，最后强制点击。
    如果普通点击失败，再退回 JS click。
    """
    locator = page.locator(selector).first
    try:
        page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
        locator.scroll_into_view_if_needed(timeout=timeout_ms)
        random_sleep(0.2, 0.4)
        locator.click(force=True, timeout=timeout_ms)
    except PlaywrightTimeoutError as exc:
        raise RuntimeError(f"{desc}失败: {selector}") from exc
    except Exception:
        try:
            page.evaluate("(el) => el.click()", locator.element_handle(timeout=timeout_ms))
        except Exception as exc:
            raise RuntimeError(f"{desc}失败: {selector}") from exc


def click_first_visible(page, selectors, desc, timeout_ms=DEFAULT_TIMEOUT_MS):
    """在多个 selector 里找第一个可见元素并点击。"""
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
    """通用悬浮；优先使用 Playwright hover，失败后退回鼠标坐标移动。"""
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
    """在多个候选输入框中，找到第一个可见且可编辑的输入框并填写。"""
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
    """等待某个 selector 下出现第一个可见元素，并返回 locator。"""
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
