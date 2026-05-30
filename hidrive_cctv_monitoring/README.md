# HiDrive CCTV Review

 Web app for reviewing CCTV footage and logging events. Supports both a locally-mounted HiDrive share and HiDrive Online (WebDAV).

## Run

```bash
pip install -r requirements.txt
python app.py
# http://<host-ip>:5000
```

Accessible to anyone on the network. Multiple reviewers can use it simultaneously — each gets their own persistent CSV log.

## Usage

1. Enter your name and choose **Local mount** or **HiDrive Online**
   - HiDrive Online: enter your HiDrive username and password — credentials are validated immediately and never written to disk
2. Select a **unit** and **date** from the sidebar
3. Click a video to start playback — the next video preloads automatically
4. Use the action buttons (or keyboard shortcuts) to log events at the current frame:

| Key / Button | Action |
|---|---|
| `G` / Good | Log Good |
| `B` / Bad | Log Bad |
| `I` / Issue | Log Issue |
| `R` / Reject | Log Reject |
| `U` / Undo | Remove last entry |
| `N` / `P` or ⏭ ⏮ | Next / previous video |
| `Space` or ▶⏸ | Play / pause |
| `← / →` or ⏪ ⏩ | ±5 s |
| `Shift+← / →` | ±30 s |

5. Use the **seek scrubber** below the video to jump to any point — shows current position and clip duration
6. Per-session **event counts** appear as badges on each action button
7. Adjust **playback speed** (0.75× – 2×) in the controls bar
8. Update the **Product** field any time — captured with each log entry
9. **Download CSV** to export your session log
10. Toggle **light / dark mode** with the ☀/☾ button in the header

## Logs

Per-operator CSV files stored in `logs/`, appended across sessions and server restarts:

```
logs/
  Felix.csv
  Sarah.csv
```

**CSV columns:** `PPX, Date, Time, Index, Status, Product, Operator`

PPX is inferred from the unit name


## Android

A self-contained Android APK is available — see [`android/`](android/README.md). It connects directly to HiDrive WebDAV (no server needed), persists the CSV log to device storage across sessions, and exports via the Android share sheet.

## iOS

A self-contained iOS app is available — see [`ios/`](ios/README.md). Identical feature set to Android. Requires a one-time setup on a Mac with Xcode; web assets are shared with the Android app so changes to `android/www/index.html` apply to both.
