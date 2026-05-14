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

// MARK: - 示例（应用内「创建示例」）

extension GrowthDimensionsFile {
    private static let embeddedExampleJSON = #"""
    {"dimensions":[{"description":"夏令营、导师、院所、报名系统、申请材料与路径选择。","enabled":true,"hosts":["ucas.ac.cn","ict.cas.cn","buaa.edu.cn","bupt.edu.cn"],"id":"admission","keywords":["夏令营","招生","报名","导师","申请","推免"],"name":"升学与申请"},{"description":"论文、模型、数据集、研究方向、实验复现与科研阅读。","enabled":true,"hosts":["scholar.google.com","arxiv.org","openaccess.thecvf.com"],"id":"ai_research","keywords":["ICLR","ICCV","CVPR","论文","paper","模型","深度学习"],"name":"AI 科研"},{"description":"GitHub、API、云服务、开发环境、agent 工具和工程协作。","enabled":true,"hosts":["github.com","openrouter.ai","aistudio.google.com","aliyun.com"],"id":"engineering_tools","keywords":["GitHub","pull request","SSH","API","Cursor","AI Studio","阿里云","配置","仓库"],"name":"工程与工具链"},{"description":"日记、人生叙事、焦虑缓解、长期目标与自我观察。","enabled":true,"hosts":[],"id":"personal_growth","keywords":["diary","journal","growth","人生","成长","焦虑","复盘","目标","叙事"],"name":"个人成长与自我理解"},{"description":"睡眠、运动、饮食、身体状态与恢复节奏。","enabled":true,"hosts":[],"id":"health_recovery","keywords":["健康","睡眠","运动","饮食","health","sleep","exercise"],"name":"健康与恢复"},{"description":"未归入明确成长维度的信息输入。","enabled":true,"hosts":[],"id":"general_input","keywords":[],"name":"一般信息输入"}]}
    """#

    static func makeExampleFromEmbedded() throws -> GrowthDimensionsFile {
        let data = Data(Self.embeddedExampleJSON.utf8)
        return try JSONDecoder().decode(GrowthDimensionsFile.self, from: data)
    }
}
