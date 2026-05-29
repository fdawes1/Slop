# Leap CCTV — Android (Capacitor)

Self-contained Android APK for Leap CCTV review. No server required — the app connects directly to HiDrive WebDAV using a local proxy it runs on-device.

## How it works

On launch the app asks for your HiDrive username, password, and operator name. It starts a local WebDAV proxy (port 18765) that forwards requests to `webdav.hidrive.strato.com` with Basic Auth, working around the WebView's CORS and custom-header restrictions. The full review UI runs inside the Capacitor WebView.

Log data is written to a CSV file on the device after every event and loaded back on the next session — no data is lost when the app is closed.

## Get the APK

The APK is built automatically by GitHub Actions on every push to `hidrive_cctv_monitoring/android/`.

1. Go to the **Actions** tab → latest **Build Leap CCTV Android APK** run
2. Download the `leap-cctv-debug-N` artifact and unzip to get `app-debug.apk`

## Install on device

1. Enable *Install unknown apps* in Android settings
2. Transfer the APK and open it via the Files app
3. Enter your HiDrive credentials and operator name on first launch — these are remembered across restarts

## Usage

| Key / Button | Action |
|---|---|
| Good / Bad / Issue / Reject | Log an event at the current frame |
| Undo | Remove last entry |
| N / P | Next / previous video |
| Space | Play / pause |
| ← / → | ±5 s |
| Shift+← / → | ±30 s |
| **Share CSV** | Export log via Android share sheet |
| **New** | Clear log and start a fresh session (with confirmation) |

## Log persistence

Each operator's log is saved to:

```
/sdcard/Android/data/com.fdawes1.cctv/files/{operator}_cctv.csv
```

This file is written after every event and read back on the next session. It survives app restarts and device reboots. Accessible via any file manager app.

**CSV columns:** `PPX, Date, Time, Index, Status, Product, Operator`

Tapping **New** deletes the file and resets the in-app log. Use **Share CSV** first if you want to keep the data.

## Native plugins

| Plugin | Purpose |
|---|---|
| `HiDriveProxyPlugin` | Starts the on-device WebDAV proxy (OkHttp-based, supports PROPFIND) |
| `CsvLogPlugin` | Reads, writes, and clears the per-operator CSV file on device storage |

## Build locally

```bash
cd hidrive_cctv_monitoring/android
npm install
npx cap sync android
cd android && ./gradlew assembleDebug
# APK at android/app/build/outputs/apk/debug/app-debug.apk
```
