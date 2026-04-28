"""Configuration helpers for the Playwright automation package."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    debug_port: int = 9555
    user_data_dir: str = r"C:\Temp\PlaywrightSession"
    chrome_path: str = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    default_timeout_ms: int = 600000
    keep_browser_open_on_error: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings from environment variables once per process."""
    return Settings(
        debug_port=int(os.getenv("PW_DEBUG_PORT", "9555")),
        user_data_dir=os.getenv("PW_USER_DATA_DIR", r"C:\Temp\PlaywrightSession"),
        chrome_path=os.getenv(
            "PW_CHROME_PATH",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        ),
        default_timeout_ms=int(os.getenv("PW_DEFAULT_TIMEOUT_MS", "600000")),
        keep_browser_open_on_error=_get_bool("PW_KEEP_BROWSER_OPEN_ON_ERROR", True),
    )
