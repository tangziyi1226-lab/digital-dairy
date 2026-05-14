import AppKit
import SwiftUI

@main
struct DigitalDairyNativeApp: App {
    @StateObject private var model = AppModel()

    init() {
        // 设置 Dock / Finder / 切换器中的应用图标（圆角比例对齐 Apple 图标模板网格）
        if let url = Bundle.module.url(forResource: "DigitalDiary", withExtension: "png"),
           let image = NSImage(contentsOf: url) {
            NSApplication.shared.applicationIconImage = image.withMacOSApplicationIconShape()
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
        }
        .defaultSize(width: 980, height: 720)
    }
}

private extension NSImage {
    /// 将方形图标裁成与 macOS / Apple 图标模板相近的圆角矩形（短边 × ~22.37%）。
    func withMacOSApplicationIconShape(cornerRadiusFraction: CGFloat = 0.2237) -> NSImage {
        let s = size
        guard s.width > 0, s.height > 0 else { return self }
        let r = min(s.width, s.height) * cornerRadiusFraction
        return NSImage(size: s, flipped: false) { bounds in
            NSBezierPath(roundedRect: bounds, xRadius: r, yRadius: r).addClip()
            self.draw(in: bounds, from: NSRect(origin: .zero, size: s), operation: .copy, fraction: 1.0)
            return true
        }
    }
}
