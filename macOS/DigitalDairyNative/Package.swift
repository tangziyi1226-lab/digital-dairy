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
    dependencies: [
        .package(url: "https://github.com/gonzalezreal/swift-markdown-ui", from: "2.3.0"),
    ],
    targets: [
        .executableTarget(
            name: "DigitalDairyNative",
            dependencies: [
                .product(name: "MarkdownUI", package: "swift-markdown-ui"),
            ],
            path: "Sources/DigitalDairyNative",
            resources: [
                .process("Resources"),
            ]
        ),
    ]
)
