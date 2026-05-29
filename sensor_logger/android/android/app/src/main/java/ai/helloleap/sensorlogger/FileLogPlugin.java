package com.fdawes1.sensorlogger;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;

import androidx.core.content.FileProvider;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@CapacitorPlugin(name = "FileLog")
public class FileLogPlugin extends Plugin {

    private BufferedWriter writer;
    private File logFile;
    private String openSession;
    // Single-threaded executor ensures rows are written in order without blocking the bridge
    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    private File sessionFile(String session) {
        String safe = session.replaceAll("[^a-zA-Z0-9_\\-]", "_");
        return new File(getContext().getFilesDir(), safe + "_sensorlog.csv");
    }

    @PluginMethod
    public void open(PluginCall call) {
        String session = call.getString("session", "session_" + System.currentTimeMillis());
        executor.execute(() -> {
            try {
                if (writer != null) { writer.close(); }
                logFile     = sessionFile(session);
                openSession = session;
                writer      = new BufferedWriter(new FileWriter(logFile, false));
                writer.write("timestamp_ms,sensor_type,v0,v1,v2,v3\n");
                writer.flush();
                JSObject ret = new JSObject();
                ret.put("path", logFile.getAbsolutePath());
                call.resolve(ret);
            } catch (IOException e) {
                call.reject(e.getMessage());
            }
        });
    }

    @PluginMethod
    public void appendRow(PluginCall call) {
        String row = call.getString("row", "");
        if (writer == null) { call.resolve(); return; }
        executor.execute(() -> {
            try {
                writer.write(row);
                call.resolve();
            } catch (IOException e) {
                call.reject(e.getMessage());
            }
        });
    }

    @PluginMethod
    public void flush(PluginCall call) {
        if (writer == null) { call.resolve(); return; }
        executor.execute(() -> {
            try {
                writer.flush();
                call.resolve();
            } catch (IOException e) {
                call.reject(e.getMessage());
            }
        });
    }

    @PluginMethod
    public void close(PluginCall call) {
        executor.execute(() -> {
            try {
                if (writer != null) { writer.close(); writer = null; }
                call.resolve();
            } catch (IOException e) {
                call.reject(e.getMessage());
            }
        });
    }

    @PluginMethod
    public void share(PluginCall call) {
        String session = call.getString("session", openSession != null ? openSession : "");
        File f = sessionFile(session);
        if (!f.exists()) { call.reject("No log file for session: " + session); return; }

        // Flush before sharing
        executor.execute(() -> {
            try {
                if (writer != null) writer.flush();
            } catch (IOException ignored) {}
        });

        // Save a copy to public Documents
        try { saveToDocuments(f); } catch (IOException ignored) {}

        Uri uri = FileProvider.getUriForFile(
            getContext(), getContext().getPackageName() + ".fileprovider", f);

        Intent intent = new Intent(Intent.ACTION_SEND);
        intent.setType("text/csv");
        intent.putExtra(Intent.EXTRA_STREAM, uri);
        intent.putExtra(Intent.EXTRA_SUBJECT, f.getName());
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        getActivity().startActivity(Intent.createChooser(intent, "Export sensor log"));
        call.resolve();
    }

    @PluginMethod
    public void clear(PluginCall call) {
        String session = call.getString("session", openSession != null ? openSession : "");
        executor.execute(() -> {
            if (writer != null && session.equals(openSession)) {
                try { writer.close(); } catch (IOException ignored) {}
                writer = null;
            }
            sessionFile(session).delete();
            call.resolve();
        });
    }

    private void saveToDocuments(File src) throws IOException {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ContentResolver resolver = getContext().getContentResolver();
            Uri col = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL);
            resolver.delete(col,
                MediaStore.MediaColumns.DISPLAY_NAME + "=? AND " +
                MediaStore.MediaColumns.RELATIVE_PATH + "=?",
                new String[]{ src.getName(), Environment.DIRECTORY_DOCUMENTS + "/" });
            ContentValues cv = new ContentValues();
            cv.put(MediaStore.MediaColumns.DISPLAY_NAME, src.getName());
            cv.put(MediaStore.MediaColumns.MIME_TYPE, "text/csv");
            cv.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOCUMENTS);
            Uri uri = resolver.insert(col, cv);
            if (uri != null) {
                try (OutputStream os = resolver.openOutputStream(uri);
                     java.io.FileInputStream fis = new java.io.FileInputStream(src)) {
                    if (os != null) {
                        byte[] buf = new byte[8192]; int n;
                        while ((n = fis.read(buf)) != -1) os.write(buf, 0, n);
                    }
                }
            }
        } else {
            File dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS);
            dir.mkdirs();
            File dst = new File(dir, src.getName());
            try (java.io.FileInputStream fis = new java.io.FileInputStream(src);
                 java.io.FileOutputStream fos = new java.io.FileOutputStream(dst)) {
                byte[] buf = new byte[8192]; int n;
                while ((n = fis.read(buf)) != -1) fos.write(buf, 0, n);
            }
        }
    }
}
