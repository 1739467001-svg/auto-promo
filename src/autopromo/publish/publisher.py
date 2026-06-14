"""发布编排：在一个浏览器会话里依次把各平台待发布包送上去。"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..models import PublishPackage, PublishResult
from .browser import browser_context
from .flow import execute_flow
from .flows import get_flow, login_url


def publish_packages(
    cfg: Config,
    packages: list[PublishPackage],
    *,
    debug_dir: Path | None = None,
    keep_open: bool = False,
    log=print,
) -> list[PublishResult]:
    """对每个待发布包执行上传。每个平台用新标签页，互不影响。"""
    results: list[PublishResult] = []
    with browser_context(
        cfg.browser_profile_dir, headless=cfg.headless, slow_mo_ms=cfg.slow_mo_ms
    ) as ctx:
        for pkg in packages:
            toggle = cfg.platform_toggle(pkg.platform)
            page = ctx.new_page()
            try:
                flow = get_flow(pkg.platform)
                res = execute_flow(
                    page, flow, pkg,
                    auto_submit=toggle.auto_submit,
                    debug_dir=debug_dir,
                    log=log,
                )
            except Exception as exc:  # noqa: BLE001 - 单平台失败不影响其它平台
                res = PublishResult(pkg.platform, ok=False, submitted=False,
                                   message=f"异常：{exc}")
            results.append(res)
            log(f"[{pkg.platform}] => {'OK' if res.ok else 'FAIL'} "
                f"{'(已发布)' if res.submitted else '(待人工发布)'} {res.message}")
            if not keep_open:
                page.close()

        if keep_open:
            log("keep_open=True：浏览器保持打开，核对/手动发布后按回车关闭…")
            try:
                input()
            except EOFError:
                pass
    return results


def open_login(cfg: Config, platform: str, log=print) -> None:
    """打开某平台登录页，供首次手动登录（cookie 存进持久化 profile）。"""
    url = login_url(platform)
    with browser_context(cfg.browser_profile_dir, headless=False, slow_mo_ms=0) as ctx:
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        log(f"已打开 {platform} 登录页：{url}")
        log("请在浏览器里完成登录（扫码/账号密码），登录态会保存在该 profile。")
        log("完成后回到终端按回车关闭浏览器…")
        try:
            input()
        except EOFError:
            pass
