// swift-tools-version: 5.9
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "ComputerUseDaemon",
    platforms: [
        .macOS(.v14) // Require macOS 14.0+ for SCScreenshotManager
    ],
    products: [
        // Products define the executables and libraries a package produces, making them visible to other packages.
        .executable(
            name: "computer-use-daemon",
            targets: ["computer-use-daemon"]
        )
    ],
    targets: [
        // Targets are the basic building blocks of a package, defining a module or a test suite.
        // Targets can depend on other targets in this package and products from dependencies.
        .executableTarget(
            name: "computer-use-daemon",
            path: "Sources"
        )
    ]
)
