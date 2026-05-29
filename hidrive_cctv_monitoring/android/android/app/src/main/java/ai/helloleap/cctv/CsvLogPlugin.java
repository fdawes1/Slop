package com.fdawes1.cctv;

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
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

@CapacitorPlugin(name = "CsvLog")
public class CsvLogPlugin extends Plugin {

    private File csvFile(String operator) {
        String safe = operator.replaceAll("[^a-zA-Z0-9_\\-]", "_");
        return new File(getContext().getExternalFilesDir(null), safe + "_cctv.csv");
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
