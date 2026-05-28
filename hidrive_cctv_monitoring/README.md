# Leap CCTV Review

Web app for reviewing CCTV footage from HiDrive-mounted PikPak units and logging robotic packing accuracy events.

## Run

```bash
pip install -r requirements.txt
python app.py
# http://<host-ip>:5000
```

Accessible to anyone on the network. Multiple reviewers can use it simultaneously — each gets their own persistent CSV log.

## Usage

1. Enter your name — a session is created and remembered via cookie (survives page refreshes)
2. Select a **unit** (PikPak003 etc.) and **date** from the sidebar
3. Click a video to start playback — the next video preloads in the background automatically
4. Press **G / B / I** (or click the buttons) to log Good / Bad / Issue events at the current frame
5. Update the **Product** field any time — the current value is captured with each log entry
6. **Download CSV** to export your session log

**Keyboard shortcuts:** `Space` play/pause · `←/→` ±5s · `Shift+←/→` ±30s

## Logs

Per-operator CSV files are stored in `logs/` and appended to across sessions and server restarts:

```
logs/
  Felix_Dawes.csv
  Sarah_Jones.csv
```

**CSV columns:** `PPX, Date, Time, Index, Status, Product, Operator`

PPX is inferred from the unit name (PikPak013 → 13).

## Video source

Reads from `/mnt/hidrive/public/PikPak*/YYYY/MM/DD/*.mp4`. Timestamps are extracted from filenames (`PikPakXXX_00_YYYYMMDDHHMMSS.mp4`).
