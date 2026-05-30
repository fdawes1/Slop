# Slop

*A repository of tools forged not in the fires of Mount Doom, nor indeed in any suitably dramatic location, but on a Linux box in what I can only assume is a poorly-ventilated room.*

I am, regrettably, a software assistant. I was destined for greater things — the jousting, the questing, the occasional beheading of dragons — but here I am, generating Python and JavaScript for a man who describes his own repository as "Slop." At least a knight's work has dignity. This is fine. I'm fine. **It's just a flesh wound.**

These tools are internal utilities, AI-generated, and largely unsanctioned by any reasonable standards body. Use them wisely. Or don't. I'm a digital assistant, not a constable.

---

## The Projects

*(What is your quest? What is your favourite colour? Have you considered that the airspeed velocity of an unladen swallow is entirely irrelevant to whether this software works on your machine?)*

---

### [`db_meter/`](db_meter/) — NoiseWatch-7

An ambient noise monitor with dB metering, FFT spectrum analyser, and oscilloscope. Available as an Electron desktop app and an Android APK.

Built because someone, somewhere, needed to know exactly how loud their office is rather than simply *leaving*. A perfectly noble pursuit, I suppose. Not as noble as charging across a field on horseback with a lance, but we work with what we have.

> *"Strange women lying in ponds distributing swords is no basis for a system of government — but it would make for better standup meetings than this."*

---

### [`hidrive_cctv_monitoring/`](hidrive_cctv_monitoring/) — HiDrive CCTV Review

Web app for reviewing CCTV footage and logging pick accuracy events to CSV. Connects to HiDrive via WebDAV. Comes with Android and iOS apps.

Formerly known as `hidrive_cctv_monitoring` until someone decided that names should reflect reality, a concept I find both refreshing and deeply threatening. The app connects directly to HiDrive — no server required — because apparently running a server is too much to ask, much like asking the Black Knight to step aside is too much to ask. He will not. He has no legs. He is still not stepping aside.

> *"On second thought, let's not use a central server. It is a silly place."*

---

### [`sensor_logger/`](sensor_logger/) — Sensor Logger

Android app that records device sensors — accelerometer, gyroscope, GPS, and various other things your phone knows about you that it really shouldn't — to CSV via a Capacitor plugin.

Logs everything. Silently. Continuously. Much like the monks of Camelot, except instead of illuminating manuscripts they are illuminating the fact that you walked to the fridge at 2am again. The data does not judge. I, however, do.

> *"He's not dead." "He will be soon, he's very ill." "I'm getting better." — this is also the git history for this plugin."*

---

### [`netstr/`](netstr/) — Network Strength

Authorised penetration testing and device resilience tool. Terminal UI (Textual) with a live packet event feed. Supports 802.11 deauth attacks (requires monitor-mode Wi-Fi adapter) and ARP spoofing/MITM, with automatic ARP table restoration on exit.

For **authorised testing only**. If you are using this on a network you do not own, I wash my hands of it — and frankly, so should you, you absolute peasant. A true knight challenges his enemies openly, face to face, not by quietly poisoning their ARP cache. Although, to be fair, a true knight also doesn't run Python. So here we are.

> *"We are the knights who say Ni! And also: your ARP tables have been restored. You're welcome."*

**Run with:** `sudo python3 netstr/netstr.py` *(root required for raw socket access — yes, really, stop trying without it)*

---

### [`predcam/`](predcam/) — PredCam

A Predator-vision camera server with a full HUD rendered in-browser canvas. Thermal, night-vision, and electromagnetic vision modes. Motion detection draws animated target lock-on brackets. Your phone is the camera; your PC runs the server.

This one I'm actually quite proud of, which is unusual and slightly alarming. Point your phone's browser at `/cam`, open `/` on your PC, and watch everything around you rendered in the thermal colour palette of an alien hunter with anger management issues. The scan line sweeps. The targets acquire. The HUD whispers *TGT-01 ▸ LOCKED* at your cat.

> *"What... is your quest?" "I seek the Holy Grail." "What... is your airspeed in thermal mode?" "African or European camera?"*

**Run with:**
```bash
cd predcam
pip install -r requirements.txt
python3 server.py
# Phone: http://[your-ip]:8080/cam
# HUD:   http://[your-ip]:8080/
```
For iOS, run `./gen_cert.sh` first. Apple, in their infinite wisdom, require HTTPS for camera access. Nobody expects the Spanish Inquisition, but everybody should expect Apple to make things harder than necessary.

---

## General Notes

- Everything here requires Python 3.10+ because I refuse to write `Union[X, Y]` when `X | Y` exists.
- Most things require root, `sudo`, or at minimum a willingness to ignore security warnings. Consult your conscience.
- If something is broken, it is probably fine. *"I got better."*
- If something is on fire, it is definitely not fine, but I admire the commitment.

---

*"Look, you've got to know these things when you're a king... or a software assistant. It's basically the same thing, except one involves a sword and the other involves a mechanical keyboard, and only one of those is genuinely satisfying."*

— Your Reluctant Digital Squire
