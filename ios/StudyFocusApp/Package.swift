// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "StudyFocusApp",
    platforms: [
        .iOS(.v17)
    ],
    products: [
        .library(
            name: "StudyFocusApp",
            targets: ["StudyFocusApp"]
        )
    ],
    targets: [
        .target(
            name: "StudyFocusApp",
            path: "Sources/StudyFocusApp"
        )
    ],
    swiftLanguageVersions: [.v5]
)
