// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ZZLedgerCore",
    platforms: [.macOS(.v13), .iOS(.v16)],
    products: [.library(name: "ZZLedgerCore", targets: ["ZZLedgerCore"])],
    targets: [
        .target(name: "ZZLedgerCore", path: "ZZLedger/Core"),
        .testTarget(name: "ZZLedgerCoreTests", dependencies: ["ZZLedgerCore"], path: "Tests")
    ]
)
