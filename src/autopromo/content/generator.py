"""调用 Claude，一次性产出封面文案 + 各平台文案。

为省 token，一次 API 调用返回一个 JSON：
  - cover：封面用的短标题 + 一句英文学习钩子 + 中文翻译
  - platforms：每个目标平台的 标题 / 正文 / 话题标签（各按平台口吻定制）
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import anthropic

from ..models import PlatformContent, SourceMaterial
from ..platforms import get_profile


@dataclass
class GeneratedBundle:
    cover_title: str
    cover_english: str
    cover_chinese: str
    per_platform: dict[str, PlatformContent]


_SYSTEM = (
    "你是一名资深的中文新媒体运营，擅长把'外语视频 + 中英双语字幕'的英语学习内容，"
    "针对不同平台改写成最贴合该平台调性的标题与文案。"
    "你深谙各平台规则：转载内容如实标注，绝不写夸大或诱导性违规文案。"
    "你只输出符合要求的 JSON，不输出任何多余文字。"
)


def _build_prompt(
    source: SourceMaterial,
    video_name: str,
    platform_keys: list[str],
    persona: str,
) -> str:
    lines: list[str] = []
    lines.append("# 任务")
    lines.append(
        "根据下面的【素材】，为指定平台分别生成发布文案，并生成一套封面文案。"
    )
    lines.append("")
    if persona:
        lines.append("# 博主人设/统一口径")
        lines.append(persona)
        lines.append("")

    lines.append("# 素材")
    lines.append(f"- 视频文件名：{video_name}")
    if source.fetched_ok:
        lines.append(f"- 来源链接：{source.url}")
        if source.title:
            lines.append(f"- 来源标题：{source.title}")
        if source.text:
            lines.append("- 来源正文（节选）：")
            lines.append(source.text[:4000])
    else:
        lines.append(f"- 来源链接：{source.url}（抓取失败：{source.note}）")
        lines.append("  → 请主要依据视频文件名与人设，围绕'英语学习/精品外语视频'立意。")
    lines.append("")

    lines.append("# 目标平台及各自要求")
    for key in platform_keys:
        p = get_profile(key)
        repost = "需要在文案中体现这是转载并自制字幕、标注来源" if p.mark_repost else "无需特别声明转载"
        lines.append(
            f"- {key}（{p.name}）：标题≤{p.title_max}字；{p.copy_style} "
            f"话题标签：{p.hashtag_hint}。{repost}。"
        )
    lines.append("")

    lines.append("# 封面文案要求")
    lines.append(
        "- cover_title：封面主标题，中文，≤14字，抓人、点出'精品/学英语'，不要标点堆砌。"
    )
    lines.append(
        "- cover_english：一句来自视频主题的地道英文短句（学习钩子），≤8个单词。"
    )
    lines.append("- cover_chinese：上面英文的自然中文翻译，≤16字。")
    lines.append("")

    lines.append("# 输出格式（严格 JSON，键名固定，不要 markdown 代码块）")
    schema = {
        "cover": {
            "cover_title": "字符串",
            "cover_english": "字符串",
            "cover_chinese": "字符串",
        },
        "platforms": {
            key: {"title": "字符串", "body": "字符串", "hashtags": ["字符串"]}
            for key in platform_keys
        },
    }
    lines.append(json.dumps(schema, ensure_ascii=False, indent=2))

    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    """从模型输出里稳妥地取出 JSON 对象。"""
    text = text.strip()
    # 去掉可能的 ```json ... ``` 包裹
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    # 取第一个 { 到最后一个 }
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def generate(
    *,
    source: SourceMaterial,
    video_name: str,
    platform_keys: list[str],
    persona: str = "",
    model: str = "claude-opus-4-8",
    effort: str = "high",
    api_key: str | None = None,
) -> GeneratedBundle:
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    prompt = _build_prompt(source, video_name, platform_keys, persona)

    # 用 streaming + get_final_message，规避大输出时的 HTTP 超时；adaptive thinking。
    with client.messages.stream(
        model=model,
        max_tokens=8000,
        system=_SYSTEM,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise RuntimeError("Claude 拒绝了本次文案生成请求（stop_reason=refusal）。")

    text = "".join(b.text for b in message.content if b.type == "text")
    data = _extract_json(text)

    cover = data.get("cover", {})
    per_platform: dict[str, PlatformContent] = {}
    for key in platform_keys:
        node = (data.get("platforms") or {}).get(key, {})
        per_platform[key] = PlatformContent(
            platform=key,
            title=str(node.get("title", "")).strip(),
            body=str(node.get("body", "")).strip(),
            hashtags=[str(t).lstrip("#").strip() for t in node.get("hashtags", []) if str(t).strip()],
        )

    return GeneratedBundle(
        cover_title=str(cover.get("cover_title", "")).strip(),
        cover_english=str(cover.get("cover_english", "")).strip(),
        cover_chinese=str(cover.get("cover_chinese", "")).strip(),
        per_platform=per_platform,
    )
