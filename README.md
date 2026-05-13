# Personal Growth OS

Personal Growth OS 是一个 **AI 成长日志系统**：把「今天到底干了啥」说清楚，让人**安心收尾**，而不是为了反思而越想越焦虑——尤其是肯定「今天不是白过」。

### 想缓解什么

- **焦虑与脑力内耗**：刷了很多、干了很多，但关电脑前脑子里还是一团杂音；日报用温和口吻把散落线索串成**一条可读完的叙事**，减少「我是不是又荒废了」的反刍。
- **信息爆炸、没有锚点**：收藏夹、历史记录、对话页、任务钩子在各处堆叠，却缺少**同一天、同一视角的锚**。本项目在固定时间把多源痕迹**收束到一份** Markdown 总结（可选推到邮箱），让你第二天能从一个清晰的「昨日坐标」出发，而不是在无痕 tabs 里漂流。

在设定时间，它会自动从浏览器、效率工具、IDE 与 AI 对话等多处**只读采集**痕迹数据，调用你配置的 LLM 生成当日 Markdown 总结，并可推送邮箱或企业微信；事件与总结默认保留在本机 `data/`，便于长期回顾与二次加工。

模型的初始配置适合一个 **AI/CS、正在经历保研的学生**，用户可以根据自己的需求在/configs里面修改自己关注的领域

## 项目特点

- **数据归属你**：原始事件与总结落在本地，密钥走环境变量或本地配置文件，不入库。
- **轻量可组合**：用 `tool_switches` 按需启用数据源，未开启的采集器不会运行。
- **可演进协作**：模板、维度、采集器都可 Fork 后按自己的习惯改；欢迎通过 Issue / PR 扩展平台与文档。

## 功能介绍

| 能力 | 说明 |
|------|------|
| **每日采集 + 总结** | `run_daily.py` 聚合当日事件，按 `templates/daily_summary_prompt.md` 与成长维度生成 Markdown 总结。 |
| **多源采集器** | 浏览器历史、资讯站点、滴答清单专注、Cursor / VS Code、ChatGPT / 豆包 / DeepSeek 对话页等（见下表）。 |
| **可选可视化** | 生成 HTML 报告；若安装 Playwright 与 Chromium，可将移动端长截图附录到总结末尾。 |
| **通知** | 支持 SMTP 邮件（可将 Markdown 渲染为 HTML 内联图片）与企业微信机器人 Webhook。 |
| **问答与 Inbox** | `answer_reply.py` 单条提问；`add_inbox_message.py` + `process_inbox.py` 批量处理并回发。 |
| **定时执行（macOS）** | `install_launchd.py` 安装 LaunchAgent：每日总结与 Inbox 轮询。 |
| **保留策略** | 按 `data_retention.daily_summaries_keep_days` 自动清理旧总结。 |

## 环境与依赖

建议使用 **Python 3.10+**。安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

若需要**可视化报告附录截图**（长图 PNG），还需在本机安装 Chromium（与当前 venv 的 Python 一致）：

```bash
python -m playwright install chromium
```

## 快速开始

1. **复制配置模板**

   ```bash
   cp config/settings.example.json config/settings.json
   cp config/tool_switches.example.json config/tool_switches.json
   ```

2. **配置 LLM API Key（推荐环境变量）**

   ```bash
   export DEEPSEEK_API_KEY="your_key_here"
   ```

3. **编辑 `config/settings.json`**（见下一节「个人设置」）。

4. **编辑 `config/tool_switches.json`**，只开启你需要的采集项。

5. **试跑一日（可不推送、不截图）**

   ```bash
   python3 scripts/run_daily.py --date 2026-05-13 --no-notify
   ```

   仅采集、不调模型：

   ```bash
   python3 scripts/run_daily.py --date 2026-05-13 --dry-run
   ```

   输出示例：`data/events/YYYY-MM-DD-events.json`、`data/summaries/YYYY-MM-DD-summary.md`。

## 个人设置（`config/settings.json`）

与「日报怎么说、何时跑、往哪推」相关的核心字段：

| 区块 | 作用 |
|------|------|
| `user` | `nickname` / `display_name`：称呼与展示名。 |
| `timezone` | 时区（如 `Asia/Shanghai`）。 |
| `schedule.time` | 每日执行参考时间（与 LaunchAgent / 文案中的「几点」一致）。 |
| `messages.daily_opening_hint` | 日报开场句模板，支持 `{opening_time}`、`{nickname}`、`{user_name}` 等占位（见 `run_daily.py`）。 |
经历| `api` | `base_url`、`model`、温度、最大 token；`api_key_env` 指定环境变量名。 |
| `templates.daily_prompt` | 总结用系统/用户提示模板路径，默认 `templates/daily_summary_prompt.md`。 |
| `tool_switches_path` | 工具开关 JSON 路径，默认 `config/tool_switches.json`。 |
| `data_retention` | 如 `daily_summaries_keep_days`：保留最近 N 天总结。 |
| `visual_report` | 可视化 HTML / 截图视口、是否启用等。 |
| `notifications` | `email`（SMTP）与 `wechat`（企微 Webhook）。 |
| `replies.poll_minutes` | Inbox 轮询间隔（与 LaunchAgent 配合）。 |

密钥与 API Key 请走环境变量；**SMTP 密码、Webhook 等敏感信息只应出现在本地 `settings.json`，勿提交 Git。**

## `config/` 目录：有哪些文件、怎么配、怎么自定义

### 目录里有什么

| 文件 | 作用 |
|------|------|
| `settings.example.json` | **全局设置模板**：复制为 `settings.json` 后填写 API、通知、时区等。 |
| `settings.json` | **你的本地设置**（含密钥占位）；请勿把真实密码提交到公开仓库。 |
| `tool_switches.example.json` | **采集器开关模板**：复制为 `tools` 配置（见下）。 |
| `tool_switches.json` | **实际启用哪些数据源**；路径由 `settings.json` 里的 `tool_switches_path` 指定（默认即此文件）。 |
| `growth_dimensions.json` | **成长维度定义**：决定事件如何打上「升学 / 科研 / 工程」等标签，并进入日报叙事结构。 |

首次建议：

```bash
cp config/settings.example.json config/settings.json
cp config/tool_switches.example.json config/tool_switches.json
```

之后主要改 **`settings.json`**（何时总结、用哪家模型、是否发邮件）和 **`tool_switches.json`**（采不采 Chrome、采不采滴答等）。**`growth_dimensions.json`** 偏「你的人生关注点 taxonomy」，可大胆改成自己的维度与关键词。

### `settings.json` 常用字段与自定义空间

- **`user` / `timezone` / `schedule` / `messages`**：称呼、时区、日报「收工」时间、开场白话术；可直接改文案，支持占位符（与 `run_daily` 里注入逻辑一致，如 `{nickname}`、`{opening_time}`）。
- **`api`**：兼容 OpenAI 式 `POST .../chat/completions` 的服务均可尝试（`base_url`、`model`、`temperature`、`max_tokens`）；密钥优先读 `api_key_env` 指向的环境变量，其次才是文件里的 `api_key`（勿填真实 key 进公开分支）。
- **`templates.daily_prompt`**：指向 Markdown 提示词文件，**默认** `templates/daily_summary_prompt.md`。可换成你自己的路径（例如 `templates/my_prompt.md`），实现完全不同的章节与语气。
- **`tool_switches_path`**：工具开关 JSON 的相对路径（相对于项目根目录）。若留空或不存在，部分脚本会回退去读 `settings` 里的 **`tools`** 内联对象（与 `tool_switches.json` 结构相同）。
- **`data_retention.daily_summaries_keep_days`**：保留最近 N 天总结文件，其余自动清理。
- **`replies.poll_minutes`**：`process_inbox` 等与「隔多久拉一次回复」相关的间隔（与 LaunchAgent 搭配时参照此值）。
- **`visual_report`**（可视化 HTML 与附录截图）：  
  - **`enabled`**：`false` 可关掉整条可视化链路（与 `run_daily` 里截图附录逻辑一致）。  
  - **`viewport_width` / `viewport_height` / `device_scale_factor`**：Playwright 截长图时的视口与像素密度。  
  - **`screenshot_stem`**：输出 PNG 文件名前缀。  
  - **`cleanup_screenshot_dirs`**：为 `true`（默认）时，日报跑完会按策略清理旧截图目录；若想手顺 debug 可改为 `false`。  
  - **`focus_goal_minutes`**：可视化报告里与「专注目标」相关的参照分钟数（见 `visual_html_report`）。  
  - **`coding_lines_bar_cap`**：编码行数类图表的上限（`null` 表示用默认逻辑）。
- **`notifications`**：见前文「邮箱推送」与下表企微；开启前务必确认 **`enabled`** 与 Webhook/密码已填。

企业微信机器人：在 `notifications.wechat` 中设置 `enabled: true` 与 `webhook_url`（企微群机器人地址）。正文以 Markdown 形式推送，长度会裁剪（见 `notifier.py`）。

脚本可通过参数覆盖设置路径，例如：

```bash
python3 scripts/run_daily.py --settings config/settings.json
```

### `tool_switches.json`：每个采集器怎么开

顶层 **键名**必须与 `tools/registry.py` 里的 `TOOL_REGISTRY` 一致。每一项至少包含 **`enabled`: true/false**。常用附加字段：

| 键 | 含义 |
|----|------|
| `chrome` / `edge` / `safari` | 是否从对应浏览器读历史（Safari 默认常关）。 |
| `bilibili_history` / `zhihu_history` / `xiaohongshu_history` | 是否从浏览器历史里归纳资讯流；可选 **`browsers`** 数组，如 `["edge","chrome"]`。 |
| `chatgpt` / `doubao` / `deepseek` | 是否采集 AI 对话页线索；同样可选 **`browsers`**。 |
| `ticktick_focus` / `cursor` / `vscode` | 效率与 IDE 侧采集；无需 `browsers`。 |
| `manual_imports` / `mobile_imports` | 是否读 `data/imports`、`data/mobile` 等约定目录下的导入文件。 |
| `mi_health` | 健康 CSV 等；可选 **`folders`** 列表（默认示例为 `["data/health"]`）。 |

禁用某项只需设 **`"enabled": false`**，该采集器在 `run_daily` 中会被跳过。

### `growth_dimensions.json`：自定义「成长维度」

文件为 JSON，顶层 **`dimensions`** 数组。每一项支持：

| 字段 | 作用 |
|------|------|
| `id` | 稳定标识，会写进事件的 `dimensions` 列表并供报告统计；建议英文短横线风格。 |
| `name` | 人类可读名称（会出现在提示词/报告上下文中）。 |
| `description` | 维度的文字说明，帮助 LLM 理解归类语义。 |
| `keywords` | **关键词**：若出现在事件标题、主题或 URL 片段中，则命中该维度（不区分大小写匹配逻辑见 `assign_dimensions`）。 |
| `hosts` | **域名片段**：事件的 `url_host` 若包含其中任一字符串，则命中（适合把整类站点归为同一成长线）。 |

若某条事件未命中任何维度，系统会落到 **`general_input`**（请在 JSON 中保留该兜底维度，或按你的模板改写提示词）。

**可自定义方向举例**：删掉与本人生阶段无关的维度、改成「主业 / 副业 / 家庭 / 运动」、为常去的学校/公司域名加 `hosts`、为关注的技术栈加 `keywords`——改完后无需改 Python，下次 `run_daily` 即生效。

### 与 `templates/` 的配合

`settings.json` 里的 **`templates.daily_prompt`** 指向的 Markdown，会作为「总结怎么写」的核心说明；`config/growth_dimensions.json` 的内容会作为结构化上下文喂给模型。**两处一起改**，才能把「分拣逻辑」和「叙事口吻」调到完全符合你的习惯。

## 邮箱推送配置（SMTP）

日报与 `process_inbox` 等通知可走邮件。实现上使用 **`smtplib.SMTP_SSL`**（TLS/SSL 直连），默认端口 **`465`**，需与你的邮箱服务商提供的 **SMTP SSL 发信端口**一致。

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
| `enabled` | `true` 时才会发信。 |
| `smtp_host` / `smtp_port` | 发信服务器与端口；未写端口时**默认 465**（SSL）。 |
| `username` / `password` | 登录 SMTP 的账号与密码；主流邮箱应使用**应用专用密码 / 授权码**，不要用普通登录密码。 |
| `from` / `to` | 发件人与收件人地址（常见场景下可与 `username` 相同）。 |

**Markdown 邮件**：已安装依赖里的 `markdown` 时，日报推送会尽量把正文转成 HTML，并**内联本地图片**（例如总结里引用的截图）；未安装则退回纯文本（见 `tools/notifier.py` 行为）。

**自测是否配置正确**（需已 `enabled: true` 并填好上述字段）：

```bash
python3 scripts/send_test_email.py
```

若收不到，请检查：服务商是否开启 SMTP、是否必须用授权码、防火墙是否拦截 465，以及垃圾箱。当前代码路径为 **SSL 465**；若你的邮箱只提供 **587 + STARTTLS** 而无 465，需改服务商或后续扩展发信实现（欢迎 PR）。

## 工具与平台一览

以下为 `tool_switches` 中可调用的采集维度（具体键名以 `config/tool_switches.example.json` 为准）：

| 类别 | 平台 / 数据源 | 说明 |
|------|----------------|------|
| **浏览器** | Chrome、Edge、Safari | 本地历史库只读复制后解析；不读 Cookie / 密码 / 页面正文。 |
| **资讯流（经浏览器历史）** | 哔哩哔哩、知乎、小红书 | 从指定浏览器的访问记录中归纳当日访问。 |
| **生产力** | 滴答清单（专注） | 本地滴答清单数据目录解析专注记录。 |
| **IDE** | Cursor、VS Code | Cursor 为 SQLite 对话侧记录；VS Code 可按占位扩展。 |
| **AI 对话（经浏览器历史）** | ChatGPT、豆包、DeepSeek | 按对话线程 URL 规则过滤，避免营销页干扰。 |
| **导入** | 手动导入、手机导入、小米运动健康等 | 目录 CSV/约定格式；`mi_health` 等见 `folders` 配置。 |

浏览器侧 AI / 资讯采集通常可配置 `browsers` 列表（如 `["edge","chrome"]`），与 `tool_switches` 中各项对应。

更多站点域名归类（如 GitHub、CSDN、arXiv 等）可在 `tools/platforms.py` 中查看，用于浏览历史的平台识别。

## 目录结构

```text
config/
  settings.example.json          # 全局配置模板
  settings.json                  # 本地配置（不要提交）
  tool_switches.example.json     # 工具使能开关模板
  tool_switches.json             # 本地工具开关（可选）
  growth_dimensions.json

data/
  events/ summaries/ replies/ inbox/ imports/ mobile/ health/ logs/ visual/

tools/
  collectors/                    # 按类别拆分的采集入口
  registry.py reporting.py llm.py notifier.py qa.py ...

scripts/
  run_daily.py                   # 每日采集 + 总结
  answer_reply.py                # 单条问答
  add_inbox_message.py           # 写入 Inbox
  process_inbox.py               # 处理 Inbox 并回发
  install_launchd.py             # macOS 定时任务
  ...

templates/
  daily_summary_prompt.md
```

## 定时任务（macOS）

```bash
python3 scripts/install_launchd.py
launchctl load ~/Library/LaunchAgents/com.personal-growth-os.daily.plist
launchctl load ~/Library/LaunchAgents/com.personal-growth-os.inbox.plist
```

## 模板可定制

编辑 `templates/daily_summary_prompt.md` 可改结构、口吻与最关心维度。开场提示由 `messages.daily_opening_hint` 注入。

## 邮箱 / 企业微信回复与自动问答

**单条：**

```bash
python3 scripts/answer_reply.py --question "我今天主要成长在哪里？"
```

模型会根据缓存在 data 里的事件与总结，生成一个符合要求的回复。

**队列：**

```bash
python3 scripts/add_inbox_message.py --channel email --text "今天最值得肯定的三件事是什么？"
python3 scripts/process_inbox.py
```

## 参与贡献

改进采集器、补充平台文档、修 Bug、优化提示词或本地化说明都十分欢迎。建议：**先开 Issue 简述场景**，再 Fork 后提交 PR；请保持变更聚焦、避免无关大重构。许可证与行为边界以仓库内文件为准。

## 隐私说明

- 浏览器数据库会复制到临时目录后读取，**不直接修改**原始文件。
- **不读取** Cookie、密码和页面正文。
- 密钥建议放环境变量或本地配置，**勿提交**到 Git。
- 原始事件和总结默认保留在本地 `data/`。
