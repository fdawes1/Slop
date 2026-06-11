from __future__ import annotations
from pathlib import Path
from typing import Dict
from models import Script, VideoMetadata


def generate_thumbnail(
    script: Script,
    metadata: VideoMetadata,
    run_id: str,
    settings: Dict,
    env: Dict,
    output_dir: str = "output",
) -> str:
    from tools.image_gen import generate_image

    run_dir = Path(output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    base_path = str(run_dir / "thumbnail_base.png")
    final_path = str(run_dir / "thumbnail.jpg")

    branding = settings.get("branding", {})
    primary_color = branding.get("primary_color", "#6C63FF")

    image_prompt = (
        f"YouTube thumbnail background for video about: {script.topic}. "
        f"Dramatic, eye-catching, cinematic. High contrast. Vivid colors with {primary_color} accents. "
        f"No text or watermarks. Widescreen 16:9. Professional photography or CGI. "
        f"Evokes: {script.angle}"
    )

    try:
        generate_image(image_prompt, base_path, settings["models"], env)
    except Exception as e:
        print(f"  Thumbnail image gen failed: {e} — using gradient")
        _gradient_background(base_path, primary_color)

    _compose_thumbnail(base_path, final_path, metadata.title, settings)
    return final_path


def _gradient_background(output_path: str, primary_color: str):
    from PIL import Image, ImageDraw

    hex_c = primary_color.lstrip("#")
    r, g, b = (int(hex_c[i:i+2], 16) for i in (0, 2, 4))

    img = Image.new("RGB", (1280, 720))
    draw = ImageDraw.Draw(img)
    for y in range(720):
        t = y / 720
        draw.line([(0, y), (1280, y)], fill=(
            int(r * (1 - t) + 10 * t),
            int(g * (1 - t) + 10 * t),
            int(b * (1 - t) + 30 * t),
        ))
    img.save(output_path)


def _compose_thumbnail(bg_path: str, output_path: str, title: str, settings: Dict):
    from PIL import Image, ImageDraw, ImageFont

    thumb_cfg = settings.get("thumbnail", {})
    max_chars = thumb_cfg.get("text_max_chars", 38)
    gradient_opacity = thumb_cfg.get("gradient_opacity", 0.65)

    img = Image.open(bg_path).convert("RGB").resize((1280, 720), Image.LANCZOS)

    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    draw_o = ImageDraw.Draw(overlay)
    for y in range(360, 720):
        alpha = int(255 * gradient_opacity * ((y - 360) / 360))
        draw_o.line([(0, y), (1280, y)], fill=(0, 0, 0, min(alpha, 220)))

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    try:
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 78)
        font_reg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except OSError:
        font_bold = font_reg = ImageFont.load_default()

    words = title.split()
    lines, current = [], []
    for word in words:
        current.append(word)
        if len(" ".join(current)) > max_chars:
            if len(current) > 1:
                current.pop()
                lines.append(" ".join(current))
                current = [word]
            else:
                lines.append(" ".join(current))
                current = []
    if current:
        lines.append(" ".join(current))
    lines = lines[:3]

    y = 720 - 55 - len(lines) * 88
    for line in lines:
        draw.text((58, y + 3), line, font=font_bold, fill=(0, 0, 0))
        draw.text((55, y), line, font=font_bold, fill="white")
        y += 88

    img.save(output_path, "JPEG", quality=95)
