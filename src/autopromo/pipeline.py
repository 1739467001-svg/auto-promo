"""主流水线：把"视频 + 链接 + 平台"产出文案/标题/封面，并组装待发布包。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import Config
from .content.generator import GeneratedBundle, generate
from .content.source import fetch_source
from .content.spec import load_spec, write_template
from .cover.builder import build_covers
from .models import PublishPackage, VideoAsset
from .platforms import get_profile

_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm", ".m4v"}


def find_video(input_dir: Path, explicit: str | None = None) -> VideoAsset:
    """识别要发布的视频：显式指定优先，否则取 input 文件夹里最新的视频文件。"""
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = (input_dir / explicit).resolve()
        if not p.exists():
            raise FileNotFoundError(f"指定的视频不存在：{p}")
        return VideoAsset(path=p)

    if not input_dir.exists():
        raise FileNotFoundError(f"input 文件夹不存在：{input_dir}")
    vids = [
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _VIDEO_EXTS
    ]
    if not vids:
        raise FileNotFoundError(
            f"{input_dir} 里没有视频文件（支持 {', '.join(sorted(_VIDEO_EXTS))}）。"
        )
    vids.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return VideoAsset(path=vids[0])


def _write_outputs(
    run_dir: Path,
    video: VideoAsset,
    link: str,
    bundle: GeneratedBundle,
    platform_keys: list[str],
    covers_index: dict,
) -> None:
    """落地一份人类可读 + 机器可读的产物清单。"""
    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "video": str(video.path),
        "source_link": link,
        "cover_text": {
            "title": bundle.cover_title,
            "english": bundle.cover_english,
            "chinese": bundle.cover_chinese,
        },
        "platforms": {
            k: {
                "name": get_profile(k).name,
                "title": c.title,
                "body": c.body,
                "hashtags": c.hashtags,
                "mark_repost": get_profile(k).mark_repost,
            }
            for k, c in bundle.per_platform.items()
        },
        "covers": covers_index,
    }
    (run_dir / "content.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 便于人工上传时"照着发"的 Markdown 清单
    platform_cover = covers_index.get("platform", {})
    md = [f"# 发布物料 · {video.path.name}", ""]
    md.append(f"- 视频：`{video.path}`")
    md.append(f"- 来源链接：{link}")
    md.append(f"- 封面文案：**{bundle.cover_title}** / {bundle.cover_english} · {bundle.cover_chinese}")
    md.append("")
    md.append("> 每个平台一段：用对应封面图 + 标题 + 简介。标题/简介可直接复制。")
    md.append("")
    for k, c in bundle.per_platform.items():
        p = get_profile(k)
        cover_path = platform_cover.get(k, "")
        cover_name = Path(cover_path).name if cover_path else "（无）"
        md.append(f"## {p.name}（{k}）")
        md.append(f"- 🖼 封面：`covers/{cover_name}`（{p.ratio}）")
        if p.mark_repost:
            md.append("- ⚠️ 发布时请勾选「转载/非原创」并填写来源链接")
        md.append(f"- 📌 标题（≤{p.title_max}字）：")
        md.append("")
        md.append(f"```\n{c.title}\n```")
        md.append("- 📝 简介：")
        md.append("")
        md.append(f"```\n{c.caption_with_tags()}\n```")
        md.append("")
    (run_dir / "content.md").write_text("\n".join(md), encoding="utf-8")


def produce(
    cfg: Config,
    *,
    link: str,
    platform_keys: list[str],
    video_path: str | None = None,
    content_spec: str | None = None,
    log=print,
) -> tuple[list[PublishPackage], Path]:
    """产出阶段：返回 (待发布包列表, 本次运行输出目录)。

    content_spec 提供时（推荐：在 Claude Code 里我直接写好文案），读取该 JSON，
    跳过抓链接与调用 API，全程不联网、不用 API Key。
    """
    video = find_video(cfg.input_dir, video_path)
    log(f"识别到视频：{video.path}")

    if content_spec:
        log(f"读取已写好的文案：{content_spec}（跳过抓链接与 API）")
        bundle = load_spec(content_spec, platform_keys)
    else:
        log("抓取文案来源链接…")
        source = fetch_source(link)
        if not source.fetched_ok:
            log(f"  · 链接抓取未成功：{source.note}（将基于视频与人设生成）")
        log(f"调用 {cfg.content_model} 生成各平台文案…")
        bundle = generate(
            source=source,
            video_name=video.path.name,
            platform_keys=platform_keys,
            persona=cfg.persona,
            model=cfg.content_model,
            effort=cfg.content_effort,
            api_key=cfg.anthropic_api_key,
        )

    run_dir = cfg.output_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    covers_dir = run_dir / "covers"
    log("生成封面（各平台专属 + 三张通用）…")
    platform_covers, standard_covers = build_covers(
        video=video.path,
        out_dir=covers_dir,
        platform_keys=platform_keys,
        standard_ratios=cfg.standard_ratios,
        title=bundle.cover_title or video.path.stem,
        english=bundle.cover_english,
        chinese=bundle.cover_chinese,
        font_path=cfg.font_regular,
    )

    covers_index = {
        "platform": {k: str(c.path) for k, c in platform_covers.items()},
        "standard": {c.ratio: str(c.path) for c in standard_covers},
    }
    _write_outputs(run_dir, video, link, bundle, platform_keys, covers_index)
    log(f"产物已输出到：{run_dir}")

    packages: list[PublishPackage] = []
    for k in platform_keys:
        profile = get_profile(k)
        packages.append(
            PublishPackage(
                platform=k,
                video=video.path,
                content=bundle.per_platform[k],
                cover=platform_covers[k],
                mark_repost=profile.mark_repost,
            )
        )
    return packages, run_dir
