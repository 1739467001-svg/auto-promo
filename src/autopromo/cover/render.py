"""用 Pillow 把底图 + 文案渲染成封面图。

入口 render_cover()：给定底图（视频帧或 None）、目标比例、风格、文案，产出一张封面。
两种布局：
  - bottom：标题压在底部暗化区（抖音/视频号/西瓜/B站等短视频/横版常见）
  - card  ：顶部留白色卡片写标题，底图在下（小红书笔记风）
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..platforms import CoverStyle

# 各比例对应的输出像素尺寸
_RATIO_SIZE: dict[str, tuple[int, int]] = {
    "16:9": (1920, 1080),
    "4:3": (1440, 1080),
    "3:4": (1080, 1440),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
}


def ratio_size(ratio: str) -> tuple[int, int]:
    if ratio not in _RATIO_SIZE:
        raise ValueError(f"不支持的封面比例 '{ratio}'，可选：{', '.join(_RATIO_SIZE)}")
    return _RATIO_SIZE[ratio]


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _text_w(font: ImageFont.FreeTypeFont, s: str) -> int:
    if not s:
        return 0
    box = font.getbbox(s)
    return box[2] - box[0]


def _wrap(font: ImageFont.FreeTypeFont, text: str, max_w: int) -> list[str]:
    """按像素宽度折行。中文逐字、英文整词，兼顾两者。"""
    lines: list[str] = []
    cur = ""
    token = ""

    def flush_token():
        nonlocal cur, token
        if not token:
            return
        if _text_w(font, cur + token) <= max_w:
            cur += token
        else:
            if cur:
                lines.append(cur)
            cur = token
        token = ""

    for ch in text:
        if ch == "\n":
            flush_token()
            lines.append(cur)
            cur = ""
            continue
        if ch.isascii() and not ch.isspace():
            token += ch
            continue
        # 中文或空格：先结算英文 token，再处理当前字符
        flush_token()
        if ch == " ":
            if _text_w(font, cur + " ") <= max_w:
                cur += " "
            continue
        if _text_w(font, cur + ch) <= max_w:
            cur += ch
        else:
            if cur:
                lines.append(cur)
            cur = ch
    flush_token()
    if cur:
        lines.append(cur)
    return lines or [""]


def _cover_crop(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """等比缩放后居中裁剪到目标尺寸（cover 行为）。"""
    tw, th = size
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    nw, nh = int(iw * scale + 0.5), int(ih * scale + 0.5)
    resized = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - tw) // 2, (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def _gradient_bg(size: tuple[int, int], accent: tuple[int, int, int]) -> Image.Image:
    """无视频帧时的兜底：从深色到强调色的竖向渐变。"""
    w, h = size
    top = (18, 18, 24)
    bot = tuple(int(c * 0.55 + 18) for c in accent)
    base = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        base.putpixel(
            (0, y),
            tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)),
        )
    return base.resize(size)


def _bottom_scrim(size: tuple[int, int], strength: int) -> Image.Image:
    """底部向上的黑色渐变遮罩（RGBA），让压底文字清晰。"""
    w, h = size
    grad = Image.new("L", (1, h), 0)
    start = int(h * 0.40)
    for y in range(h):
        if y < start:
            a = 0
        else:
            a = int(strength * (y - start) / max(1, h - start))
        grad.putpixel((0, y), min(255, a))
    alpha = grad.resize(size)
    scrim = Image.new("RGBA", size, (0, 0, 0, 0))
    scrim.putalpha(alpha)
    return scrim


def _draw_badge(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    accent: tuple[int, int, int],
) -> int:
    """画一个强调色圆角徽章，返回其高度。"""
    pad_x, pad_y = int(font.size * 0.55), int(font.size * 0.30)
    tw = _text_w(font, text)
    box_h = font.size + pad_y * 2
    x, y = xy
    draw.rounded_rectangle(
        [x, y, x + tw + pad_x * 2, y + box_h],
        radius=box_h // 2,
        fill=accent + (255,),
    )
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=(255, 255, 255, 255))
    return box_h


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    line_gap: float = 1.18,
    stroke: tuple[int, int, int] | None = None,
) -> int:
    """逐行绘制，返回总高度。"""
    lh = int(font.size * line_gap)
    sw = max(2, font.size // 18) if stroke else 0
    for i, line in enumerate(lines):
        draw.text(
            (x, y + i * lh),
            line,
            font=font,
            fill=fill + (255,),
            stroke_width=sw,
            stroke_fill=(stroke + (255,)) if stroke else None,
        )
    return lh * len(lines)


def render_cover(
    *,
    out_path: Path,
    ratio: str,
    style: CoverStyle,
    title: str,
    english: str,
    chinese: str,
    background: Image.Image | None,
    font_path: str,
) -> Path:
    size = ratio_size(ratio)
    w, h = size

    if background is not None:
        base = _cover_crop(background, size).convert("RGBA")
    else:
        base = _gradient_bg(size, style.accent).convert("RGBA")

    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(base)

    margin = int(w * 0.06)
    title_size = int(h * (0.085 if ratio == "16:9" else 0.072))
    sub_size = int(title_size * 0.5)
    badge_size = int(title_size * 0.42)

    f_title = _font(font_path, title_size)
    f_sub = _font(font_path, sub_size)
    f_badge = _font(font_path, badge_size)

    if style.layout == "card":
        # 顶部白色卡片写标题（小红书笔记风）
        card_h = int(h * 0.34)
        card = Image.new("RGBA", (w, card_h), (255, 255, 255, 245))
        canvas.alpha_composite(card, (0, 0))
        draw = ImageDraw.Draw(canvas)
        y = margin
        y += _draw_badge((draw), (margin, y), style.badge_text, f_badge, style.accent) + int(margin * 0.5)
        title_lines = _wrap(f_title, title, w - margin * 2)[:3]
        y += _draw_lines(draw, margin, y, title_lines, f_title, style.title_color)
        # 卡片底部一条强调色细线 + 双语钩子
        line_y = card_h - int(margin * 0.4)
        draw.rectangle([margin, line_y, margin + int(w * 0.16), line_y + max(4, h // 240)], fill=style.accent + (255,))
        if english or chinese:
            sub = f"{english}  {chinese}".strip()
            _draw_lines(draw, margin, card_h + int(margin * 0.4),
                        _wrap(f_sub, sub, w - margin * 2)[:2], f_sub, (255, 255, 255), stroke=(0, 0, 0))
    else:
        # bottom：底部暗化 + 压字
        canvas.alpha_composite(_bottom_scrim(size, style.scrim))
        draw = ImageDraw.Draw(canvas)
        # 顶部徽章
        _draw_badge(draw, (margin, margin), style.badge_text, f_badge, style.accent)

        # 自底向上排：先算各块高度
        title_lines = _wrap(f_title, title, w - margin * 2)[:3]
        sub_text = f"{english}".strip()
        sub_cn = f"{chinese}".strip()
        title_h = int(title_size * 1.18) * len(title_lines)
        sub_lines = _wrap(f_sub, sub_text, w - margin * 2)[:1] if sub_text else []
        cn_lines = _wrap(f_sub, sub_cn, w - margin * 2)[:1] if sub_cn else []
        sub_h = int(sub_size * 1.25) * (len(sub_lines) + len(cn_lines))

        block_h = title_h + (int(margin * 0.5) + sub_h if sub_h else 0)
        y = h - margin - block_h

        y += _draw_lines(draw, margin, y, title_lines, f_title, style.title_color, stroke=(0, 0, 0))
        if sub_h:
            y += int(margin * 0.5)
            # 双语钩子前加一段强调色竖条
            bar_x = margin
            draw.rectangle([bar_x, y + 6, bar_x + max(6, w // 200), y + sub_h - 6], fill=style.accent + (255,))
            tx = bar_x + int(w * 0.025)
            if sub_lines:
                y += _draw_lines(draw, tx, y, sub_lines, f_sub, style.accent, stroke=(0, 0, 0))
            if cn_lines:
                _draw_lines(draw, tx, y, cn_lines, f_sub, (235, 235, 235), stroke=(0, 0, 0))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out_path, "JPEG", quality=90)
    return out_path
