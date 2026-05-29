package com.fdawes1.cctv;

import android.util.Base64;
import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import okhttp3.*;

/**
 * Minimal HTTP proxy that forwards requests to HiDrive WebDAV with Basic Auth.
 * Uses OkHttp so non-standard methods like PROPFIND are supported.
 */
public class HiDriveProxyServer {
    private static final String HIDRIVE_HOST = "https://webdav.hidrive.strato.com";

    private final int port;
    private final String authHeader;
    private final OkHttpClient httpClient;
    private ServerSocket serverSocket;
    private volatile boolean running;

    public HiDriveProxyServer(int port, String username, String password) {
        this.port = port;
        String creds = username + ":" + password;
        this.authHeader = "Basic " + Base64.encodeToString(creds.getBytes(), Base64.NO_WRAP);
        this.httpClient = new OkHttpClient.Builder()
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(60, TimeUnit.SECONDS)
                .followRedirects(true)
                .build();
    }

    public void start() throws IOException {
        serverSocket = new ServerSocket(port, 50, InetAddress.getByName("127.0.0.1"));
        running = true;
        Thread t = new Thread(this::acceptLoop);
        t.setDaemon(true);
        t.start();
    }

    public void stop() {
        running = false;
        try { if (serverSocket != null) serverSocket.close(); } catch (IOException ignored) {}
        httpClient.dispatcher().executorService().shutdown();
    }

    private void acceptLoop() {
        while (running) {
            try {
                Socket client = serverSocket.accept();
                Thread t = new Thread(() -> {
                    try { handle(client); } catch (Exception e) { e.printStackTrace(); }
                });
                t.setDaemon(true);
                t.start();
            } catch (IOException e) {
                if (running) e.printStackTrace();
            }
        }
    }

    private void handle(Socket client) throws Exception {
        try (client) {
            InputStream in = client.getInputStream();

            // Read request line
            String requestLine = readLine(in);
            if (requestLine == null || requestLine.isEmpty()) return;
            String[] parts = requestLine.split(" ", 3);
            if (parts.length < 2) return;
            String method = parts[0];
            String rawPath = parts[1];

            // Read request headers
            Map<String, String> reqHeaders = new LinkedHashMap<>();
            String line;
            while ((line = readLine(in)) != null && !line.isEmpty()) {
                int colon = line.indexOf(':');
                if (colon > 0) {
                    reqHeaders.put(line.substring(0, colon).trim().toLowerCase(),
                                   line.substring(colon + 1).trim());
                }
            }

            // CORS preflight
            if ("OPTIONS".equals(method)) {
                writeStatus(client.getOutputStream(), 204);
                return;
            }

            // Read body if present
            int contentLen = 0;
            try { contentLen = Integer.parseInt(reqHeaders.getOrDefault("content-length", "0")); }
            catch (NumberFormatException ignored) {}
            RequestBody body = null;
            if (contentLen > 0) {
                byte[] bodyBytes = readFully(in, contentLen);
                String ct = reqHeaders.getOrDefault("content-type", "application/octet-stream");
                body = RequestBody.create(bodyBytes, MediaType.parse(ct));
            }

            // Build OkHttp request — supports PROPFIND and any other WebDAV method
            Request.Builder reqBuilder = new Request.Builder()
                    .url(HIDRIVE_HOST + rawPath)
                    .method(method, body)
                    .header("Authorization", authHeader)
                    .header("Connection", "close");

            for (String h : Arrays.asList("depth", "range", "content-type")) {
                String v = reqHeaders.get(h);
                if (v != null) reqBuilder.header(h, v);
            }

            try (Response response = httpClient.newCall(reqBuilder.build()).execute()) {
                int status = response.code();
                ResponseBody responseBody = response.body();

                OutputStream out = client.getOutputStream();
                StringBuilder hdr = new StringBuilder();
                hdr.append("HTTP/1.1 ").append(status).append(" OK\r\n");
                hdr.append("Access-Control-Allow-Origin: *\r\n");
                hdr.append("Access-Control-Allow-Methods: GET, PROPFIND, OPTIONS\r\n");
                hdr.append("Access-Control-Allow-Headers: Depth, Range, Content-Type\r\n");
                hdr.append("Access-Control-Expose-Headers: Content-Range, Content-Length, Accept-Ranges\r\n");
                hdr.append("Connection: close\r\n");

                Headers respHeaders = response.headers();
                for (int i = 0; i < respHeaders.size(); i++) {
                    String key = respHeaders.name(i);
                    String lk = key.toLowerCase();
                    if (lk.equals("transfer-encoding") || lk.equals("connection")) continue;
                    hdr.append(key).append(": ").append(respHeaders.value(i)).append("\r\n");
                }
                hdr.append("\r\n");
                out.write(hdr.toString().getBytes("UTF-8"));

                if (responseBody != null) {
                    byte[] buf = new byte[65536];
                    InputStream bodyStream = responseBody.byteStream();
                    int n;
                    while ((n = bodyStream.read(buf)) != -1) out.write(buf, 0, n);
                }
                out.flush();
            }
        }
    }

    private void writeStatus(OutputStream out, int status) throws IOException {
        String resp = "HTTP/1.1 " + status + " OK\r\n" +
                "Access-Control-Allow-Origin: *\r\n" +
                "Access-Control-Allow-Methods: GET, PROPFIND, OPTIONS\r\n" +
                "Access-Control-Allow-Headers: Depth, Range, Content-Type\r\n" +
                "Connection: close\r\n\r\n";
        out.write(resp.getBytes("UTF-8"));
        out.flush();
    }

    private String readLine(InputStream in) throws IOException {
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        int prev = -1, b;
        while ((b = in.read()) != -1) {
            if (b == '\n' && prev == '\r') {
                byte[] bytes = buf.toByteArray();
                return new String(bytes, 0, bytes.length - 1, "UTF-8");
            }
            buf.write(b);
            prev = b;
        }
        return buf.size() > 0 ? buf.toString("UTF-8") : null;
    }

    private byte[] readFully(InputStream in, int length) throws IOException {
        byte[] buf = new byte[length];
        int read = 0;
        while (read < length) {
            int n = in.read(buf, read, length - read);
            if (n < 0) break;
            read += n;
        }
        return buf;
    }
}
