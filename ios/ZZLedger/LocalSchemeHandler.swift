import Foundation
import WebKit

final class LocalSchemeHandler: NSObject, WKURLSchemeHandler {
    private let root: URL
    init(root: URL) { self.root = root }

    func webView(_ webView: WKWebView, start urlSchemeTask: WKURLSchemeTask) {
        // Small bundled resources are delivered synchronously; no callback can race a stopped task.
        do {
            guard let url = urlSchemeTask.request.url else { throw LedgerFileError.invalidResource }
            let resource = try BundledResource.resolve(url, root: root)
            let data = try Data(contentsOf: resource.url)
            urlSchemeTask.didReceive(URLResponse(url: url, mimeType: resource.mime,
                                                expectedContentLength: data.count,
                                                textEncodingName: resource.mime == "image/png" ? nil : "utf-8"))
            urlSchemeTask.didReceive(data)
            urlSchemeTask.didFinish()
        } catch { urlSchemeTask.didFailWithError(error) }
    }

    func webView(_ webView: WKWebView, stop urlSchemeTask: WKURLSchemeTask) {}
}
