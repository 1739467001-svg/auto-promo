"""Playwright 浏览器会话。

用"持久化用户数据目录"（persistent context）复用登录态：
你只需第一次用 `python -m autopromo login <平台>` 在这个 profile 里手动登录各平台，
cookie 会保存在 browser_profile_dir，之后自动化发布时直接复用，无需重复登录。
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from playwright.sync_api import BrowserContext, sync_playwright


@contextmanager
def browser_context(
    profile_dir: Path,
    *,
    headless: bool = False,
    slow_mo_ms: int = 300,
) -> Iterator[BrowserContext]:
    """打开一个复用登录态的 Chromium 持久化上下文。"""
    profile_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            slow_mo=slow_mo_ms,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            yield context
        finally:
            context.close()
