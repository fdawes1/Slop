package ai.hidrive.cctv;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "HiDriveProxy")
public class HiDriveProxyPlugin extends Plugin {
    private HiDriveProxyServer server;

    @PluginMethod
    public void start(PluginCall call) {
        String username = call.getString("username", "");
        String password = call.getString("password", "");
        int port = call.getInt("port", 18765);

        if (server != null) server.stop();

        server = new HiDriveProxyServer(port, username, password);
        try {
            server.start();
            JSObject ret = new JSObject();
            ret.put("port", port);
            call.resolve(ret);
        } catch (Exception e) {
            call.reject("Failed to start proxy: " + e.getMessage());
        }
    }

    @PluginMethod
    public void stop(PluginCall call) {
        if (server != null) { server.stop(); server = null; }
        call.resolve();
    }

    @Override
    protected void handleOnDestroy() {
        if (server != null) server.stop();
    }
}
