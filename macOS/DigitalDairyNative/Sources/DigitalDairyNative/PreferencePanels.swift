import AppKit
import SwiftUI

// MARK: - 常规与日程

struct PrefsGeneralView: View {
    @Binding var settings: AppSettings

    var body: some View {
        Form {
            Section("用户") {
                TextField("显示名", text: $settings.user.displayName)
                TextField("昵称（用于开场文案）", text: $settings.user.nickname)
            }
            Section("时间与日程") {
                TextField("时区（IANA）", text: $settings.timezone)
                    .textFieldStyle(.roundedBorder)
                TextField("每日参考时间", text: $settings.schedule.time)
                    .help("例如 11:00")
            }
            Section("开场话术") {
                TextEditor(text: $settings.messages.dailyOpeningHint)
                    .font(.body)
                    .frame(minHeight: 100)
            }
            Section("Inbox 轮询") {
                Stepper(value: $settings.replies.pollMinutes, in: 1 ... 240) {
                    Text("轮询间隔：\(settings.replies.pollMinutes) 分钟")
                }
            }
        }
        .formStyle(.grouped)
    }
}

// MARK: - 模型与 API

struct PrefsApiView: View {
    @Binding var settings: AppSettings

    var body: some View {
        Form {
            Section("模型服务") {
                TextField("提供商标识", text: $settings.api.provider)
                TextField("Base URL", text: $settings.api.baseUrl)
                TextField("模型名", text: $settings.api.model)
            }
            Section("鉴权") {
                TextField("环境变量名（优先）", text: $settings.api.apiKeyEnv)
                SecureField("本地 api_key（勿提交仓库）", text: $settings.api.apiKey)
                Text("若已在 shell 中 export 对应环境变量，可留空本地密钥。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Section("生成参数") {
                Slider(value: $settings.api.temperature, in: 0 ... 1) {
                    Text("温度 \(settings.api.temperature, specifier: "%.2f")")
                }
                Stepper(value: $settings.api.maxTokens, in: 512 ... 32000, step: 128) {
                    Text("max_tokens：\(settings.api.maxTokens)")
                }
            }
        }
        .formStyle(.grouped)
    }
}

// MARK: - 采集数据源

struct PrefsCollectorsView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        Form {
            Section {
                Text("勾选要参与当日采集的数据源；带浏览器的条目可多选 Edge / Chrome。")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
            ForEach(ToolCatalog.orderedToolIds, id: \.self) { id in
                Section(ToolCatalog.displayTitle(for: id)) {
                    Toggle("启用", isOn: enabledBinding(id))
                    if ToolCatalog.supportsBrowsers(id) {
                        Toggle("Edge", isOn: browserBinding(id, "edge"))
                        Toggle("Chrome", isOn: browserBinding(id, "chrome"))
                    }
                    if ToolCatalog.supportsFolders(id) {
                        TextField("健康数据目录（逗号分隔，相对项目根）", text: foldersBinding(id), axis: .vertical)
                            .lineLimit(2 ... 4)
                    }
                }
            }
        }
        .formStyle(.grouped)
    }

    private func enabledBinding(_ id: String) -> Binding<Bool> {
        Binding(
            get: { model.toolSwitches[id]?.enabled ?? false },
            set: { on in
                var row = model.toolSwitches[id] ?? ToolSwitchRow(enabled: false, browsers: nil, folders: nil)
                row.enabled = on
                model.toolSwitches[id] = row
            }
        )
    }

    private func browserBinding(_ id: String, _ name: String) -> Binding<Bool> {
        Binding(
            get: { model.toolSwitches[id]?.browsers?.contains(name) ?? false },
            set: { on in
                var row = model.toolSwitches[id] ?? ToolSwitchRow(enabled: true, browsers: [], folders: nil)
                var b = row.browsers ?? []
                if on {
                    if !b.contains(name) { b.append(name) }
                } else {
                    b.removeAll { $0 == name }
                }
                row.browsers = b.isEmpty ? nil : b
                model.toolSwitches[id] = row
            }
        )
    }

    private func foldersBinding(_ id: String) -> Binding<String> {
        Binding(
            get: { (model.toolSwitches[id]?.folders ?? []).joined(separator: ", ") },
            set: { raw in
                let parts = raw.split(separator: ",")
                    .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                    .filter { !$0.isEmpty }
                var row = model.toolSwitches[id] ?? ToolSwitchRow(enabled: true, browsers: nil, folders: nil)
                row.folders = parts.isEmpty ? nil : parts
                model.toolSwitches[id] = row
            }
        )
    }
}

// MARK: - 通知

struct PrefsNotificationsView: View {
    @Binding var settings: AppSettings

    var body: some View {
        Form {
            Section("邮件（SMTP）") {
                Toggle("启用", isOn: $settings.notifications.email.enabled)
                TextField("SMTP 主机", text: $settings.notifications.email.smtpHost)
                Stepper(value: $settings.notifications.email.smtpPort, in: 1 ... 65535) {
                    Text("端口：\(settings.notifications.email.smtpPort)")
                }
                TextField("用户名", text: $settings.notifications.email.username)
                SecureField("密码 / 授权码", text: $settings.notifications.email.password)
                TextField("发件人", text: $settings.notifications.email.from)
                TextField("收件人", text: $settings.notifications.email.to)
            }
            Section("企业微信") {
                Toggle("启用", isOn: $settings.notifications.wechat.enabled)
                TextField("Webhook URL", text: $settings.notifications.wechat.webhookUrl, axis: .vertical)
                    .lineLimit(2 ... 6)
            }
        }
        .formStyle(.grouped)
    }
}

// MARK: - 高级

struct PrefsAdvancedView: View {
    @Binding var settings: AppSettings

    var body: some View {
        Form {
            Section("路径") {
                TextField("tool_switches 相对路径", text: $settings.toolSwitchesPath)
                TextField("日报提示词模板路径", text: $settings.templates.dailyPrompt)
            }
            Section("数据保留") {
                Stepper(value: $settings.dataRetention.dailySummariesKeepDays, in: 1 ... 365) {
                    Text("保留最近 \(settings.dataRetention.dailySummariesKeepDays) 天总结")
                }
            }
            Section("HTML 可视化（旧版）") {
                Toggle("启用 Playwright 截图并附加到 Markdown", isOn: $settings.visualReport.enabled)
                Text("推荐关闭：日报中的图表与分布已由本应用内「数据图表」页面展示，无需再生成 HTML 与长截图。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Stepper(value: $settings.visualReport.viewportWidth, in: 280 ... 800, step: 10) {
                    Text("截图视口宽：\(settings.visualReport.viewportWidth)")
                }
                Stepper(value: $settings.visualReport.viewportHeight, in: 600 ... 2000, step: 20) {
                    Text("截图视口高：\(settings.visualReport.viewportHeight)")
                }
                Toggle("清理旧截图目录", isOn: $settings.visualReport.cleanupScreenshotDirs)
            }
        }
        .formStyle(.grouped)
    }
}

// MARK: - 外观

struct AppearancePanel: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        Form {
            Section("窗口渐变") {
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [Color(hex: model.themeStartHex), Color(hex: model.themeEndHex)],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .frame(height: 56)
                    .overlay {
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .strokeBorder(.white.opacity(0.35), lineWidth: 1)
                    }
                ColorPicker("起始色", selection: hexBinding(\.themeStartHex))
                ColorPicker("结束色", selection: hexBinding(\.themeEndHex))
            }
        }
        .formStyle(.grouped)
        .padding(8)
    }

    private func hexBinding(_ keyPath: ReferenceWritableKeyPath<AppModel, String>) -> Binding<Color> {
        Binding(
            get: { Color(hex: model[keyPath: keyPath]) },
            set: { newValue in
                if let cg = NSColor(newValue).usingColorSpace(.deviceRGB) {
                    let r = Int(round(cg.redComponent * 255))
                    let g = Int(round(cg.greenComponent * 255))
                    let b = Int(round(cg.blueComponent * 255))
                    model[keyPath: keyPath] = String(format: "#%02X%02X%02X", r, g, b)
                    model.saveTheme()
                }
            }
        )
    }
}

// MARK: - 关于

struct AboutPanel: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Digital Dairy")
                .font(.title2.weight(.semibold))
            Text("Personal Growth OS 原生桌面壳：SwiftUI + 系统材质；日报与采集仍由本机 Python 脚本执行。")
                .foregroundStyle(.secondary)
            if let v = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String {
                Text("版本 \(v)")
            }
            if let bid = Bundle.main.infoDictionary?["CFBundleIdentifier"] as? String {
                Text(bid)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .textSelection(.enabled)
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .padding(20)
    }
}

// MARK: - 容器（处理可选 settings）

struct PreferencesHostView: View {
    @EnvironmentObject private var model: AppModel
    let tab: AppModel.SidebarItem

    var body: some View {
        Group {
            switch tab {
            case .prefsCollectors:
                if model.settingsTargetRoot() != nil {
                    PrefsCollectorsView()
                } else {
                    Text("未找到配置根目录。")
                        .foregroundStyle(.secondary)
                        .padding(20)
                }
            case .about:
                AboutPanel()
            case .appearance:
                AppearancePanel()
            case .prefsGeneral, .prefsApi, .prefsNotifications, .prefsAdvanced:
                if let settings = model.appSettings {
                    switch tab {
                    case .prefsGeneral:
                        PrefsGeneralView(settings: binding(settings))
                    case .prefsApi:
                        PrefsApiView(settings: binding(settings))
                    case .prefsNotifications:
                        PrefsNotificationsView(settings: binding(settings))
                    case .prefsAdvanced:
                        PrefsAdvancedView(settings: binding(settings))
                    default:
                        EmptyView()
                    }
                } else {
                    Text(model.settingsFormError ?? "无法加载 settings.json。")
                        .foregroundStyle(.secondary)
                        .padding(20)
                }
            default:
                EmptyView()
            }
        }
    }

    private func binding(_ snapshot: AppSettings) -> Binding<AppSettings> {
        Binding(
            get: { model.appSettings ?? snapshot },
            set: { model.appSettings = $0 }
        )
    }
}
