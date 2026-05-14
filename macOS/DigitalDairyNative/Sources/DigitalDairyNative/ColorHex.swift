import SwiftUI

extension Color {
    init(hex: String) {
        let raw = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        let s = raw.hasPrefix("#") ? String(raw.dropFirst()) : raw
        guard s.count == 6, let v = UInt32(s, radix: 16) else {
            self = Color(nsColor: .windowBackgroundColor)
            return
        }
        let r = Double((v >> 16) & 0xFF) / 255.0
        let g = Double((v >> 8) & 0xFF) / 255.0
        let b = Double(v & 0xFF) / 255.0
        self.init(red: r, green: g, blue: b)
    }
}
