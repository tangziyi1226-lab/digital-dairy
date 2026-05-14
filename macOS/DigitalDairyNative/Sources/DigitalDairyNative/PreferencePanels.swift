import AppKit
import SwiftUI

// MARK: - 内置日报模版（下拉；未写入 settings 时使用）

private enum TemplatePresetCatalog {
    static let builtin: [TemplatePreset] = [
        TemplatePreset(id: "standard", label: "标准日报", path: "templates/daily_summary_prompt.md"),
        TemplatePreset(id: "minimal", label: "精简要点", path: "templates/presets/minimal_daily.md"),
        TemplatePreset(id: "wellness", label: "情绪与健康", path: "templates/presets/wellness_focus.md"),
        TemplatePreset(id: "work", label: "执行与交付", path: "templates/presets/work_execution.md"),
    ]
}

// MARK: - 常规与日程

struct PrefsGeneralView: View {
    @Binding var settings: AppSettings

    private static let timezonePresets: [String] = [
        "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Taipei", "Asia/Singapore", "Asia/Tokyo", "Asia/Seoul",
        "Europe/London", "Europe/Paris", "Europe/Berlin",
        "America/New_York", "America/Chicago", "America/Los_Angeles",
        "America/Sao_Paulo", "Australia/Sydney", "Pacific/Auckland", "UTC",
    ]

    private static func scheduleHalfHours() -> [String] {
        var out: [String] = []
        for h in 5 ... 23 {
            out.append(String(format: "%02d:00", h))
            out.append(String(format: "%02d:30", h))
        }
        return out
    }

    private var timezonePickerValues: [String] {
        var s = Self.timezonePresets
        if !s.contains(settings.timezone) { s.append(settings.timezone) }
        return s
    }

    private var schedulePickerValues: [String] {
        var s = Self.scheduleHalfHours()
        if !s.contains(settings.schedule.time) { s.append(settings.schedule.time) }
        return s.sorted()
    }

    var body: some View {
        Form {
            Section("用户") {
                TextField("显示名", text: $settings.user.displayName)
                TextField("昵称（用于开场文案）", text: $settings.user.nickname)
            }
            Section("时间与日程") {
                Picker("时区（IANA）", selection: $settings.timezone) {
                    ForEach(timezonePickerValues, id: \.self) { id in
                        Text(id).tag(id)
                    }
                }
                .help("下拉选择常用时区；列表已包含当前值。")
                Picker("每日参考时间", selection: $settings.schedule.time) {
                    ForEach(schedulePickerValues, id: \.self) { t in
                        Text(t).tag(t)
                    }
                }
                .help("用于日报节奏与开场话术占位符。")
            }
            Section("开场话术 ✨") {
                ZStack(alignment: .topLeading) {
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(
                            LinearGradient(
                                colors: [
                                    Color.purple.opacity(0.14),
                                    Color.teal.opacity(0.1),
                                    Color.blue.opacity(0.08),
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                    TextEditor(text: $settings.messages.dailyOpeningHint)
                        .scrollContentBackground(.hidden)
                        .font(.system(.body, design: .rounded))
                        .frame(minHeight: 110)
                        .padding(8)
                }
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .strokeBorder(Color.primary.opacity(0.06), lineWidth: 1)
                )
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

// MARK: - 成长维度

struct PrefsGrowthDimensionsView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        Form {
            Section {
                Text("字段与 `config/growth_dimensions.json` 一致，保存后 Python 侧 `load_dimensions` 即生效。")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
            if model.growthDimensionsFile != nil {
                Section {
                    Button("新增维度") { addDimensionRow() }
                }
                if let doc = model.growthDimensionsFile {
                    ForEach(Array(doc.dimensions.enumerated()), id: \.offset) { index, row in
                        dimensionSection(index: index, headerTitle: row.name.isEmpty ? "维度 \(index + 1)" : row.name)
                    }
                }
            } else {
                Section {
                    Text(model.growthDimensionsError ?? "未加载到 growth_dimensions.json。")
                        .foregroundStyle(.secondary)
                    Button("创建示例配置文件") {
                        model.createGrowthDimensionsFromExample()
                    }
                }
            }
        }
        .formStyle(.grouped)
    }

    private func addDimensionRow() {
        guard var doc = model.growthDimensionsFile else { return }
        let nid = "dim_\(Int(Date().timeIntervalSince1970))"
        doc.dimensions.append(
            GrowthDimensionsFile.Row(
                id: nid,
                name: "新维度",
                description: "",
                keywords: [],
                hosts: [],
                enabled: true
            )
        )
        model.growthDimensionsFile = doc
    }

    private func deleteRow(at index: Int) {
        guard var doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return }
        doc.dimensions.remove(at: index)
        model.growthDimensionsFile = doc
    }

    @ViewBuilder
    private func dimensionSection(index: Int, headerTitle: String) -> some View {
        Section(headerTitle) {
            Toggle("参与归类", isOn: enabledBinding(index: index))
            TextField("id（唯一标识）", text: idBinding(index: index))
                .textSelection(.enabled)
            TextField("显示名称", text: nameBinding(index: index))
            TextField("描述", text: descriptionBinding(index: index), axis: .vertical)
                .lineLimit(2 ... 8)
            TextField("关键词（逗号分隔）", text: keywordsBinding(index: index), axis: .vertical)
                .lineLimit(2 ... 6)
            TextField("域名 / hosts（逗号分隔）", text: hostsBinding(index: index), axis: .vertical)
                .lineLimit(2 ... 6)
            Button("删除此维度", role: .destructive) {
                deleteRow(at: index)
            }
        }
    }

    private func enabledBinding(index: Int) -> Binding<Bool> {
        Binding(
            get: {
                guard let doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return true }
                return doc.dimensions[index].enabled
            },
            set: { newValue in
                guard var doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return }
                doc.dimensions[index].enabled = newValue
                model.growthDimensionsFile = doc
            }
        )
    }

    private func idBinding(index: Int) -> Binding<String> {
        Binding(
            get: {
                guard let doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return "" }
                return doc.dimensions[index].id
            },
            set: { newValue in
                guard var doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return }
                doc.dimensions[index].id = newValue.trimmingCharacters(in: .whitespacesAndNewlines)
                model.growthDimensionsFile = doc
            }
        )
    }

    private func nameBinding(index: Int) -> Binding<String> {
        Binding(
            get: {
                guard let doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return "" }
                return doc.dimensions[index].name
            },
            set: { newValue in
                guard var doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return }
                doc.dimensions[index].name = newValue
                model.growthDimensionsFile = doc
            }
        )
    }

    private func descriptionBinding(index: Int) -> Binding<String> {
        Binding(
            get: {
                guard let doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return "" }
                return doc.dimensions[index].description
            },
            set: { newValue in
                guard var doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return }
                doc.dimensions[index].description = newValue
                model.growthDimensionsFile = doc
            }
        )
    }

    private func keywordsBinding(index: Int) -> Binding<String> {
        Binding(
            get: {
                guard let doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return "" }
                return doc.dimensions[index].keywords.joined(separator: ", ")
            },
            set: { raw in
                guard var doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return }
                let parts = raw.split(separator: ",")
                    .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                    .filter { !$0.isEmpty }
                doc.dimensions[index].keywords = parts
                model.growthDimensionsFile = doc
            }
        )
    }

    private func hostsBinding(index: Int) -> Binding<String> {
        Binding(
            get: {
                guard let doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return "" }
                return doc.dimensions[index].hosts.joined(separator: ", ")
            },
            set: { raw in
                guard var doc = model.growthDimensionsFile, doc.dimensions.indices.contains(index) else { return }
                let parts = raw.split(separator: ",")
                    .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                    .filter { !$0.isEmpty }
                doc.dimensions[index].hosts = parts
                model.growthDimensionsFile = doc
            }
        )
    }
}

// MARK: - 模版

struct PrefsTemplatesView: View {
    @EnvironmentObject private var model: AppModel
    @Binding var settings: AppSettings
    @State private var editorBody: String = ""
    @State private var editorStatus: String = ""
    @State private var showNewSheet = false
    @State private var newLabel: String = "我的模版"
    @State private var newRelativePath: String = "templates/presets/my_prompt.md"

    private var basePresets: [TemplatePreset] {
        if let p = settings.templates.promptPresets, !p.isEmpty { return p }
        return TemplatePresetCatalog.builtin
    }

    private var pickerPresets: [TemplatePreset] {
        let path = settings.templates.dailyPrompt
        var rows = basePresets
        if !rows.contains(where: { $0.path == path }) {
            let tail = path.split(separator: "/").last.map(String.init) ?? path
            rows.insert(TemplatePreset(id: "_adhoc", label: "当前文件：\(tail)", path: path), at: 0)
        }
        return rows
    }

    var body: some View {
        Form {
            Section("当前模版") {
                Picker("选择模版", selection: $settings.templates.dailyPrompt) {
                    ForEach(pickerPresets) { pr in
                        Text(pr.label).tag(pr.path)
                    }
                }
                .onChange(of: settings.templates.dailyPrompt) { _, _ in
                    reloadFromDisk()
                }
                Text(settings.templates.dailyPrompt)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
            }
            Section("正文（Markdown）") {
                TextEditor(text: $editorBody)
                    .font(.system(.body, design: .monospaced))
                    .frame(minHeight: 300)
                HStack(spacing: 12) {
                    Button("从磁盘重新载入") { reloadFromDisk() }
                    Button("保存模版到磁盘") { saveTemplateToDisk() }
                }
                if !editorStatus.isEmpty {
                    Text(editorStatus)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Section("模版列表与新建") {
                Button("将当前路径加入列表（若尚未列出）") { addCurrentPathToPresets() }
                Button("新建模版文件…") { showNewSheet = true }
                Text("内置四项可直接选用；自定义项在「保存到磁盘」写入 settings.json 的 `prompt_presets` 后出现。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .onAppear { reloadFromDisk() }
        .sheet(isPresented: $showNewSheet) {
            Form {
                TextField("列表中的显示名", text: $newLabel)
                TextField("相对项目根的路径", text: $newRelativePath)
                Text("若文件不存在，将写入一份简单 Markdown 骨架。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                HStack {
                    Button("取消", role: .cancel) { showNewSheet = false }
                    Spacer()
                    Button("创建并选用") { confirmNewTemplate() }
                }
            }
            .padding(16)
            .frame(minWidth: 420, minHeight: 200)
        }
    }

    private func reloadFromDisk() {
        editorStatus = ""
        let path = settings.templates.dailyPrompt
        do {
            editorBody = try model.readProjectTextFile(relativePath: path)
        } catch {
            editorBody = ""
            editorStatus = "读取失败：\(error.localizedDescription)"
        }
    }

    private func saveTemplateToDisk() {
        do {
            try model.writeProjectTextFile(relativePath: settings.templates.dailyPrompt, content: editorBody)
            editorStatus = "已保存 \(settings.templates.dailyPrompt)"
        } catch {
            editorStatus = "保存失败：\(error.localizedDescription)"
        }
    }

    private func addCurrentPathToPresets() {
        let path = settings.templates.dailyPrompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !path.isEmpty else { return }
        var list = settings.templates.promptPresets ?? TemplatePresetCatalog.builtin
        guard !list.contains(where: { $0.path == path }) else {
            editorStatus = "该路径已在列表中。"
            return
        }
        let tail = path.split(separator: "/").last.map(String.init) ?? path
        list.append(TemplatePreset(id: UUID().uuidString, label: tail, path: path))
        settings.templates.promptPresets = list
        editorStatus = "已加入列表；请再点侧栏「保存到磁盘」写入 settings.json。"
    }

    private func confirmNewTemplate() {
        let path = newRelativePath.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !path.isEmpty else { return }
        let label = newLabel.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? (path.split(separator: "/").last.map(String.init) ?? path)
            : newLabel.trimmingCharacters(in: .whitespacesAndNewlines)

        var list = settings.templates.promptPresets ?? TemplatePresetCatalog.builtin
        if !list.contains(where: { $0.path == path }) {
            list.append(TemplatePreset(id: UUID().uuidString, label: label, path: path))
            settings.templates.promptPresets = list
        }
        settings.templates.dailyPrompt = path

        let starter = """
        # 日报提示词

        请基于 Personal Growth OS 今日数据，生成 **{date}** 的每日总结。

        （在此编写你对结构、语气与优先级的说明。）
        """
        do {
            if let u = model.fileURLForProjectRelativePath(path), !FileManager.default.fileExists(atPath: u.path) {
                try model.writeProjectTextFile(relativePath: path, content: starter)
            }
        } catch {
            editorStatus = "创建文件失败：\(error.localizedDescription)"
            showNewSheet = false
            return
        }
        reloadFromDisk()
        showNewSheet = false
        editorStatus = "已创建并切换到新模版；请保存 settings.json 与模版正文。"
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
            case .prefsGrowthDimensions:
                PrefsGrowthDimensionsView()
            case .prefsGeneral, .prefsApi, .prefsNotifications, .prefsAdvanced, .prefsTemplates:
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
                    case .prefsTemplates:
                        PrefsTemplatesView(settings: binding(settings))
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
