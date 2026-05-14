import SwiftUI

struct MarkdownDailyView: View {
    @EnvironmentObject private var model: AppModel
    @State private var preparedMarkdown: String = ""
    @State private var loadMessage: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
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

            if !loadMessage.isEmpty {
                Text(loadMessage)
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("✨ 今日总结")
                        .font(.system(.title2, design: .rounded).weight(.semibold))
                        .foregroundStyle(.primary)
                    WrappingMarkdownTextView(markdown: preparedMarkdown)
                        .frame(minWidth: 0, maxWidth: .infinity, minHeight: 120, alignment: .leading)
                }
                .padding(18)
            }
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(.ultraThinMaterial)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .strokeBorder(
                        LinearGradient(
                            colors: [
                                Color.purple.opacity(0.22),
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
        .padding(14)
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
            commit("未找到数据目录。")
            return
        }
        guard FileManager.default.fileExists(atPath: url.path) else {
            commit("该日尚无总结文件。可先运行「生成今日日报」或选择其它日期。✨")
            return
        }
        do {
            let raw = try String(contentsOf: url, encoding: .utf8)
            let prepared = DailySummaryMarkdown.prepareSourceForParsing(raw)
            commit(prepared)
        } catch {
            commit("读取失败：\(error.localizedDescription)")
        }
    }
}
