"""抓取"文案来源链接"，提取标题与正文，作为写文案的原始素材。

只做尽力而为的轻量抓取：拿到标题 + 正文纯文本即可。
抓取失败不致命（返回 fetched_ok=False），文案仍可基于视频文件名与人设生成。
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from ..models import SourceMaterial

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

_MAX_TEXT = 6000  # 截断正文，避免喂太多 token


def fetch_source(url: str, timeout: int = 20) -> SourceMaterial:
    if not url or not re.match(r"^https?://", url):
        return SourceMaterial(
            url=url, fetched_ok=False, note="链接为空或不是 http(s) 地址，跳过抓取。"
        )

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return SourceMaterial(url=url, fetched_ok=False, note=f"抓取失败：{exc}")

    resp.encoding = resp.apparent_encoding or resp.encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    # 去掉脚本/样式/导航等噪声
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "form"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip() or title

    # 正文：优先 <article>，否则取正文区块文字
    container = soup.find("article") or soup.body or soup
    text = re.sub(r"\n{3,}", "\n\n", container.get_text("\n", strip=True))
    text = text[:_MAX_TEXT]

    return SourceMaterial(url=url, title=title, text=text, fetched_ok=True)
