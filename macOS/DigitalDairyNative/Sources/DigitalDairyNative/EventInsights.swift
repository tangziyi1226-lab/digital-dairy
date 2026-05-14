import Foundation

/// 从 `data/events/YYYY-MM-DD-events.json` 解析并聚合，供「今日回望」视图使用（弱化计数、偏叙事）。
enum EventInsights {
    struct AttentionStream: Identifiable {
        var id: String { label }
        let label: String
        /// 0…1，仅用于相对宽度，界面不展示具体数值。
        let relativeWeight: Double
    }

    struct DayPartRhythm: Identifiable {
        var id: String { key }
        let key: String
        let title: String
        let caption: String
        /// 0…1，相对当日最高段的强度。
        let intensity: Double
    }

    struct DayNarrative {
        let heroParagraph: String
        let observationParagraph: String
        let activityToneLine: String
    }

    struct TraceLine: Identifiable {
        var id: String { text }
        let text: String
    }

    struct Pack {
        let attentionStreams: [AttentionStream]
        let dayRhythm: [DayPartRhythm]
        let topDimensionIds: [String]
        let traces: [TraceLine]
        let narrative: DayNarrative
        /// 内部保留：是否有足够事件用于展示（不在 UI 中强调条数）。
        let hasEvents: Bool
    }

    static func load(from url: URL, dimensionTitles: [String: String]) -> Pack? {
        guard let data = try? Data(contentsOf: url),
              let arr = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]]
        else {
            return nil
        }

        if arr.isEmpty {
            return Pack(
                attentionStreams: [],
                dayRhythm: defaultRhythm(parts: [:]),
                topDimensionIds: [],
                traces: [],
                narrative: DayNarrative(
                    heroParagraph: "这一天几乎没有留下自动化记录。若你希望看见回声，可以先跑一次采集或生成日报。",
                    observationParagraph: "没有数据并不等于空白的一天，只是镜头还没打开。",
                    activityToneLine: ""
                ),
                hasEvents: false
            )
        }

        var attentionCounts: [String: Int] = [:]
        var byDimension: [String: Int] = [:]
        var byHour: [Int: Int] = [:]
        var byType: [String: Int] = [:]

        for obj in arr {
            let label = attentionLabel(for: obj)
            attentionCounts[label, default: 0] += 1

            if let dims = obj["dimensions"] as? [String] {
                for d in dims {
                    let key = d.isEmpty ? "（空）" : d
                    byDimension[key, default: 0] += 1
                }
            }

            if let hour = hourFromTimestamp(obj["timestamp"] as? String) {
                byHour[hour, default: 0] += 1
            }

            let typeName = (obj["type"] as? String) ?? "unknown"
            byType[typeName, default: 0] += 1
        }

        let streams = buildAttentionStreams(from: attentionCounts)
        let parts = dayPartCounts(from: byHour)
        let rhythm = defaultRhythm(parts: parts)
        let topDimIds = topDimensionIds(from: byDimension, limit: 3)
        let traces = buildTraces(from: arr)
        let narrative = buildNarrative(
            attentionCounts: attentionCounts,
            partCounts: parts,
            topDimensionIds: topDimIds,
            dimensionTitles: dimensionTitles,
            typeCounts: byType
        )

        return Pack(
            attentionStreams: streams,
            dayRhythm: rhythm,
            topDimensionIds: topDimIds,
            traces: traces,
            narrative: narrative,
            hasEvents: true
        )
    }

    // MARK: - 注意力分类（叙事向）

    private static let attentionOrder: [String] = [
        "申请与沟通", "工程与开发", "学术与论文", "AI 协作",
        "长文本阅读", "信息输入", "娱乐与恢复", "其他痕迹",
    ]

    private static func attentionLabel(for obj: [String: Any]) -> String {
        let dims = obj["dimensions"] as? [String] ?? []
        if let picked = pickDimensionAttention(dims) {
            return picked
        }

        let source = ((obj["source"] as? String) ?? "").lowercased()
        let host = ((obj["url_host"] as? String) ?? "").lowercased()
        let typeName = ((obj["type"] as? String) ?? "").lowercased()

        if typeName == "rest" { return "娱乐与恢复" }

        if aiSourceOrHost(source: source, host: host) { return "AI 协作" }
        if engineeringHost(host) || source == "cursor" { return "工程与开发" }
        if academicHost(host) { return "学术与论文" }
        if admissionHost(host) || host.contains("mail.") || host.contains("outlook")
            || host.contains("slack") || host.contains("teams")
        {
            return "申请与沟通"
        }
        if longReadHost(host) { return "长文本阅读" }
        if restHost(host) { return "娱乐与恢复" }

        switch typeName {
        case "work", "creation": return "工程与开发"
        case "learning": return "信息输入"
        case "social": return "申请与沟通"
        case "health": return "娱乐与恢复"
        case "reflection": return "长文本阅读"
        default: break
        }

        return "信息输入"
    }

    private static func pickDimensionAttention(_ dims: [String]) -> String? {
        let priority: [(String, String)] = [
            ("admission", "申请与沟通"),
            ("engineering_tools", "工程与开发"),
            ("ai_research", "学术与论文"),
            ("health_recovery", "娱乐与恢复"),
            ("general_input", "信息输入"),
            ("personal_growth", "长文本阅读"),
        ]
        var best: (Int, String)?
        for d in dims {
            guard let idx = priority.firstIndex(where: { $0.0 == d }) else { continue }
            if best == nil || idx < best!.0 {
                best = (idx, priority[idx].1)
            }
        }
        return best?.1
    }

    private static func aiSourceOrHost(source: String, host: String) -> Bool {
        let aiSources: Set<String> = [
            "chatgpt", "doubao", "deepseek", "claude", "perplexity", "copilot",
        ]
        if aiSources.contains(source) { return true }
        return host.contains("openai.com")
            || host.contains("chatgpt.com")
            || host.contains("anthropic.com")
            || host.contains("claude.ai")
            || host.contains("perplexity.ai")
            || host.contains("doubao.com")
            || host.contains("deepseek.com")
    }

    private static func engineeringHost(_ host: String) -> Bool {
        host.contains("github.com")
            || host.contains("gitlab.com")
            || host.contains("stackoverflow.com")
            || host.contains("openrouter.ai")
            || host.contains("aistudio.google.com")
            || host.contains("aliyun.com")
            || host.contains("vercel.app")
            || host.contains("vercel.com")
            || host.contains("cloud.google.com")
            || host.contains("aws.amazon.com")
    }

    private static func academicHost(_ host: String) -> Bool {
        host.contains("arxiv.org")
            || host.contains("scholar.google")
            || host.contains("ieee.org")
            || host.contains("acm.org")
            || host.contains("semanticscholar.org")
            || host.contains("openaccess.thecvf.com")
    }

    private static func admissionHost(_ host: String) -> Bool {
        host.contains("ucas.ac.cn")
            || host.contains("edu.cn")
            || host.contains("apply")
            || host.contains("admission")
    }

    private static func longReadHost(_ host: String) -> Bool {
        host.contains("medium.com")
            || host.contains("substack.com")
            || host.contains("wikipedia.org")
            || host.contains("notion.so")
    }

    private static func restHost(_ host: String) -> Bool {
        host.contains("youtube.com")
            || host.contains("bilibili.com")
            || host.contains("netflix.com")
            || host.contains("twitch.tv")
            || host.contains("steam")
    }

    private static func buildAttentionStreams(from counts: [String: Int]) -> [AttentionStream] {
        let total = max(counts.values.reduce(0, +), 1)
        let maxCount = counts.values.max() ?? 1
        let ordered = attentionOrder.compactMap { key -> AttentionStream? in
            guard let c = counts[key], c > 0 else { return nil }
            let rel = Double(c) / Double(maxCount)
            return AttentionStream(label: key, relativeWeight: rel)
        }
        // 包含「其他」类里未在 order 中的键
        let extras = counts.keys.filter { !attentionOrder.contains($0) }.sorted()
        var streams = ordered
        for k in extras {
            guard let c = counts[k], c > 0 else { continue }
            let rel = Double(c) / Double(maxCount)
            streams.append(AttentionStream(label: k, relativeWeight: rel))
        }
        _ = total // 保留语义；相对宽度已用 maxCount 归一
        return streams
    }

    // MARK: - 日节奏（上午 / 下午 / 晚间 / 凌晨）

    private static func dayPartCounts(from byHour: [Int: Int]) -> [String: Int] {
        var m: [String: Int] = ["dawn": 0, "morning": 0, "afternoon": 0, "evening": 0]
        for (h, c) in byHour {
            switch h {
            case 0 ..< 5: m["dawn", default: 0] += c
            case 5 ..< 12: m["morning", default: 0] += c
            case 12 ..< 18: m["afternoon", default: 0] += c
            default: m["evening", default: 0] += c
            }
        }
        return m
    }

    private static func defaultRhythm(parts: [String: Int]) -> [DayPartRhythm] {
        let keys = ["morning", "afternoon", "evening", "dawn"]
        let labels = ["上午", "下午", "晚间", "凌晨"]
        let maxV = max(keys.map { parts[$0, default: 0] }.max() ?? 0, 1)
        return zip(keys, labels).map { key, title in
            let v = parts[key, default: 0]
            let t = Double(v) / Double(maxV)
            let caption = rhythmCaption(for: key, intensity: t)
            return DayPartRhythm(key: key, title: title, caption: caption, intensity: t)
        }
    }

    private static func rhythmCaption(for key: String, intensity: Double) -> String {
        let tier: String
        if intensity > 0.72 { tier = "高" }
        else if intensity > 0.38 { tier = "中" }
        else { tier = "低" }

        switch (key, tier) {
        case ("morning", "高"): return "逐步进入状态"
        case ("morning", _): return "节奏柔和"
        case ("afternoon", "高"): return "持续推进感"
        case ("afternoon", _): return "平稳展开"
        case ("evening", "高"): return "输入与会话偏多"
        case ("evening", _): return "放缓、留白"
        case ("dawn", "高"): return "深夜仍在线"
        case ("dawn", _): return "较为安静"
        default: return "较为安静"
        }
    }

    // MARK: - 成长维度 Top3

    private static func topDimensionIds(from byDimension: [String: Int], limit: Int) -> [String] {
        let sorted = byDimension
            .filter { $0.key != "（空）" }
            .sorted { $0.value > $1.value }
        return Array(sorted.prefix(limit)).map(\.key)
    }

    // MARK: - 痕迹（轻量语义，不用 importance 分箱）

    private static func buildTraces(from arr: [[String: Any]]) -> [TraceLine] {
        var lines: [String] = []
        var seen = Set<String>()

        func push(_ s: String) {
            guard !s.isEmpty, !seen.contains(s) else { return }
            seen.insert(s)
            lines.append(s)
        }

        var hasGitHub = false
        var hasAI = false
        var hasAcademic = false
        var hasMail = false

        var titleSamples: [String] = []

        for obj in arr.prefix(400) {
            let host = ((obj["url_host"] as? String) ?? "").lowercased()
            let source = ((obj["source"] as? String) ?? "").lowercased()
            if host.contains("github.com") { hasGitHub = true }
            if aiSourceOrHost(source: source, host: host) { hasAI = true }
            if academicHost(host) { hasAcademic = true }
            if host.contains("mail.google") || host.contains("outlook") { hasMail = true }

            let title = (obj["title"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            if title.count >= 10, titleSamples.count < 4 {
                let short = String(title.prefix(44))
                let clipped = title.count > 44 ? short + "…" : short
                if !titleSamples.contains(where: { $0.hasPrefix(String(clipped.prefix(20))) }) {
                    titleSamples.append("「\(clipped)」")
                }
            }
        }

        if hasGitHub { push("在代码与仓库相关页面留下过足迹") }
        if hasAI { push("与 AI 助手或模型有过一段或数段协作") }
        if hasAcademic { push("学术阅读或检索在记录里出现过") }
        if hasMail { push("有邮件或沟通类页面被记下") }

        for t in titleSamples where lines.count < 6 {
            push(t)
        }

        if lines.isEmpty {
            push("记录较碎，但这也是生活本身的纹理")
        }

        return lines.map { TraceLine(text: $0) }
    }

    // MARK: - 叙事合成（规则生成，非 LLM）

    private static func buildNarrative(
        attentionCounts: [String: Int],
        partCounts: [String: Int],
        topDimensionIds: [String],
        dimensionTitles: [String: String],
        typeCounts: [String: Int]
    ) -> DayNarrative {
        let sortedAtt = attentionCounts.sorted { $0.value > $1.value }
        let topLabels = sortedAtt.prefix(3).map { $0.0 }
        let total = max(attentionCounts.values.reduce(0, +), 1)
        let topShare = sortedAtt.first.map { Double($0.value) / Double(total) } ?? 0

        var heroParts: [String] = []
        if topLabels.count >= 2 {
            heroParts.append(
                "今天的大部分注意力落在「\(topLabels[0])」与「\(topLabels[1])」附近，像是在围绕几条熟悉的主线打转。"
            )
        } else if let only = topLabels.first {
            heroParts.append("今天的记录里，「\(only)」这一脉最为突出。")
        }

        if topShare > 0.48, let first = topLabels.first {
            heroParts.append("其中「\(first)」是最显眼的一条回声，不必把它读成「效率」，它只是你今天反复触碰的世界。")
        }

        let dom = dominantDayPart(from: partCounts)
        switch dom {
        case "afternoon":
            heroParts.append("从时间分布上看，下午是相对更「在场」的时段，更像在推进一些事情，而不是碎片漂流。")
        case "evening":
            heroParts.append("晚间在记录里仍占一席，多半偏轻输入、浏览或与工具对话——这也很像现代人的收束方式。")
        case "morning":
            heroParts.append("上午的能量在记录里更明显一些，像慢慢把齿轮扣上。")
        default:
            heroParts.append("节奏在一天里分布得比较散，这并不坏，只是说明镜头捕捉得更碎。")
        }

        let hero = heroParts.joined(separator: "\n\n")

        var obs: [String] = []
        let dimNames = topDimensionIds.map { dimensionTitles[$0] ?? $0 }
        if dimNames.count >= 2 {
            obs.append("若从成长维度标签看，「\(dimNames[0])」与「\(dimNames[1])」今天更常被你的行为「引用」。")
        } else if let one = dimNames.first {
            obs.append("成长维度里，「\(one)」今天更常被你的行为「引用」。")
        }

        obs.append("这些只是自动化记录的侧写，不是评分，更不是考勤；你比任何图表都更清楚自己经历了什么。")

        let observation = obs.joined(separator: "\n\n")

        let tone = qualitativeTypeLine(from: typeCounts)
        return DayNarrative(heroParagraph: hero, observationParagraph: observation, activityToneLine: tone)
    }

    private static func dominantDayPart(from parts: [String: Int]) -> String {
        parts.max(by: { $0.value < $1.value })?.key ?? "afternoon"
    }

    private static func qualitativeTypeLine(from typeCounts: [String: Int]) -> String {
        let sorted = typeCounts.sorted { $0.value > $1.value }
        guard let top = sorted.first?.key else { return "" }
        switch top {
        case "work", "creation":
            return "活动类型上，更偏「做事与产出」的一侧略占上风。"
        case "learning":
            return "活动类型上，「摄取与探索」的痕迹更明显一些。"
        case "rest":
            return "活动类型里，「恢复与放空」也诚实留下了位置——这同样重要。"
        case "reflection":
            return "有一些「向内看」的记录冒头，像慢快门。"
        case "social":
            return "「连接与沟通」在类型层面偶尔探头。"
        case "health":
            return "「身体与节律」在类型里被记下一笔。"
        default:
            return "类型标签比较杂，说明这一天在工具眼里并不单一。"
        }
    }

    private static func hourFromTimestamp(_ raw: String?) -> Int? {
        guard let raw else { return nil }
        guard let tIdx = raw.firstIndex(of: "T") else { return nil }
        let afterT = raw[raw.index(after: tIdx)...]
        let prefix2 = String(afterT.prefix(2))
        guard prefix2.count == 2, let h = Int(prefix2), (0 ..< 24).contains(h) else { return nil }
        return h
    }
}
