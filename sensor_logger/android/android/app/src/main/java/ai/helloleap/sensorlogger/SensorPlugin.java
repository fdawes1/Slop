package com.fdawes1.sensorlogger;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.util.LinkedHashMap;
import java.util.Map;

@CapacitorPlugin(name = "Sensors")
public class SensorPlugin extends Plugin implements SensorEventListener {

    private SensorManager sensorManager;
    private int rateUs = SensorManager.SENSOR_DELAY_UI;

    private static final Map<String, Integer> SENSOR_TYPES = new LinkedHashMap<>();
    static {
        SENSOR_TYPES.put("ACCELEROMETER",       Sensor.TYPE_ACCELEROMETER);
        SENSOR_TYPES.put("GYROSCOPE",            Sensor.TYPE_GYROSCOPE);
        SENSOR_TYPES.put("GRAVITY",              Sensor.TYPE_GRAVITY);
        SENSOR_TYPES.put("LINEAR_ACCELERATION",  Sensor.TYPE_LINEAR_ACCELERATION);
        SENSOR_TYPES.put("MAGNETIC_FIELD",       Sensor.TYPE_MAGNETIC_FIELD);
        SENSOR_TYPES.put("ROTATION_VECTOR",      Sensor.TYPE_ROTATION_VECTOR);
        SENSOR_TYPES.put("LIGHT",                Sensor.TYPE_LIGHT);
        SENSOR_TYPES.put("PRESSURE",             Sensor.TYPE_PRESSURE);
        SENSOR_TYPES.put("AMBIENT_TEMPERATURE",  Sensor.TYPE_AMBIENT_TEMPERATURE);
        SENSOR_TYPES.put("RELATIVE_HUMIDITY",    Sensor.TYPE_RELATIVE_HUMIDITY);
        SENSOR_TYPES.put("PROXIMITY",            Sensor.TYPE_PROXIMITY);
        SENSOR_TYPES.put("STEP_COUNTER",         Sensor.TYPE_STEP_COUNTER);
    }

    @Override
    public void load() {
        sensorManager = (SensorManager) getContext().getSystemService(Context.SENSOR_SERVICE);
    }

    @PluginMethod
    public void getAvailable(PluginCall call) {
        JSArray list = new JSArray();
        for (Map.Entry<String, Integer> e : SENSOR_TYPES.entrySet()) {
            if (sensorManager.getDefaultSensor(e.getValue()) != null) {
                list.put(e.getKey());
            }
        }
        JSObject ret = new JSObject();
        ret.put("sensors", list);
        call.resolve(ret);
    }

    @PluginMethod
    public void startAll(PluginCall call) {
        rateUs = call.getInt("rateUs", SensorManager.SENSOR_DELAY_UI);
        for (Map.Entry<String, Integer> e : SENSOR_TYPES.entrySet()) {
            Sensor s = sensorManager.getDefaultSensor(e.getValue());
            if (s != null) sensorManager.registerListener(this, s, rateUs);
        }
        call.resolve();
    }

    @PluginMethod
    public void stopAll(PluginCall call) {
        sensorManager.unregisterListener(this);
        call.resolve();
    }

    @PluginMethod
    public void setRate(PluginCall call) {
        rateUs = call.getInt("rateUs", SensorManager.SENSOR_DELAY_UI);
        // Re-register all active sensors at new rate
        sensorManager.unregisterListener(this);
        for (Map.Entry<String, Integer> e : SENSOR_TYPES.entrySet()) {
            Sensor s = sensorManager.getDefaultSensor(e.getValue());
            if (s != null) sensorManager.registerListener(this, s, rateUs);
        }
        call.resolve();
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        String name = nameForType(event.sensor.getType());
        if (name == null) return;

        JSArray vals = new JSArray();
        // Clamp to 4 values max (rotation vector can have 5; we drop accuracy estimate)
        int len = Math.min(event.values.length, 4);
        for (int i = 0; i < len; i++) vals.put(event.values[i]);

        JSObject data = new JSObject();
        data.put("sensorType", name);
        data.put("timestamp",  event.timestamp / 1_000_000L); // ns → ms
        data.put("values",     vals);
        notifyListeners("sensorData", data);
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {}

    private String nameForType(int type) {
        for (Map.Entry<String, Integer> e : SENSOR_TYPES.entrySet()) {
            if (e.getValue() == type) return e.getKey();
        }
        return null;
    }
}
