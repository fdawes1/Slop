package com.fdawes1.sensorlogger;

import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;

@CapacitorPlugin(
    name = "Audio",
    permissions = {
        @Permission(strings = { android.Manifest.permission.RECORD_AUDIO }, alias = "microphone")
    }
)
public class AudioPlugin extends Plugin {

    private AudioRecord audioRecord;
    private Thread captureThread;
    private volatile boolean running = false;

    @PluginMethod
    public void start(PluginCall call) {
        if (!hasRequiredPermissions()) {
            requestAllPermissions(call, "micPermCallback");
            return;
        }
        doStart(call);
    }

    @com.getcapacitor.annotation.PermissionCallback
    private void micPermCallback(PluginCall call) {
        if (hasRequiredPermissions()) doStart(call);
        else call.reject("Microphone permission denied");
    }

    private void doStart(PluginCall call) {
        if (running) { call.resolve(); return; }
        int rate = call.getInt("sampleRate", 44100);
        int minBuf = AudioRecord.getMinBufferSize(rate,
            AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
        int bufSize = Math.max(minBuf, 4096);

        try {
            audioRecord = new AudioRecord(MediaRecorder.AudioSource.MIC, rate,
                AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, bufSize * 2);
        } catch (SecurityException e) {
            call.reject(e.getMessage());
            return;
        }

        audioRecord.startRecording();
        running = true;

        final short[] pcmBuf = new short[bufSize];
        captureThread = new Thread(() -> {
            while (running) {
                int n = audioRecord.read(pcmBuf, 0, bufSize);
                if (n <= 0) continue;

                double sumSq = 0;
                for (int i = 0; i < n; i++) sumSq += (double) pcmBuf[i] * pcmBuf[i];
                double rms = Math.sqrt(sumSq / n);
                // Calibrated to match db_meter: 0 dB ≈ silence reference
                double db = rms > 0 ? 20.0 * Math.log10(rms / 32768.0) + 90.0 : 0.0;

                JSObject data = new JSObject();
                data.put("sensorType", "AUDIO");
                data.put("timestamp",  System.currentTimeMillis());
                data.put("db",         db);
                notifyListeners("audioLevel", data);

                try { Thread.sleep(100); } catch (InterruptedException ignored) {}
            }
        }, "audio-capture");
        captureThread.setDaemon(true);
        captureThread.start();

        call.resolve();
    }

    @PluginMethod
    public void stop(PluginCall call) {
        running = false;
        if (captureThread != null) {
            try { captureThread.join(500); } catch (InterruptedException ignored) {}
            captureThread = null;
        }
        if (audioRecord != null) {
            try { audioRecord.stop(); } catch (Exception ignored) {}
            audioRecord.release();
            audioRecord = null;
        }
        call.resolve();
    }
}
