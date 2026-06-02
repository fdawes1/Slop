# PLAGUE — Medieval Disease Spread Simulator (SIR Model)

A real-time spatial SIR simulation rendered as a live ASCII heatmap. Press **UNLEASH** to seed patient zero at a random location and watch the outbreak propagate.

## Parameters

| Parameter | Default | Description |
|---|---|---|
| beta | 0.4 | Infection rate |
| gamma | 0.1 | Recovery rate |

R₀ = beta / gamma. Above 1: pandemic. Below 1: contained.

## Display

| Character | Meaning |
|---|---|
| `#` (red) | Heavily infected |
| `.` (yellow) | Spreading |
| `+` (green) | Recovered |
| `.` (dim) | Susceptible |

## Run

```bash
pip install -r requirements.txt
python3 plague.py
```

Space to pause, `r` to reset, `q` to quit.
