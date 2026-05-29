import Foundation
import Capacitor
import UIKit

@objc(CsvLogPlugin)
public class CsvLogPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier   = "CsvLogPlugin"
    public let jsName       = "CsvLog"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "readAll",  returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "writeAll", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "clear",    returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "share",    returnType: CAPPluginReturnPromise),
    ]

    // MARK: - Helpers

    private func csvURL(for operator: String) -> URL {
        let safe = `operator`.replacingOccurrences(
            of: "[^a-zA-Z0-9_\\-]", with: "_", options: .regularExpression)
        return FileManager.default
            .urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("\(safe)_cctv.csv")
    }

    // MARK: - Plugin methods

    @objc func readAll(_ call: CAPPluginCall) {
        let op = call.getString("operator") ?? "log"
        let url = csvURL(for: op)
        let content = (try? String(contentsOf: url, encoding: .utf8)) ?? ""
        call.resolve(["content": content])
    }

    @objc func writeAll(_ call: CAPPluginCall) {
        let op      = call.getString("operator") ?? "log"
        let content = call.getString("content")  ?? ""
        do {
            try content.write(to: csvURL(for: op), atomically: true, encoding: .utf8)
            call.resolve()
        } catch {
            call.reject(error.localizedDescription)
        }
    }

    @objc func clear(_ call: CAPPluginCall) {
        let op = call.getString("operator") ?? "log"
        try? FileManager.default.removeItem(at: csvURL(for: op))
        call.resolve()
    }

    @objc func share(_ call: CAPPluginCall) {
        let op      = call.getString("operator") ?? "log"
        let content = call.getString("content")  ?? ""
        let url     = csvURL(for: op)

        // Always write to Documents so the file is accessible from Files app
        do {
            try content.write(to: url, atomically: true, encoding: .utf8)
        } catch {
            call.reject(error.localizedDescription)
            return
        }

        DispatchQueue.main.async {
            let vc = UIActivityViewController(activityItems: [url], applicationActivities: nil)
            // Anchor for iPad popover
            if let popover = vc.popoverPresentationController,
               let view = self.bridge?.viewController?.view {
                popover.sourceView = view
                popover.sourceRect = CGRect(
                    x: view.bounds.midX, y: view.bounds.midY, width: 0, height: 0)
                popover.permittedArrowDirections = []
            }
            self.bridge?.viewController?.present(vc, animated: true)
            call.resolve()
        }
    }
}
