# Personal Growth OS

Personal Growth OS 是一个 **AI 成长日志系统**：把「今天到底干了啥」说清楚，让人**安心收尾**，并肯定「今天不是白过」。它在固定时间从浏览器、效率工具、IDE、AI 对话等处**只读采集**痕迹，调用你配置的 LLM 生成 Markdown 总结，可选推送到邮箱或企业微信；数据默认落在本机 `data/`。
目前支持的采集项有：
- **浏览器历史和主流平台（b 站、知乎）分析**（Edge/Chrome）
- **主流AI平台（ChatGPT、豆包、DeepSeek）对话标题分析**
- **cursor、vscodeIDE 使用记录分析**
- **TickTick 任务**（滴答清单）
- **小米运动健康**
## 项目是做什么的

### 想缓解什么

- **焦虑与脑力内耗**：温和地把散落线索串成一条**可读完的叙事**，减少「我是不是又荒废了」的反刍。
- **信息爆炸、缺少锚点**：多源痕迹在固定时间**收束成一份**总结（可读、可推邮箱），作为清晰的「昨日坐标」。

仓库里的默认证据维度与提示词偏 **AI/CS、保研升学** 等场景；你可在 **`config/`** 里改成自己关心的领域与口吻。


**下面从「快速开始」上手即可**；各字段含义、`config/` 怎么改、邮箱怎么配等，见文末 **[详细配置与自定义](#详细配置与自定义)**。

## 快速开始

### 1. 环境与依赖

建议使用 **Python 3.10+**。

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

- **可选**：若要在日报末尾自动贴「可视化报告」的长截图，需再安装 Chromium（与当前 venv 一致）：

  ```bash
  python -m playwright install chromium
  ```

### 2. 准备配置

```bash
cp config/settings.example.json config/settings.json
cp config/tool_switches.example.json config/tool_switches.json
```

### 3. 填入 LLM API Key（推荐环境变量）

```bash
export DEEPSEEK_API_KEY="your_key_here"
```

（变量名默认与 `settings.json` 里 `api.api_key_env` 一致；亦可仅在本地 `settings.json` 填写 `api.api_key`，勿提交公开仓库。）

### 4. 按需微调（初学可跳过）

- `config/settings.json`：时区、日报时间点、`user.nickname` 等。
- `config/tool_switches.json`：只把你想采集的项设为 `"enabled": true`。

更细的字段说明见后文 **「详细配置与自定义」**。

### 5. 跑一天试试

不推送通知（先验证采集 + 总结）：

```bash
python3 scripts/run_daily.py --date 2026-05-13 --no-notify
```

只采集、不调模型：

```bash
python3 scripts/run_daily.py --date 2026-05-13 --dry-run
```

**输出位置：**

- `data/events/YYYY-MM-DD-events.json` — 当日事件
- `data/summaries/YYYY-MM-DD-summary.md` — 当日 Markdown 总结

### 接下来你可以…

| 想做的事 | 命令或位置 |
|----------|------------|
| 开邮箱 / 企微推送 | 在 `settings.json` 里打开 `notifications`，详见后文 [邮箱（SMTP）](#邮箱推送配置smtp) |
| 每天自动生成 | macOS：后文 [定时任务](#定时任务macos) |
| 改总结语气与结构 | 编辑 `templates/daily_summary_prompt.md` |
| 单条提问 / Inbox 队列 | 后文 [问答与 Inbox](#问答与-inbox) |

---


### 项目特点

- **数据归属你**：事件与总结在本地；API Key 优先环境变量。
- **轻量可组合**：`tool_switches` 按需开采集器。
- **可演进协作**：欢迎 Issue / PR 扩展采集与文档。

## 功能一览

| 能力 | 说明 |
|------|------|
| **每日采集 + 总结** | `run_daily.py` 聚合当日事件，按提示词与成长维度生成 Markdown。 |
| **多源采集器** | 浏览器、资讯站、滴答专注、Cursor / VS Code、ChatGPT / 豆包 / DeepSeek 等（见下表）。 |
| **可选可视化** | HTML 报告 + Playwright 长截图附录到总结。 |
| **通知** | SMTP 邮件（可 Markdown→HTML + 内联图）、企业微信 Webhook。 |
| **问答与 Inbox** | `answer_reply.py`；`add_inbox_message.py` + `process_inbox.py` 批量回发。 |
| **定时（macOS）** | `install_launchd.py`：日报 + Inbox 轮询。 |
| **保留策略** | `data_retention.daily_summaries_keep_days` 清理旧总结。 |

## 支持的数据源（工具与平台）

以下为 `tool_switches` 中可调用的采集维度（键名以 `config/tool_switches.example.json` 为准）：

| 类别 | 平台 / 数据源 | 说明 |
|------|----------------|------|
| **浏览器** | Chrome、Edge、Safari | 只读复制本地历史库；不读 Cookie / 密码 / 页面正文。 |
| **资讯流** | 哔哩哔哩、知乎、小红书 | 从指定浏览器历史归纳访问。 |
| **生产力** | 滴答清单（专注） | 本地专注数据。 |
| **IDE** | Cursor、VS Code | Cursor 读本地 SQLite；VS Code 可按需扩展。 |
| **AI 对话** | ChatGPT、豆包、DeepSeek | 按对话线程 URL 过滤。 |
| **导入** | 手动 / 手机 / 小米运动健康等 | 见 `data/imports`、`data/mobile`、`data/health` 约定。 |

资讯与 AI 类常配 **`browsers`**，如 `["edge","chrome"]`。更多域名归类见 `tools/platforms.py`。

## 目录结构（简）

```text
config/          # settings、tool_switches、growth_dimensions（详见后文）
data/            # events、summaries、replies、inbox、imports、health、visual …
tools/           # 采集、LLM、通知、报告
scripts/         # run_daily、问答、Inbox、install_launchd …
templates/       # daily_summary_prompt.md 等
```

## 定时任务（macOS）

```bash
python3 scripts/install_launchd.py
launchctl load ~/Library/LaunchAgents/com.personal-growth-os.daily.plist
launchctl load ~/Library/LaunchAgents/com.personal-growth-os.inbox.plist
```

开场白话术等在 `settings.json` 的 `messages.daily_opening_hint`；总结结构在 `templates/daily_summary_prompt.md`。

## macOS 桌面应用 + DMG 打包

默认桌面端已改为 **原生 SwiftUI + AppKit 材质**（`macOS/DigitalDairyNative`）：使用 `NSVisualEffectView` 与系统 `Material` 叠加渐变，观感接近 macOS 的毛玻璃/液态层次；业务仍通过本机 `python3` 调用仓库内 `scripts/run_daily.py`（与原先逻辑一致）。

**从 DMG 安装后**：`Contents/Resources/app-runtime/` 内含 `scripts/`、`tools/` 等；配置与数据仍在 `~/Documents/DigitalDairy/`，**无需选择项目目录**。从源码调试时，应用会尝试自动识别仓库根目录，也可在界面里手动选择。

旧版 **Tkinter 桌面**（`app/desktop_app.py`）仍保留作参考。旧版 **py2app** 打包脚本见 `scripts/build_macos_dmg_py2app.sh`。

另有可选的状态栏脚本 `app/status_bar.py`（需自行 `pip install rumps`）。

### 1) 构建 `.dmg`（SwiftUI 原生壳 + Python 运行时）

需要本机已安装 **Xcode Command Line Tools** 或 **Xcode**（提供 `swift`）。

```bash
bash scripts/build_macos_dmg.sh
```

该脚本会：

- 用 SwiftPM 编译 `macOS/DigitalDairyNative`
- 通过 `scripts/bundle_app_runtime.sh` 将 **完整项目**（`scripts/`、`tools/`、`templates/`、`config/`、`app/`、`fig/`、`macOS/DigitalDairyNative/` 源码、`data/` 目录骨架，以及根目录 `README.md`、`requirements*.txt`、`setup.py`）同步到 `app-runtime/` 并打入 `Digital Dairy.app`
- 生成 `dist/Digital-Dairy.dmg`

安装后可在 `Digital Dairy.app` 的 **显示包内容 → Contents → Resources → app-runtime** 中浏览上述文件。个人运行数据与密钥仍仅在 `~/Documents/DigitalDairy`。

生成日报时，安装版会用系统 `python3`（或你放在 `PATH` 里的解释器）执行包内脚本；若需 `markdown` / `playwright` 等可选依赖，请在本机执行：

```bash
python3 -m pip install -r requirements.txt
```

### 2) 生成物

- `dist/Digital Dairy.app`
- `dist/Digital-Dairy.dmg`

### 3) 桌面应用功能

- **DMG 安装版**：数据与配置在 `~/Documents/DigitalDairy`（含 `state.json`），首次启动会自动从模板生成 `settings.json` / `tool_switches.json` 等；无需选择项目目录。
- **源码 / 调试运行**：在 Xcode 中打开 `macOS/DigitalDairyNative/Package.swift`，或执行 `cd macOS/DigitalDairyNative && swift run`；若未识别到仓库根，可在界面「选择项目目录…」指向克隆路径。
- 生成今日日报 / 仅采集（Dry Run），日志在窗口内展示；侧栏提供**表单化偏好设置**（常规、API、采集开关、通知、高级），以及 **Markdown 日报阅览** 与基于当日 `events.json` 的 **Swift Charts 嵌入式图表**（默认不再依赖 HTML/Playwright 截图附录；原生应用调用日报时会附加 `--no-visual-screenshots`）。
- 打开今日总结、在 Finder 中打开数据目录（安装版）或项目目录（开发版）。

旧版 Tk 入口（仍可用）：

```bash
python3 app/desktop_app.py
```

> 说明：日报任务会优先使用项目内 `.venv/bin/python3`，否则使用系统 `python3`（通过 `/usr/bin/env python3` 调用）。

### 4) 旧版 py2app（Tk 壳）打包

若仍需 Tkinter + py2app 的 `.app`：

```bash
bash scripts/build_macos_dmg_py2app.sh
```

## 问答与 Inbox

**单条：**

```bash
python3 scripts/answer_reply.py --question "我今天主要成长在哪里？"
```

（会结合 `data/` 下已有事件与总结作答。）

**队列：**

```bash
python3 scripts/add_inbox_message.py --channel email --text "今天最值得肯定的三件事是什么？"
python3 scripts/process_inbox.py
```

---

## 详细配置与自定义

### 个人设置速查（`config/settings.json`）

| 区块 | 作用 |
|------|------|
| `user` | `nickname` / `display_name`。 |
| `timezone` | 如 `Asia/Shanghai`。 |
| `schedule.time` | 日报参考时间、LaunchAgent / 开场文案用。 |
| `messages.daily_opening_hint` | 开场模板；支持 `{opening_time}`、`{nickname}`、`{user_name}`。 |
| `api` | `base_url`、`model`、温度、`max_tokens`；`api_key_env` / `api_key`。 |
| `templates.daily_prompt` | 总结提示词 Markdown 路径，默认 `templates/daily_summary_prompt.md`。 |
| `tool_switches_path` | 工具开关文件路径，默认 `config/tool_switches.json`。 |
| `data_retention` | 如 `daily_summaries_keep_days`。 |
| `visual_report` | 可视化 HTML 与截图参数（见下节「`settings.json` 常用字段」）。 |
| `notifications` | `email`、`wechat`。 |
| `replies.poll_minutes` | Inbox 轮询间隔。 |

**安全**：API Key 优先环境变量；**SMTP 密码、企微 Webhook 只放本地 `settings.json`，勿提交公开仓库。**

### `config/` 里有哪些文件

| 文件 | 作用 |
|------|------|
| `settings.example.json` | 全局设置模板 → 复制为 `settings.json`。 |
| `settings.json` | 你的本地设置。 |
| `tool_switches.example.json` | 采集器开关模板。 |
| `tool_switches.json` | 实际启用的数据源（路径由 `tool_switches_path` 指定）。 |
| `growth_dimensions.json` | 成长维度（标签 / 叙事结构）；可按人生阶段改写。 |

主要改 **`settings.json`**（模型、通知、时间）和 **`tool_switches.json`**（采什么）；**`growth_dimensions.json`** 管「事件归到哪些成长线」。

### `settings.json` 常用字段（扩展说明）

- **`user` / `timezone` / `schedule` / `messages`**：称呼、时区、收工时间、开场话术与占位符。
- **`api`**：兼容 OpenAI 式 `POST .../chat/completions`；密钥先读 `api_key_env`，再读 `api_key`。
- **`templates.daily_prompt`**：可改为自定义路径（如 `templates/my_prompt.md`）。
- **`tool_switches_path`**：相对项目根。若文件不存在，部分脚本可回退读 `settings.tools` 内联对象（结构与 `tool_switches.json` 相同）。
- **`data_retention.daily_summaries_keep_days`**：保留最近 N 天总结。
- **`replies.poll_minutes`**：与 LaunchAgent 搭配的 Inbox 间隔。
- **`visual_report`**：  
  - **`enabled`**：`false` 关闭可视化与附录截图链路。  
  - **`viewport_width` / `viewport_height` / `device_scale_factor`**：截图视口与像素密度。  
  - **`screenshot_stem`**：PNG 文件名前缀。  
  - **`cleanup_screenshot_dirs`**：是否清理旧截图目录（调试用可 `false`）。  
  - **`focus_goal_minutes`**、**`coding_lines_bar_cap`**：HTML 报告内图表参照（见 `visual_html_report`）。
- **`notifications.wechat`**：`enabled` + `webhook_url`；正文为 Markdown，长度会截断（见 `notifier.py`）。

使用非默认设置文件：

```bash
python3 scripts/run_daily.py --settings config/settings.json
```

### `tool_switches.json`

顶层键名与 `tools/registry.py` 中 `TOOL_REGISTRY` 一致；每项至少 **`enabled`**。常用附加字段：

| 键 | 含义 |
|----|------|
| `chrome` / `edge` / `safari` | 是否读对应浏览器历史。 |
| `bilibili_history` / `zhihu_history` / `xiaohongshu_history` | 可选 **`browsers`**。 |
| `chatgpt` / `doubao` / `deepseek` | 可选 **`browsers`**。 |
| `ticktick_focus` / `cursor` / `vscode` | 无需 `browsers`。 |
| `manual_imports` / `mobile_imports` | `data/imports`、`data/mobile` 等。 |
| `mi_health` | 可选 **`folders`**，如 `["data/health"]`。 |

### `growth_dimensions.json`

顶层 **`dimensions`** 数组。每项含：`id`、`name`、`description`、`keywords`（标题/主题匹配）、`hosts`（URL host 子串匹配）。未命中时落到 **`general_input`**（建议保留或自建兜底）。

与 **`templates.daily_prompt`** 同时修改，可统一「怎么分拣」和「怎么说」。

### 邮箱推送配置（SMTP）

日报与 `process_inbox` 使用 **`smtplib.SMTP_SSL`**，默认端口 **`465`**（需与邮箱服务商 SSL 发信端口一致）。

在 `config/settings.json` 的 `notifications.email` 中配置，例如：

```json
"notifications": {
  "email": {
    "enabled": true,
    "smtp_host": "smtp.example.com",
    "smtp_port": 465,
    "username": "you@example.com",
    "password": "你的授权码或应用专用密码",
    "from": "you@example.com",
    "to": "you@example.com"
  }
}
```

| 字段 | 说明 |
|------|------|
| `enabled` | `true` 才发信。 |
| `smtp_host` / `smtp_port` | 未写端口时默认 **465**。 |
| `username` / `password` | 建议**应用专用密码 / 授权码**。 |
| `from` / `to` | 发件人与收件人。 |

安装依赖里的 **`markdown`** 后，邮件可把正文转为 HTML 并内联本地图片；否则退回纯文本。

自测：

```bash
python3 scripts/send_test_email.py
```

若只有 **587 + STARTTLS** 而无 465，需换服务商或扩展发信实现（欢迎 PR）。

---

## 参与贡献

改进采集器、补充文档、修 Bug、优化提示词都十分欢迎。建议先开 Issue 简述场景，再 Fork 提交 PR；变更尽量聚焦。

## 隐私说明

- 浏览器数据库复制到临时目录后读取，**不直接修改**原库。
- **不读取** Cookie、密码和页面正文。
- 密钥放环境变量或本地配置，**勿提交**到 Git。
- 原始事件和总结默认在本地 **`data/`**。
