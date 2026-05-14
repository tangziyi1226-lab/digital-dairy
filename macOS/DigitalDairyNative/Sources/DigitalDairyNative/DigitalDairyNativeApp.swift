import SwiftUI

@main
struct DigitalDairyNativeApp: App {
    @StateObject private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
        }
        .defaultSize(width: 980, height: 720)
    }
}
