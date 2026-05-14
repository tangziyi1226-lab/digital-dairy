import AppKit
import SwiftUI

/// 「数据图表」页：弱化 KPI 与精确计数，偏叙事、节奏与陪伴感。
struct EventChartsView: View {
    @EnvironmentObject private var model: AppModel
    @State private var pack: EventInsights.Pack?
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
            VStack(alignment: .leading, spacing: 22) {
                headerBanner

                HStack(alignment: .firstTextBaseline) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("数据图表")
                            .font(.title3.weight(.semibold))
                        Text("生活telemetry的回声，不是考勤后台")
                            .font(.caption)
                            .foregroundStyle(.tertiary)
                    }
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
                        .font(.caption2)
                        .foregroundStyle(.quaternary)
                        .textSelection(.enabled)
                }

                if !hint.isEmpty {
                    Text(hint)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                } else if let pack {
                    softDisclaimer

                    narrativeHeroCard(pack)

                    narrativeObservationCard(pack)

                    attentionFlowCard(pack)

                    dayRhythmCard(pack)

                    mainThreadDimensionsCard(pack)

                    if !pack.narrative.activityToneLine.isEmpty {
                        activityToneCard(pack.narrative.activityToneLine)
                    }

                    tracesCard(pack)
                }
            }
            .padding(18)
        }
        .onAppear(perform: reload)
        .onChange(of: model.dashboardDate) { _, _ in reload() }
        .onChange(of: model.configurationEpoch) { _, _ in reload() }
    }

    private var softDisclaimer: some View {
        Text("以下为基于当日记录生成的柔软侧写：不展示精确条数对比，也不做重要度打分。")
            .font(.subheadline)
            .foregroundStyle(.secondary)
            .fixedSize(horizontal: false, vertical: true)
    }

    @ViewBuilder
    private func narrativeHeroCard(_ pack: EventInsights.Pack) -> some View {
        narrativeCard(
            eyebrow: "今天的重心",
            body: pack.narrative.heroParagraph,
            gradient: [
                Color(red: 0.35, green: 0.22, blue: 0.52).opacity(0.35),
                Color(red: 0.12, green: 0.35, blue: 0.48).opacity(0.28),
            ]
        )
    }

    @ViewBuilder
    private func narrativeObservationCard(_ pack: EventInsights.Pack) -> some View {
        narrativeCard(
            eyebrow: "今日观察",
            body: pack.narrative.observationParagraph,
            gradient: [
                Color(red: 0.15, green: 0.42, blue: 0.38).opacity(0.28),
                Color(red: 0.18, green: 0.22, blue: 0.40).opacity(0.22),
            ]
        )
    }

    private func narrativeCard(eyebrow: String, body: String, gradient: [Color]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(eyebrow)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
                .textCase(.uppercase)
                .tracking(0.6)
            Text(body)
                .font(.body)
                .foregroundStyle(.primary)
                .lineSpacing(5)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: gradient,
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay {
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .strokeBorder(Color.white.opacity(0.12), lineWidth: 1)
                }
        )
    }

    private func attentionFlowCard(_ pack: EventInsights.Pack) -> some View {
        softSectionCard(title: "今日注意力流向", subtitle: "用更人话的类目聚合站点与来源，而非浏览器名字排行榜") {
            if pack.attentionStreams.isEmpty {
                Text("暂无可用分类。").foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 14) {
                    ForEach(pack.attentionStreams) { row in
                        attentionRow(row)
                    }
                    Text(attentionClosingLine(for: pack))
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .padding(.top, 4)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private func attentionRow(_ row: EventInsights.AttentionStream) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(row.label)
                .font(.subheadline.weight(.medium))
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(Color.primary.opacity(0.06))
                        .frame(height: 10)
                    Capsule()
                        .fill(
                            LinearGradient(
                                colors: [
                                    Color.accentColor.opacity(0.45),
                                    Color.cyan.opacity(0.35),
                                ],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: max(12, geo.size.width * row.relativeWeight), height: 10)
                        .blur(radius: 0.3)
                }
            }
            .frame(height: 12)
        }
    }

    private func attentionClosingLine(for pack: EventInsights.Pack) -> String {
        guard let first = pack.attentionStreams.first?.label else {
            return ""
        }
        if pack.attentionStreams.count == 1 {
            return "整体看，今天更像是在「\(first)」这一带反复徘徊——这可以是一条主线，而不是一项指标。"
        }
        return "若用一句话收束：今天更像是在「\(first)」与周边需求之间来回照应，而不必解读成「多还是少」。"
    }

    private func dayRhythmCard(_ pack: EventInsights.Pack) -> some View {
        softSectionCard(title: "一天的节奏感", subtitle: "按上午 / 下午 / 晚间 / 凌晨粗分，只看相对起伏，不对照工时") {
            HStack(alignment: .bottom, spacing: 10) {
                ForEach(pack.dayRhythm) { part in
                    rhythmColumn(part)
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.top, 6)
        }
    }

    private func rhythmColumn(_ part: EventInsights.DayPartRhythm) -> some View {
        VStack(spacing: 8) {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color.purple.opacity(0.15 + part.intensity * 0.35),
                            Color.blue.opacity(0.12 + part.intensity * 0.28),
                        ],
                        startPoint: .bottom,
                        endPoint: .top
                    )
                )
                .frame(height: 28 + CGFloat(part.intensity) * 86)
                .overlay {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .strokeBorder(Color.white.opacity(0.08 + part.intensity * 0.12), lineWidth: 1)
                }
            Text(part.title)
                .font(.caption.weight(.semibold))
            Text(part.caption)
                .font(.caption2)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity)
    }

    private func mainThreadDimensionsCard(_ pack: EventInsights.Pack) -> some View {
        softSectionCard(title: "今日主线维度", subtitle: "取成长标签里相对更常被「引用」的前几项，不做精确排名对比") {
            let names = pack.topDimensionIds.map { dimensionTitleMap[$0] ?? $0 }
            if names.isEmpty {
                Text("当日事件未带成长维度标签。").foregroundStyle(.secondary)
            } else {
                VStack(alignment: .leading, spacing: 10) {
                    Text("今天主要围绕：")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    ForEach(Array(names.enumerated()), id: \.offset) { _, name in
                        Label {
                            Text(name)
                                .font(.body)
                        } icon: {
                            Image(systemName: "leaf")
                                .symbolRenderingMode(.hierarchical)
                                .foregroundStyle(.teal.opacity(0.85))
                        }
                    }
                    if let first = names.first, names.count >= 2 {
                        Text("「\(first)」在标签层面更明显一些——把它当作镜头语言，而不是人生分数。")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .padding(.top, 4)
                            .fixedSize(horizontal: false, vertical: true)
                    } else if let first = names.first {
                        Text("「\(first)」在标签层面反复出现，像背景里持续播放的一段动机。")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .padding(.top, 4)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        }
    }

    private func activityToneCard(_ line: String) -> some View {
        softSectionCard(title: "活动基调", subtitle: "来自事件 type 的粗颗粒感受，而非统计结论") {
            Text(line)
                .font(.body)
                .foregroundStyle(.primary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func tracesCard(_ pack: EventInsights.Pack) -> some View {
        softSectionCard(title: "今日留下痕迹的事情", subtitle: "从标题与站点模式里抽取几笔，代替「重要度分箱」") {
            VStack(alignment: .leading, spacing: 8) {
                ForEach(pack.traces) { t in
                    Text("· " + t.text)
                        .font(.callout)
                        .foregroundStyle(.primary.opacity(0.92))
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    @ViewBuilder
    private func softSectionCard(title: String, subtitle: String, @ViewBuilder content: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.headline)
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            content()
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(Color.primary.opacity(0.06), lineWidth: 1)
        }
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
                        .overlay { Image(systemName: "waveform.path.ecg").font(.title2) }
                }
            }
            VStack(alignment: .leading, spacing: 4) {
                Text("Digital Diary")
                    .font(.system(.title3, design: .rounded).weight(.semibold))
                Text("把自动化记录，翻译成更像「我在场」的叙述。")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Spacer(minLength: 0)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color.purple.opacity(0.12),
                            Color.cyan.opacity(0.08),
                            Color.blue.opacity(0.06),
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
        )
        .overlay {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(Color.white.opacity(0.18), lineWidth: 1)
        }
    }

    private func reload() {
        guard let url = model.eventsURL(for: model.dashboardDate) else {
            hint = "未找到数据目录。"
            pack = nil
            return
        }
        guard FileManager.default.fileExists(atPath: url.path) else {
            hint = "该日尚无 events JSON。可先运行「仅采集」或「生成今日日报」。"
            pack = nil
            return
        }
        if let loaded = EventInsights.load(from: url, dimensionTitles: dimensionTitleMap) {
            pack = loaded
            hint = ""
        } else {
            hint = "无法解析事件文件。"
            pack = nil
        }
    }
}
