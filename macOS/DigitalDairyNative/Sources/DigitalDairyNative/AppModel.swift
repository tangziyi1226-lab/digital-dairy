import AppKit
import Combine
import Foundation
import SwiftUI

@MainActor
final class AppModel: ObservableObject {
    enum SidebarItem: String, CaseIterable, Identifiable {
        case run = "运行与日志"
        case dailyReport = "日报阅览"
        case charts = "数据图表"
        case prefsGeneral = "常规与日程"
        case prefsApi = "模型与 API"
        case prefsCollectors = "采集数据源"
        case prefsNotifications = "通知"
        case prefsAdvanced = "高级与保留"
        case prefsGrowthDimensions = "成长维度"
        case prefsTemplates = "模版设置"
        case appearance = "外观与主题"
        case about = "关于"

        var id: String { rawValue }

        var symbolName: String {
            switch self {
            case .run: return "play.circle"
            case .dailyReport: return "doc.text"
            case .charts: return "chart.bar"
            case .prefsGeneral: return "person.text.rectangle"
            case .prefsApi: return "cpu"
            case .prefsCollectors: return "arrow.down.doc"
            case .prefsNotifications: return "bell"
            case .prefsAdvanced: return "slider.horizontal.3"
            case .prefsGrowthDimensions: return "leaf.fill"
            case .prefsTemplates: return "doc.richtext"
            case .appearance: return "paintpalette"
            case .about: return "info.circle"
            }
        }

        var sidebarSection: Int {
            switch self {
            case .run, .dailyReport, .charts: return 0
            case .prefsGeneral, .prefsApi, .prefsCollectors, .prefsNotifications, .prefsAdvanced,
                 .prefsGrowthDimensions, .prefsTemplates:
                return 1
            case .appearance, .about: return 2
            }
        }

        var sectionTitle: String {
            switch sidebarSection {
            case 0: return "工作台"
            case 1: return "偏好设置"
            default: return "其他"
            }
        }

        static func items(in section: Int) -> [SidebarItem] {
            allCases.filter { $0.sidebarSection == section }
        }
    }

    static let appName = "Digital Dairy"
    private static let writableDisplayName = "DigitalDairy"

    @Published var sidebarSelection: SidebarItem = .run
    @Published var projectPathDisplay: String = ""
    @Published var isBundled: Bool = false
    @Published var statusText: String = "就绪"
    @Published var logText: String = ""
    @Published var busy: Bool = false
    @Published var themeStartHex: String = "#7FA8FF"
    @Published var themeEndHex: String = "#9DE7D7"
    @Published var dashboardDate: Date = .init()
    @Published var appSettings: AppSettings?
    @Published var toolSwitches: [String: ToolSwitchRow] = [:]
    @Published var settingsFormError: String?
    @Published var growthDimensionsFile: GrowthDimensionsFile?
    @Published var growthDimensionsError: String?
    @Published var configurationEpoch: Int = 0
    @Published var alertTitle: String = ""
    @Published var alertMessage: String = ""
    @Published var showAlert: Bool = false

    private var state: [String: String] = [:]
    private let writableRoot: URL
    private var payloadRoot: URL?
    private var projectRoot: URL?

    private var stateURL: URL {
        writableRoot.appendingPathComponent("state.json")
    }

    init() {
        let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        writableRoot = documents.appendingPathComponent(Self.writableDisplayName, isDirectory: true)
        try? FileManager.default.createDirectory(at: writableRoot, withIntermediateDirectories: true)

        loadState()
        themeStartHex = Self.normalizeHex(state["theme_start"] ?? themeStartHex, fallback: "#7FA8FF")
        themeEndHex = Self.normalizeHex(state["theme_end"] ?? themeEndHex, fallback: "#9DE7D7")

        resolveRoots()
        projectPathDisplay = displayProjectPath()

        if isBundled, let payload = payloadRoot {
            do {
                try UserLayout.ensureUserLayout(payload: payload, writable: writableRoot)
                projectRoot = writableRoot
                projectPathDisplay = displayProjectPath()
                appendLog("安装版：脚本在应用包内；配置与数据在「文稿/\(Self.writableDisplayName)」。")
            } catch {
                appendLog("初始化用户目录失败：\(error.localizedDescription)")
            }
        } else {
            if projectRoot == nil, let dev = Self.findDevRepoRoot() {
                projectRoot = dev
                state["project_root"] = dev.path
                saveState()
            }
            projectPathDisplay = displayProjectPath()
        }

        loadConfiguration()
    }

    func dayString(_ date: Date) -> String {
        Self.localYyyyMmDd(date)
    }

    func summaryURL(for date: Date) -> URL? {
        guard let root = settingsTargetRoot() else { return nil }
        return root.appendingPathComponent("data/summaries/\(dayString(date))-summary.md")
    }

    func eventsURL(for date: Date) -> URL? {
        guard let root = settingsTargetRoot() else { return nil }
        return root.appendingPathComponent("data/events/\(dayString(date))-events.json")
    }

    func saveTheme() {
        state["theme_start"] = themeStartHex
        state["theme_end"] = themeEndHex
        saveState()
    }

    func loadConfiguration() {
        settingsFormError = nil
        guard let root = settingsTargetRoot() else {
            appSettings = nil
            toolSwitches = [:]
            growthDimensionsFile = nil
            growthDimensionsError = nil
            settingsFormError = "未找到配置根目录（开发版请在「运行与日志」中选择仓库根目录）。"
            configurationEpoch += 1
            return
        }
        let settingsURL = root.appendingPathComponent("config/settings.json")
        if FileManager.default.fileExists(atPath: settingsURL.path) {
            do {
                appSettings = try AppSettings.load(from: settingsURL)
            } catch {
                appSettings = nil
                settingsFormError = "读取 settings.json 失败：\(error.localizedDescription)"
            }
        } else {
            appSettings = nil
            settingsFormError = "未找到 config/settings.json。安装版首次启动应已自动生成；若缺失请删除「文稿/\(Self.writableDisplayName)/config」后重启应用。"
        }

        let toolURL = toolSwitchesFileURL(projectRoot: root, settings: appSettings)
        if FileManager.default.fileExists(atPath: toolURL.path) {
            do {
                let raw = try ToolSwitchesFile.load(from: toolURL)
                toolSwitches = ToolSwitchesFile.normalized(raw)
            } catch {
                toolSwitches = ToolSwitchesFile.normalized([:])
                settingsFormError = (settingsFormError.map { $0 + "\n" } ?? "")
                    + "读取 tool_switches 失败：\(error.localizedDescription)"
            }
        } else {
            toolSwitches = ToolSwitchesFile.normalized([:])
        }

        growthDimensionsFile = nil
        growthDimensionsError = nil
        let growthURL = root.appendingPathComponent("config/growth_dimensions.json")
        if FileManager.default.fileExists(atPath: growthURL.path) {
            do {
                growthDimensionsFile = try GrowthDimensionsFile.load(from: growthURL)
            } catch {
                growthDimensionsError = "读取 growth_dimensions.json 失败：\(error.localizedDescription)"
            }
        } else {
            growthDimensionsError = "未找到 config/growth_dimensions.json。"
        }

        configurationEpoch += 1
    }

    func saveAppSettingsToDisk() {
        guard let settings = appSettings, let root = settingsTargetRoot() else {
            presentAlert(title: Self.appName, message: "没有可保存的设置（请先解决读取错误）。")
            return
        }
        let url = root.appendingPathComponent("config/settings.json")
        do {
            try settings.save(to: url)
            presentAlert(title: Self.appName, message: "已保存「常规 / API / 通知」等设置。")
            loadConfiguration()
        } catch {
            presentAlert(title: "保存失败", message: error.localizedDescription)
        }
    }

    func saveToolSwitchesToDisk() {
        guard let root = settingsTargetRoot() else { return }
        let url = toolSwitchesFileURL(projectRoot: root, settings: appSettings)
        do {
            try ToolSwitchesFile.save(toolSwitches, to: url)
            presentAlert(title: Self.appName, message: "已保存采集开关。")
            loadConfiguration()
        } catch {
            presentAlert(title: "保存失败", message: error.localizedDescription)
        }
    }

    func saveGrowthDimensionsToDisk() {
        guard let doc = growthDimensionsFile, let root = settingsTargetRoot() else {
            presentAlert(title: Self.appName, message: "没有可保存的成长维度配置。")
            return
        }
        let url = root.appendingPathComponent("config/growth_dimensions.json")
        do {
            try doc.save(to: url)
            presentAlert(title: Self.appName, message: "已保存成长维度；下次采集 / 日报将按开关生效。")
            loadConfiguration()
        } catch {
            presentAlert(title: "保存失败", message: error.localizedDescription)
        }
    }

    func chooseProjectFolder() {
        guard !isBundled else {
            presentAlert(title: Self.appName, message: "安装版已将配置与数据放在「文稿/\(Self.writableDisplayName)」，无需选择项目。")
            return
        }
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.prompt = "选择"
        panel.message = "请选择 digital-dairy 仓库根目录（含 scripts/run_daily.py）"
        if panel.runModal() == .OK, let url = panel.url {
            guard Self.looksLikeProjectRoot(url) else {
                presentAlert(title: Self.appName, message: "该目录不是有效项目根目录（缺少 scripts/run_daily.py）。")
                return
            }
            projectRoot = url
            state["project_root"] = url.path
            saveState()
            projectPathDisplay = displayProjectPath()
            loadConfiguration()
            appendLog("已选择项目：\(url.path)")
        }
    }

    func runDaily() {
        // 可视化改由应用内 Swift Charts 呈现，不再附加 HTML/Playwright 截图到 Markdown。
        runSubprocess(label: "日报生成", extraArgs: ["--no-visual-screenshots"], needApi: true)
    }

    func runDry() {
        runSubprocess(label: "仅采集", extraArgs: ["--dry-run", "--no-notify"], needApi: false)
    }

    func openTodaySummaryExternally() {
        guard let ctx = dailyContext() else {
            presentAlert(title: Self.appName, message: "无法打开：请先完成项目配置。")
            return
        }
        let (_, writable) = ctx
        let day = Self.localYyyyMmDd(Date())
        let path = writable.appendingPathComponent("data/summaries/\(day)-summary.md")
        guard FileManager.default.fileExists(atPath: path.path) else {
            presentAlert(title: Self.appName, message: "未找到：\(path.path)")
            return
        }
        NSWorkspace.shared.open(path)
    }

    func openInFinder() {
        guard let ctx = dailyContext() else {
            presentAlert(title: Self.appName, message: "无法打开：请先完成项目配置。")
            return
        }
        let (code, writable) = ctx
        let target = isBundled ? writable : code
        NSWorkspace.shared.open(target)
    }

    func appendLog(_ line: String) {
        if logText.isEmpty {
            logText = line
        } else {
            logText += "\n" + line
        }
    }

    private func presentAlert(title: String, message: String) {
        alertTitle = title
        alertMessage = message
        showAlert = true
    }

    private func loadState() {
        guard FileManager.default.fileExists(atPath: stateURL.path) else {
            state = [:]
            return
        }
        do {
            let data = try Data(contentsOf: stateURL)
            let obj = try JSONSerialization.jsonObject(with: data)
            if let dict = obj as? [String: String] {
                state = dict
            } else if let dict = obj as? [String: Any] {
                state = dict.compactMapValues { "\($0)" }
            } else {
                state = [:]
            }
        } catch {
            state = [:]
        }
    }

    private func saveState() {
        do {
            let data = try JSONSerialization.data(withJSONObject: state, options: [.prettyPrinted, .sortedKeys])
            try FileManager.default.createDirectory(at: writableRoot, withIntermediateDirectories: true)
            try data.write(to: stateURL)
        } catch {
            appendLog("保存 state.json 失败：\(error.localizedDescription)")
        }
    }

    private func resolveRoots() {
        if let resource = Bundle.main.resourceURL {
            let candidate = resource.appendingPathComponent("app-runtime", isDirectory: true)
            let marker = candidate.appendingPathComponent("scripts/run_daily.py")
            if FileManager.default.fileExists(atPath: marker.path) {
                payloadRoot = candidate
                isBundled = true
                return
            }
        }
        isBundled = false
        payloadRoot = nil
        if let raw = state["project_root"]?.trimmingCharacters(in: .whitespacesAndNewlines), !raw.isEmpty {
            let url = URL(fileURLWithPath: (raw as NSString).expandingTildeInPath).resolvingSymlinksInPath()
            if Self.looksLikeProjectRoot(url) {
                projectRoot = url
            }
        }
    }

    private func displayProjectPath() -> String {
        if isBundled {
            return "\(writableRoot.path)（本应用数据目录，自动使用）"
        }
        if let p = projectRoot {
            return p.path
        }
        return "未选择"
    }

    func settingsTargetRoot() -> URL? {
        if isBundled {
            return writableRoot
        }
        if let p = projectRoot, Self.looksLikeProjectRoot(p) {
            return p
        }
        return nil
    }

    private func toolSwitchesFileURL(projectRoot: URL, settings: AppSettings?) -> URL {
        guard let s = settings else {
            return resolvedToolSwitchesURLLegacy(projectRoot: projectRoot)
        }
        let rel = s.toolSwitchesPath
        if rel.hasPrefix("/") {
            return URL(fileURLWithPath: rel)
        }
        return projectRoot.appendingPathComponent(rel)
    }

    private func resolvedToolSwitchesURLLegacy(projectRoot: URL) -> URL {
        let settingsPath = projectRoot.appendingPathComponent("config/settings.json")
        var relative = "config/tool_switches.json"
        if let data = try? Data(contentsOf: settingsPath),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let p = json["tool_switches_path"] as? String, !p.isEmpty
        {
            relative = p
        }
        if relative.hasPrefix("/") {
            return URL(fileURLWithPath: relative)
        }
        return projectRoot.appendingPathComponent(relative)
    }

    private func dailyContext() -> (code: URL, writable: URL)? {
        if isBundled, let payload = payloadRoot {
            return (payload, writableRoot)
        }
        if let p = projectRoot, Self.looksLikeProjectRoot(p) {
            return (p, p)
        }
        return nil
    }

    private func pythonCommand(codeRoot: URL) -> String {
        let venv = codeRoot.appendingPathComponent(".venv/bin/python3")
        if FileManager.default.fileExists(atPath: venv.path) {
            return venv.path
        }
        return "/usr/bin/env"
    }

    private func pythonArguments(codeRoot: URL, extraArgs: [String]) -> [String] {
        let cmd = pythonCommand(codeRoot: codeRoot)
        if cmd == "/usr/bin/env" {
            return ["python3", "scripts/run_daily.py"] + extraArgs
        }
        return ["scripts/run_daily.py"] + extraArgs
    }

    private func sanitizedEnvironment(writable: URL) -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        for k in ["PYTHONHOME", "PYTHONPATH", "PYTHONEXECUTABLE", "__PYVENV_LAUNCHER__"] {
            env.removeValue(forKey: k)
        }
        if env["PATH"] == nil || env["PATH"]?.isEmpty == true {
            env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin"
        }
        env["DIGITAL_DAIRY_USER_HOME"] = writable.path
        env["PYTHONUTF8"] = "1"
        return env
    }

    private func apiReady(writable: URL) -> (Bool, String) {
        if let s = appSettings {
            let envName = s.api.apiKeyEnv
            if let v = ProcessInfo.processInfo.environment[envName], !v.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                return (true, "")
            }
            let literal = s.api.apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
            if !literal.isEmpty, !literal.hasPrefix("PUT_") {
                return (true, "")
            }
            return (false, "未配置 API Key：请设置环境变量 \(envName)，或在「模型与 API」中填写密钥。")
        }
        let path = writable.appendingPathComponent("config/settings.json")
        guard FileManager.default.fileExists(atPath: path.path) else {
            return (false, "未找到 config/settings.json，请先在「常规与日程」保存一次配置。")
        }
        guard let data = try? Data(contentsOf: path),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return (false, "config/settings.json 解析失败。")
        }
        let api = json["api"] as? [String: Any] ?? [:]
        let envName = (api["api_key_env"] as? String).flatMap { $0.isEmpty ? nil : $0 } ?? "DEEPSEEK_API_KEY"
        if let v = ProcessInfo.processInfo.environment[envName], !v.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return (true, "")
        }
        let literal = (api["api_key"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if !literal.isEmpty, !literal.hasPrefix("PUT_") {
            return (true, "")
        }
        return (false, "未配置 API Key：请设置环境变量 \(envName)，或在「模型与 API」中填写密钥。")
    }

    private func runSubprocess(label: String, extraArgs: [String], needApi: Bool) {
        guard let ctx = dailyContext() else {
            presentAlert(title: Self.appName, message: "未找到有效的 digital-dairy 项目。开发版请先选择仓库根目录。")
            return
        }
        guard !busy else {
            presentAlert(title: Self.appName, message: "已有任务在运行，请稍候。")
            return
        }
        let (codeRoot, writable) = ctx
        if needApi {
            let (ok, msg) = apiReady(writable: writable)
            if !ok {
                presentAlert(title: Self.appName, message: msg)
                return
            }
        }

        busy = true
        statusText = "\(label) 运行中…"
        appendLog("--- 开始：\(label) ---")

        let pythonCmd = pythonCommand(codeRoot: codeRoot)
        let args = pythonArguments(codeRoot: codeRoot, extraArgs: extraArgs)
        let env = sanitizedEnvironment(writable: writable)

        Task.detached { [weak self] in
            let result = Self.runProcess(executable: pythonCmd, arguments: args, cwd: codeRoot, env: env)
            await MainActor.run { [weak self] in
                guard let self else { return }
                self.busy = false
                self.statusText = "就绪"
                self.appendLog("--- \(label) 结束 (exit \(result.code)) ---")
                if !result.output.isEmpty {
                    self.appendLog(result.output)
                }
                if result.code == 0 {
                    self.loadConfiguration()
                    self.presentAlert(title: Self.appName, message: "\(label)已完成。")
                } else {
                    self.presentAlert(title: Self.appName, message: "\(label)失败，请查看日志。")
                }
            }
        }
    }

    private nonisolated static func runProcess(
        executable: String,
        arguments: [String],
        cwd: URL,
        env: [String: String]
    ) -> (code: Int32, output: String) {
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: executable)
        proc.arguments = arguments
        proc.currentDirectoryURL = cwd
        proc.environment = env

        let pipe = Pipe()
        proc.standardOutput = pipe
        proc.standardError = pipe

        do {
            try proc.run()
            proc.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let text = String(data: data, encoding: .utf8) ?? ""
            return (proc.terminationStatus, text.trimmingCharacters(in: .whitespacesAndNewlines))
        } catch {
            return (127, error.localizedDescription)
        }
    }

    private static func looksLikeProjectRoot(_ url: URL) -> Bool {
        let runDaily = url.appendingPathComponent("scripts/run_daily.py")
        let tools = url.appendingPathComponent("tools")
        return FileManager.default.fileExists(atPath: runDaily.path)
            && FileManager.default.fileExists(atPath: tools.path)
    }

    private static func findDevRepoRoot() -> URL? {
        let thisFile = URL(fileURLWithPath: #filePath).resolvingSymlinksInPath()
        var cur = thisFile.deletingLastPathComponent()
        for _ in 0 ..< 12 {
            if looksLikeProjectRoot(cur) {
                return cur
            }
            cur = cur.deletingLastPathComponent()
            if cur.path == "/" { break }
        }
        return nil
    }

    private static func normalizeHex(_ value: String, fallback: String) -> String {
        let t = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard t.count == 7, t.hasPrefix("#"), let _ = UInt32(t.dropFirst(), radix: 16) else {
            return fallback
        }
        return t.uppercased()
    }

    private static func localYyyyMmDd(_ date: Date) -> String {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .gregorian)
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = .current
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: date)
    }
}
