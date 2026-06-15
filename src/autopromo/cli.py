"""命令行入口。

启动工作流（产出 + 可选发布）：
    python -m autopromo run --link <文案来源链接> [--platforms douyin,xiaohongshu] \
        [--video xxx.mp4] [--no-publish] [--keep-open]

首次登录某平台（cookie 存进持久化 profile）：
    python -m autopromo login douyin

查看支持的平台：
    python -m autopromo platforms
"""

from __future__ import annotations

import argparse
import sys

from .config import load_config
from .platforms import PLATFORMS


def _resolve_platforms(cfg, arg: str | None) -> list[str]:
    if arg:
        keys = [k.strip() for k in arg.split(",") if k.strip()]
    else:
        keys = cfg.enabled_platforms()
    unknown = [k for k in keys if k not in PLATFORMS]
    if unknown:
        raise SystemExit(f"未知平台：{', '.join(unknown)}；可选：{', '.join(PLATFORMS)}")
    if not keys:
        raise SystemExit("没有选择任何平台。用 --platforms 指定，或在 config.yaml 里启用。")
    return keys


def cmd_run(args) -> int:
    cfg = load_config(args.config)
    platform_keys = _resolve_platforms(cfg, args.platforms)
    print(f"目标平台：{', '.join(platform_keys)}")

    from .pipeline import produce

    packages, run_dir = produce(
        cfg,
        link=args.link,
        platform_keys=platform_keys,
        video_path=args.video,
        content_spec=args.content,
    )

    do_publish = args.publish and cfg.publish_enabled
    if not do_publish:
        print("\n仅产出模式：未发布。物料见上面的输出目录，可人工上传。")
        print(f"  封面 + 文案：{run_dir}")
        return 0

    print("\n开始浏览器自动化发布…")
    from .publish.publisher import publish_packages

    debug_dir = run_dir / "debug"
    results = publish_packages(
        cfg, packages, debug_dir=debug_dir, keep_open=args.keep_open
    )

    print("\n==== 发布结果 ====")
    for r in results:
        state = "已发布" if r.submitted else ("已就绪(待人工发布)" if r.ok else "失败")
        print(f"  {r.platform:12s} {state}  {r.message}")
    return 0 if all(r.ok for r in results) else 1


def cmd_login(args) -> int:
    cfg = load_config(args.config)
    if args.platform not in PLATFORMS:
        raise SystemExit(f"未知平台 {args.platform}；可选：{', '.join(PLATFORMS)}")
    from .publish.publisher import open_login

    open_login(cfg, args.platform)
    return 0


def cmd_template(args) -> int:
    cfg = load_config(args.config)
    platform_keys = _resolve_platforms(cfg, args.platforms)
    from .pipeline import write_template

    out = write_template(args.out, platform_keys)
    print(f"已生成文案模板：{out}")
    print("按里面 _guidance 的各平台要求填好 cover 与 platforms，再用：")
    print(f"  python -m autopromo run --content {out} --platforms {','.join(platform_keys)} --no-publish")
    return 0


def cmd_platforms(args) -> int:
    print("支持的平台：")
    for k, p in PLATFORMS.items():
        repost = "，标转载" if p.mark_repost else ""
        print(f"  {k:12s} {p.name}  封面{p.ratio}{repost} —— {p.notes}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autopromo", description="英语学习视频自动化分发工作流")
    parser.add_argument("--config", default=None, help="配置文件路径（默认 config.yaml）")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="启动工作流：产出文案/封面并发布")
    p_run.add_argument("--link", default="", help="文案来源超链接（仅记录用；--content 模式可省）")
    p_run.add_argument("--content", default=None,
                       help="已写好的文案 JSON（推荐：在 Claude Code 里我直接写好），提供后跳过抓链接与 API")
    p_run.add_argument("--platforms", default=None, help="逗号分隔的平台，缺省用配置里启用的")
    p_run.add_argument("--video", default=None, help="指定视频文件，缺省取 input 里最新的")
    p_run.add_argument("--no-publish", dest="publish", action="store_false",
                       help="只产出文案/封面，不自动发布")
    p_run.add_argument("--keep-open", action="store_true",
                       help="发布后保持浏览器打开，便于人工核对/手动发布")
    p_run.set_defaults(publish=True, func=cmd_run)

    p_login = sub.add_parser("login", help="打开某平台登录页，首次手动登录")
    p_login.add_argument("platform", help="平台 key，如 douyin")
    p_login.set_defaults(func=cmd_login)

    p_tpl = sub.add_parser("template", help="生成文案模板（含各平台要求），照着填")
    p_tpl.add_argument("--platforms", default=None, help="逗号分隔的平台，缺省用配置里启用的")
    p_tpl.add_argument("--out", default="content.json", help="模板输出路径")
    p_tpl.set_defaults(func=cmd_template)

    p_plat = sub.add_parser("platforms", help="列出支持的平台")
    p_plat.set_defaults(func=cmd_platforms)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
