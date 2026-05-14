// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "DigitalDairyNative",
    platforms: [
        .macOS(.v14),
    ],
    products: [
        .executable(name: "DigitalDairyNative", targets: ["DigitalDairyNative"]),
    ],
    targets: [
        .executableTarget(
            name: "DigitalDairyNative",
            path: "Sources/DigitalDairyNative",
            resources: [
                .process("Resources"),
            ]
        ),
    ]
)
