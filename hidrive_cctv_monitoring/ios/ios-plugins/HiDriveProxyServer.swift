import Foundation

/// Minimal HTTP proxy that forwards requests to HiDrive WebDAV with Basic Auth.
/// Runs on localhost so the WebView can load videos and list directories without
/// CORS or auth-header restrictions. URLSession handles all HTTP methods including PROPFIND.
final class HiDriveProxyServer {
    private static let hiDriveHost = "https://webdav.hidrive.strato.com"

    private let port: UInt16
    private let authHeader: String
    private var serverFd: Int32 = -1
    private var running = false
    private let queue = DispatchQueue(label: "com.fdawes1.proxy", attributes: .concurrent)
    private let session = URLSession(configuration: .default)

    init(port: UInt16, username: String, password: String) {
        self.port = port
        let creds = Data("\(username):\(password)".utf8).base64EncodedString()
        self.authHeader = "Basic \(creds)"
    }

    func start() throws {
        let fd = socket(AF_INET, SOCK_STREAM, 0)
        guard fd >= 0 else { throw proxyError("socket() failed") }

        var reuse: Int32 = 1
        setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse, socklen_t(MemoryLayout<Int32>.size))

        var addr = sockaddr_in()
        addr.sin_family   = sa_family_t(AF_INET)
        addr.sin_port     = port.bigEndian
        addr.sin_addr     = in_addr(s_addr: inet_addr("127.0.0.1"))
        addr.sin_zero     = (0,0,0,0,0,0,0,0)

        let bound = withUnsafeMutablePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                bind(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        guard bound == 0, listen(fd, 16) == 0 else {
            close(fd)
            throw proxyError("bind/listen failed: \(errno)")
        }

        serverFd = fd
        running  = true
        queue.async(flags: .barrier) { self.acceptLoop() }
    }

    func stop() {
        running = false
        if serverFd >= 0 { close(serverFd); serverFd = -1 }
    }

    // MARK: - Accept loop

    private func acceptLoop() {
        while running {
            let client = accept(serverFd, nil, nil)
            if client < 0 { break }
            queue.async { self.handle(client) }
        }
    }

    // MARK: - Request handler

    private func handle(_ fd: Int32) {
        defer { close(fd) }

        // Read until we see the end-of-headers marker
        let headerTerminator = Data("\r\n\r\n".utf8)
        var raw = Data()
        let buf = UnsafeMutablePointer<UInt8>.allocate(capacity: 8192)
        defer { buf.deallocate() }

        while raw.range(of: headerTerminator) == nil {
            let n = recv(fd, buf, 8192, 0)
            guard n > 0 else { return }
            raw.append(buf, count: n)
            if raw.count > 65_536 { return }
        }

        guard let headerText = String(data: raw, encoding: .utf8) else { return }
        let lines = headerText.components(separatedBy: "\r\n")
        guard let requestLine = lines.first else { return }

        let parts = requestLine.components(separatedBy: " ")
        guard parts.count >= 2 else { return }
        let method  = parts[0]
        let rawPath = parts[1]

        // CORS preflight
        if method == "OPTIONS" {
            sendString(fd, "HTTP/1.1 200 OK\r\n" +
                "Access-Control-Allow-Origin: *\r\n" +
                "Access-Control-Allow-Methods: GET, PROPFIND, OPTIONS\r\n" +
                "Access-Control-Allow-Headers: Depth, Range, Content-Type\r\n" +
                "Content-Length: 0\r\nConnection: close\r\n\r\n")
            return
        }

        // Parse request headers
        var hdrs: [String: String] = [:]
        for line in lines.dropFirst() {
            guard !line.isEmpty, let sep = line.range(of: ": ") else { continue }
            hdrs[String(line[..<sep.lowerBound]).lowercased()] = String(line[sep.upperBound...])
        }

        // Build upstream URLRequest
        guard let url = URL(string: Self.hiDriveHost + rawPath) else { return }
        var req = URLRequest(url: url, timeoutInterval: 60)
        req.httpMethod = method
        req.setValue(authHeader, forHTTPHeaderField: "Authorization")
        for h in ["depth", "range", "content-type"] {
            if let v = hdrs[h] { req.setValue(v, forHTTPHeaderField: h) }
        }

        // Read body if present
        if let clStr = hdrs["content-length"], let cl = Int(clStr), cl > 0,
           let sep = raw.range(of: headerTerminator) {
            var body = Data(raw[sep.upperBound...])
            while body.count < cl {
                let n = recv(fd, buf, min(8192, cl - body.count), 0)
                guard n > 0 else { break }
                body.append(buf, count: n)
            }
            req.httpBody = body
        }

        // Execute synchronously on this background thread
        let sem = DispatchSemaphore(value: 0)
        var respData: Data?
        var httpResp: HTTPURLResponse?

        session.dataTask(with: req) { data, resp, _ in
            respData = data
            httpResp  = resp as? HTTPURLResponse
            sem.signal()
        }.resume()
        sem.wait()

        guard let resp = httpResp else {
            sendString(fd, "HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            return
        }

        var out  = "HTTP/1.1 \(resp.statusCode) OK\r\n"
        out += "Access-Control-Allow-Origin: *\r\n"
        out += "Access-Control-Allow-Methods: GET, PROPFIND, OPTIONS\r\n"
        out += "Access-Control-Allow-Headers: Depth, Range, Content-Type\r\n"
        out += "Access-Control-Expose-Headers: Content-Range, Content-Length, Accept-Ranges\r\n"
        out += "Connection: close\r\n"
        for (k, v) in resp.allHeaderFields {
            let key = "\(k)".lowercased()
            guard key != "transfer-encoding", key != "connection" else { continue }
            out += "\(k): \(v)\r\n"
        }
        out += "\r\n"

        var response = out.data(using: .utf8) ?? Data()
        if let body = respData { response.append(body) }
        sendData(fd, response)
    }

    // MARK: - Helpers

    private func sendString(_ fd: Int32, _ s: String) {
        guard let d = s.data(using: .utf8) else { return }
        sendData(fd, d)
    }

    private func sendData(_ fd: Int32, _ data: Data) {
        data.withUnsafeBytes { ptr in
            guard let base = ptr.baseAddress else { return }
            var sent = 0
            while sent < data.count {
                let n = send(fd, base + sent, data.count - sent, 0)
                guard n > 0 else { return }
                sent += n
            }
        }
    }

    private func proxyError(_ msg: String) -> Error {
        NSError(domain: "HiDriveProxy", code: -1, userInfo: [NSLocalizedDescriptionKey: msg])
    }
}
