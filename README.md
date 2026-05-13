# Personal Growth OS

Personal Growth OS 是一个本地优先、可开源协作的 AI 成长日志系统：  
每天按设定时间自动采集多源数据（Edge / Chrome / 滴答清单 / Cursor / VS Code / 豆包 / DeepSeek / ChatGPT 等），生成当天总结到 Markdown，并推送到邮箱或企业微信。

## 目录结构

```text
config/
  settings.example.json          # 全局配置模板
  settings.json                  # 本地配置（不要提交）
  tool_switches.example.json     # 工具使能开关模板
  tool_switches.json             # 本地工具开关（可选）
  growth_dimensions.json

data/
  events/
  summaries/
  replies/
  inbox/
  imports/
  mobile/
  health/
  logs/

tools/
  collectors/                    # 分类工具入口
    browsers.py                  # edge/chrome
    productivity.py              # ticktick
    ides.py                      # cursor/vscode
    ai_platforms.py              # chatgpt/doubao/deepseek
    imports.py                   # 手动/手机/健康导入
  registry.py
  reporting.py
  llm.py
  notifier.py
  qa.py

scripts/
  run_daily.py                   # 每日采集+总结
  answer_reply.py                # 单条问题问答
  add_inbox_message.py           # 写入一条待处理回复
  process_inbox.py               # 批量处理邮箱/微信回复并自动回发
  install_launchd.py             # 安装 macOS 定时任务

templates/
  daily_summary_prompt.md
```

## 快速开始

1) 复制配置文件：

```bash
cp config/settings.example.json config/settings.json
cp config/tool_switches.example.json config/tool_switches.json
```

2) 配置 API Key（推荐环境变量）：

```bash
export DEEPSEEK_API_KEY="your_key_here"
```

3) 修改 `config/settings.json`：
- `schedule.time`: 每日执行时间（默认 `11:00`）
- `user.nickname`: 称呼（用于开头语）
- `messages.daily_opening_hint`: 开场句模板
- `notifications.email` / `notifications.wechat`: 推送配置
- `api`: 模型接口配置

4) 修改 `config/tool_switches.json`，按需启用工具。

## 工具使能 JSON

`config/tool_switches.json` 示例：

```json
{
  "chrome": { "enabled": true },
  "edge": { "enabled": true },
  "ticktick_focus": { "enabled": true },
  "cursor": { "enabled": true },
  "vscode": { "enabled": false },
  "chatgpt": { "enabled": true },
  "doubao": { "enabled": true },
  "deepseek": { "enabled": true },
  "manual_imports": { "enabled": true },
  "mobile_imports": { "enabled": true },
  "mi_health": { "enabled": true }
}
```

## 每日执行

手动运行：

```bash
python3 scripts/run_daily.py --date 2026-05-13 --no-notify
```

只采集不调用模型：

```bash
python3 scripts/run_daily.py --date 2026-05-13 --dry-run
```

输出文件：
- `data/events/YYYY-MM-DD-events.json`
- `data/summaries/YYYY-MM-DD-summary.md`

系统会根据 `data_retention.daily_summaries_keep_days`（默认 3）自动删除旧总结。

## 定时任务（macOS）

安装 LaunchAgent（包含每日总结任务 + inbox 回复轮询任务）：

```bash
python3 scripts/install_launchd.py
launchctl load ~/Library/LaunchAgents/com.personal-growth-os.daily.plist
launchctl load ~/Library/LaunchAgents/com.personal-growth-os.inbox.plist
```

## 模板可定制

编辑 `templates/daily_summary_prompt.md`。  
可改开场语风格、最关心维度、章节结构、口吻要求。

默认开场提示由全局配置注入，例如：  
`11:00 了，xxx 辛苦了。你今天做了很多事情，可以慢慢放松下来，准备休息了。`

## 邮箱/微信回复 -> 自动问答

### 单条问答（手动）

```bash
python3 scripts/answer_reply.py --question "我今天主要成长在哪里？"
```

### 自动队列（推荐）

1) 把用户回复写入 inbox：

```bash
python3 scripts/add_inbox_message.py --channel email --text "今天最值得肯定的三件事是什么？"
```

2) 处理并回发：

```bash
python3 scripts/process_inbox.py
```

处理后会：
- 读取 `data/events` 与 `data/summaries`
- 调用你配置的 API 回答问题
- 保存回答到 `data/replies`
- 按渠道回发到邮箱或企业微信

## 隐私说明

- 浏览器数据库会复制到临时目录后读取，不直接修改原始文件。
- 不读取 Cookie、密码和页面正文。
- 密钥建议放环境变量或本地配置，不提交到仓库。
- 原始事件和总结均保留在本地 `data/`。
