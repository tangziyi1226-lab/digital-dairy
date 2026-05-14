import MarkdownUI
import SwiftUI

struct MarkdownDailyView: View {
    @EnvironmentObject private var model: AppModel
    @State private var preparedMarkdown: String = ""
    @State private var loadMessage: String = ""

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                // 顶部标题栏
                HStack {
                    Text("📔 日报阅览")
                        .font(.system(.title3, design: .rounded).weight(.semibold))
                    Spacer()
                    DatePicker(
                        "日期",
                        selection: $model.dashboardDate,
                        displayedComponents: .date
                    )
                    .labelsHidden()
                }

                if let url = model.summaryURL(for: model.dashboardDate) {
                    Text(url.path)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .textSelection(.enabled)
                }

                // 状态消息
                if !loadMessage.isEmpty {
                    HStack(spacing: 8) {
                        Image(systemName: "info.circle")
                            .foregroundStyle(.secondary)
                        Text(loadMessage)
                            .font(.callout)
                            .foregroundStyle(.secondary)
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                }

                // 内容卡片
                if !preparedMarkdown.isEmpty {
                    VStack(alignment: .leading, spacing: 14) {
                        HStack(spacing: 6) {
                            Text("✨")
                            Text("今日总结")
                                .font(.system(.title2, design: .rounded).weight(.semibold))
                                .foregroundStyle(.primary)
                        }

                        Divider()
                            .opacity(0.4)

                        // 基于 GitHub 主题，但去掉 `.text` 上大块 BackgroundColor（深色模式会像整板黑底）
                        Markdown(preparedMarkdown)
                            .markdownTheme(.digitalDairyReading)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .textSelection(.enabled)
                    }
                    .padding(20)
                    .background(
                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                            .fill(.ultraThinMaterial)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                            .strokeBorder(
                                LinearGradient(
                                    colors: [
                                        Color.purple.opacity(0.25),
                                        Color.mint.opacity(0.18),
                                        Color.blue.opacity(0.15),
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                ),
                                lineWidth: 1
                            )
                    )
                }
            }
            .padding(16)
        }
        .onAppear(perform: reload)
        .onChange(of: model.dashboardDate) { _, _ in reload() }
        .onChange(of: model.configurationEpoch) { _, _ in reload() }
    }

    private func reload() {
        func commit(_ text: String, message: String = "") {
            preparedMarkdown = text
            loadMessage = message
        }
        guard let url = model.summaryURL(for: model.dashboardDate) else {
            commit("", message: "未找到数据目录。")
            return
        }
        guard FileManager.default.fileExists(atPath: url.path) else {
            commit("", message: "该日尚无总结文件。可先运行「生成今日日报」或选择其它日期。✨")
            return
        }
        do {
            let raw = try String(contentsOf: url, encoding: .utf8)
            let prepared = DailySummaryMarkdown.prepareSourceForParsing(raw)
            commit(prepared)
        } catch {
            commit("", message: "读取失败：\(error.localizedDescription)")
        }
    }
}

// MARK: - 阅读用 Markdown 主题

private extension Theme {
    /// 自 `.gitHub` 派生：去掉正文整块 `BackgroundColor`（深色模式下会像黑板贴在卡片上）；
    /// 正文用系统衬线、略增行距与段距；代码块用浅色高光替代深色底。
    static var digitalDairyReading: Theme {
        Theme.gitHub
            .text {
                ForegroundColor(.primary)
                BackgroundColor(nil)
                FontFamily(.system(.serif))
                FontSize(16)
            }
            .code {
                FontFamilyVariant(.monospaced)
                FontSize(.em(0.88))
                ForegroundColor(.primary)
                BackgroundColor(Color.primary.opacity(0.1))
            }
            .paragraph { configuration in
                configuration.label
                    .fixedSize(horizontal: false, vertical: true)
                    .relativeLineSpacing(.em(0.42))
                    .markdownMargin(top: 0, bottom: 18)
            }
            .codeBlock { configuration in
                ScrollView(.horizontal) {
                    configuration.label
                        .fixedSize(horizontal: false, vertical: true)
                        .relativeLineSpacing(.em(0.28))
                        .markdownTextStyle {
                            FontFamilyVariant(.monospaced)
                            FontSize(.em(0.88))
                        }
                        .padding(14)
                }
                .background(Color.primary.opacity(0.07))
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .markdownMargin(top: 0, bottom: 16)
            }
            .listItem { configuration in
                configuration.label
                    .markdownMargin(top: .em(0.42))
            }
    }
}
