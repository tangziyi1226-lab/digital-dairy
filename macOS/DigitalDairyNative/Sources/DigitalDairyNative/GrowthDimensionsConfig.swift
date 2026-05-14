import Foundation

/// 与 `config/growth_dimensions.json` 对齐，供 SwiftUI 编辑与保存。
struct GrowthDimensionsFile: Codable, Equatable {
    struct Row: Codable, Equatable, Identifiable {
        var id: String
        var name: String
        var description: String
        var keywords: [String]
        var hosts: [String]
        /// 缺省解码为 `true`，与 Python `load_dimensions` 一致。
        var enabled: Bool

        enum CodingKeys: String, CodingKey {
            case id, name, description, keywords, hosts, enabled
        }

        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            id = try c.decode(String.self, forKey: .id)
            name = try c.decode(String.self, forKey: .name)
            description = try c.decodeIfPresent(String.self, forKey: .description) ?? ""
            keywords = try c.decodeIfPresent([String].self, forKey: .keywords) ?? []
            hosts = try c.decodeIfPresent([String].self, forKey: .hosts) ?? []
            enabled = try c.decodeIfPresent(Bool.self, forKey: .enabled) ?? true
        }

        init(id: String, name: String, description: String, keywords: [String], hosts: [String], enabled: Bool) {
            self.id = id
            self.name = name
            self.description = description
            self.keywords = keywords
            self.hosts = hosts
            self.enabled = enabled
        }

        func encode(to encoder: Encoder) throws {
            var c = encoder.container(keyedBy: CodingKeys.self)
            try c.encode(id, forKey: .id)
            try c.encode(name, forKey: .name)
            try c.encode(description, forKey: .description)
            try c.encode(keywords, forKey: .keywords)
            try c.encode(hosts, forKey: .hosts)
            try c.encode(enabled, forKey: .enabled)
        }
    }

    var dimensions: [Row]

    static func load(from url: URL) throws -> GrowthDimensionsFile {
        let data = try Data(contentsOf: url)
        let decoder = JSONDecoder()
        return try decoder.decode(GrowthDimensionsFile.self, from: data)
    }

    func save(to url: URL) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(self)
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try data.write(to: url, options: .atomic)
    }
}
