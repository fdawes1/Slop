package ai.hidrive.cctv;

import android.content.Intent;
import android.net.Uri;

import androidx.core.content.FileProvider;

import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

@CapacitorPlugin(name = "AppUpdate")
public class UpdatePlugin extends Plugin {

    @PluginMethod
    public void downloadAndInstall(PluginCall call) {
        String url   = call.getString("url");
        String token = call.getString("token", "");

        if (url == null || url.isEmpty()) {
            call.reject("url is required");
            return;
        }

        new Thread(() -> {
            try {
                File apkFile = downloadApk(url, token);
                installApk(apkFile);
                call.resolve();
            } catch (Exception e) {
                call.reject(e.getMessage());
            }
        }).start();
    }

    private File downloadApk(String url, String token) throws IOException {
        // Strip the Authorization header when redirected to a non-GitHub host (e.g. S3
        // pre-signed URLs reject requests that also carry a Bearer token).
        OkHttpClient client = new OkHttpClient.Builder()
            .addNetworkInterceptor(chain -> {
                Request req = chain.request();
                String host = req.url().host();
                if (!host.endsWith("github.com") && !host.endsWith("githubusercontent.com")) {
                    req = req.newBuilder().removeHeader("Authorization").build();
                }
                return chain.proceed(req);
            })
            .build();

        Request.Builder req = new Request.Builder()
            .url(url)
            .header("Accept", "application/octet-stream");
        if (token != null && !token.isEmpty()) {
            req.header("Authorization", "Bearer " + token);
        }

        try (Response resp = client.newCall(req.build()).execute()) {
            if (!resp.isSuccessful()) throw new IOException("Download failed: HTTP " + resp.code());
            File apkFile = new File(getContext().getCacheDir(), "update.apk");
            try (InputStream is = resp.body().byteStream();
                 FileOutputStream fos = new FileOutputStream(apkFile)) {
                byte[] buf = new byte[65536];
                int n;
                while ((n = is.read(buf)) != -1) fos.write(buf, 0, n);
            }
            return apkFile;
        }
    }

    private void installApk(File apkFile) {
        Uri apkUri = FileProvider.getUriForFile(
            getContext(),
            getContext().getPackageName() + ".fileprovider",
            apkFile
        );
        Intent intent = new Intent(Intent.ACTION_VIEW);
        intent.setDataAndType(apkUri, "application/vnd.android.package-archive");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
        getContext().startActivity(intent);
    }
}
