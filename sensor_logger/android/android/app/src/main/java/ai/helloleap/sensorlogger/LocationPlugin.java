package com.fdawes1.sensorlogger;

import android.Manifest;
import android.content.Context;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

@CapacitorPlugin(
    name = "Location",
    permissions = {
        @Permission(strings = {
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        }, alias = "location")
    }
)
public class LocationPlugin extends Plugin implements LocationListener {

    private LocationManager locationManager;
    private boolean active = false;

    @Override
    public void load() {
        locationManager = (LocationManager) getContext()
            .getSystemService(Context.LOCATION_SERVICE);
    }

    @PluginMethod
    public void start(PluginCall call) {
        if (!hasRequiredPermissions()) {
            requestAllPermissions(call, "locationPermCallback");
            return;
        }
        doStart(call);
    }

    @PermissionCallback
    private void locationPermCallback(PluginCall call) {
        if (hasRequiredPermissions()) doStart(call);
        else call.reject("Location permission denied");
    }

    private void doStart(PluginCall call) {
        long minTimeMs = call.getLong("minTimeMs", 1000L);
        float minDistM = call.getDouble("minDistM", 0.0).floatValue();
        try {
            if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                locationManager.requestLocationUpdates(
                    LocationManager.GPS_PROVIDER, minTimeMs, minDistM, this);
            }
            if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                locationManager.requestLocationUpdates(
                    LocationManager.NETWORK_PROVIDER, minTimeMs, minDistM, this);
            }
            active = true;
            call.resolve();
        } catch (SecurityException e) {
            call.reject(e.getMessage());
        }
    }

    @PluginMethod
    public void stop(PluginCall call) {
        locationManager.removeUpdates(this);
        active = false;
        call.resolve();
    }

    @Override
    public void onLocationChanged(Location loc) {
        JSObject data = new JSObject();
        data.put("sensorType", "GPS");
        data.put("timestamp",  loc.getTime());
        data.put("lat",        loc.getLatitude());
        data.put("lon",        loc.getLongitude());
        data.put("accuracy",   loc.getAccuracy());
        data.put("altitude",   loc.getAltitude());
        data.put("speed",      loc.getSpeed());
        data.put("bearing",    loc.getBearing());
        notifyListeners("locationUpdate", data);
    }

    @Override public void onStatusChanged(String p, int s, Bundle e) {}
    @Override public void onProviderEnabled(String p) {}
    @Override public void onProviderDisabled(String p) {}
}
