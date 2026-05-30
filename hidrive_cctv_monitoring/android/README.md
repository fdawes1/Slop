# HiDrive CCTV — Android (Capacitor)

Self-contained Android APK for HiDrive CCTV review. No server required — the app connects directly to HiDrive WebDAV using a local proxy it runs on-device.

## How it works

On launch the app asks for your HiDrive username, password, and operator name. It starts a local WebDAV proxy (port 18765) that forwards requests to `webdav.hidrive.strato.com` with Basic Auth, working around the WebView's CORS and custom-header restrictions. The full review UI runs inside the Capacitor WebView.

Log data is written to a CSV file on the device after every event and loaded back on the next session — no data is lost when the app is closed.

## Get the APK

The APK is built automatically by GitHub Actions on every push to `hidrive_cctv_monitoring/android/`.

1. Go to the **Actions** tab → latest **Build HiDrive CCTV Android APK** run
2. Download the `hidrive-cctv-debug-N` artifact and unzip to get `app-debug.apk`

## Install on device

1. Enable *Install unknown apps* in Android settings
2. Transfer the APK and open it via the Files app
3. Enter your HiDrive credentials and operator name on first launch — these are remembered across restarts

## Usage

| Button | Action |
|---|---|
| Good / Bad / Issue / Reject | Log an event at the current frame |
| ↩ Undo | Remove last entry |
| ⏮ ⏭ | Previous / next video (auto-closes drawer) |
| ⏪ ⏩ | Seek ±5 s |
| ▶ / ⏸ | Play / pause |
| Scrubber | Drag to seek; shows `current / total` time |
| Speed buttons | 0.75× / 1× / 1.5× / 2× |
| **CSV ▾** | Opens dropdown: **Share CSV** or **New session** |
| 🌙 / ☀ | Toggle dark / light mode |
| ☰ | Open footage drawer (unit, date, video list) |

## Log persistence

Each operator's log is saved to device internal storage after every event and reloaded on next launch. Tapping **CSV ▾ → Share CSV**:
- Writes the file to the public **Documents** folder (`Documents/{operator}_cctv.csv`) — a toast confirms the path
- Opens the Android share sheet so you can email / upload it

Tapping **New session** clears the in-app log and the saved file (with confirmation).

**CSV columns:** `PPX, Date, Time, Index, Status, Product, Operator`

## Session badges

Each action button shows a running count of how many events of that type you've logged this session. Resets on New Session.

## Native plugins

| Plugin | Purpose |
|---|---|
| `HiDriveProxyPlugin` | Starts the on-device WebDAV proxy (OkHttp-based, supports PROPFIND) |
| `CsvLogPlugin` | Read/write/clear CSV in internal storage; save to Documents; native share intent via FileProvider |

## Build locally

```bash
cd hidrive_cctv_monitoring/android
npm install
npx cap sync android
cd android && ./gradlew assembleDebug
# APK at android/app/build/outputs/apk/debug/app-debug.apk
```
