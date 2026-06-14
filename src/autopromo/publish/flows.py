"""各平台 UploadFlow 规格 + 登录页 URL。

选择器为"合理初值"，覆盖各平台创作中心网页版上传页的常见结构。由于平台前端
经常改版，请在首次实跑时用 `--keep-open` 配合 output/<时间>/debug 截图按需微调。

每个平台的 video_input 优先用通用 `input[type=file]`；标题/简介给出按 placeholder
文案、role、常见 class 的多个候选，逐个尝试。
"""

from __future__ import annotations

from .flow import UploadFlow

# 各平台登录页：首次用 `python -m autopromo login <平台>` 打开后手动登录
LOGIN_URLS: dict[str, str] = {
    "douyin": "https://creator.douyin.com/",
    "xiaohongshu": "https://creator.xiaohongshu.com/",
    "shipinhao": "https://channels.weixin.qq.com/platform",
    "xigua": "https://studio.ixigua.com/",
    "toutiao": "https://mp.toutiao.com/",
    "bilibili": "https://member.bilibili.com/",
}


_FLOWS: dict[str, UploadFlow] = {
    "douyin": UploadFlow(
        platform="douyin",
        upload_url="https://creator.douyin.com/creator-micro/content/upload",
        video_input=["input[type=file][accept*=video]", "input[type=file]"],
        title_input=[
            "input[placeholder*='标题']",
            "input[placeholder*='作品标题']",
            ".title-input input",
        ],
        content_input=[
            "div[data-placeholder*='简介']",
            "div.editor-kit-container[contenteditable=true]",
            "div[contenteditable=true]",
        ],
        cover_open_button=["text=选择封面", "text=设置封面", "text=封面"],
        cover_input=["input[type=file][accept*=image]"],
        cover_confirm_button=["button:has-text('确定')", "button:has-text('完成')"],
        submit_button=["button:has-text('发布')"],
        ready_indicator=["text=上传成功", "text=重新上传", "input[placeholder*='标题']"],
    ),
    "xiaohongshu": UploadFlow(
        platform="xiaohongshu",
        upload_url="https://creator.xiaohongshu.com/publish/publish?from=menu",
        video_input=["input[type=file][accept*=video]", "input[type=file]"],
        title_input=[
            "input[placeholder*='标题']",
            "input[placeholder*='填写标题']",
            ".titleInput input",
        ],
        content_input=[
            "div[contenteditable=true]",
            "div[data-placeholder*='正文']",
            "#post-textarea",
        ],
        cover_open_button=["text=设置封面", "text=编辑封面", "text=封面"],
        cover_input=["input[type=file][accept*=image]"],
        cover_confirm_button=["button:has-text('确定')", "button:has-text('完成')"],
        submit_button=["button:has-text('发布')"],
        ready_indicator=["text=上传成功", "input[placeholder*='标题']"],
    ),
    "shipinhao": UploadFlow(
        platform="shipinhao",
        upload_url="https://channels.weixin.qq.com/platform/post/create",
        video_input=["input[type=file][accept*=video]", "input[type=file]"],
        title_input=[
            "input[placeholder*='标题']",
            "input[placeholder*='概括视频主要内容']",
        ],
        content_input=[
            "div[contenteditable=true]",
            "div[data-placeholder*='添加描述']",
        ],
        cover_open_button=["text=更换封面", "text=编辑封面", "text=封面"],
        cover_input=["input[type=file][accept*=image]"],
        cover_confirm_button=["button:has-text('确定')", "button:has-text('确认')"],
        submit_button=["button:has-text('发表')", "button:has-text('发布')"],
        ready_indicator=["text=删除", "input[placeholder*='标题']"],
    ),
    "xigua": UploadFlow(
        platform="xigua",
        upload_url="https://studio.ixigua.com/upload",
        video_input=["input[type=file][accept*=video]", "input[type=file]"],
        title_input=["input[placeholder*='标题']", "textarea[placeholder*='标题']"],
        content_input=["div[contenteditable=true]", "textarea[placeholder*='简介']"],
        cover_open_button=["text=选择封面", "text=设置封面", "text=封面"],
        cover_input=["input[type=file][accept*=image]"],
        cover_confirm_button=["button:has-text('确定')", "button:has-text('完成')"],
        submit_button=["button:has-text('发布')"],
        ready_indicator=["text=上传成功", "input[placeholder*='标题']"],
    ),
    "toutiao": UploadFlow(
        platform="toutiao",
        upload_url="https://mp.toutiao.com/profile_v4/xigua/upload-video",
        video_input=["input[type=file][accept*=video]", "input[type=file]"],
        title_input=["input[placeholder*='标题']", "textarea[placeholder*='标题']"],
        content_input=["div[contenteditable=true]", "textarea[placeholder*='简介']"],
        cover_open_button=["text=选择封面", "text=设置封面", "text=封面"],
        cover_input=["input[type=file][accept*=image]"],
        cover_confirm_button=["button:has-text('确定')", "button:has-text('完成')"],
        submit_button=["button:has-text('发布')"],
        ready_indicator=["text=上传成功", "input[placeholder*='标题']"],
    ),
    "bilibili": UploadFlow(
        platform="bilibili",
        upload_url="https://member.bilibili.com/platform/upload/video/frame",
        video_input=["input[type=file][accept*=video]", "input[type=file]"],
        title_input=[
            "input[placeholder*='标题']",
            ".video-title input",
        ],
        content_input=[
            "div.ql-editor[contenteditable=true]",
            "div[contenteditable=true]",
        ],
        cover_open_button=["text=更改封面", "text=设置封面", "text=封面"],
        cover_input=["input[type=file][accept*=image]"],
        cover_confirm_button=["button:has-text('完成')", "button:has-text('确定')"],
        # B 站"转载"：选择来源类型为转载并填来源
        repost_toggle=["text=转载", "label:has-text('转载')"],
        submit_button=["button:has-text('立即投稿')", "button:has-text('投稿')"],
        ready_indicator=["text=上传完成", "input[placeholder*='标题']"],
    ),
}


def get_flow(key: str) -> UploadFlow:
    try:
        return _FLOWS[key]
    except KeyError as exc:
        raise KeyError(f"平台 '{key}' 暂无上传流程定义，可在 flows.py 添加。") from exc


def login_url(key: str) -> str:
    return LOGIN_URLS.get(key, "about:blank")
