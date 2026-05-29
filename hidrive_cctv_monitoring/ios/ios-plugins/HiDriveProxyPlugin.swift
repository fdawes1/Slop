import Foundation
import Capacitor

@objc(HiDriveProxyPlugin)
public class HiDriveProxyPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier   = "HiDriveProxyPlugin"
    public let jsName       = "HiDriveProxy"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "start", returnType: CAPPluginReturnPromise),
    ]

    private var server: HiDriveProxyServer?

    @objc func start(_ call: CAPPluginCall) {
        guard let username = call.getString("username"),
              let password = call.getString("password") else {
            call.reject("username and password are required")
            return
        }
        let port = UInt16(call.getInt("port") ?? 18765)

        let srv = HiDriveProxyServer(port: port, username: username, password: password)
        do {
            try srv.start()
            self.server = srv
            call.resolve(["port": port])
        } catch {
            call.reject(error.localizedDescription)
        }
    }
}
