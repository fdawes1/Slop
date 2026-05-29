# Leap CCTV Review

Web app for reviewing CCTV footage from PikPak units and logging robotic packing accuracy events. Supports both a locally-mounted HiDrive share and HiDrive Online (WebDAV).

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
2. Select a **unit** (PikPak003 etc.) and **date** from the sidebar
3. Click a video to start playback — the next video preloads automatically
4. Use the action buttons (or keyboard shortcuts) to log events at the current frame:

| Key | Action |
|-----|--------|
| `G` | Good |
| `B` | Bad |
| `I` | Issue |
| `R` | Reject |
| `U` | Undo last event |
| `N` / `P` | Next / previous video |
| `Space` | Play / pause |
| `← / →` | ±5 s |
| `Shift+← / →` | ±30 s |

5. Adjust **playback speed** (0.75× – 2×) in the controls bar
6. Update the **Product** field any time — captured with each log entry
7. **Download CSV** to export your session log

## Logs

Per-operator CSV files stored in `logs/`, appended across sessions and server restarts:

```
logs/
  Felix.csv
  Sarah.csv
```

**CSV columns:** `PPX, Date, Time, Index, Status, Product, Operator`

PPX is inferred from the unit name (PikPak013 → 13).

## Video source

Reads from `/mnt/hidrive/public/PikPak*/YYYY/MM/DD/*.mp4` (local) or the same structure via HiDrive WebDAV (`webdav.hidrive.strato.com`). Timestamps are extracted from filenames (`PikPakXXX_00_YYYYMMDDHHMMSS.mp4`).

## Android

A self-contained Android APK is available — see [`android/`](android/README.md). It connects directly to HiDrive WebDAV (no server needed), persists the CSV log to device storage across sessions, and exports via the Android share sheet.
