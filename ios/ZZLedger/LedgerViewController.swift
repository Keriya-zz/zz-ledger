import UIKit
import WebKit
import UniformTypeIdentifiers

private typealias NativeReply = (Any?, String?) -> Void

/// The content controller retains its handler; a weak proxy avoids retaining the screen.
private final class LedgerBridge: NSObject, WKScriptMessageHandlerWithReply {
    weak var owner: LedgerViewController?
    init(owner: LedgerViewController) { self.owner = owner }

    func userContentController(_ userContentController: WKUserContentController,
                               didReceive message: WKScriptMessage,
                               replyHandler: @escaping (Any?, String?) -> Void) {
        guard let owner = owner else { replyHandler(nil, "界面已关闭"); return }
        owner.receive(message, reply: replyHandler)
    }
}

final class LedgerViewController: UIViewController, WKNavigationDelegate, UIDocumentPickerDelegate {
    private var webView: WKWebView!
    private let io = DispatchQueue(label: "com.zzledger.ios.files", qos: .userInitiated)
    private let store = LedgerStore(directory: FileManager.default.urls(for: .applicationSupportDirectory,
                                                                        in: .userDomainMask)[0]
        .appendingPathComponent("ZZLedger", isDirectory: true))
    private var documentReply: NativeReply?
    private var documentID: UUID?
    private var exporting = false
    private var exportDirectory: URL?
    private let paper = UIColor(red: 250/255, green: 248/255, blue: 245/255, alpha: 1)

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = paper
        overrideUserInterfaceStyle = .light
        guard let root = Bundle.main.resourceURL?.appendingPathComponent("Web"),
              FileManager.default.fileExists(atPath: root.appendingPathComponent("index.html").path) else {
            showLoadError("缺少界面资源，请重新构建 App。")
            return
        }
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        config.preferences.javaScriptCanOpenWindowsAutomatically = false
        config.setURLSchemeHandler(LocalSchemeHandler(root: root), forURLScheme: BundledResource.scheme)
        config.userContentController.addScriptMessageHandler(LedgerBridge(owner: self),
                                                            contentWorld: .page, name: "zzLedger")
        webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = self
        webView.backgroundColor = paper
        webView.isOpaque = false
        webView.scrollView.backgroundColor = paper
        webView.scrollView.bounces = false
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.allowsBackForwardNavigationGestures = false
        webView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(webView)
        NSLayoutConstraint.activate([
            webView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            webView.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor),
            webView.bottomAnchor.constraint(equalTo: view.keyboardLayoutGuide.topAnchor)
        ])
        webView.load(URLRequest(url: BundledResource.home))
        // Clean only our own stale export copies after a previous interrupted picker.
        let oldExports = FileManager.default.temporaryDirectory.appendingPathComponent("ZZLedgerExports")
        io.async { try? FileManager.default.removeItem(at: oldExports) }
    }

    fileprivate func receive(_ message: WKScriptMessage, reply: @escaping (Any?, String?) -> Void) {
        guard message.frameInfo.isMainFrame,
              message.frameInfo.request.url?.scheme == BundledResource.scheme,
              message.frameInfo.request.url?.host == BundledResource.host,
              let body = message.body as? [String: Any], let action = body["action"] as? String else {
            reply(nil, "不允许的本地请求"); return
        }
        switch action {
        case "read":
            performIO(reply: reply) { [store] in
                if let text = try store.read() { return text }
                return NSNull()
            }
        case "write":
            guard let value = body["value"] as? String else { reply(nil, "账本格式不正确"); return }
            performIO(reply: reply) { [store] in try store.write(value); return NSNull() }
        case "import": startImport(reply: reply)
        case "export":
            guard let content = body["content"] as? String, let filename = body["filename"] as? String else {
                reply(nil, "导出内容不正确"); return
            }
            startExport(content: content, filename: filename, reply: reply)
        default: reply(nil, "不支持的操作")
        }
    }

    private func performIO(reply: @escaping NativeReply, work: @escaping () throws -> Any) {
        // A quick switch to another app must not interrupt the atomic save mid-flight.
        var task = UIBackgroundTaskIdentifier.invalid
        task = UIApplication.shared.beginBackgroundTask(withName: "账本文件操作") {
            if task != .invalid { UIApplication.shared.endBackgroundTask(task); task = .invalid }
        }
        io.async {
            let result = Result { try work() }
            DispatchQueue.main.async {
                switch result {
                case .success(let value): reply(value, nil)
                case .failure(let error): reply(nil, error.localizedDescription)
                }
                if task != .invalid { UIApplication.shared.endBackgroundTask(task); task = .invalid }
            }
        }
    }

    private func reserveDocument(export: Bool, reply: @escaping NativeReply) -> Bool {
        guard documentReply == nil, presentedViewController == nil else {
            reply(nil, "请先完成当前文件操作"); return false
        }
        documentReply = reply
        documentID = UUID()
        exporting = export
        return true
    }

    private func startImport(reply: @escaping NativeReply) {
        guard reserveDocument(export: false, reply: reply) else { return }
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: [.json, .plainText, .data], asCopy: true)
        picker.allowsMultipleSelection = false
        picker.delegate = self
        present(picker, animated: true)
    }

    private func startExport(content: String, filename: String, reply: @escaping NativeReply) {
        do { try LedgerStore.validateExport(content: content, filename: filename) }
        catch { reply(nil, error.localizedDescription); return }
        guard reserveDocument(export: true, reply: reply) else { return }
        let id = documentID
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ZZLedgerExports")
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        exportDirectory = directory
        performIO(reply: { [weak self] value, error in
            guard let self = self, self.documentID == id else { return }
            if let error = error { self.finishDocument(error: error); return }
            let picker = UIDocumentPickerViewController(forExporting: [directory.appendingPathComponent(filename)], asCopy: true)
            picker.delegate = self
            self.present(picker, animated: true)
        }) {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            try Data(content.utf8).write(to: directory.appendingPathComponent(filename),
                                       options: [.atomic, .completeFileProtection])
            return NSNull()
        }
    }

    func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
        finishDocument(error: exporting ? "已取消导出" : nil)
    }

    func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
        guard let url = urls.first else { documentPickerWasCancelled(controller); return }
        if exporting { finishDocument(value: "saved"); return }
        let id = documentID
        performIO(reply: { [weak self] value, error in
            guard let self = self, self.documentID == id else { return }
            self.finishDocument(value: value, error: error)
        }) {
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            var coordinationError: NSError?
            var result: Result<String, Error>?
            NSFileCoordinator().coordinate(readingItemAt: url, options: [], error: &coordinationError) { localURL in
                result = Result { try LedgerStore.readText(at: localURL) }
            }
            if let error = coordinationError { throw error }
            guard let result = result else { throw LedgerFileError.invalidUTF8 }
            return try result.get()
        }
    }

    private func finishDocument(value: Any? = nil, error: String? = nil) {
        let reply = documentReply
        documentReply = nil
        documentID = nil
        if let directory = exportDirectory {
            io.async { try? FileManager.default.removeItem(at: directory) }
        }
        exportDirectory = nil
        reply?(value ?? NSNull(), error)
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        // Bundled subresources use the scheme handler. Only our home document can navigate.
        let url = navigationAction.request.url
        let allowed = navigationAction.targetFrame?.isMainFrame == true &&
            url?.scheme == BundledResource.scheme && url?.host == BundledResource.host &&
            url?.path == "/index.html"
        decisionHandler(allowed ? .allow : .cancel)
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        if let picker = presentedViewController as? UIDocumentPickerViewController { picker.dismiss(animated: false) }
        finishDocument(error: "界面已重新加载，请重试")
        // All acknowledged changes are already on disk. Unsubmitted fields are not saved.
        webView.load(URLRequest(url: BundledResource.home))
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        showLoadError(error.localizedDescription)
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        showLoadError(error.localizedDescription)
    }

    private func showLoadError(_ message: String) {
        let label = UILabel()
        label.text = "zz记暂时无法打开\n\n" + message + "\n\n请关闭后重新打开 App。"
        label.numberOfLines = 0
        label.textAlignment = .center
        label.translatesAutoresizingMaskIntoConstraints = false
        label.accessibilityTraits = .staticText
        view.addSubview(label)
        NSLayoutConstraint.activate([
            label.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 24),
            label.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -24),
            label.centerYAnchor.constraint(equalTo: view.centerYAnchor)
        ])
    }
}
