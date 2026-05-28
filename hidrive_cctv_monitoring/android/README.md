# Leap CCTV — Android (Capacitor)

Android APK for Leap CCTV Review, packaged via Capacitor. The app is a WebView launcher that connects to a Leap CCTV server running on the local network or in the cloud.

## How it works

On first launch the app asks for the server URL (e.g. `http://192.168.1.x:5000`). It stores this in local storage and navigates to it — the full CCTV review UI then runs inside the WebView exactly as it does in a desktop browser. The URL is remembered across restarts.

## Get the APK

The APK is built automatically by GitHub Actions on every push to `hidrive_cctv_monitoring/android/`.

1. Go to the **Actions** tab → latest **Build Leap CCTV Android APK** run
2. Download the `leap-cctv-debug-N` artifact and unzip to get `app-debug.apk`

## Install on device

1. Enable *Install unknown apps* in Android settings
2. Transfer the APK to your device and open it via the Files app
3. On first launch, enter the server URL

## Run the server

The server must be reachable from the device. Start it on any machine on the same network:

```bash
cd hidrive_cctv_monitoring
pip install -r requirements.txt
python app.py          # listens on 0.0.0.0:5000
```

Then enter `http://<machine-ip>:5000` in the Android app.

## Build locally

```bash
npm install
npx cap sync android
cd android && ./gradlew assembleDebug
# APK at android/app/build/outputs/apk/debug/app-debug.apk
```
