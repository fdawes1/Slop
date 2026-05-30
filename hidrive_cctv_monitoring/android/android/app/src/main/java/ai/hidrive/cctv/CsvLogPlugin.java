package ai.hidrive.cctv;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;
import android.widget.Toast;

import androidx.core.content.FileProvider;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

@CapacitorPlugin(name = "CsvLog")
public class CsvLogPlugin extends Plugin {

    private File csvFile(String operator) {
        String safe = operator.replaceAll("[^a-zA-Z0-9_\\-]", "_");
        return new File(getContext().getFilesDir(), safe + "_cctv.csv");
    }

    private String safeFilename(String operator) {
        return operator.replaceAll("[^a-zA-Z0-9_\\-]", "_") + "_cctv.csv";
    }

    @PluginMethod
    public void readAll(PluginCall call) {
        String op = call.getString("operator", "log");
        File f = csvFile(op);
        try {
            String content = f.exists() ? readBytes(f) : "";
            JSObject ret = new JSObject();
            ret.put("content", content);
            call.resolve(ret);
        } catch (IOException e) {
            call.reject(e.getMessage());
        }
    }

    @PluginMethod
    public void writeAll(PluginCall call) {
        String op = call.getString("operator", "log");
        String content = call.getString("content", "");
        File f = csvFile(op);
        try (FileWriter fw = new FileWriter(f, false)) {
            fw.write(content);
            call.resolve();
        } catch (IOException e) {
            call.reject(e.getMessage());
        }
    }

    @PluginMethod
    public void clear(PluginCall call) {
        String op = call.getString("operator", "log");
        File f = csvFile(op);
        if (f.exists()) f.delete();
        call.resolve();
    }

    @PluginMethod
    public void share(PluginCall call) {
        String op = call.getString("operator", "log");
        String content = call.getString("content", "");
        String filename = safeFilename(op);

        // Always save to public Documents folder first
        try {
            saveToDocuments(filename, content);
            final String msg = "Saved to Documents/" + filename;
            getActivity().runOnUiThread(() ->
                Toast.makeText(getContext(), msg, Toast.LENGTH_LONG).show());
        } catch (IOException e) {
            // Non-fatal — proceed to share sheet even if Documents write fails
        }

        // Also open share sheet so they can send it somewhere
        File f = new File(getContext().getFilesDir(), filename);
        try (FileWriter fw = new FileWriter(f, false)) {
            fw.write(content);
        } catch (IOException e) {
            call.reject(e.getMessage());
            return;
        }

        Uri uri = FileProvider.getUriForFile(
            getContext(),
            getContext().getPackageName() + ".fileprovider",
            f
        );

        Intent intent = new Intent(Intent.ACTION_SEND);
        intent.setType("text/csv");
        intent.putExtra(Intent.EXTRA_STREAM, uri);
        intent.putExtra(Intent.EXTRA_SUBJECT, filename);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);

        getActivity().startActivity(Intent.createChooser(intent, "Share CSV"));
        call.resolve();
    }

    private void saveToDocuments(String filename, String content) throws IOException {
        byte[] bytes = content.getBytes(StandardCharsets.UTF_8);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ContentResolver resolver = getContext().getContentResolver();
            Uri collection = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL);

            // Delete any existing file with the same name so we overwrite cleanly
            resolver.delete(collection,
                MediaStore.MediaColumns.DISPLAY_NAME + "=? AND " +
                MediaStore.MediaColumns.RELATIVE_PATH + "=?",
                new String[]{filename, Environment.DIRECTORY_DOCUMENTS + "/"});

            ContentValues cv = new ContentValues();
            cv.put(MediaStore.MediaColumns.DISPLAY_NAME, filename);
            cv.put(MediaStore.MediaColumns.MIME_TYPE, "text/csv");
            cv.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOCUMENTS);

            Uri uri = resolver.insert(collection, cv);
            if (uri == null) throw new IOException("MediaStore insert failed");
            try (OutputStream os = resolver.openOutputStream(uri)) {
                if (os == null) throw new IOException("openOutputStream returned null");
                os.write(bytes);
            }
        } else {
            // Android 9 and below — write directly (needs WRITE_EXTERNAL_STORAGE permission)
            File dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS);
            dir.mkdirs();
            try (FileWriter fw = new FileWriter(new File(dir, filename), false)) {
                fw.write(content);
            }
        }
    }

    private static String readBytes(File f) throws IOException {
        try (FileInputStream fis = new FileInputStream(f);
             ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
            byte[] buf = new byte[8192];
            int n;
            while ((n = fis.read(buf)) != -1) baos.write(buf, 0, n);
            return baos.toString(StandardCharsets.UTF_8.name());
        }
    }
}
