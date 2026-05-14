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

    static func load(from url: URL) -> (sources: [SourceCount], hours: [HourCount], types: [TypeCount], total: Int)? {
        guard let data = try? Data(contentsOf: url),
              let arr = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]]
        else {
            return nil
        }

        var bySource: [String: Int] = [:]
        var byHour: [Int: Int] = [:]
        var byType: [String: Int] = [:]

        for obj in arr {
            let source = (obj["source"] as? String) ?? "unknown"
            bySource[source, default: 0] += 1

            let typeName = (obj["type"] as? String) ?? "unknown"
            byType[typeName, default: 0] += 1

            if let hour = hourFromTimestamp(obj["timestamp"] as? String) {
                byHour[hour, default: 0] += 1
            }
        }

        let sources = bySource.map { SourceCount(source: $0.key, count: $0.value) }
            .sorted { $0.count > $1.count }

        let hours = (0 ..< 24).map { h in
            HourCount(hour: h, count: byHour[h] ?? 0)
        }

        let types = byType.map { TypeCount(typeName: $0.key, count: $0.value) }
            .sorted { $0.count > $1.count }

        return (sources, hours, types, arr.count)
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
