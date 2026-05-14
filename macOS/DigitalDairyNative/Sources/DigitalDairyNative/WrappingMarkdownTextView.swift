import AppKit
import Foundation
import SwiftUI

/// 使用 `NSTextView` 渲染 Markdown，在 `ScrollView` 等横向无界布局下仍能按视口宽度自动折行。
struct WrappingMarkdownTextView: NSViewRepresentable {
    var markdown: String

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeNSView(context: Context) -> NSScrollView {
        let scroll = NSScrollView()
        scroll.drawsBackground = false
        scroll.borderType = .noBorder
        scroll.hasVerticalScroller = true
        scroll.hasHorizontalScroller = false
        scroll.autohidesScrollers = true
        scroll.scrollerStyle = .overlay

        let tv = NSTextView()
        tv.drawsBackground = false
        tv.backgroundColor = .clear
        tv.isEditable = false
        tv.isSelectable = true
        tv.isRichText = true
        tv.importsGraphics = false
        tv.textContainerInset = NSSize(width: 10, height: 12)
        tv.autoresizingMask = [.width]
        tv.minSize = NSSize(width: 0, height: 0)
        tv.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
        tv.isVerticallyResizable = true
        tv.isHorizontallyResizable = false
        tv.textContainer?.lineFragmentPadding = 0
        tv.textContainer?.widthTracksTextView = false

        scroll.documentView = tv
        return scroll
    }

    func updateNSView(_ scrollView: NSScrollView, context: Context) {
        guard let tv = scrollView.documentView as? NSTextView else { return }

        let clipW = scrollView.contentView.bounds.width
        let inner = max(32, clipW - tv.textContainerInset.width * 2)
        if abs(context.coordinator.lastContainerWidth - inner) > 0.5 || context.coordinator.lastMarkdown != markdown {
            context.coordinator.lastContainerWidth = inner
            context.coordinator.lastMarkdown = markdown
            tv.textContainer?.containerSize = NSSize(width: inner, height: CGFloat.greatestFiniteMagnitude)
            tv.textContainer?.widthTracksTextView = false

            let attr = Self.buildAttributedMarkdown(markdown)
            tv.textStorage?.setAttributedString(attr)

            tv.layoutManager?.ensureLayout(for: tv.textContainer!)
            let usedH = tv.layoutManager?.usedRect(for: tv.textContainer!).height ?? 0
            let h = max(44, usedH + tv.textContainerInset.height * 2)
            tv.setFrameSize(NSSize(width: clipW, height: h))
        }
    }

    private static func buildAttributedMarkdown(_ source: String) -> NSAttributedString {
        var opts = AttributedString.MarkdownParsingOptions()
        opts.interpretedSyntax = .full
        guard let attr = try? AttributedString(markdown: source, options: opts) else {
            return NSAttributedString(string: source, attributes: [.font: NSFont.systemFont(ofSize: NSFont.systemFontSize)])
        }
        let base: NSAttributedString
        if let ns = try? NSAttributedString(attr, including: \.appKit) {
            base = ns
        } else {
            base = NSAttributedString(string: source, attributes: [.font: NSFont.systemFont(ofSize: NSFont.systemFontSize)])
        }
        let m = NSMutableAttributedString(attributedString: base)
        applyPreferredSerif(to: m)
        return m
    }

    /// 在保留 Markdown 各级字号的前提下尽量换成偏编辑向的衬线体。
    private static func applyPreferredSerif(to attr: NSMutableAttributedString) {
        guard let serifFace = resolvedSerifFontName() else { return }
        let full = NSRange(location: 0, length: attr.length)
        attr.enumerateAttribute(.font, in: full) { value, range, _ in
            guard let f = value as? NSFont else { return }
            let size = f.pointSize
            if let ny = NSFont(name: serifFace, size: max(10, size)) {
                attr.addAttribute(.font, value: ny, range: range)
            }
        }
    }

    private static func resolvedSerifFontName() -> String? {
        let probe = NSFont.systemFontSize
        for name in ["New York Small", "New York Medium", "Charter", "Palatino", "Baskerville"] where NSFont(name: name, size: probe) != nil {
            return name
        }
        return nil
    }

    final class Coordinator {
        var lastMarkdown: String = ""
        var lastContainerWidth: CGFloat = 0
    }
}
