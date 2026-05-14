import Foundation

enum UserLayout {
    /// 与 `app/desktop_app.py` 中 `_ensure_user_layout` 对齐：首次启动在用户目录生成配置骨架。
    static func ensureUserLayout(payload: URL, writable: URL) throws {
        let fm = FileManager.default
        let dirs: [URL] = [
            writable.appendingPathComponent("config", isDirectory: true),
            writable.appendingPathComponent("data/events", isDirectory: true),
            writable.appendingPathComponent("data/summaries", isDirectory: true),
            writable.appendingPathComponent("data/visual", isDirectory: true),
            writable.appendingPathComponent("data/inbox", isDirectory: true),
            writable.appendingPathComponent("data/imports", isDirectory: true),
            writable.appendingPathComponent("data/mobile", isDirectory: true),
            writable.appendingPathComponent("data/health", isDirectory: true),
        ]
        for d in dirs {
            try fm.createDirectory(at: d, withIntermediateDirectories: true)
        }

        let cfg = writable.appendingPathComponent("config", isDirectory: true)
        let ex = payload.appendingPathComponent("config", isDirectory: true)

        let settingsDst = cfg.appendingPathComponent("settings.json")
        let settingsEx = ex.appendingPathComponent("settings.example.json")
        if !fm.fileExists(atPath: settingsDst.path), fm.fileExists(atPath: settingsEx.path) {
            try fm.copyItem(at: settingsEx, to: settingsDst)
        }

        let switchesDst = cfg.appendingPathComponent("tool_switches.json")
        let switchesEx = ex.appendingPathComponent("tool_switches.example.json")
        if !fm.fileExists(atPath: switchesDst.path), fm.fileExists(atPath: switchesEx.path) {
            try fm.copyItem(at: switchesEx, to: switchesDst)
        }

        let growthDst = cfg.appendingPathComponent("growth_dimensions.json")
        if !fm.fileExists(atPath: growthDst.path) {
            let growthEx = ex.appendingPathComponent("growth_dimensions.json")
            if fm.fileExists(atPath: growthEx.path) {
                try fm.copyItem(at: growthEx, to: growthDst)
            } else {
                let minimal =
                    #"{"dimensions":[{"id":"general_input","name":"日常","description":"","keywords":[],"hosts":[]}]}"#
                try minimal.write(to: growthDst, atomically: true, encoding: .utf8)
            }
        }
    }
}
