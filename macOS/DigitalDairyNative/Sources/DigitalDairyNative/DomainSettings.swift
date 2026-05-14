import Foundation

/// 日报模版库条目（`settings.json` → `templates.prompt_presets`）。
struct TemplatePreset: Codable, Equatable, Identifiable, Hashable {
    var id: String
    var label: String
    var path: String
}

/// 与 `config/settings.example.json` 对齐的应用设置（用于 GUI 编辑与保存）。
struct AppSettings: Codable, Equatable {
    struct UserBlock: Codable, Equatable {
        var displayName: String
        var nickname: String
    }

    struct ScheduleBlock: Codable, Equatable {
        var time: String
    }

    struct MessagesBlock: Codable, Equatable {
        var dailyOpeningHint: String
    }

    struct RepliesBlock: Codable, Equatable {
        var pollMinutes: Int
    }

    struct ApiBlock: Codable, Equatable {
        var provider: String
        var baseUrl: String
        var model: String
        var apiKeyEnv: String
        var apiKey: String
        var temperature: Double
        var maxTokens: Int
    }

    struct TemplatesBlock: Codable, Equatable {
        var dailyPrompt: String
        /// 可选；为空时界面使用内置下拉列表，不改变 `daily_prompt` 语义。
        var promptPresets: [TemplatePreset]?

        init(dailyPrompt: String, promptPresets: [TemplatePreset]? = nil) {
            self.dailyPrompt = dailyPrompt
            self.promptPresets = promptPresets
        }

        // 注意：外层使用 key(Decoding|Encoding)Strategy 的 snake_case 时，
        // 不要在此处再写 `daily_prompt` 形式的 CodingKey 字面量，否则与策略转换后的键对不上，会导致整份 settings 解码失败。
    }

    struct DataRetentionBlock: Codable, Equatable {
        var dailySummariesKeepDays: Int
    }

    struct VisualReportBlock: Codable, Equatable {
        var enabled: Bool
        var viewportWidth: Int
        var viewportHeight: Int
        var deviceScaleFactor: Double
        var screenshotStem: String
        var cleanupScreenshotDirs: Bool
        var focusGoalMinutes: Int
        var codingLinesBarCap: Int?
    }

    struct EmailBlock: Codable, Equatable {
        var enabled: Bool
        var smtpHost: String
        var smtpPort: Int
        var username: String
        var password: String
        var from: String
        var to: String
    }

    struct WechatBlock: Codable, Equatable {
        var enabled: Bool
        var webhookUrl: String
    }

    struct NotificationsBlock: Codable, Equatable {
        var email: EmailBlock
        var wechat: WechatBlock
    }

    var user: UserBlock
    var timezone: String
    var schedule: ScheduleBlock
    var messages: MessagesBlock
    var replies: RepliesBlock
    var api: ApiBlock
    var templates: TemplatesBlock
    var toolSwitchesPath: String
    var dataRetention: DataRetentionBlock
    var visualReport: VisualReportBlock
    var notifications: NotificationsBlock

    static func makeDefaultTemplate() -> AppSettings {
        AppSettings(
            user: UserBlock(displayName: "xxx", nickname: "xxx"),
            timezone: "Asia/Shanghai",
            schedule: ScheduleBlock(time: "11:00"),
            messages: MessagesBlock(
                dailyOpeningHint: "{opening_time} 了，{nickname} 辛苦了。你今天做了很多事情，可以慢慢放松下来，准备休息了。"
            ),
            replies: RepliesBlock(pollMinutes: 10),
            api: ApiBlock(
                provider: "deepseek",
                baseUrl: "https://api.deepseek.com",
                model: "deepseek-chat",
                apiKeyEnv: "DEEPSEEK_API_KEY",
                apiKey: "PUT_YOUR_KEY_HERE_FOR_LOCAL_ONLY",
                temperature: 0.55,
                maxTokens: 4200
            ),
            templates: TemplatesBlock(dailyPrompt: "templates/daily_summary_prompt.md"),
            toolSwitchesPath: "config/tool_switches.json",
            dataRetention: DataRetentionBlock(dailySummariesKeepDays: 3),
            visualReport: VisualReportBlock(
                enabled: false,
                viewportWidth: 390,
                viewportHeight: 844,
                deviceScaleFactor: 2,
                screenshotStem: "report-mobile",
                cleanupScreenshotDirs: true,
                focusGoalMinutes: 120,
                codingLinesBarCap: nil
            ),
            notifications: NotificationsBlock(
                email: EmailBlock(
                    enabled: false,
                    smtpHost: "smtp.example.com",
                    smtpPort: 465,
                    username: "you@example.com",
                    password: "PUT_APP_PASSWORD_HERE",
                    from: "you@example.com",
                    to: "you@example.com"
                ),
                wechat: WechatBlock(enabled: false, webhookUrl: "PUT_WECHAT_WORK_BOT_WEBHOOK_HERE")
            )
        )
    }

    static func load(from url: URL) throws -> AppSettings {
        let data = try Data(contentsOf: url)
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        do {
            return try decoder.decode(AppSettings.self, from: data)
        } catch {
            // 兼容旧版/不完整的 settings.json：将缺失字段用默认值补全后再解码
            let patched = try Self.patchWithDefaults(data: data)
            return try decoder.decode(AppSettings.self, from: patched)
        }
    }

    /// 将用户已有的 JSON 与默认值深度合并：用户值优先，缺失键用默认值补全。
    private static func patchWithDefaults(data: Data) throws -> Data {
        guard let existing = try JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] else {
            throw NSError(domain: "AppSettings", code: 2,
                          userInfo: [NSLocalizedDescriptionKey: "settings.json 不是合法的 JSON 对象"])
        }
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        let defaultData = try encoder.encode(makeDefaultTemplate())
        guard let defaultDict = try JSONSerialization.jsonObject(with: defaultData, options: []) as? [String: Any] else {
            throw NSError(domain: "AppSettings", code: 3,
                          userInfo: [NSLocalizedDescriptionKey: "内部默认值序列化失败"])
        }
        let merged = deepMerge(base: defaultDict, override: existing)
        return try JSONSerialization.data(withJSONObject: merged, options: [])
    }

    /// 深度合并：`override` 中的值覆盖 `base`；对嵌套 Dict 递归合并而非整体替换。
    private static func deepMerge(base: [String: Any], override: [String: Any]) -> [String: Any] {
        var result = base
        for (key, value) in override {
            if let baseDict = result[key] as? [String: Any],
               let overrideDict = value as? [String: Any] {
                result[key] = deepMerge(base: baseDict, override: overrideDict)
            } else {
                result[key] = value
            }
        }
        return result
    }

    func save(to url: URL) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.keyEncodingStrategy = .convertToSnakeCase
        let data = try encoder.encode(self)
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try data.write(to: url, options: .atomic)
    }
}

/// 单条采集器开关，对应 `tool_switches.json` 中的值。
struct ToolSwitchRow: Codable, Equatable {
    var enabled: Bool
    var browsers: [String]?
    var folders: [String]?
}

enum ToolCatalog {
    static let orderedToolIds: [String] = [
        "chrome", "edge", "safari",
        "bilibili_history", "zhihu_history", "xiaohongshu_history",
        "ticktick_focus",
        "cursor", "vscode",
        "chatgpt", "doubao", "deepseek",
        "manual_imports", "mobile_imports", "mi_health",
    ]

    static func displayTitle(for id: String) -> String {
        switch id {
        case "chrome": return "Chrome 历史"
        case "edge": return "Edge 历史"
        case "safari": return "Safari 历史"
        case "bilibili_history": return "哔哩哔哩"
        case "zhihu_history": return "知乎"
        case "xiaohongshu_history": return "小红书"
        case "ticktick_focus": return "滴答专注"
        case "cursor": return "Cursor"
        case "vscode": return "VS Code"
        case "chatgpt": return "ChatGPT"
        case "doubao": return "豆包"
        case "deepseek": return "DeepSeek"
        case "manual_imports": return "手动导入"
        case "mobile_imports": return "手机导入"
        case "mi_health": return "小米运动健康"
        default: return id
        }
    }

    static func supportsBrowsers(_ id: String) -> Bool {
        [
            "bilibili_history", "zhihu_history", "xiaohongshu_history",
            "chatgpt", "doubao", "deepseek",
        ].contains(id)
    }

    static func supportsFolders(_ id: String) -> Bool {
        id == "mi_health"
    }
}

enum ToolSwitchesFile {
    static func load(from url: URL) throws -> [String: ToolSwitchRow] {
        let data = try Data(contentsOf: url)
        let decoder = JSONDecoder()
        return try decoder.decode([String: ToolSwitchRow].self, from: data)
    }

    static func save(_ value: [String: ToolSwitchRow], to url: URL) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(value)
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try data.write(to: url, options: .atomic)
    }

    /// 合并默认键顺序与示例中缺失的采集器项。
    static func normalized(_ raw: [String: ToolSwitchRow]) -> [String: ToolSwitchRow] {
        var out: [String: ToolSwitchRow] = [:]
        for id in ToolCatalog.orderedToolIds {
            if let row = raw[id] {
                out[id] = row
            } else {
                out[id] = ToolSwitchRow(enabled: false, browsers: nil, folders: nil)
            }
        }
        for (k, v) in raw where out[k] == nil {
            out[k] = v
        }
        return out
    }
}
