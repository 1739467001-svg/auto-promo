"""读取 config.yaml，提供带默认值的配置访问。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PlatformToggle:
    enabled: bool = False
    auto_submit: bool = False


@dataclass
class Config:
    raw: dict[str, Any]
    root: Path

    # ---- paths ----
    @property
    def input_dir(self) -> Path:
        return self._path("paths.input_dir", "./input")

    @property
    def output_dir(self) -> Path:
        return self._path("paths.output_dir", "./output")

    @property
    def browser_profile_dir(self) -> Path:
        return self._path("paths.browser_profile_dir", "./browser-profiles/default")

    # ---- content ----
    @property
    def content_model(self) -> str:
        return self._get("content.model", "claude-opus-4-8")

    @property
    def content_effort(self) -> str:
        return self._get("content.effort", "high")

    @property
    def persona(self) -> str:
        return self._get("content.persona", "").strip()

    @property
    def anthropic_api_key(self) -> str | None:
        return os.environ.get("ANTHROPIC_API_KEY")

    # ---- cover ----
    @property
    def font_regular(self) -> str:
        return self._get(
            "cover.font_regular", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        )

    @property
    def font_bold(self) -> str:
        return self._get("cover.font_bold", self.font_regular)

    @property
    def standard_ratios(self) -> list[str]:
        return list(self._get("cover.standard_ratios", ["16:9", "4:3", "3:4"]))

    # ---- publish ----
    @property
    def publish_enabled(self) -> bool:
        return bool(self._get("publish.enabled", True))

    @property
    def headless(self) -> bool:
        return bool(self._get("publish.headless", False))

    @property
    def global_auto_submit(self) -> bool:
        return bool(self._get("publish.auto_submit", False))

    @property
    def slow_mo_ms(self) -> int:
        return int(self._get("publish.slow_mo_ms", 300))

    def platform_toggle(self, key: str) -> PlatformToggle:
        node = self._get(f"platforms.{key}", {}) or {}
        return PlatformToggle(
            enabled=bool(node.get("enabled", False)),
            # 平台级 auto_submit 与全局 auto_submit 取"与"，双保险防误发
            auto_submit=bool(node.get("auto_submit", False)) and self.global_auto_submit,
        )

    def enabled_platforms(self) -> list[str]:
        node = self._get("platforms", {}) or {}
        return [k for k, v in node.items() if (v or {}).get("enabled")]

    # ---- helpers ----
    def _get(self, dotted: str, default: Any = None) -> Any:
        cur: Any = self.raw
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def _path(self, dotted: str, default: str) -> Path:
        raw = self._get(dotted, default)
        p = Path(raw).expanduser()
        return p if p.is_absolute() else (self.root / p).resolve()


def load_config(path: str | Path | None = None) -> Config:
    """加载配置。未指定时优先 config.yaml，回退 config.example.yaml。"""
    if path is not None:
        cfg_path = Path(path)
    else:
        for cand in ("config.yaml", "config.example.yaml"):
            if Path(cand).exists():
                cfg_path = Path(cand)
                break
        else:
            cfg_path = Path("config.yaml")  # 触发下面的报错

    if not cfg_path.exists():
        raise FileNotFoundError(
            f"找不到配置文件 {cfg_path}。请先 `cp config.example.yaml config.yaml` 并按需修改。"
        )

    with cfg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return Config(raw=raw, root=cfg_path.resolve().parent)
