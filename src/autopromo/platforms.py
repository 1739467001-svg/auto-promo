"""平台注册表。

每个平台一份 PlatformProfile，集中定义它的：
  - 封面比例与视觉风格（迎合各平台调性，做到"每个平台封面不一样"）
  - 文案口吻 / 标题长度（喂给 Claude 写文案时用）
  - 是否需要标注"转载/非原创"（B 站、百家号这类查搬运严的平台）

这是整套工作流里"平台个性化"的单一事实来源，加平台/改风格都改这里。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoverStyle:
    """封面视觉风格。颜色为 RGB 元组。"""

    name: str
    accent: tuple[int, int, int]          # 主题强调色（徽章/标题描边/色块）
    title_color: tuple[int, int, int]     # 主标题颜色
    badge_text: str                       # 左上/角标文案，体现平台调性
    # 底部暗化遮罩强度 0~255（越大底图越暗、字越清晰），竖版默认重一点
    scrim: int = 170
    # 布局：bottom = 标题压底（短视频常见）；card = 顶部留白卡片（小红书笔记风）
    layout: str = "bottom"


@dataclass(frozen=True)
class PlatformProfile:
    key: str
    name: str
    ratio: str                  # 该平台主封面比例
    cover: CoverStyle
    # 文案口吻，直接进 Claude 的 prompt
    copy_style: str
    title_max: int              # 标题字数上限（提示模型，不强制截断）
    mark_repost: bool = False   # 平台侧是否勾选"转载/非原创声明"
    hashtag_hint: str = ""      # 话题标签风格提示
    notes: str = ""             # 备注（人看的）


# ---- 各平台封面风格 ----------------------------------------------------------

_DOUYIN_STYLE = CoverStyle(
    name="douyin",
    accent=(254, 44, 85),       # 抖音红
    title_color=(255, 255, 255),
    badge_text="HOT 热点 · 中英精听",
    scrim=185,
    layout="bottom",
)

_XHS_STYLE = CoverStyle(
    name="xiaohongshu",
    accent=(255, 36, 66),       # 小红书红
    title_color=(40, 40, 50),
    badge_text="英语精读笔记",
    scrim=70,                   # 笔记风偏亮
    layout="card",
)

_SHIPINHAO_STYLE = CoverStyle(
    name="shipinhao",
    accent=(7, 193, 96),        # 微信绿
    title_color=(255, 255, 255),
    badge_text="中英字幕 · 精听",
    scrim=170,
    layout="bottom",
)

_XIGUA_STYLE = CoverStyle(
    name="xigua",
    accent=(255, 122, 0),       # 西瓜/头条橙
    title_color=(255, 255, 255),
    badge_text="原声 + 中英字幕",
    scrim=150,
    layout="bottom",
)

_TOUTIAO_STYLE = CoverStyle(
    name="toutiao",
    accent=(237, 64, 20),       # 头条红橙
    title_color=(255, 255, 255),
    badge_text="精选外语视频 · 中英字幕",
    scrim=150,
    layout="bottom",
)

_BILI_STYLE = CoverStyle(
    name="bilibili",
    accent=(251, 114, 153),     # B 站粉
    title_color=(255, 255, 255),
    badge_text="转载 · 字幕自制",   # 明确转载属性
    scrim=160,
    layout="bottom",
)


# ---- 平台注册 ----------------------------------------------------------------

PLATFORMS: dict[str, PlatformProfile] = {
    "douyin": PlatformProfile(
        key="douyin",
        name="抖音",
        ratio="3:4",
        cover=_DOUYIN_STYLE,
        copy_style=(
            "口吻：短视频钩子风，开头一句话制造好奇/痛点，强调'别人刷不到的精品'和'学英语'。"
            "结尾引导关注。语气年轻、口语化，可用 1~2 个 emoji。"
        ),
        title_max=55,
        mark_repost=False,
        hashtag_hint="3~5 个：#英语学习 #英语口语 #每日英语听力 + 1 个当下热点相关标签",
        notes="主战场，靠流量不靠激励。",
    ),
    "xiaohongshu": PlatformProfile(
        key="xiaohongshu",
        name="小红书",
        ratio="3:4",
        cover=_XHS_STYLE,
        copy_style=(
            "口吻：学习笔记/干货风，第一人称分享。正文用小标题或分点列出'这条视频能学到什么'，"
            "突出可收藏、可跟读。语气真诚，emoji 适量点缀。"
        ),
        title_max=20,
        mark_repost=False,
        hashtag_hint="6~8 个：#英语学习 #英语笔记 #英语口语 #外刊精读 #干货分享 等",
        notes="最适合英语学习，靠涨粉→带货/接广。",
    ),
    "shipinhao": PlatformProfile(
        key="shipinhao",
        name="视频号",
        ratio="3:4",
        cover=_SHIPINHAO_STYLE,
        copy_style=(
            "口吻：偏稳重、适合微信生态传播，强调'值得转发给想学英语的朋友'。"
            "正文简洁，1~2 句点出价值。"
        ),
        title_max=40,
        mark_repost=False,
        hashtag_hint="2~4 个：#英语学习 #英语 等",
        notes="有创作分成计划，值得做。",
    ),
    "xigua": PlatformProfile(
        key="xigua",
        name="西瓜视频",
        ratio="16:9",
        cover=_XIGUA_STYLE,
        copy_style=(
            "口吻：横版中视频风，标题信息量足、点明主题，正文像内容简介，"
            "说明视频讲了什么、适合谁看。偏正式一点。"
        ),
        title_max=30,
        mark_repost=False,
        hashtag_hint="3~5 个：#英语 #英语学习 #涨知识 等",
        notes="横版 16:9、时长>1min 走中视频计划。",
    ),
    "toutiao": PlatformProfile(
        key="toutiao",
        name="今日头条",
        ratio="16:9",
        cover=_TOUTIAO_STYLE,
        copy_style=(
            "口吻：资讯/科普标题党（不浮夸），正文像一段导读，"
            "信息密度高，利于搜索长尾。"
        ),
        title_max=30,
        mark_repost=False,
        hashtag_hint="3~5 个：#英语学习 #英语 #涨知识",
        notes="与西瓜打通中视频计划。",
    ),
    "bilibili": PlatformProfile(
        key="bilibili",
        name="B站",
        ratio="16:9",
        cover=_BILI_STYLE,
        copy_style=(
            "口吻：B 站学习区风格，亲切、带一点梗。正文说明这是转载并自制中英字幕，"
            "标注来源，引导三连。"
        ),
        title_max=40,
        mark_repost=True,           # B 站投稿如实标"转载"
        hashtag_hint="标签：英语学习 英语 字幕组 等（B 站用 tag 不用 #）",
        notes="当作品集/口碑阵地，标转载，不指望激励。",
    ),
}


def get_profile(key: str) -> PlatformProfile:
    try:
        return PLATFORMS[key]
    except KeyError as exc:
        raise KeyError(
            f"未知平台 '{key}'，已支持：{', '.join(PLATFORMS)}"
        ) from exc


def all_keys() -> list[str]:
    return list(PLATFORMS)
