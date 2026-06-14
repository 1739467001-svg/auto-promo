"""封面构建器：抽帧一次，复用底图渲染多张封面。

产出两类封面：
  1. 各平台专属封面：用该平台的比例 + 风格（做到每个平台封面不一样）
  2. 三张通用封面：16:9 / 4:3 / 3:4，中性风格，覆盖横版/通用/竖版平台
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from ..models import Cover
from ..platforms import CoverStyle, get_profile
from .frames import best_frame
from .render import render_cover

# 通用封面用的中性风格
_GENERIC_STYLE = CoverStyle(
    name="generic",
    accent=(255, 196, 0),
    title_color=(255, 255, 255),
    badge_text="中英字幕 · 英语精听",
    scrim=170,
    layout="bottom",
)


def build_covers(
    *,
    video: Path,
    out_dir: Path,
    platform_keys: list[str],
    standard_ratios: list[str],
    title: str,
    english: str,
    chinese: str,
    font_path: str,
) -> tuple[dict[str, Cover], list[Cover]]:
    """返回 (各平台封面 dict, 通用封面 list)。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    background: Image.Image | None = best_frame(video)

    platform_covers: dict[str, Cover] = {}
    for key in platform_keys:
        profile = get_profile(key)
        path = out_dir / f"cover_{key}_{profile.ratio.replace(':', 'x')}.jpg"
        render_cover(
            out_path=path,
            ratio=profile.ratio,
            style=profile.cover,
            title=title,
            english=english,
            chinese=chinese,
            background=background,
            font_path=font_path,
        )
        platform_covers[key] = Cover(
            path=path, ratio=profile.ratio, style=profile.cover.name, platform=key
        )

    standard_covers: list[Cover] = []
    for ratio in standard_ratios:
        path = out_dir / f"cover_generic_{ratio.replace(':', 'x')}.jpg"
        render_cover(
            out_path=path,
            ratio=ratio,
            style=_GENERIC_STYLE,
            title=title,
            english=english,
            chinese=chinese,
            background=background,
            font_path=font_path,
        )
        standard_covers.append(Cover(path=path, ratio=ratio, style="generic"))

    return platform_covers, standard_covers
