package com.fdawes1.cctv;

import android.content.Intent;
import android.net.Uri;

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
import java.nio.charset.StandardCharsets;

@CapacitorPlugin(name = "CsvLog")
public class CsvLogPlugin extends Plugin {

    private File csvFile(String operator) {
        String safe = operator.replaceAll("[^a-zA-Z0-9_\\-]", "_");
        return new File(getContext().getFilesDir(), safe + "_cctv.csv");
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
        String safe = op.replaceAll("[^a-zA-Z0-9_\\-]", "_");
        String filename = safe + "_cctv.csv";

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
