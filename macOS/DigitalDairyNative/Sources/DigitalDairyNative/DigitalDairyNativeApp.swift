import AppKit
import SwiftUI

@main
struct DigitalDairyNativeApp: App {
    @StateObject private var model = AppModel()

    init() {
        // 设置 Dock / Finder / 切换器中的应用图标
        if let url = Bundle.module.url(forResource: "DigitalDiary", withExtension: "png"),
           let image = NSImage(contentsOf: url) {
            NSApplication.shared.applicationIconImage = image
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
