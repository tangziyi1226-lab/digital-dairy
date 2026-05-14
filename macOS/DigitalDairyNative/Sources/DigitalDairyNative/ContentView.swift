import AppKit
import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        ZStack {
            VisualEffectBackground()
            LinearGradient(
                colors: [
                    Color(hex: model.themeStartHex).opacity(0.42),
                    Color(hex: model.themeEndHex).opacity(0.38),
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .allowsHitTesting(false)

            NavigationSplitView {
                List(selection: $model.sidebarSelection) {
                    Section("工作台") {
                        ForEach(AppModel.SidebarItem.items(in: 0)) { item in
                            Label(item.rawValue, systemImage: item.symbolName)
                                .tag(item)
                        }
                    }
                    Section("偏好设置") {
                        ForEach(AppModel.SidebarItem.items(in: 1)) { item in
                            Label(item.rawValue, systemImage: item.symbolName)
                                .tag(item)
                        }
                    }
                    Section("其他") {
                        ForEach(AppModel.SidebarItem.items(in: 2)) { item in
                            Label(item.rawValue, systemImage: item.symbolName)
                                .tag(item)
                        }
                    }
                }
                .listStyle(.sidebar)
                .scrollContentBackground(.hidden)
                .background(.ultraThinMaterial)
                .navigationSplitViewColumnWidth(min: 210, ideal: 240, max: 300)
            } detail: {
                detailContent
                    .background(.regularMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    .padding(10)
            }
            .navigationTitle(AppModel.appName)
        }
        .alert(model.alertTitle, isPresented: $model.showAlert) {
            Button("好", role: .cancel) {}
        } message: {
            Text(model.alertMessage)
        }
    }

    @ViewBuilder
    private var detailContent: some View {
        switch model.sidebarSelection {
        case .run:
            RunTabView()
        case .dailyReport:
            MarkdownDailyView()
        case .charts:
            EventChartsView()
        case .prefsGeneral, .prefsApi, .prefsCollectors, .prefsNotifications, .prefsAdvanced:
            PreferenceDetailShell(tab: model.sidebarSelection)
        case .appearance:
            ScrollView {
                AppearancePanel()
            }
            .padding(8)
        case .about:
            AboutPanel()
        }
    }
}

// MARK: - 偏好页外壳（保存 / 重新载入）

private struct PreferenceDetailShell: View {
    @EnvironmentObject private var model: AppModel
    let tab: AppModel.SidebarItem

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                PreferencesHostView(tab: tab)
                    .padding(.bottom, 8)
            }
            if showsActionBar {
                HStack(spacing: 12) {
                    Button("保存到磁盘") {
                        if tab == .prefsCollectors {
                            model.saveToolSwitchesToDisk()
                        } else {
                            model.saveAppSettingsToDisk()
                        }
                    }
                    .keyboardShortcut("s", modifiers: [.command])
                    Button("重新载入") {
                        model.loadConfiguration()
                    }
                    Spacer()
                }
                .padding(12)
                .background(.ultraThinMaterial)
            }
        }
    }

    private var showsActionBar: Bool {
        guard model.settingsTargetRoot() != nil else { return false }
        switch tab {
        case .prefsGeneral, .prefsApi, .prefsNotifications, .prefsAdvanced:
            return model.appSettings != nil
        case .prefsCollectors:
            return true
        default:
            return false
        }
    }
}

// MARK: - 运行

private struct RunTabView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        HSplitView {
            Form {
                Section("目录") {
                    LabeledContent("路径") {
                        Text(model.projectPathDisplay)
                            .font(.callout)
                            .textSelection(.enabled)
                            .multilineTextAlignment(.trailing)
                    }
                    if !model.isBundled {
                        Button("选择项目目录…") {
                            model.chooseProjectFolder()
                        }
                    } else {
                        Text("安装版已自动使用「文稿」目录")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Section("快捷操作") {
                    Button("生成今日日报") { model.runDaily() }
                        .disabled(model.busy)
                    Button("仅采集（Dry Run）") { model.runDry() }
                        .disabled(model.busy)
                    Button("用外部编辑器打开今日总结") { model.openTodaySummaryExternally() }
                    Button(model.isBundled ? "在 Finder 中打开数据目录" : "在 Finder 中打开项目") {
                        model.openInFinder()
                    }
                }

                Section("提示") {
                    Text("日报正文与图表请在侧栏「日报阅览」「数据图表」查看；生成时已跳过 HTML 截图附录。")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .formStyle(.grouped)
            .frame(minWidth: 280, idealWidth: 320, maxWidth: 400)
            .scrollContentBackground(.hidden)
            .background(.thinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))

            RunLogPanel()
                .frame(minWidth: 360)
        }
        .padding(14)
    }
}

private struct RunLogPanel: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("运行日志")
                    .font(.title3.weight(.semibold))
                Spacer()
                Text(model.statusText)
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }

            ScrollView {
                Text(model.logText.isEmpty ? "（尚无输出）" : model.logText)
                    .font(.system(.body, design: .monospaced))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
            }
            .padding(10)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
        }
        .padding(10)
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}
