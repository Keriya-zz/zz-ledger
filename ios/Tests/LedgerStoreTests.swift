import Foundation
import XCTest
@testable import ZZLedgerCore

final class LedgerStoreTests: XCTestCase {
    var folder: URL!
    var store: LedgerStore!
    let first = "{\"version\":1,\"accounts\":[],\"entries\":[]}"
    let second = "{\"version\":1,\"accounts\":[],\"entries\":[],\"debts\":[],\"transfers\":[]}"

    override func setUpWithError() throws {
        folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        store = LedgerStore(directory: folder)
    }
    override func tearDownWithError() throws {
        if FileManager.default.fileExists(atPath: folder.path) { try FileManager.default.removeItem(at: folder) }
    }

    func testFirstLaunchAndRestartAndPreviousVersion() throws {
        XCTAssertNil(try store.read())
        try store.write(first)
        XCTAssertEqual(try LedgerStore(directory: folder).read(), first)
        try store.write(second)
        XCTAssertEqual(try store.read(), second)
        XCTAssertEqual(try LedgerStore.readText(at: store.previousURL), first)
    }

    func testInvalidWriteDoesNotReplaceLedgerOrBackup() throws {
        try store.write(first)
        try store.write(second)
        for invalid in ["{bad", "[]", "{\"version\":true,\"accounts\":[],\"entries\":[]}",
                        "{\"version\":2,\"accounts\":[],\"entries\":[]}"] {
            XCTAssertThrowsError(try store.write(invalid))
            XCTAssertEqual(try store.read(), second)
            XCTAssertEqual(try LedgerStore.readText(at: store.previousURL), first)
        }
    }

    func testBackupFailureAbortsBeforeReplacingLedger() throws {
        try store.write(first)
        try FileManager.default.createDirectory(at: store.previousURL, withIntermediateDirectories: true)
        try Data("keep".utf8).write(to: store.previousURL.appendingPathComponent("sentinel"))
        XCTAssertThrowsError(try store.write(second))
        XCTAssertEqual(try store.read(), first)
    }

    func testCorruptAndEmptyFilesAreNotTreatedAsFirstLaunch() throws {
        try store.write(first)
        try store.write(second)
        try Data("broken".utf8).write(to: store.ledgerURL)
        XCTAssertEqual(try store.read(), "broken")
        try store.write(second) // explicit validated import preserves the damaged original
        XCTAssertEqual(try LedgerStore.readText(at: folder.appendingPathComponent("ledger.recovered-original.json")), "broken")
        XCTAssertEqual(try LedgerStore.readText(at: store.previousURL), first)
        try Data().write(to: store.ledgerURL)
        XCTAssertThrowsError(try store.read())
    }

    func testSizeAndEncodingLimits() throws {
        try store.write(first)
        let oversized = String(repeating: "x", count: LedgerStore.limit + 1)
        XCTAssertThrowsError(try store.write(oversized))
        XCTAssertEqual(try store.read(), first)
        let imported = folder.appendingPathComponent("import.json")
        try Data(oversized.utf8).write(to: imported)
        XCTAssertThrowsError(try LedgerStore.readText(at: imported))
        try Data([0xff, 0xfe]).write(to: imported)
        XCTAssertThrowsError(try LedgerStore.readText(at: imported))
    }

    func testExportNamesAndUnicodeBytes() throws {
        try LedgerStore.validateExport(content: first, filename: "zz记-账本备份.json")
        try LedgerStore.validateExport(content: "日期,金额", filename: "每日.csv")
        for name in ["../ledger.json", "a/b.json", "a\\b.json", "a\n.json", "bad.html", ""] {
            XCTAssertThrowsError(try LedgerStore.validateExport(content: first, filename: name))
        }
        XCTAssertThrowsError(try LedgerStore.validateExport(content: String(repeating: "记", count: LedgerStore.limit / 3 + 1), filename: "a.json"))
    }

    func testResourceOriginTraversalAndSymlinks() throws {
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        let file = try BundledResource.resolve(URL(string: "zzledger://app/styles/overview.css")!, root: folder)
        XCTAssertEqual(file.mime, "text/css")
        XCTAssertTrue(file.url.path.hasSuffix("/styles/overview.css"))
        for url in ["https://app/index.html", "zzledger://other/index.html", "zzledger://app/../ledger.json",
                    "zzledger://app/%2e%2e/secret.js", "zzledger://app/a.txt", "zzledger://user@app/index.html"] {
            XCTAssertThrowsError(try BundledResource.resolve(URL(string: url)!, root: folder))
        }
        try FileManager.default.createSymbolicLink(at: folder.appendingPathComponent("outside"),
                                                 withDestinationURL: folder.deletingLastPathComponent())
        XCTAssertThrowsError(try BundledResource.resolve(URL(string: "zzledger://app/outside/secret.js")!, root: folder))
    }
}
