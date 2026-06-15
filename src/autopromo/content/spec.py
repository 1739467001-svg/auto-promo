"""文案规格（content spec）：把"已写好的文案"喂进流水线，无需调用 API。

主用法（在 Claude Code App 里）：由我（Claude）按各平台要求亲手写好一份 JSON，
然后流水线直接读它来出封面 / 清单，全程不联网、不用 API Key。

JSON 结构：
{
  "cover":     {"title": "...", "english": "...", "chinese": "..."},
  "platforms": {
    "douyin": {"title": "...", "body": "...", "hashtags": ["...", "..."]},
    ...
  }
}
顶层可有 "_guidance" 键（模板里给我看的提示），读取时忽略。
"""

from __future__ import annotations

import json
from pathlib import Path

from ..models import PlatformContent
from ..platforms import get_profile
from .generator import GeneratedBundle


def load_spec(path: str | Path, platform_keys: list[str]) -> GeneratedBundle:
    """读取文案 JSON，校验目标平台齐全，返回 GeneratedBundle。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"找不到文案文件：{p}")
    data = json.loads(p.read_text(encoding="utf-8"))

    cover = data.get("cover", {}) or {}
    platforms = data.get("platforms", {}) or {}

    missing = [k for k in platform_keys if k not in platforms]
    if missing:
        raise ValueError(
            f"文案文件缺少这些平台的内容：{', '.join(missing)}（请在 platforms 下补齐）"
        )

    per_platform: dict[str, PlatformContent] = {}
    for k in platform_keys:
        node = platforms[k] or {}
        title = str(node.get("title", "")).strip()
        body = str(node.get("body", "")).strip()
        if not title or not body:
            raise ValueError(f"平台 {k} 的 title / body 不能为空。")
        per_platform[k] = PlatformContent(
            platform=k,
            title=title,
            body=body,
            hashtags=[str(t).lstrip("#").strip() for t in node.get("hashtags", []) if str(t).strip()],
        )

    return GeneratedBundle(
        cover_title=str(cover.get("title", "")).strip(),
        cover_english=str(cover.get("english", "")).strip(),
        cover_chinese=str(cover.get("chinese", "")).strip(),
        per_platform=per_platform,
    )


def write_template(path: str | Path, platform_keys: list[str]) -> Path:
    """写一份带"各平台要求提示"的空模板，便于照着填。"""
    guidance: dict[str, dict] = {}
    platforms_skel: dict[str, dict] = {}
    for k in platform_keys:
        p = get_profile(k)
        guidance[k] = {
            "平台": p.name,
            "标题上限": p.title_max,
            "口吻": p.copy_style,
            "话题标签": p.hashtag_hint,
            "需标转载": p.mark_repost,
        }
        platforms_skel[k] = {"title": "", "body": "", "hashtags": []}

    skeleton = {
        "_guidance": {
            "说明": "按 _guidance 里各平台要求填写下面 cover 与 platforms；_guidance 读取时忽略。",
            "cover": {
                "title": "封面主标题，中文 ≤14 字，抓人、点出精品/学英语",
                "english": "一句来自视频主题的地道英文短句 ≤8 词",
                "chinese": "上面英文的中文翻译 ≤16 字",
            },
            "platforms": guidance,
        },
        "cover": {"title": "", "english": "", "chinese": ""},
        "platforms": platforms_skel,
    }

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(skeleton, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
