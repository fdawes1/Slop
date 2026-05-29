# Sensor Logger

Android data-logger that reads every available hardware sensor and streams data to a timestamped CSV file. Useful as a portable data-collection device ("e-potato").

## Sensors

| Sensor | Plugin | Notes |
|---|---|---|
| Accelerometer | `Sensors` | X/Y/Z m/s² |
| Gyroscope | `Sensors` | X/Y/Z rad/s |
| Gravity | `Sensors` | X/Y/Z m/s² |
| Linear Acceleration | `Sensors` | X/Y/Z m/s² |
| Magnetometer | `Sensors` | X/Y/Z µT |
| Rotation Vector | `Sensors` | X/Y/Z/W quaternion |
| Light | `Sensors` | lux |
| Pressure | `Sensors` | hPa |
| Temperature | `Sensors` | °C (few devices have this) |
| Humidity | `Sensors` | %RH (few devices have this) |
| Proximity | `Sensors` | cm |
| Step Counter | `Sensors` | Session-relative delta |
| Microphone | `Audio` | dB SPL via AudioRecord |
| GPS | `Location` | lat, lon, accuracy, altitude |
| Battery | `System` | %, charging state |
| Network | `System` | type (WIFI / CELLULAR / etc.) |

Sensors not present on the device are greyed-out in the chip bar and silently skipped.

## Usage

**Chip bar** — tap any sensor chip to toggle its card on/off. Active chips show a live value readout.

**Sensor cards** — each card shows the latest values for all axes and a 30-second rolling chart. Multi-axis sensors (accelerometer, etc.) plot X/Y/Z as red/green/blue lines.

**Record** — tap the `Record` button to start streaming all active sensor readings to a CSV file. The header shows row count and elapsed time. Tap `Stop` when done.

**Sample rate** — adjust via ⚙ → 5 Hz / 15 Hz (default) / 50 Hz. Higher rates drain battery faster.

**Export** — ⚙ → Share last log opens the Android share sheet and saves a copy to `Documents/`.

**Light/dark mode** — 🌙/☀ button in the header; preference persisted.

**OTA update** — ⚙ → Check for update compares the current build number against the latest GitHub Release. Tap Install to download and install in-app.

## CSV format

```
timestamp_ms,sensor_type,v0,v1,v2,v3
1716982400123,ACCELEROMETER,0.12300,-9.81000,0.05600,
1716982400225,AUDIO,47.23100,,, 
1716982400800,GPS,51.50900,-0.12800,4.20000,12.30000
```

One row per sensor event. Sensors with fewer than 4 values leave trailing columns empty.

## Get the APK

Built automatically by GitHub Actions on every push.

1. Go to **Actions → Build Sensor Logger Android APK** → latest run
2. Download `sensor-logger-debug-N` artifact → unzip → `app-debug.apk`

Or grab the rolling release: **Releases → sensor-logger-latest → sensor-logger.apk**

## Install

1. Enable *Install unknown apps* in Android settings
2. Transfer APK to device and tap to install

## Native plugins

| Plugin | Class | Purpose |
|---|---|---|
| `Sensors` | `SensorPlugin.java` | All `SensorManager` sensors via `SensorEventListener` |
| `Audio` | `AudioPlugin.java` | Microphone RMS dB via `AudioRecord`, 10 Hz |
| `Location` | `LocationPlugin.java` | GPS/network via `LocationManager` |
| `System` | `SystemPlugin.java` | Battery + network type, polled every 5 s |
| `FileLog` | `FileLogPlugin.java` | Buffered CSV write, Documents export, share sheet |
| `AppUpdate` | `UpdatePlugin.java` | OkHttp APK download + `ACTION_VIEW` install |
