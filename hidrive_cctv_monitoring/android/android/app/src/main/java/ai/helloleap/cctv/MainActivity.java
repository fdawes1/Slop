package com.fdawes1.cctv;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(HiDriveProxyPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
