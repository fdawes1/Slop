package com.fdawes1.sensorlogger;

import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;
import android.os.BatteryManager;
import android.os.Handler;
import android.os.Looper;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "System")
public class SystemPlugin extends Plugin {

    private Handler handler;
    private Runnable pollTask;
    private volatile boolean polling = false;

    @Override
    public void load() {
        handler = new Handler(Looper.getMainLooper());
    }

    @PluginMethod
    public void startPolling(PluginCall call) {
        int intervalMs = call.getInt("intervalMs", 5000);
        polling = true;
        pollTask = new Runnable() {
            @Override
            public void run() {
                if (!polling) return;
                emitSystemData();
                handler.postDelayed(this, intervalMs);
            }
        };
        handler.post(pollTask);
        // Emit immediately
        emitSystemData();
        call.resolve();
    }

    @PluginMethod
    public void stopPolling(PluginCall call) {
        polling = false;
        if (pollTask != null) handler.removeCallbacks(pollTask);
        call.resolve();
    }

    private void emitSystemData() {
        long ts = System.currentTimeMillis();

        // Battery
        IntentFilter filter = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);
        Intent batt = getContext().registerReceiver(null, filter);
        if (batt != null) {
            int level  = batt.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
            int scale  = batt.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
            int status = batt.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
            float pct  = scale > 0 ? level * 100f / scale : -1;
            boolean charging = status == BatteryManager.BATTERY_STATUS_CHARGING
                            || status == BatteryManager.BATTERY_STATUS_FULL;

            JSObject bd = new JSObject();
            bd.put("sensorType",  "BATTERY");
            bd.put("timestamp",   ts);
            bd.put("batteryPct",  pct);
            bd.put("isCharging",  charging);
            notifyListeners("systemData", bd);
        }

        // Network
        ConnectivityManager cm = (ConnectivityManager)
            getContext().getSystemService(Context.CONNECTIVITY_SERVICE);
        String netType = "NONE";
        if (cm != null) {
            android.net.Network active = cm.getActiveNetwork();
            if (active != null) {
                NetworkCapabilities cap = cm.getNetworkCapabilities(active);
                if (cap != null) {
                    if (cap.hasTransport(NetworkCapabilities.TRANSPORT_WIFI))
                        netType = "WIFI";
                    else if (cap.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR))
                        netType = "CELLULAR";
                    else if (cap.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET))
                        netType = "ETHERNET";
                    else
                        netType = "OTHER";
                }
            }
        }

        JSObject nd = new JSObject();
        nd.put("sensorType",   "NETWORK");
        nd.put("timestamp",    ts);
        nd.put("networkType",  netType);
        notifyListeners("systemData", nd);
    }
}
