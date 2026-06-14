"""贯穿整个流水线的数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class VideoAsset:
    """input 文件夹里识别到的、已配好中英字幕的视频。"""

    path: Path
    duration_sec: float | None = None  # 抽帧/估算时长用，未知则 None

    @property
    def stem(self) -> str:
        return self.path.stem


@dataclass
class SourceMaterial:
    """从"文案来源链接"抓回来的原始资料，喂给文案生成。"""

    url: str
    title: str = ""
    text: str = ""          # 正文纯文本（已去标签、截断到合理长度）
    fetched_ok: bool = True
    note: str = ""          # 抓取失败时的说明


@dataclass
class PlatformContent:
    """单个平台的成品文案。"""

    platform: str
    title: str
    body: str                       # 正文/简介
    hashtags: list[str] = field(default_factory=list)

    def caption_with_tags(self) -> str:
        """正文 + 话题标签，拼成大多数平台直接粘贴的简介。"""
        tags = " ".join(f"#{t.lstrip('#')}" for t in self.hashtags)
        return f"{self.body}\n\n{tags}".strip() if tags else self.body


@dataclass
class Cover:
    """一张生成好的封面图。"""

    path: Path
    ratio: str              # "16:9" / "4:3" / "3:4"
    style: str              # 风格名（平台 key 或 "generic"）
    platform: str | None = None  # 若是某平台专属封面则填平台 key


@dataclass
class PublishPackage:
    """某一平台的"待发布包"：视频 + 文案 + 该平台封面。"""

    platform: str
    video: Path
    content: PlatformContent
    cover: Cover
    mark_repost: bool = False       # 是否在平台上勾选"转载/非原创"


@dataclass
class PublishResult:
    platform: str
    ok: bool
    submitted: bool                 # 是否真正点了发布（auto_submit）
    message: str = ""
