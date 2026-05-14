import AppKit
import Foundation
import SwiftUI

/// 日报 Markdown：换行预处理 + 解析后标题/正文样式。
enum DailySummaryMarkdown {
    /// 句末单换行扩成段落；普通相邻行加 CommonMark 硬换行；给各级标题行补 emoji。
    static func prepareSourceForParsing(_ raw: String) -> String {
        var s = raw.replacingOccurrences(of: "\r\n", with: "\n")
        s = expandParagraphBreaksAfterClosingPunctuation(s)
        s = insertHardBreaksBetweenPlainLines(s)
        s = decorateHeadingLinesWithEmoji(s)
        return s
    }

    static func parseStyledDocument(_ markdown: String) throws -> AttributedString {
        var opts = AttributedString.MarkdownParsingOptions()
        opts.interpretedSyntax = .full
        var doc = try AttributedString(markdown: markdown, options: opts)
        applyHeadingTypography(&doc)
        applyBodySerifSkippingCode(&doc)
        return doc
    }

    // MARK: - 换行

    private static func expandParagraphBreaksAfterClosingPunctuation(_ s: String) -> String {
        var result = s
        for sep in ["。", "！", "？", "；", ".", "!", "?", ";"] {
            result = result.replacingOccurrences(of: "\(sep)\n", with: "\(sep)\n\n")
        }
        return result
    }

    private static func insertHardBreaksBetweenPlainLines(_ s: String) -> String {
        var lines = s.components(separatedBy: "\n")
        guard lines.count > 1 else { return s }
        for i in 0 ..< (lines.count - 1) {
            let a = lines[i]
            let b = lines[i + 1]
            let ta = a.trimmingCharacters(in: .whitespaces)
            let tb = b.trimmingCharacters(in: .whitespaces)
            if ta.isEmpty || tb.isEmpty { continue }
            if isStructuralMarkdownLine(ta) || isStructuralMarkdownLine(tb) { continue }
            if a.hasSuffix("  ") || a.hasSuffix("\\") { continue }
            lines[i] = a + "  "
        }
        return lines.joined(separator: "\n")
    }

    private static func isStructuralMarkdownLine(_ line: String) -> Bool {
        let t = line.trimmingCharacters(in: .whitespaces)
        if t.isEmpty { return true }
        if t.hasPrefix("#") { return true }
        if t == "---" || t == "***" || t == "___" { return true }
        if t.hasPrefix("```") { return true }
        if t.hasPrefix(">") { return true }
        if t.hasPrefix("- ") || t.hasPrefix("* ") || t.hasPrefix("+ ") { return true }
        if t.hasPrefix("|") { return true }
        if t.range(of: #"^\d+\.\s"#, options: .regularExpression) != nil { return true }
        return false
    }

    // MARK: - 标题 emoji

    private static func decorateHeadingLinesWithEmoji(_ s: String) -> String {
        s.split(separator: "\n", omittingEmptySubsequences: false)
            .map { line -> String in
                let lineStr = String(line)
                let trimmed = lineStr.trimmingCharacters(in: .whitespaces)
                guard let level = headingLevel(of: trimmed), level <= 3 else { return lineStr }
                let title = headingTitleText(trimmed, level: level)
                guard !title.isEmpty, !titleStartsWithEmoji(title) else { return lineStr }
                let em = emojiForHeading(level: level, title: title)
                return replaceHeadingLine(lineStr, level: level, newTitle: "\(em) \(title)")
            }
            .joined(separator: "\n")
    }

    /// 标准 ATX 标题：`#`…`######` 后至少一个空白再跟正文。
    private static func headingLevel(of trimmedLine: String) -> Int? {
        var n = 0
        for ch in trimmedLine {
            if ch == "#" {
                n += 1
                if n > 6 { return nil }
            } else {
                break
            }
        }
        guard n >= 1 else { return nil }
        let rest = trimmedLine.dropFirst(n)
        guard let first = rest.first, first.isWhitespace else { return nil }
        let body = String(rest).trimmingCharacters(in: .whitespaces)
        guard !body.isEmpty else { return nil }
        return n
    }

    private static func headingTitleText(_ trimmedLine: String, level: Int) -> String {
        let dropCount = trimmedLine.prefix(while: { $0 == "#" }).count
        return String(trimmedLine.dropFirst(dropCount)).trimmingCharacters(in: .whitespaces)
    }

    private static func replaceHeadingLine(_ original: String, level: Int, newTitle: String) -> String {
        let trimmed = original.trimmingCharacters(in: .whitespaces)
        let leadLen = original.count - trimmed.count
        let wsLeading = String(original.prefix(leadLen))
        let hashes = String(repeating: "#", count: level)
        return "\(wsLeading)\(hashes) \(newTitle)"
    }

    private static func titleStartsWithEmoji(_ title: String) -> Bool {
        guard let ch = title.first else { return false }
        return ch.unicodeScalars.contains(where: { scalar in
            scalar.properties.isEmojiPresentation || scalar.properties.generalCategory == .otherSymbol
        })
    }

    private static func emojiForHeading(level: Int, title: String) -> String {
        let pairs: [(String, String)] = [
            ("今日", "🌅"), ("总结", "📋"), ("复盘", "🔁"), ("成长", "🌱"), ("亮点", "✨"), ("情绪", "💭"),
            ("感受", "💗"), ("明日", "🔭"), ("计划", "🗓"), ("待办", "✅"), ("运动", "🏃"), ("睡眠", "😴"),
            ("学习", "📚"), ("工作", "💼"), ("社交", "👥"), ("健康", "🩺"), ("阅读", "📖"), ("娱乐", "🎮"),
            ("财务", "💰"), ("家庭", "🏠"), ("关系", "🤝"), ("反思", "🪞"), ("感恩", "🙏"), ("挑战", "⛰"),
            ("习惯", "🔄"), ("时间", "⏱"), ("专注", "🎯"), ("产出", "📤"), ("会议", "🗣"), ("技术", "🛠"),
        ]
        for (k, e) in pairs where title.contains(k) {
            if level == 1 { return e }
            if level == 2 { return e }
            return "▫️"
        }
        switch level {
        case 1: return "📌"
        case 2: return "▪️"
        default: return "▫️"
        }
    }

    // MARK: - 解析后样式

    private static func applyHeadingTypography(_ doc: inout AttributedString) {
        for run in doc.runs {
            guard let pi = run.presentationIntent else { continue }
            let r = run.range
            for comp in pi.components {
                guard case .header(let level) = comp.kind else { continue }
                switch level {
                case 1:
                    doc[r].font = .system(.largeTitle, design: .rounded).weight(.bold)
                    doc[r].foregroundColor = NSColor.labelColor
                case 2:
                    doc[r].font = .system(.title, design: .rounded).weight(.semibold)
                    doc[r].foregroundColor = NSColor.labelColor.withAlphaComponent(0.95)
                case 3:
                    doc[r].font = .system(.title2, design: .rounded).weight(.semibold)
                default:
                    doc[r].font = .system(.title3, design: .rounded).weight(.semibold)
                }
            }
        }
    }

    private static func applyBodySerifSkippingCode(_ doc: inout AttributedString) {
        for run in doc.runs {
            if run.presentationIntent != nil { continue }
            if let ipi = run.inlinePresentationIntent, ipi.contains(.code) { continue }
            let r = run.range
            if doc[r].font != nil { continue }
            doc[r].font = .system(.body, design: .serif)
        }
    }
}
