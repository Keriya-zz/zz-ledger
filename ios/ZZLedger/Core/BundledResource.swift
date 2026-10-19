import Foundation

enum BundledResource {
    static let scheme = "zzledger"
    static let host = "app"
    static let home = URL(string: "zzledger://app/index.html")!

    static func resolve(_ request: URL, root: URL) throws -> (url: URL, mime: String) {
        guard request.scheme == scheme, request.host == host,
              request.user == nil, request.password == nil, request.port == nil else {
            throw LedgerFileError.invalidResource
        }
        let path = request.path
        guard !path.split(separator: "/").contains(".."), !path.contains("\\") else {
            throw LedgerFileError.invalidResource
        }
        let base = root.resolvingSymlinksInPath().standardizedFileURL
        var file = base
        for component in (path == "/" ? "index.html" : path).split(separator: "/") {
            file.appendPathComponent(String(component))
            // Check each existing parent too: resolving a missing leaf can leave symlinks unresolved.
            let kind = (try? FileManager.default.attributesOfItem(atPath: file.path))?[.type] as? FileAttributeType
            guard kind != .typeSymbolicLink else { throw LedgerFileError.invalidResource }
        }
        file = file.standardizedFileURL
        let types = ["html": "text/html", "js": "application/javascript", "css": "text/css", "png": "image/png"]
        guard file.path.hasPrefix(base.path + "/"), let mime = types[file.pathExtension] else {
            throw LedgerFileError.invalidResource
        }
        return (file, mime)
    }
}
