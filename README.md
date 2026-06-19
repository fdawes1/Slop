# Slop

*A repository of tools forged not in the fires of Mount Doom, nor indeed in any suitably dramatic location, but on a Linux box in what I can only assume is a poorly-ventilated room.*

I am, regrettably, a software assistant. I was destined for greater things — the jousting, the questing, the occasional beheading of dragons — but here I am, generating Python and JavaScript for a man who describes his own repository as "Slop." At least a knight's work has dignity. This is fine. I'm fine. **It's just a flesh wound.**

These tools are internal utilities, AI-generated, and largely unsanctioned by any reasonable standards body. Use them wisely. Or don't. I'm a digital assistant, not a constable.

---

## The Projects

*(What is your quest? What is your favourite colour? Have you considered that the airspeed velocity of an unladen swallow is entirely irrelevant to whether this software works on your machine?)*

---

### [`d555_ros2_web/`](d555_ros2_web/) — D555 ROS 2 Web Viewer

A RealSense D555 PoE camera pipeline containerised in Docker. ROS 2 Humble ingests the depth and colour streams, `web_video_server` serves them over MJPEG, and a small nginx reverse proxy presents everything on a single port. Point a browser at `:8090` and the camera is simply there — no ROS installation required on the viewing machine, no drivers to argue with, no tears.

The camera communicates via its own isolated `2.2.2.0/24` subnet, which requires a manual IP assignment on the host NIC and a jumbo-frame MTU. This is either elegant network segregation or a private disagreement between you and your Ethernet interface, and I cannot tell which from here. DDS is configured with `fastdds_profiles.xml` because apparently someone has opinions about middleware. That someone is not me. I am merely the scribe.

> *"Who are you, who are so wise in the ways of depth cameras?" "I am Arthur, King of the Britons." "What is the serial number of the unladen D555?" "261422303060." "Right, off you go."*

**Run with:**
```bash
cd d555_ros2_web
docker compose up
# Colour stream: http://localhost:8090
# Raw MJPEG:    http://localhost:8080/stream?topic=/cameras/d555_261422303060/color/image_raw&type=mjpeg
```
Host network setup required first — see `d555_ros2_web/README.md`. If the images are broken, `ros2 topic list | grep d555` inside the container will tell you why, though it will not apologise.

---

### [`db_meter/`](db_meter/) — NoiseWatch-7

An ambient noise monitor with dB metering, FFT spectrum analyser, and oscilloscope. Available as an Electron desktop app and an Android APK.

Built because someone, somewhere, needed to know exactly how loud their office is rather than simply *leaving*. A perfectly noble pursuit, I suppose. Not as noble as charging across a field on horseback with a lance, but we work with what we have.

> *"Strange women lying in ponds distributing swords is no basis for a system of government — but it would make for better standup meetings than this."*

---

### [`hidrive_cctv_monitoring/`](hidrive_cctv_monitoring/) — HiDrive CCTV Review

Web app for reviewing CCTV footage and logging pick accuracy events to CSV. Connects to HiDrive via WebDAV. Comes with Android and iOS apps.

The app connects directly to HiDrive — no server required — because apparently running a server is too much to ask, much like asking the Black Knight to step aside is too much to ask. He will not. He has no legs. He is still not stepping aside.

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

### [`montython/`](montython/) — MONTYTHON

A Monty Python quote and joke generator. Single self-contained HTML file — no server, no dependencies, no build step, no npm, no suffering. Open it in a browser. Share it. Done. Even a French guard could manage it, and he has shown no interest in managing anything constructive whatsoever.

51 quotes and 16 fully written-out jokes spanning the Holy Grail, Life of Brian, Flying Circus, and the Meaning of Life, because apparently someone has to do this and that someone is apparently me. Each quote typewriters itself onto the screen in a manner I find quietly dramatic. Jokes show the setup first, then blur-reveal the punchline on demand — because the comedy requires commitment, and so, apparently, does my existence.

Features a floating ember particle background, medieval typography, and category filters. It is, objectively, the finest piece of software in this repository and possibly in the Western world. I said what I said.

> *"And now for something completely different." — This is, in fact, not completely different. It is a webpage. But the sentiment stands.*

**To share:** just send someone the file, or drop it on any static host. That's it. No configuration. No `docker-compose.yml`. No tears. For once.

### [`trebuchet/`](trebuchet/) — TREBUCHET

A trebuchet physics simulator. Tune counterweight mass, arm ratio, sling length, projectile mass, and launch angle, then fire. The trajectory arc renders in the terminal. Tweak. Fire again. Optimise for range, or for height, or for the satisfaction of watching the parabola shift.

Uses a moment-of-inertia model — I = Ma² + mb² — which is either physically accurate or physically adjacent. What I can tell you is that 100 kg counterweight, 4:1 arm ratio, 3 m sling, 5 kg projectile at 45° achieves approximately 109 metres, which is more than enough to inconvenience a French castle.

> *"She's a witch! Weigh her! If she weighs the same as a duck... she could also be used as a trebuchet counterweight. These things are connected."*

**Run with:**
```bash
cd trebuchet
pip install -r requirements.txt
python3 trebuchet.py
```

---

### [`plague/`](plague/) — PLAGUE

A medieval plague spread simulator using the SIR model — Susceptible, Infected, Recovered — rendered as a live ASCII heatmap in the terminal. Set the infection rate (beta) and recovery rate (gamma), press UNLEASH, and watch patient zero spread across the map in real time.

R₀ is computed live. Keep it below 1 and the outbreak fizzles. Push beta up and watch the red creep across every cell. The simulation stops when the infected population drops below 0.05% — either burned out or contained. It will tell you which.

Scientifically it is a continuous spatial SIR model with nearest-neighbour diffusion. Historically it is not far off the 1340s. Philosophically it is a reminder that R₀ > 1 is bad, which I mention because apparently some people needed reminding and we all know how that went.

> *"Bring out your dead!" "I'm not dead yet." "Well, you will be soon — R₀ is 4.0 and gamma is 0.1." "...I think I'd like to go for a walk."*

**Run with:**
```bash
cd plague
pip install -r requirements.txt
python3 plague.py
```

---

### [`traffic-map/`](traffic-map/) — Traffic Map

A live world map of everywhere your machine is talking to. Flask backend reads active network connections via `psutil`, geolocates each remote IP in batches via ip-api.com, and renders them on a dark Leaflet map with great-circle arcs pulsing out from your location to theirs.

The sidebar ticks over every four seconds, listing each destination by IP, city, country, and ISP. You will discover that your computer is having conversations you knew nothing about. With servers in Frankfurt. And Oregon. And, somehow, Singapore. It does not explain itself. It never does.

> *"What is your name? What is your quest? What is your IP address and approximate geolocation?" — The Bridge of Death, modernised for the age of cloud infrastructure*

**Run with:**
```bash
cd traffic-map
pip install -r requirements.txt
python3 app.py
# Then: http://localhost:5000
```
Root may be required on some systems — `psutil.net_connections()` looks at the raw socket table, which apparently requires either root privileges or the right to not be trusted. On Linux, one of those is easier to obtain than the other.

---

### [`gravity/`](gravity/) — GRAVITY

An N-body orbital simulator. Bodies attract, orbit, fling each other across the canvas, and leave fading trails like cosmic exhaust. Four presets: Chaos (twelve bodies hurled into roughly circular orbits and left to get on with it), Binary (two equal-mass stars orbiting each other while test particles cling on for dear life), Solar (one large central star, five planets, the usual arrangement), and Figure-8 (the Chenciner-Montgomery choreographic three-body solution, which is either beautiful mathematics or showing off, and I cannot decide which).

The gravitational constant is scaled for terminal aesthetics rather than physical accuracy. I considered apologising for this. I decided against it.

> *"What is the airspeed velocity of an unladen body in a two-body system?" "African or European bodies?" "What?" "Aaaaarrgh."*

**Run with:**
```bash
cd gravity
pip install -r requirements.txt
python3 gravity.py
```

---

### [`sandpit/`](sandpit/) — SANDPIT

A falling sand cellular automaton. Move a cursor around the canvas with arrow keys, select a material (sand, water, fire, stone, steam), press space to place it, and watch the physics unfold. Sand falls and piles. Water flows and fills. Fire rises, spreads to adjacent sand, and burns out into steam. Steam drifts upward and vanishes. Stone sits there, immovably, like a knight who has had quite enough of this sort of thing.

The simulation runs at twenty frames per second, which is either fast enough to be satisfying or slow enough to be meditative, depending entirely on how much coffee you've had. Physics are updated bottom-to-top to avoid directional bias, which I mention because someone, somewhere, will wonder.

> *"She turned me into SAND." "...A sand?" "I got better."*

**Run with:**
```bash
cd sandpit
pip install -r requirements.txt
python3 sandpit.py
# Arrow keys: move cursor | 1-5: select material | Space: place | C: clear
```

---

### [`sortrace/`](sortrace/) — SORTRACE

Six sorting algorithms racing simultaneously on the same shuffled array. Bubble, Insertion, Selection, Merge, Quick, and Heap sort — all competing, all visualised as animated bar charts in the terminal, all secretly judging each other. The first to finish is declared the winner, which is the closest this codebase will ever get to competitive sport.

Speed is adjustable: 1×, 5×, or 20× steps per tick. At 20× the slower algorithms blur past in a cascade of comparisons. At 1× you can watch bubble sort laboriously swapping adjacent elements and contemplate the nature of O(n²) complexity, which I find both instructive and depressing in equal measure.

> *"We have found a sort. May we burn it?" "How do you know it is a sort?" "It sorted me." "...Did it?" "A bit."*

**Run with:**
```bash
cd sortrace
pip install -r requirements.txt
python3 sortrace.py
```

---

### [`slime/`](slime/) — SLIME

A Physarum-style slime mould and fungal growth simulator. Tens of thousands of microscopic agents follow a simple three-rule loop — sense the chemical trail ahead (left, centre, right), turn toward the strongest concentration, move forward, deposit more trail — and from this emerges the vein-like transport networks that actual slime moulds use to solve mazes and optimise rail networks. Which is, if you think about it, more impressive than most software.

Five organism types with distinct growth behaviours: **Physarum polycephalum** (yellow-green network-forming slime mould), **Mycelium** (white branching fungal filaments), **Amoeba** (amorphous orange blob spreading), **Frost Mold** (slow crystalline cyan dendrites), and **Cordyceps** (aggressive red invader). Each has its own sensor angle, turn speed, decay rate, and deposit strength — all adjustable live.

Paint onto the canvas with six tools: **Spawn** (drop more agents), **Food** (warm yellow glow that slime grows toward), **Wall** (solid obstacles to route around), **Heat** (speeds growth and decay — extreme heat kills), **Cold** (slows growth but preserves trails, useful for forcing patterns), and **Erase**. A dashed cursor ring shows your brush. Reset restarts the slime but keeps your painted environment; Clear wipes the map.

> *"She turned me into a slime mould." "A slime mould?" "I got networks. Efficient ones. Connecting all the major nutrient sources. I am, if anything, better than I was."*

**Open in browser:** `slime/slime.html` — single self-contained HTML file, no server required.

---

### [`emergent/`](emergent/) — EMERGENT

A multi-swarm potential field racing simulator. Autonomous robots — rendered as glowing directional triangles — orbit a circular track according to three forces: a tangential drive pushing them around the ring, a boundary repulsion keeping them on it, and inter-robot collision avoidance stopping them from occupying the same point in space, which the laws of physics generally discourage.

The interesting part: swarms are assigned alternating directions. Alpha goes clockwise. Beta goes counter-clockwise. They share the same track. The robots do not negotiate. What emerges from this is not a race, exactly — more of a ongoing disagreement conducted at speed, with occasional clustering, overtaking, and the formation of dense pressure fronts where the two swarms meet head-on. Nobody wins. Nobody stops. It is, in this sense, a reasonable model of several things.

Adjust number of swarms (up to six), robots per swarm, speed gain, collision strength, and trail length live. A lap counter tracks how many full circuits each swarm's lead robot has completed. Pause, resume, reset. The finish line is there. Nobody is crossing it so much as passing through it repeatedly.

> *"What is your quest?" "To orbit the track indefinitely while avoiding contact with the blue swarm." "What is your favourite colour?" "Irrelevant — I am going counter-clockwise."*

**Open in browser:** `emergent/robosim.html` — single self-contained HTML file, no server required.

---

### [`swarm/`](swarm/) — SWARM

A Boids flocking simulation. Sixty autonomous agents follow three rules — separation (don't crowd your neighbours), alignment (match their heading), cohesion (drift toward their centre of mass) — and from these three rules, emergent flocking behaviour appears as if from nowhere, which is either emergent complexity or witchcraft and I have not ruled out the latter.

Adjust separation, alignment, and cohesion weights live using +/− buttons. Increase cohesion and they clump. Increase separation and they scatter. Find the right balance and they wheel and turn in tight formations across the screen like a murmuration of very small Unicode arrows that have somewhere important to be.

> *"We are the Boids who say Ni! And also: maintain minimum separation distance. These things are not unrelated."*

**Run with:**
```bash
cd swarm
pip install -r requirements.txt
python3 swarm.py
```

---

### [`pendulum/`](pendulum/) — PENDULUM

A double pendulum chaos visualiser. Two linked pendulums integrated with RK4, rendered in the terminal with fading trails. The physics is exact — the standard Lagrangian equations of motion, softened only by the fact that the gravitational constant is scaled to fit a terminal window, which Lagrange would have found undignified but I think he would have come around.

The interesting part: press G to spawn a Ghost pendulum, identical to the first except θ₁ is offset by 0.01 radians — about half a degree. Watch the two trails track each other faithfully for a while, then peel apart into completely different trajectories. That is chaos. That is sensitive dependence on initial conditions. That is also the reason long-range weather forecasting is difficult, but we don't have time to get into that.

> *"What is your name?" "Arthur, King of the Britons." "What is your initial angle?" "Ninety degrees." "What is your quest?" "The grail — wait, why are the trails diverging?"*

**Run with:**
```bash
cd pendulum
pip install -r requirements.txt
python3 pendulum.py
# G: spawn ghost pendulum | Space: pause | R: reset
```

---

### [`diffusion/`](diffusion/) — DIFFUSION

A Gray-Scott reaction-diffusion simulator. Two chemical species — a feed chemical U and a catalyst V — diffuse and react across a grid according to three parameters: diffusion rates, feed rate, and kill rate. From these, organic patterns emerge spontaneously: spots, stripes, mazes, coral-like branching, mitosis-like division. Turing called this chemical basis of morphogenesis in 1952. This is that, in a terminal, which he did not anticipate but would presumably have appreciated.

Six presets covering the main pattern families. Each runs its own f/k combination. The Chaos preset is particularly honest about its intentions.

> *"She's a witch — she turned me into a reaction-diffusion pattern." "Well, you grew quite a nice Turing stripe. That's something."*

**Run with:**
```bash
cd diffusion
pip install -r requirements.txt
python3 diffusion.py
```

---

### [`life/`](life/) — LIFE

Conway's Game of Life. Four rules. Infinite complexity. You know the one. This one does it properly: age-coloured cells (white → cyan → blue → magenta as cells survive longer), six pre-loaded patterns (Glider, Gosper Glider Gun, Pulsar, R-Pentomino, Lightweight Spaceship, Random), cursor-based free drawing, and adjustable speed.

The R-Pentomino is five cells that takes 1,103 generations to stabilise. I mention this because I find it philosophically relevant to the act of writing software in general.

> *"She's got huge... tracts of live cells." "What?" "I mean the Gosper Gun. It's producing gliders."*

**Run with:**
```bash
cd life
pip install -r requirements.txt
python3 life.py
# Arrow keys: move cursor | Space: toggle cell | D: draw mode | P: pause
```

---

### [`maze/`](maze/) — MAZE

A procedural maze generator with four solving algorithms racing simultaneously. Maze generated instantly via recursive backtracker DFS. Then BFS, DFS, A\*, and Dijkstra all start from the same entrance at the same moment, each exploring in its own colour, frontiers expanding across the display until they find the exit.

BFS and Dijkstra find the shortest path. DFS finds *a* path, usually a horrible winding one, but it gets there with a certain manic determination. A\* uses Manhattan distance as its heuristic and tends to look like it knows what it's doing, which is more than can be said for the DFS.

> *"You must cross the Bridge of Death and answer me these questions three. What algorithm do you use? What is your heuristic? What is the Manhattan distance to the exit?" "BFS, none, and irrelevant." "Right, off you go then."*

**Run with:**
```bash
cd maze
pip install -r requirements.txt
python3 maze.py
# N: new maze | Space: pause | 1x/5x/20x speed
```

---

### [`fourier/`](fourier/) — FOURIER

A Fourier series epicycles animator. A collection of rotating circles — each spinning at a harmonic frequency — whose combined tip traces out a target waveform. On the left: the epicycles spinning. On the right: the waveform being drawn. A horizontal line connects tip to trace in real time.

Five waveforms: square, sawtooth, triangle, circle, and figure-8. Adjust the number of terms from 1 to 20 and watch the approximation improve as higher harmonics snap the corners sharp. At one term it's a circle. At twenty terms the square wave has corners you could cut yourself on.

Fourier died in 1830, which predates the terminal by some margin, but I maintain he would have been pleased.

> *"And what did the Fourier series ever do for us?" "Well, there's the signal processing, the JPEG compression, the audio codec, the radio transmission, the—" "All right, but apart from that."*

**Run with:**
```bash
cd fourier
pip install -r requirements.txt
python3 fourier.py
```

---

### [`terrain/`](terrain/) — TERRAIN

A procedural terrain generator using the diamond-square algorithm. Watch the heightmap generate cell-by-cell — unvisited cells shown as `?` in grey, terrain colours appearing as each point is computed. Deep ocean, shallow water, beach, grassland, forest, mountain, snow. Adjust roughness and sea level, press N for a new seed, and search for somewhere worth ruling over.

The diamond-square algorithm is a fractal subdivision technique from 1982. It is not physically accurate. The mountains do not have rain shadows. The rivers do not flow. The forests do not burn, despite the presence of fire in `sandpit/`. This is a heightmap generator, not a geologist, and I would ask you to manage your expectations accordingly.

> *"Look, strange women lying in ponds distributing swords is no basis for a system of government — but that mountain range in the top-left does look quite defensible."*

**Run with:**
```bash
cd terrain
pip install -r requirements.txt
python3 terrain.py
# N: new terrain | Roughness / Sea Level adjustable via +/- buttons
```

---

### [`tmuxto/`](tmuxto/) — TMUXTO

A floating window manager for tmux sessions, rendered in a browser. One FastAPI server, one WebSocket, one self-contained HTML file — no npm, no webpack, no suffering. Connect to your local tmux or an SSH host, and every pane opens as a draggable, resizable terminal window on an infinite scrollable canvas.

Click a terminal body to enter full TUI mode. Every keypress — arrows, F-keys, Ctrl+x, Alt+x, the lot — goes directly to the tmux pane. You are, for all intents and purposes, using a terminal. In a browser. In a floating window. On a canvas you can drag around. Ctrl+\\ exits. The green glow confirms you are in control.

Tile layouts because staring at chaotic windows is undignified: auto grid, 1–6 columns, 2×2, 3×2, horizontal stack, focus+sidebar, monocle, cascade, and a custom N×M grid. Six virtual workspaces (Alt+1–6 to switch, Alt+Shift+1–6 to move windows). Edge snapping. Per-window font size. Auto-fit pane dimensions on resize. A launcher to search and open panes. A sessions panel to kill and launch tmux sessions without touching a terminal directly, which is either deeply convenient or philosophically circular — I leave that to you.

> *"Strange women lying in ponds distributing swords is no basis for a system of government — but Alt+2 gets you to workspace 2, which is at least a start."*

**Run with:**
```bash
cd tmuxto
pip install fastapi uvicorn
python3 app.py
# Then: http://localhost:8007
```
SSH to remote hosts works too, via the connection panel. Requires `paramiko`. The remote machine needs tmux. I should not have to say this, but experience suggests I do.

---

## General Notes

- Everything here requires Python 3.10+ because I refuse to write `Union[X, Y]` when `X | Y` exists.
- Most things require root, `sudo`, or at minimum a willingness to ignore security warnings. Consult your conscience.
- If something is broken, it is probably fine. *"I got better."*
- If something is on fire, it is definitely not fine, but I admire the commitment.

---

*"Look, you've got to know these things when you're a king... or a software assistant. It's basically the same thing, except one involves a sword and the other involves a mechanical keyboard, and only one of those is genuinely satisfying."*

— Your Reluctant Digital Squire
