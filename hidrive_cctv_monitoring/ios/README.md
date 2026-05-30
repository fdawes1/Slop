# HiDrive CCTV — iOS (Capacitor)

Self-contained iOS app for HiDrive CCTV review. No server required — connects directly to HiDrive WebDAV via a local proxy running on-device, identical in behaviour to the Android app.

## Requirements

| Tool | Purpose |
|---|---|
| Mac with Xcode 15+ | Required for one-time project setup and signing |
| CocoaPods | iOS dependency management (`brew install cocoapods`) |
| Node 20+ | Capacitor CLI |
| Apple Developer account | Required to install on a real device or distribute |

## First-time setup (run once on a Mac)

```bash
cd hidrive_cctv_monitoring/ios
./setup.sh
```

This will:
1. Install npm dependencies (`@capacitor/ios`, `@capacitor/cli`)
2. Generate the Xcode project via `npx cap add ios`
3. Copy the Swift plugin files (`HiDriveProxyPlugin`, `CsvLogPlugin`) into the project
4. Register the plugins in the Xcode `.xcodeproj` file
5. Sync web assets from `../android/www` (single shared source)
6. Run `pod install` to install CocoaPods dependencies

After setup, commit the generated `ios/` directory so CI can use it:
```bash
git add hidrive_cctv_monitoring/ios/ios
git commit -m "Add generated iOS Xcode project"
```

## Build and run

**Open in Xcode:**
```bash
open hidrive_cctv_monitoring/ios/ios/App/App.xcworkspace
```
Select your device or simulator, press ▶.

**Run directly from terminal (connected device):**
```bash
cd hidrive_cctv_monitoring/ios
npx cap run ios
```

**Sync web assets after HTML changes:**
```bash
cd hidrive_cctv_monitoring/ios
npx cap sync ios
```

## Installing on a device

### Option A — TestFlight (recommended for team distribution)
1. In Xcode → Product → Archive
2. Upload to App Store Connect
3. Distribute via TestFlight

### Option B — Ad-hoc / direct install
1. Register the device UDID in your Apple Developer account
2. In Xcode, select your team under Signing & Capabilities
3. Product → Archive → Distribute → Ad-hoc
4. Install the `.ipa` via Apple Configurator 2 or Xcode Devices window

### Option C — Sideload with AltStore (no developer account)
1. Install [AltStore](https://altstore.io) on the device
2. Build an unsigned `.ipa` from the CI artifact
3. Open the `.ipa` in AltStore → Install

## CI builds (GitHub Actions)

The workflow `build-cctv-ios.yml` runs on `macos-latest` and triggers on pushes to:
- `hidrive_cctv_monitoring/ios/**`
- `hidrive_cctv_monitoring/android/www/**` (shared web assets)

It generates the Xcode project from scratch each run, builds a simulator-compatible binary, and archives an unsigned device build. Download artifacts from the **Actions** tab.

> **Note:** The unsigned archive cannot be installed directly on a device without re-signing. For real device testing, use Option A or B above.

## Usage

Identical to the Android app — see the [Android README](../android/README.md) for the full feature list. Key differences on iOS:
- Haptic feedback uses the system feedback engine (may not vibrate on all models)
- CSV files are saved to the **Files app** under `On My iPhone → HiDrive CCTV` (Documents directory)
- Sharing uses the native iOS share sheet (AirDrop, Mail, Files, etc.)

## Native plugins

| Plugin | File | Purpose |
|---|---|---|
| `HiDriveProxy` | `HiDriveProxyPlugin.swift` + `HiDriveProxyServer.swift` | Local TCP proxy forwarding WebDAV requests with Basic Auth |
| `CsvLog` | `CsvLogPlugin.swift` | Read/write/clear CSV in Documents; share via `UIActivityViewController` |

## Project structure

```
ios/
├── package.json              # npm: @capacitor/ios, @capacitor/cli
├── capacitor.config.json     # webDir points to ../android/www (shared)
├── setup.sh                  # One-time Mac setup script
├── ios-plugins/              # Swift source files (added to Xcode by setup.sh)
│   ├── HiDriveProxyServer.swift
│   ├── HiDriveProxyPlugin.swift
│   └── CsvLogPlugin.swift
├── scripts/
│   └── add_plugins_to_xcode.rb  # Adds plugin files to .xcodeproj
└── ios/                      # Generated Xcode project (commit after setup)
    └── App/
        ├── App.xcworkspace
        ├── Podfile
        └── App/
            ├── AppDelegate.swift
            ├── HiDriveProxyPlugin.swift  (copied by setup.sh)
            ├── HiDriveProxyServer.swift  (copied by setup.sh)
            └── CsvLogPlugin.swift        (copied by setup.sh)
```
