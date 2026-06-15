# auto-promo · 英语学习视频自动化分发工作流

把一条**已配好中英双语字幕的视频** + 一个**文案来源链接** + **目标平台**喂进来，自动产出：

1. **各平台定制文案 + 标题**（按平台调性改写，调 Claude 生成）
2. **封面图**：每个平台一张**专属风格封面**（迎合各平台调性）+ 三张通用封面（16:9 / 4:3 / 3:4）
3. 通过**浏览器自动化**把视频 + 封面 + 文案送到各平台（复用你已登录的浏览器）

> 内容定位：转载精品外语视频 + 自制中英字幕，做成英语学习素材。**转载内容如实标注**（B 站等会自动勾选「转载」），不冒充原创骗激励。

---

## 它是怎么跑的

```
input/ 里的视频  ──┐
文案来源链接     ──┼─►  抓链接 → Claude 写各平台文案 → 抽帧+Pillow 出封面 ──►  output/<时间>/
目标平台         ──┘                                                          ├─ content.md   (人工复制用)
                                                                              ├─ content.json (机器可读)
                                                                              └─ covers/      (各平台 + 通用封面)
                                                                                     │
                                                          Playwright 复用已登录浏览器 ─┘──►  各平台上传页填好内容
```

默认**只填好内容、停在「发布」按钮前**，由你人工点最后一下（`auto_submit: false`），确认稳定后再逐平台打开自动发布。

---

## 两种用法

| 用法 | 文案谁写 | 需要 API Key | 需要浏览器自动化 |
|---|---|---|---|
| **A. 在 Claude Code App 里用（推荐）** | 我（App 里的 Claude）直接写 | ❌ 不需要 | ❌ 你手动上传 |
| B. 全自动 | 工作流调 Claude API 写 | ✅ 需要 | ✅ Playwright 发布 |

下面先讲推荐的 A，再讲 B。

---

## 安装

需要 Python 3.10+。最小安装（用法 A，只产出文案+封面、手动上传）：

```bash
pip install Pillow imageio-ffmpeg PyYAML
cp config.example.yaml config.yaml
```

> 用法 A **不需要** `anthropic`（不调 API）、也**不需要** `playwright`（不自动发布）。
> 想用全自动（B）再装全量：`pip install -r requirements.txt && playwright install chromium`，并 `export ANTHROPIC_API_KEY=sk-ant-...`。

---

## 用法 A：在 Claude Code App 里用（推荐）

文案由我直接写，无需 API Key，你拿到封面+文案后手动上传。流程：

1. 把配好中英字幕的视频丢进 `input/`，告诉我**链接**和**要发的平台**，让我启动。
2. 我用 WebFetch 看链接、按各平台要求**写好一份文案 JSON**（`content.json`）。
3. 我帮你跑：
   ```bash
   python -m autopromo run --content content.json --platforms douyin,xiaohongshu,bilibili --no-publish
   ```
4. 去 `output/<时间戳>/` 拿 `content.md`（每个平台：用哪张封面 + 标题 + 简介）和 `covers/`，手动上传。

想自己照着填文案，可先生成带各平台要求的模板：

```bash
python -m autopromo template --platforms douyin,xiaohongshu,bilibili --out content.json
```

---

## 用法 B：全自动（调 API 写文案 + 浏览器自动发布）

需先 `pip install -r requirements.txt && playwright install chromium` 和 `export ANTHROPIC_API_KEY=...`。

### 首次：登录各平台

工作流复用一个**持久化浏览器 profile**（路径见 `config.yaml` 的 `browser_profile_dir`）。
第一次需要在这个 profile 里手动把各平台登录好，cookie 会被保存，之后自动复用：

```bash
python -m autopromo login douyin        # 打开抖音创作中心登录页，扫码登录后回终端按回车
python -m autopromo login xiaohongshu
python -m autopromo login shipinhao
# … 你要发的每个平台都登录一次
```

支持的平台：

```bash
python -m autopromo platforms
```

| key | 平台 | 主封面 | 说明 |
|---|---|---|---|
| `douyin` | 抖音 | 3:4 | 主战场，靠流量 |
| `xiaohongshu` | 小红书 | 3:4 | 最适合英语学习，笔记风封面 |
| `shipinhao` | 视频号 | 3:4 | 有创作分成 |
| `xigua` | 西瓜视频 | 16:9 | 横版中视频计划 |
| `toutiao` | 今日头条 | 16:9 | 与西瓜打通 |
| `bilibili` | B站 | 16:9 | 标转载，当口碑阵地 |

---

### 启动工作流（全自动）

把配好中英字幕的视频丢进 `input/`，然后发"启动指令"：

```bash
# 发到配置里启用的平台
python -m autopromo run --link "https://你的文案来源链接"

# 或临时指定平台与视频
python -m autopromo run \
    --link "https://你的文案来源链接" \
    --platforms douyin,xiaohongshu,bilibili \
    --video myclip.mp4
```

常用开关：

- `--no-publish`：**只产出**文案 + 封面（不开浏览器），适合先看产物
- `--keep-open`：发布后**保持浏览器打开**，方便你核对、处理验证码、手动点发布
- `--video`：指定视频；缺省取 `input/` 里**最新**的视频文件
- `--platforms`：逗号分隔；缺省用 `config.yaml` 里 `enabled: true` 的平台

产物在 `output/<时间戳>/`：`content.md`（直接复制）、`content.json`、`covers/`，以及发布时的 `debug/` 截图（每步一张，便于排查）。

---

## 安全闸（重要）

- `publish.auto_submit`（全局）和 `platforms.<平台>.auto_submit`（单平台）**两者都为 true** 才会真正点发布，默认都 `false`。
- 建议先全程 `auto_submit: false` + `--keep-open`，盯着跑顺了，再单个平台打开自动发布。

---

## 目录结构

```
src/autopromo/
├── cli.py            命令行入口（run / login / platforms）
├── config.py         读取 config.yaml
├── platforms.py      ★ 平台注册表：各平台封面风格/文案口吻/是否标转载（单一事实来源）
├── pipeline.py       主流水线：识别视频→抓链接→写文案→出封面→组装待发布包
├── models.py         数据模型
├── content/
│   ├── source.py     抓取文案来源链接
│   └── generator.py  调 Claude 生成各平台文案（Opus 4.8 + adaptive thinking）
├── cover/
│   ├── frames.py     从视频抽最清晰的一帧（imageio-ffmpeg，无需系统 ffmpeg）
│   ├── render.py     Pillow 渲染封面（横/竖版、压底/笔记卡片两种布局）
│   └── builder.py    出"各平台专属 + 三张通用"封面
└── publish/
    ├── browser.py    Playwright 持久化上下文（复用登录态）
    ├── flow.py       通用上传执行器
    ├── flows.py      ★ 各平台上传页 URL + 选择器（平台改版时改这里）
    └── publisher.py  发布编排
```

想加平台 / 改封面风格 / 改文案口吻 → 改 `platforms.py`；
平台前端改版导致定位不到元素 → 改 `publish/flows.py` 里的候选选择器。

---

## 已知限制 / 注意

- **平台选择器会过时**：`publish/flows.py` 里的选择器是合理初值。各平台创作中心前端改版频繁，首次实跑请配合 `--keep-open` 和 `output/<时间>/debug/` 截图，按需在 `flows.py` 补选择器。
- **风控**：自动化上传有被风控/要求验证码的可能。`headless: false` + 适当 `slow_mo_ms` 更稳；遇验证码用 `--keep-open` 人工过。
- **登录态**：`browser-profiles/` 含 cookie，已被 `.gitignore` 忽略，**切勿提交或外泄**。
- **写文案模型**：默认 `claude-opus-4-8`（最强）；想省钱可在 `config.yaml` 改成 `claude-sonnet-4-6`。
- 本工具用于你已获授权/合规的转载二创与知识分享；请遵守各平台规则，转载如实标注来源。
