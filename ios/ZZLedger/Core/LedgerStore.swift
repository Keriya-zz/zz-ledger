import Foundation

enum LedgerFileError: LocalizedError {
    case tooLarge, invalidUTF8, invalidLedger, invalidFilename, invalidResource

    var errorDescription: String? {
        switch self {
        case .tooLarge: return "账本最大支持 10 MB"
        case .invalidUTF8: return "文件为空或不是 UTF-8 文本，请选择有效备份"
        case .invalidLedger: return "账本格式不正确"
        case .invalidFilename: return "导出文件名无效"
        case .invalidResource: return "无法加载本地界面资源"
        }
    }
}

/// Access only from the controller's serial I/O queue. JS validates the full domain schema.
final class LedgerStore {
    static let limit = 10 * 1024 * 1024
    let directory: URL
    private let files: FileManager
    var ledgerURL: URL { directory.appendingPathComponent("ledger.json") }
    var previousURL: URL { directory.appendingPathComponent("ledger.previous.json") }

    init(directory: URL, files: FileManager = .default) {
        self.directory = directory
        self.files = files
    }

    func read() throws -> String? {
        // Only a missing file is a first launch. Never silently reset on read failure.
        do { return try Self.readText(at: ledgerURL) }
        catch let error as NSError where error.domain == NSCocoaErrorDomain &&
            [NSFileReadNoSuchFileError, NSFileNoSuchFileError].contains(error.code) {
            return nil
        }
    }

    func write(_ text: String) throws {
        let data = Data(text.utf8)
        try Self.validateEnvelope(data)
        try files.createDirectory(at: directory, withIntermediateDirectories: true)
        if files.fileExists(atPath: ledgerURL.path) {
            let old = try Self.readLimited(at: ledgerURL)
            // Preserve a damaged original separately during explicit import recovery.
            let backup = (try? Self.validateEnvelope(old)) != nil
                ? previousURL : directory.appendingPathComponent("ledger.recovered-original.json")
            try atomicWrite(old, to: backup)
        }
        try atomicWrite(data, to: ledgerURL)
    }

    private func atomicWrite(_ data: Data, to url: URL) throws {
        #if os(iOS)
        try data.write(to: url, options: [.atomic, .completeFileProtection])
        #else
        try data.write(to: url, options: .atomic)
        #endif
    }

    static func readLimited(at url: URL) throws -> Data {
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        var data = Data()
        while let chunk = try handle.read(upToCount: min(64 * 1024, limit + 1 - data.count)), !chunk.isEmpty {
            data.append(chunk)
            if data.count > limit { throw LedgerFileError.tooLarge }
        }
        return data
    }

    static func readText(at url: URL) throws -> String {
        let data = try readLimited(at: url)
        guard let text = String(data: data, encoding: .utf8), !text.isEmpty else {
            throw LedgerFileError.invalidUTF8
        }
        return text
    }

    static func validateEnvelope(_ data: Data) throws {
        guard data.count <= limit else { throw LedgerFileError.tooLarge }
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let version = json["version"] as? NSNumber,
              String(cString: version.objCType) != "c", version == 1,
              json["accounts"] is [[String: Any]], json["entries"] is [[String: Any]] else {
            throw LedgerFileError.invalidLedger
        }
    }

    static func validateExport(content: String, filename: String) throws {
        guard content.utf8.count <= limit else { throw LedgerFileError.tooLarge }
        guard !filename.isEmpty, filename.utf8.count <= 240,
              !filename.contains("/"), !filename.contains("\\"),
              !filename.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }),
              ["json", "csv"].contains((filename as NSString).pathExtension) else {
            throw LedgerFileError.invalidFilename
        }
    }
}
