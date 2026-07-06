// swift-tools-version: 6.2
// Package manifest for the Carina macOS companion (menu bar app + IPC library).

import PackageDescription

let package = Package(
    name: "Carina",
    platforms: [
        .macOS(.v15),
    ],
    products: [
        .library(name: "CarinaIPC", targets: ["CarinaIPC"]),
        .library(name: "CarinaDiscovery", targets: ["CarinaDiscovery"]),
        .executable(name: "Carina", targets: ["Carina"]),
        .executable(name: "openclaw-mac", targets: ["CarinaMacCLI"]),
    ],
    dependencies: [
        .package(url: "https://github.com/orchetect/MenuBarExtraAccess", exact: "1.3.0"),
        .package(url: "https://github.com/swiftlang/swift-subprocess.git", from: "0.4.0"),
        .package(url: "https://github.com/apple/swift-log.git", from: "1.10.1"),
        .package(url: "https://github.com/sparkle-project/Sparkle", from: "2.9.0"),
        .package(url: "https://github.com/steipete/Peekaboo.git", exact: "3.5.2"),
        .package(path: "../shared/CarinaKit"),
        .package(path: "../swabble"),
    ],
    targets: [
        .target(
            name: "CarinaIPC",
            dependencies: [],
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
            ]),
        .target(
            name: "CarinaDiscovery",
            dependencies: [
                .product(name: "CarinaKit", package: "CarinaKit"),
            ],
            path: "Sources/CarinaDiscovery",
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
            ]),
        .executableTarget(
            name: "Carina",
            dependencies: [
                "CarinaIPC",
                "CarinaDiscovery",
                .product(name: "CarinaKit", package: "CarinaKit"),
                .product(name: "CarinaChatUI", package: "CarinaKit"),
                .product(name: "CarinaProtocol", package: "CarinaKit"),
                .product(name: "SwabbleKit", package: "swabble"),
                .product(name: "MenuBarExtraAccess", package: "MenuBarExtraAccess"),
                .product(name: "Subprocess", package: "swift-subprocess"),
                .product(name: "Logging", package: "swift-log"),
                .product(name: "Sparkle", package: "Sparkle"),
                .product(name: "PeekabooBridge", package: "Peekaboo"),
                .product(name: "PeekabooAutomationKit", package: "Peekaboo"),
            ],
            exclude: [
                "Resources/Info.plist",
            ],
            resources: [
                .copy("Resources/Carina.icns"),
                .copy("Resources/DeviceModels"),
            ],
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
            ]),
        .executableTarget(
            name: "CarinaMacCLI",
            dependencies: [
                "CarinaDiscovery",
                .product(name: "CarinaKit", package: "CarinaKit"),
                .product(name: "CarinaProtocol", package: "CarinaKit"),
            ],
            path: "Sources/CarinaMacCLI",
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
            ]),
        .testTarget(
            name: "CarinaIPCTests",
            dependencies: [
                "CarinaIPC",
                "Carina",
                "CarinaMacCLI",
                "CarinaDiscovery",
                .product(name: "CarinaProtocol", package: "CarinaKit"),
                .product(name: "SwabbleKit", package: "swabble"),
            ],
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
                .enableExperimentalFeature("SwiftTesting"),
            ]),
    ])
