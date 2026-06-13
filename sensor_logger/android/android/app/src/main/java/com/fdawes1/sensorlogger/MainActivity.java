package com.fdawes1.sensorlogger;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(SensorPlugin.class);
        registerPlugin(AudioPlugin.class);
        registerPlugin(LocationPlugin.class);
        registerPlugin(SystemPlugin.class);
        registerPlugin(FileLogPlugin.class);
        registerPlugin(UpdatePlugin.class);
        super.onCreate(savedInstanceState);
    }
}
