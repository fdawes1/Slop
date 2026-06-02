# TREBUCHET — Medieval Siege Physics Simulator

A trebuchet physics simulator. Adjust the parameters, press **FIRE**, watch the arc.

## Parameters

| Parameter | Default | Description |
|---|---|---|
| Counterweight (kg) | 100 | Mass of the counterweight |
| Arm ratio | 4 | Long arm : short arm ratio |
| Arm length (m) | 5 | Total arm length |
| Sling length (m) | 3 | Sling extension |
| Projectile (kg) | 5 | Mass of the projectile |
| Launch angle (°) | 45 | Release angle |

## Physics

Uses a moment-of-inertia model: `I = M·a² + m·b²`, giving angular velocity `ω = √(2Mgh/I)` and launch velocity `v = ω·(b + sling)`. At default settings: **~109 m range**.

## Run

```bash
pip install -r requirements.txt
python3 trebuchet.py
```

Press `q` to quit.
