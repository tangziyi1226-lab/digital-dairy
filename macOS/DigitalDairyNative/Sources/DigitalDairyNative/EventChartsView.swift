import AppKit
import Charts
import SwiftUI

struct EventChartsView: View {
    @EnvironmentObject private var model: AppModel
    @State private var sources: [EventInsights.SourceCount] = []
    @State private var hours: [EventInsights.HourCount] = []
    @State private var types: [EventInsights.TypeCount] = []
    @State private var dimensions: [EventInsights.DimensionCount] = []
    @State private var hosts: [EventInsights.HostCount] = []
    @State private var importance: [EventInsights.ImportanceBucket] = []
    @State private var total: Int = 0
    @State private var hint: String = ""

    private var dimensionTitleMap: [String: String] {
        var m: [String: String] = [:]
        for row in model.growthDimensionsFile?.dimensions ?? [] where row.enabled {
            m[row.id] = row.name
        }
        return m
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                headerBanner

                HStack {
                    Text("📊 数据图表")
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
                    Text("共 \(total) 条事件 · 含成长维度、域名与重要度分布")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }

                chartCard(title: "🗂 按来源分布") {
                    if sources.isEmpty {
                        Text("无数据").foregroundStyle(.secondary)
                    } else {
                        Chart(sources) { row in
                            BarMark(
                                x: .value("条数", row.count),
                                y: .value("来源", row.source)
                            )
                            .foregroundStyle(.purple.opacity(0.85).gradient)
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

                chartCard(title: "⏰ 按小时分布（时间戳内小时）") {
                    Chart(hours) { row in
                        BarMark(
                            x: .value("小时", row.hour),
                            y: .value("条数", row.count)
                        )
                        .foregroundStyle(
                            LinearGradient(
                                colors: [.cyan.opacity(0.9), .blue.opacity(0.75)],
                                startPoint: .bottom,
                                endPoint: .top
                            )
                        )
                    }
                    .chartXScale(domain: 0 ... 23)
                    .chartXAxisLabel("小时")
                    .chartYAxisLabel("条数")
                    .frame(height: 200)
                }

                chartCard(title: "🌿 成长维度（事件条数）") {
                    if dimensions.isEmpty {
                        Text("无维度标签（可先跑采集生成 events）。")
                            .foregroundStyle(.secondary)
                    } else {
                        Chart(dimensions.prefix(14)) { row in
                            BarMark(
                                x: .value("条数", row.count),
                                y: .value("维度", dimensionTitleMap[row.dimensionId] ?? row.dimensionId)
                            )
                            .foregroundStyle(.teal.opacity(0.85).gradient)
                            .annotation(position: .trailing) {
                                Text("\(row.count)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .chartXAxisLabel("命中条数（单事件可多维度）")
                        .frame(minHeight: min(420, CGFloat(min(dimensions.count, 14)) * 26 + 36))
                    }
                }

                chartCard(title: "🧭 重要度分布") {
                    Chart(importance) { row in
                        BarMark(
                            x: .value("区间", row.label),
                            y: .value("条数", row.count)
                        )
                        .foregroundStyle(.orange.opacity(0.75).gradient)
                    }
                    .chartXAxisLabel("importance 分箱")
                    .chartYAxisLabel("条数")
                    .frame(height: 180)
                }

                chartCard(title: "🌐 常见域名 Top（有 url_host 时）") {
                    if hosts.isEmpty {
                        Text("当日事件无 url_host 字段或为空。")
                            .foregroundStyle(.secondary)
                    } else {
                        Chart(hosts) { row in
                            BarMark(
                                x: .value("条数", row.count),
                                y: .value("域名", row.host)
                            )
                            .foregroundStyle(.indigo.opacity(0.8).gradient)
                            .annotation(position: .trailing) {
                                Text("\(row.count)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .chartXAxisLabel("条数")
                        .frame(minHeight: min(440, CGFloat(hosts.count) * 26 + 32))
                    }
                }

                chartCard(title: "🏷 按类型分布") {
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
    private var headerBanner: some View {
        HStack(alignment: .center, spacing: 14) {
            Group {
                if let url = Bundle.module.url(forResource: "DigitalDiary", withExtension: "png"),
                   let ns = NSImage(contentsOf: url)
                {
                    Image(nsImage: ns)
                        .resizable()
                        .scaledToFit()
                        .frame(width: 72, height: 72)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                        .shadow(color: .black.opacity(0.12), radius: 6, y: 2)
                } else {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(.quaternary)
                        .frame(width: 72, height: 72)
                        .overlay { Image(systemName: "chart.xyaxis.line").font(.title2) }
                }
            }
            VStack(alignment: .leading, spacing: 4) {
                Text("Digital Diary")
                    .font(.system(.title3, design: .rounded).weight(.semibold))
                Text("多维度一览：来源、时间、成长线、重要度与站点。")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Spacer(minLength: 0)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color.purple.opacity(0.14),
                            Color.cyan.opacity(0.1),
                            Color.blue.opacity(0.08),
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
        )
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .strokeBorder(.white.opacity(0.25), lineWidth: 1)
        )
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
            dimensions = pack.dimensions
            hosts = pack.hosts
            importance = pack.importance
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
        dimensions = []
        hosts = []
        importance = []
        total = 0
    }
}
