import Charts
import SwiftUI

struct EventChartsView: View {
    @EnvironmentObject private var model: AppModel
    @State private var sources: [EventInsights.SourceCount] = []
    @State private var hours: [EventInsights.HourCount] = []
    @State private var types: [EventInsights.TypeCount] = []
    @State private var total: Int = 0
    @State private var hint: String = ""

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                HStack {
                    Text("数据图表")
                        .font(.title3.weight(.semibold))
                    Spacer()
                    DatePicker(
                        "日期",
                        selection: $model.dashboardDate,
                        displayedComponents: .date
                    )
                    .labelsHidden()
                }

                if let url = model.eventsURL(for: model.dashboardDate) {
                    Text(url.path)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .textSelection(.enabled)
                }

                if !hint.isEmpty {
                    Text(hint)
                        .foregroundStyle(.secondary)
                } else {
                    Text("共 \(total) 条事件（来自当日 events JSON）")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }

                chartCard(title: "按来源分布") {
                    if sources.isEmpty {
                        Text("无数据").foregroundStyle(.secondary)
                    } else {
                        Chart(sources) { row in
                            BarMark(
                                x: .value("条数", row.count),
                                y: .value("来源", row.source)
                            )
                            .annotation(position: .trailing) {
                                Text("\(row.count)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .chartXAxisLabel("事件条数")
                        .frame(minHeight: min(520, CGFloat(sources.count) * 28 + 40))
                    }
                }

                chartCard(title: "按小时分布（本地时间戳）") {
                    Chart(hours) { row in
                        BarMark(
                            x: .value("小时", row.hour),
                            y: .value("条数", row.count)
                        )
                        .foregroundStyle(.blue.gradient)
                    }
                    .chartXScale(domain: 0 ... 23)
                    .chartXAxisLabel("小时")
                    .chartYAxisLabel("条数")
                    .frame(height: 200)
                }

                chartCard(title: "按类型分布") {
                    if types.isEmpty {
                        Text("无数据").foregroundStyle(.secondary)
                    } else {
                        Chart(types.prefix(12)) { row in
                            SectorMark(
                                angle: .value("条数", row.count),
                                innerRadius: .ratio(0.45),
                                angularInset: 1.5
                            )
                            .foregroundStyle(by: .value("类型", row.typeName))
                        }
                        .chartLegend(position: .bottom, alignment: .center, spacing: 8)
                        .frame(height: 280)
                    }
                }
            }
            .padding(14)
        }
        .onAppear(perform: reload)
        .onChange(of: model.dashboardDate) { _, _ in reload() }
        .onChange(of: model.configurationEpoch) { _, _ in reload() }
    }

    @ViewBuilder
    private func chartCard(title: String, @ViewBuilder content: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
            content()
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func reload() {
        guard let url = model.eventsURL(for: model.dashboardDate) else {
            hint = "未找到数据目录。"
            clear()
            return
        }
        guard FileManager.default.fileExists(atPath: url.path) else {
            hint = "该日尚无 events JSON。可先运行「仅采集」或「生成今日日报」。"
            clear()
            return
        }
        if let pack = EventInsights.load(from: url) {
            sources = pack.sources
            hours = pack.hours
            types = pack.types
            total = pack.total
            hint = ""
        } else {
            hint = "无法解析事件文件。"
            clear()
        }
    }

    private func clear() {
        sources = []
        hours = []
        types = []
        total = 0
    }
}
