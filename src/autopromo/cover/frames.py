"""从视频里抽一帧作为封面底图。

使用 imageio-ffmpeg 自带的 ffmpeg 二进制，无需系统安装 ffmpeg。
策略：在视频不同时间点各抽一帧，挑最"清晰"（拉普拉斯方差最大）的一张，
避免抽到黑场/转场糊帧。抽帧失败时回退到渐变底图，保证流程不中断。
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter

try:
    import imageio_ffmpeg

    _FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:  # pragma: no cover - 环境缺依赖时
    _FFMPEG = None


def probe_duration(video: Path) -> float | None:
    """用 ffmpeg 跑一遍读 stderr 里的 Duration，估算时长（秒）。"""
    if not _FFMPEG:
        return None
    try:
        proc = subprocess.run(
            [_FFMPEG, "-i", str(video)],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", proc.stderr)
    if not m:
        return None
    h, mm, ss = m.groups()
    return int(h) * 3600 + int(mm) * 60 + float(ss)


def _grab(video: Path, ts: float, out: Path) -> Image.Image | None:
    try:
        subprocess.run(
            [
                _FFMPEG, "-y", "-ss", f"{ts:.2f}", "-i", str(video),
                "-frames:v", "1", "-q:v", "2", str(out),
            ],
            capture_output=True,
            timeout=60,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    if not out.exists() or out.stat().st_size == 0:
        return None
    try:
        return Image.open(out).convert("RGB")
    except Exception:
        return None


def _sharpness(img: Image.Image) -> float:
    """近似清晰度：缩小后取边缘强度的方差，越大越清晰。"""
    small = img.convert("L").resize((160, 160))
    edges = small.filter(ImageFilter.FIND_EDGES)
    hist = edges.histogram()
    total = sum(hist) or 1
    mean = sum(i * h for i, h in enumerate(hist)) / total
    var = sum(((i - mean) ** 2) * h for i, h in enumerate(hist)) / total
    return var


def best_frame(video: Path, samples: int = 5) -> Image.Image | None:
    """在视频中均匀采样若干帧，返回最清晰的一帧。无法抽帧时返回 None。"""
    if not _FFMPEG or not video.exists():
        return None

    dur = probe_duration(video)
    if dur and dur > 1:
        # 跳过片头片尾，在 10%~85% 之间均匀取点
        lo, hi = dur * 0.10, dur * 0.85
        timestamps = [lo + (hi - lo) * i / max(1, samples - 1) for i in range(samples)]
    else:
        timestamps = [1.0, 3.0, 6.0, 10.0, 15.0][:samples]

    best: Image.Image | None = None
    best_score = -1.0
    with tempfile.TemporaryDirectory() as td:
        for i, ts in enumerate(timestamps):
            frame = _grab(video, ts, Path(td) / f"f{i}.jpg")
            if frame is None:
                continue
            score = _sharpness(frame)
            if score > best_score:
                best_score, best = score, frame.copy()
    return best
