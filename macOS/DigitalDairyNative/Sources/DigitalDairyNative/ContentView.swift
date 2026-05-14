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
        case .prefsGeneral, .prefsApi, .prefsCollectors, .prefsNotifications, .prefsAdvanced,
             .prefsGrowthDimensions, .prefsTemplates:
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
                        switch tab {
                        case .prefsCollectors:
                            model.saveToolSwitchesToDisk()
                        case .prefsGrowthDimensions:
                            model.saveGrowthDimensionsToDisk()
                        default:
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
        case .prefsGeneral, .prefsApi, .prefsNotifications, .prefsAdvanced, .prefsTemplates:
            return model.appSettings != nil
        case .prefsCollectors:
            return true
        case .prefsGrowthDimensions:
            return model.growthDimensionsFile != nil
        default:
            return false
        }
    }
}

// MARK: - 首页

private struct RunTabView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 28) {
                HomeHeroSection()
                HomeInboxSection()
                HomeReplySection()
                HomeActionGrid()
                HomeStatusSection()
                HomeLogSection()
            }
            .padding(24)
        }
        .onAppear {
            model.refreshHomePanels()
        }
    }
}

// MARK: - Inbox & Reply

private struct HomeInboxSection: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "tray.and.arrow.down.fill")
                    .foregroundStyle(Color(hex: "#7FA8FF"))
                Text("今日感想")
                    .font(.system(.title3, design: .rounded).weight(.semibold))
                Spacer()
                Button("保存") {
                    model.saveTodayInbox()
                }
                .disabled(model.settingsTargetRoot() == nil)
            }
            Text("写下今天想让日报参考的线索（对应 data/inbox/日期-today.md）。保存后点「生成今日日报」会并入提示词。")
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            TextEditor(text: $model.todayInboxText)
                .font(.system(.body, design: .rounded))
                .scrollContentBackground(.hidden)
                .frame(minHeight: 120)
                .padding(8)
                .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(.ultraThinMaterial))
                .overlay(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .strokeBorder(.primary.opacity(0.06), lineWidth: 1)
                )
        }
        .padding(16)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .strokeBorder(.primary.opacity(0.05), lineWidth: 1)
        )
    }
}

private struct HomeReplySection: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "bubble.left.and.bubble.right.fill")
                    .foregroundStyle(Color(hex: "#9DE7D7"))
                Text("今日提问")
                    .font(.system(.title3, design: .rounded).weight(.semibold))
                Spacer()
                Button("提问") {
                    model.runHomeReply()
                }
                .disabled(
                    model.busy
                        || model.homeReplyQuestion.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                )
            }
            Text("基于当天已保存的总结与 events（scripts/answer_reply.py）进行问答。结果写入 data/replies/日期-reply.md，并显示在下方。")
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            TextField("例如：今天最值得肯定的瞬间是什么？", text: $model.homeReplyQuestion, axis: .vertical)
                .lineLimit(3, reservesSpace: true)
                .textFieldStyle(.roundedBorder)
            if model.homeReplyOutput.isEmpty {
                Text("（尚无回答，填写问题后点「提问」）")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            } else {
                ScrollView {
                    Text(model.homeReplyOutput)
                        .font(.system(.body, design: .rounded))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .textSelection(.enabled)
                }
                .frame(minHeight: 100, maxHeight: 280)
                .padding(12)
                .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(.ultraThinMaterial))
                .overlay(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .strokeBorder(.primary.opacity(0.06), lineWidth: 1)
                )
            }
        }
        .padding(16)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .strokeBorder(.primary.opacity(0.05), lineWidth: 1)
        )
    }
}

// MARK: Hero

private struct HomeHeroSection: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        HStack(spacing: 20) {
            if let url = Bundle.module.url(forResource: "DigitalDiary", withExtension: "png"),
               let img = NSImage(contentsOf: url) {
                Image(nsImage: img)
                    .resizable()
                    .scaledToFit()
                    .frame(width: 72, height: 72)
                    .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                    .shadow(color: .black.opacity(0.18), radius: 8, x: 0, y: 4)
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("Digital Dairy")
                    .font(.system(.largeTitle, design: .rounded).weight(.bold))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color(hex: "#7FA8FF"), Color(hex: "#9DE7D7")],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                Text("Personal Growth OS · 记录每一天，洞见长期成长")
                    .font(.system(.title3, design: .rounded))
                    .foregroundStyle(.secondary)
            }

            Spacer()
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(.ultraThinMaterial)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .strokeBorder(
                    LinearGradient(
                        colors: [Color(hex: "#7FA8FF").opacity(0.4), Color(hex: "#9DE7D7").opacity(0.3)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    lineWidth: 1
                )
        )
    }
}

// MARK: Action Grid

private struct HomeActionGrid: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("快捷操作")
                .font(.system(.headline, design: .rounded))
                .foregroundStyle(.secondary)

            LazyVGrid(
                columns: [GridItem(.flexible(), spacing: 12), GridItem(.flexible(), spacing: 12)],
                spacing: 12
            ) {
                HomeActionButton(
                    title: "生成今日日报",
                    subtitle: "AI 分析今日数据，生成每日总结",
                    icon: "sparkles",
                    gradient: [Color(hex: "#7FA8FF"), Color(hex: "#6B8EE8")],
                    disabled: model.busy
                ) { model.runDaily() }

                HomeActionButton(
                    title: "仅采集数据",
                    subtitle: "收集今日数据，不调用 AI",
                    icon: "arrow.down.circle.fill",
                    gradient: [Color(hex: "#9DE7D7"), Color(hex: "#5BBFA8")],
                    disabled: model.busy
                ) { model.runDry() }

                HomeActionButton(
                    title: "查看今日日报",
                    subtitle: "在侧栏「日报阅览」查看正文",
                    icon: "doc.text.fill",
                    gradient: [Color(hex: "#FFB86C"), Color(hex: "#F4934A")],
                    disabled: false
                ) { model.openTodaySummaryExternally() }

                HomeActionButton(
                    title: model.isBundled ? "打开数据目录" : "在 Finder 中打开",
                    subtitle: "在 Finder 中浏览文件",
                    icon: "folder.fill",
                    gradient: [Color(hex: "#BD93F9"), Color(hex: "#9872D8")],
                    disabled: false
                ) { model.openInFinder() }
            }

            if !model.isBundled {
                HomeActionButton(
                    title: "选择项目目录…",
                    subtitle: model.projectPathDisplay == "未选择" ? "尚未配置，点此选择仓库根目录" : model.projectPathDisplay,
                    icon: "folder.badge.plus",
                    gradient: [Color.gray.opacity(0.6), Color.gray.opacity(0.4)],
                    disabled: false
                ) { model.chooseProjectFolder() }
            }
        }
    }
}

private struct HomeActionButton: View {
    let title: String
    let subtitle: String
    let icon: String
    let gradient: [Color]
    let disabled: Bool
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 14) {
                ZStack {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(LinearGradient(colors: gradient, startPoint: .topLeading, endPoint: .bottomTrailing))
                        .frame(width: 48, height: 48)
                    Image(systemName: icon)
                        .font(.system(size: 22, weight: .semibold))
                        .foregroundStyle(.white)
                }

                VStack(alignment: .leading, spacing: 3) {
                    Text(title)
                        .font(.system(.body, design: .rounded).weight(.semibold))
                        .foregroundStyle(.primary)
                    Text(subtitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }
            .padding(14)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(isHovered ? AnyShapeStyle(.thinMaterial) : AnyShapeStyle(.ultraThinMaterial))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .strokeBorder(.primary.opacity(0.06), lineWidth: 1)
            )
            .scaleEffect(isHovered ? 1.01 : 1.0)
            .animation(.spring(response: 0.2, dampingFraction: 0.7), value: isHovered)
        }
        .buttonStyle(.plain)
        .disabled(disabled)
        .opacity(disabled ? 0.5 : 1.0)
        .onHover { isHovered = $0 }
    }
}

// MARK: Status

private struct HomeStatusSection: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        HStack(spacing: 10) {
            Circle()
                .fill(model.busy ? Color.orange : Color.green)
                .frame(width: 8, height: 8)
                .shadow(color: model.busy ? .orange : .green, radius: 4)
            Text(model.busy ? "运行中…" : model.statusText)
                .font(.system(.callout, design: .rounded))
                .foregroundStyle(.secondary)
            Spacer()
            if !model.isBundled {
                Text(model.projectPathDisplay)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .textSelection(.enabled)
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .frame(maxWidth: 280)
            }
        }
        .padding(.horizontal, 4)
    }
}

// MARK: Log

private struct HomeLogSection: View {
    @EnvironmentObject private var model: AppModel
    @State private var isExpanded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Button {
                withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                    isExpanded.toggle()
                }
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "terminal.fill")
                        .foregroundStyle(.secondary)
                    Text("运行日志")
                        .font(.system(.headline, design: .rounded))
                        .foregroundStyle(.secondary)
                    Spacer()
                    Image(systemName: isExpanded ? "chevron.up" : "chevron.down")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.tertiary)
                }
            }
            .buttonStyle(.plain)

            if isExpanded {
                ScrollView {
                    Text(model.logText.isEmpty ? "（尚无输出）" : model.logText)
                        .font(.system(.body, design: .monospaced))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .textSelection(.enabled)
                        .padding(12)
                }
                .frame(minHeight: 120, maxHeight: 320)
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .strokeBorder(.primary.opacity(0.06), lineWidth: 1)
                )
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .padding(16)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .strokeBorder(.primary.opacity(0.05), lineWidth: 1)
        )
    }
}
