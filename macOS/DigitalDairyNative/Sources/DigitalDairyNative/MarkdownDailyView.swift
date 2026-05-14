import SwiftUI

struct MarkdownDailyView: View {
    @EnvironmentObject private var model: AppModel
    @State private var attributed = AttributedString()
    @State private var loadMessage: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("日报阅览")
                    .font(.title3.weight(.semibold))
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
                Text(attributed)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
                    .padding(12)
            }
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
        .padding(14)
        .onAppear(perform: reload)
        .onChange(of: model.dashboardDate) { _, _ in reload() }
        .onChange(of: model.configurationEpoch) { _, _ in reload() }
    }

    private func reload() {
        guard let url = model.summaryURL(for: model.dashboardDate) else {
            attributed = AttributedString("未找到数据目录。")
            loadMessage = ""
            return
        }
        guard FileManager.default.fileExists(atPath: url.path) else {
            attributed = AttributedString("该日尚无总结文件。可先运行「生成今日日报」或选择其它日期。")
            loadMessage = ""
            return
        }
        do {
            let raw = try String(contentsOf: url, encoding: .utf8)
            var opts = AttributedString.MarkdownParsingOptions()
            opts.interpretedSyntax = .full
            if let parsed = try? AttributedString(markdown: raw, options: opts) {
                attributed = parsed
            } else {
                attributed = AttributedString(raw)
            }
            loadMessage = ""
        } catch {
            attributed = AttributedString("读取失败：\(error.localizedDescription)")
            loadMessage = ""
        }
    }
}
