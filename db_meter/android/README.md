# NoiseWatch-7 — Android (Capacitor)

Android APK build of NoiseWatch-7, packaged via Capacitor.

## Build

The APK is built automatically by GitHub Actions on every push to `db_meter/android/`.

**Download the latest build:**
1. Go to the **Actions** tab → latest **Build Android APK** run
2. Download the `noisewatch7-debug-N` artifact and unzip to get `app-debug.apk`

## Install on device

1. Enable *Install unknown apps* in Android settings
2. Transfer the APK to your device and open it via the Files app

## Build locally

```bash
npm install
npx cap sync android
cd android && ./gradlew assembleDebug
# APK at android/app/build/outputs/apk/debug/app-debug.apk
```
