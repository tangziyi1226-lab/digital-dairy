import Charts
import Foundation

/// 从 `data/events/YYYY-MM-DD-events.json` 解析并聚合，供 Swift Charts 使用。
enum EventInsights {
    struct SourceCount: Identifiable {
        var id: String { source }
        let source: String
        let count: Int
    }

    struct HourCount: Identifiable {
        var id: Int { hour }
        let hour: Int
        let count: Int
    }

    struct TypeCount: Identifiable {
        var id: String { typeName }
        let typeName: String
        let count: Int
    }

    struct DimensionCount: Identifiable {
        var id: String { dimensionId }
        let dimensionId: String
        let count: Int
    }

    struct HostCount: Identifiable {
        var id: String { host }
        let host: String
        let count: Int
    }

    struct ImportanceBucket: Identifiable {
        var id: String { label }
        let label: String
        let count: Int
    }

    struct Pack {
        let sources: [SourceCount]
        let hours: [HourCount]
        let types: [TypeCount]
        let dimensions: [DimensionCount]
        let hosts: [HostCount]
        let importance: [ImportanceBucket]
        let total: Int
    }

    static func load(from url: URL) -> Pack? {
        guard let data = try? Data(contentsOf: url),
              let arr = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]]
        else {
            return nil
        }

        var bySource: [String: Int] = [:]
        var byHour: [Int: Int] = [:]
        var byType: [String: Int] = [:]
        var byDimension: [String: Int] = [:]
        var byHost: [String: Int] = [:]
        var importanceBins = ["0-0.25": 0, "0.25-0.5": 0, "0.5-0.75": 0, "0.75-1": 0]

        for obj in arr {
            let source = (obj["source"] as? String) ?? "unknown"
            bySource[source, default: 0] += 1

            let typeName = (obj["type"] as? String) ?? "unknown"
            byType[typeName, default: 0] += 1

            if let hour = hourFromTimestamp(obj["timestamp"] as? String) {
                byHour[hour, default: 0] += 1
            }

            if let dims = obj["dimensions"] as? [String] {
                for d in dims {
                    let key = d.isEmpty ? "（空）" : d
                    byDimension[key, default: 0] += 1
                }
            }

            if let host = obj["url_host"] as? String, !host.isEmpty {
                byHost[host, default: 0] += 1
            }

            if let imp = obj["importance"] as? Double {
                binImportance(imp, into: &importanceBins)
            } else if let imp = obj["importance"] as? Int {
                binImportance(Double(imp), into: &importanceBins)
            }
        }

        let sources = bySource.map { SourceCount(source: $0.key, count: $0.value) }
            .sorted { $0.count > $1.count }

        let hours = (0 ..< 24).map { h in
            HourCount(hour: h, count: byHour[h] ?? 0)
        }

        let types = byType.map { TypeCount(typeName: $0.key, count: $0.value) }
            .sorted { $0.count > $1.count }

        let dimensions = byDimension.map { DimensionCount(dimensionId: $0.key, count: $0.value) }
            .sorted { $0.count > $1.count }

        let hosts = Array(
            byHost.map { HostCount(host: $0.key, count: $0.value) }
                .sorted { $0.count > $1.count }
                .prefix(16)
        )

        let importance = [
            ImportanceBucket(label: "0–0.25", count: importanceBins["0-0.25"] ?? 0),
            ImportanceBucket(label: "0.25–0.5", count: importanceBins["0.25-0.5"] ?? 0),
            ImportanceBucket(label: "0.5–0.75", count: importanceBins["0.5-0.75"] ?? 0),
            ImportanceBucket(label: "0.75–1", count: importanceBins["0.75-1"] ?? 0),
        ]

        return Pack(
            sources: sources,
            hours: hours,
            types: types,
            dimensions: dimensions,
            hosts: hosts,
            importance: importance,
            total: arr.count
        )
    }

    private static func binImportance(_ value: Double, into bins: inout [String: Int]) {
        guard value.isFinite else { return }
        let v = min(max(value, 0), 1)
        if v < 0.25 {
            bins["0-0.25", default: 0] += 1
        } else if v < 0.5 {
            bins["0.25-0.5", default: 0] += 1
        } else if v < 0.75 {
            bins["0.5-0.75", default: 0] += 1
        } else {
            bins["0.75-1", default: 0] += 1
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
