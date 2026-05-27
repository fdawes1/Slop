# Slop
generally ai generated

---

## NoiseWatch-7 — Acoustic Monitor

Sci-fi HUD for real-time ambient noise monitoring. Features dB metering, FFT spectrum analyser, oscilloscope, spectrogram waterfall, and incident logging.

### Web / Desktop (Electron)

Open in a browser:
```bash
cd db_meter
python3 -m http.server 8742
# visit http://localhost:8742/noisewatch_scifi.html
```

Run as a standalone desktop app (no browser needed):
```bash
cd db_meter
npm install   # first time only
npm start
```

### Android APK

The APK is built automatically by GitHub Actions on every push.

**Download:**
1. Go to **Actions** tab on this repo
2. Click the latest **Build Android APK** run
3. Scroll to **Artifacts** and download `noisewatch7-debug-N`
4. Unzip to get `app-debug.apk`

**Install on Android:**
1. Enable *Install unknown apps* in Android settings (Settings → Apps → Special app access)
2. Transfer the APK to your device (cable, email, Google Drive, etc.)
3. Open the APK via the Files app and tap Install
4. On first launch, grant microphone permission when prompted
