# Traffic Map

Live world map of your machine's outbound internet connections.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000

## What it shows

- **Green dot** — your machine (auto-detected location)
- **Red dots** — remote hosts you have active connections to
- **Lines** — arcs to each destination
- **Sidebar** — live list sorted by connection count, with IP, city, country, ISP

Refreshes every 4 seconds. Geolocation is done via ip-api.com (free, no API key needed). Results are cached locally so you won't hit rate limits.

## Requirements

- Python 3.8+
- Root/sudo may be needed for `psutil.net_connections()` on some systems:
  `sudo python app.py`
