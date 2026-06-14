"""声明式上传流程 + 通用执行器。

各平台上传页结构不同，但步骤高度一致：
  打开上传页 → 传视频 → 等转码 → 填标题/简介 → 传封面 →（必要时）标转载 →（可选）发布。

把每个平台的差异抽成 UploadFlow（一组候选选择器），用同一个 execute_flow 驱动。
选择器写成"候选列表"：平台改版时多半只需在 flows.py 里补一个新选择器，不用改逻辑。

⚠️ 各平台前端经常改版，flows.py 里的选择器是合理初值，首次实跑时请配合
   --keep-open / 截图自检并按需微调。默认 auto_submit=False，只会把内容填好停在
   发布按钮前，由你点最后一下，避免误发。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PWTimeout

from ..models import PublishPackage, PublishResult


@dataclass
class UploadFlow:
    platform: str
    upload_url: str
    # 视频文件 input[type=file] 的候选选择器
    video_input: list[str]
    # 标题输入框候选
    title_input: list[str] = field(default_factory=list)
    # 简介/正文输入框候选
    content_input: list[str] = field(default_factory=list)
    # 打开"设置封面"对话框的按钮候选（可空 = 跳过封面自动上传）
    cover_open_button: list[str] = field(default_factory=list)
    # 封面对话框里 input[type=file] 候选
    cover_input: list[str] = field(default_factory=list)
    # 封面对话框确认按钮候选
    cover_confirm_button: list[str] = field(default_factory=list)
    # "转载/非原创"勾选项候选（mark_repost 时用）
    repost_toggle: list[str] = field(default_factory=list)
    # 发布按钮候选
    submit_button: list[str] = field(default_factory=list)
    # 传完视频后，等待转码就绪的指示元素（出现即认为可填表单）
    ready_indicator: list[str] = field(default_factory=list)
    upload_wait_ms: int = 120_000


def _first(page: Page, selectors: list[str], timeout: int = 4000):
    """返回第一个可见的元素句柄，找不到返回 None。"""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout)
            return loc
        except PWTimeout:
            continue
        except Exception:
            continue
    return None


def _fill(page: Page, selectors: list[str], text: str, log) -> bool:
    if not text:
        return False
    el = _first(page, selectors)
    if el is None:
        log(f"  · 未找到输入框：{selectors[:1]}…（跳过）")
        return False
    try:
        el.click()
        # 富文本编辑器（contenteditable）用键盘输入更稳
        try:
            el.fill("")
        except Exception:
            pass
        el.type(text, delay=15)
        return True
    except Exception as exc:
        log(f"  · 填写失败：{exc}")
        return False


def _upload(page: Page, selectors: list[str], file: Path, log) -> bool:
    for sel in selectors:
        try:
            page.locator(sel).first.set_input_files(str(file), timeout=8000)
            return True
        except Exception:
            continue
    log(f"  · 未找到文件上传 input：{selectors[:1]}…")
    return False


def _click(page: Page, selectors: list[str], log, what: str) -> bool:
    el = _first(page, selectors)
    if el is None:
        log(f"  · 未找到{what}按钮（跳过）")
        return False
    try:
        el.click()
        return True
    except Exception as exc:
        log(f"  · 点击{what}失败：{exc}")
        return False


def execute_flow(
    page: Page,
    flow: UploadFlow,
    pkg: PublishPackage,
    *,
    auto_submit: bool,
    debug_dir: Path | None,
    log=print,
) -> PublishResult:
    """执行单平台上传流程。auto_submit=False 时停在发布按钮前。"""
    def shot(tag: str):
        if debug_dir:
            debug_dir.mkdir(parents=True, exist_ok=True)
            try:
                page.screenshot(path=str(debug_dir / f"{flow.platform}_{tag}.png"))
            except Exception:
                pass

    log(f"[{flow.platform}] 打开上传页 {flow.upload_url}")
    page.goto(flow.upload_url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    shot("01_open")

    # 1) 传视频
    if not _upload(page, flow.video_input, pkg.video, log):
        shot("err_no_video_input")
        return PublishResult(flow.platform, ok=False, submitted=False,
                             message="未能定位视频上传入口，可能未登录或页面改版。")
    log("  · 已选择视频，等待上传/转码…")

    # 2) 等就绪
    if flow.ready_indicator:
        el = _first(page, flow.ready_indicator, timeout=flow.upload_wait_ms)
        if el is None:
            log("  · 未检测到就绪指示元素，按固定等待继续")
            page.wait_for_timeout(8000)
    else:
        page.wait_for_timeout(8000)
    shot("02_uploaded")

    # 3) 标题 / 简介
    if _fill(page, flow.title_input, pkg.content.title, log):
        log("  · 标题已填")
    if _fill(page, flow.content_input, pkg.content.caption_with_tags(), log):
        log("  · 简介已填")
    shot("03_text")

    # 4) 封面
    if flow.cover_open_button:
        if _click(page, flow.cover_open_button, log, "设置封面"):
            page.wait_for_timeout(1500)
            if _upload(page, flow.cover_input, pkg.cover.path, log):
                log(f"  · 封面已上传：{pkg.cover.path.name}")
                page.wait_for_timeout(1500)
                _click(page, flow.cover_confirm_button, log, "封面确认")
            shot("04_cover")

    # 5) 转载标注
    if pkg.mark_repost and flow.repost_toggle:
        if _click(page, flow.repost_toggle, log, "转载标注"):
            log("  · 已勾选转载/非原创")
        shot("05_repost")

    # 6) 发布
    if not auto_submit:
        log("  · auto_submit=False：已填好，停在发布按钮前，请人工核对后手动发布。")
        shot("06_ready_to_submit")
        return PublishResult(flow.platform, ok=True, submitted=False,
                             message="内容已就绪，等待人工点击发布。")

    if _click(page, flow.submit_button, log, "发布"):
        page.wait_for_timeout(4000)
        shot("07_submitted")
        return PublishResult(flow.platform, ok=True, submitted=True, message="已点击发布。")

    shot("err_no_submit")
    return PublishResult(flow.platform, ok=False, submitted=False,
                         message="未找到发布按钮，请检查选择器。")
