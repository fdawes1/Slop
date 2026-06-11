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
        OkHttpClient client = new OkHttpClient();
        Request.Builder req = new Request.Builder()
            .url(url)
            .header("Accept", "application/octet-stream");
        if (token != null && !token.isEmpty()) {
            req.header("Authorization", "Bearer " + token);
        }

        try (Response resp = client.newCall(req.build()).execute()) {
            if (!resp.isSuccessful()) throw new IOException("Download failed: HTTP " + resp.code());
            if (resp.body() == null) throw new IOException("Empty response body");
            File apkFile = new File(getContext().getCacheDir(), "update.apk");
            try (InputStream is = resp.body().byteStream();
                 FileOutputStream fos = new FileOutputStream(apkFile)) {
                byte[] buf = new byte[32768];
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
