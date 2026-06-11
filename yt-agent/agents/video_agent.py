from __future__ import annotations
import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from models import Script


def generate_section_images(
    script: Script,
    run_id: str,
    settings: Dict,
    env: Dict,
    output_dir: str = "output",
) -> List[str]:
    from tools.image_gen import generate_image

    images_dir = Path(output_dir) / run_id / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    prompts: List[Tuple[str, str]] = (
        [("hook", f"Cinematic opening shot representing: {script.topic}. {script.sections[0].visual_prompt if script.sections else ''}")]
        + [(f"section_{i}", s.visual_prompt) for i, s in enumerate(script.sections)]
        + [("cta", "Modern tech channel outro aesthetic, subscribe notification bell, dark background with neon accents, no text")]
    )

    image_paths = []
    for name, prompt in prompts:
        out = str(images_dir / f"{name}.png")
        full_prompt = (
            f"{prompt}. "
            "Photorealistic, cinematic lighting, 8K quality, widescreen 16:9 composition, "
            "no text or watermarks, professional photography or high-end CGI style."
        )
        try:
            generate_image(full_prompt, out, settings["models"], env)
        except Exception as e:
            print(f"  Image gen failed for {name}: {e} — using fallback")
            _fallback_image(out, script.topic, name)
        image_paths.append(out)

    return image_paths


def _fallback_image(output_path: str, topic: str, label: str):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1920, 1080), color=(10, 10, 25))
    draw = ImageDraw.Draw(img)

    for y in range(1080):
        t = y / 1080
        r = int(108 * (1 - t) + 10 * t)
        g = int(99 * (1 - t) + 10 * t)
        b = int(255 * (1 - t) + 40 * t)
        draw.line([(0, y), (1920, y)], fill=(r, g, b))

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except OSError:
        font = small = ImageFont.load_default()

    draw.text((960, 480), topic[:50], font=font, fill="white", anchor="mm")
    draw.text((960, 580), label, font=small, fill=(200, 200, 200), anchor="mm")
    img.save(output_path)


def _ken_burns_frame(img_array: np.ndarray, t: float, duration: float, scale: float, direction: str):
    from PIL import Image

    h, w = img_array.shape[:2]
    progress = t / max(duration, 0.001)

    if direction == "zoom_in":
        zoom = 1.0 + (scale - 1.0) * progress
    elif direction == "zoom_out":
        zoom = scale - (scale - 1.0) * progress
    else:
        zoom = 1.0 + (scale - 1.0) * 0.5

    new_w = int(w / zoom)
    new_h = int(h / zoom)

    if direction == "pan_left":
        x0 = int((w - new_w) * progress)
        y0 = (h - new_h) // 2
    elif direction == "pan_right":
        x0 = int((w - new_w) * (1 - progress))
        y0 = (h - new_h) // 2
    else:
        x0 = (w - new_w) // 2
        y0 = (h - new_h) // 2

    x0 = max(0, min(x0, w - new_w))
    y0 = max(0, min(y0, h - new_h))

    cropped = img_array[y0:y0 + new_h, x0:x0 + new_w]
    pil = Image.fromarray(cropped).resize((w, h), Image.LANCZOS)
    return np.array(pil)


def assemble_video(
    script: Script,
    image_paths: List[str],
    audio_durations: List[float],
    combined_audio_path: str,
    run_id: str,
    settings: Dict,
    output_dir: str = "output",
) -> str:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
    from moviepy.video.fx.all import fadein, fadeout

    run_dir = Path(output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(run_dir / "final_video.mp4")

    resolution = tuple(settings["video"]["resolution"])
    fps = settings["video"]["fps"]
    scale = settings["video"]["ken_burns_scale"]
    directions = ["zoom_in", "zoom_out", "pan_left", "zoom_in", "pan_right", "zoom_out", "zoom_in"]

    clips = []
    for i, (img_path, duration) in enumerate(zip(image_paths, audio_durations)):
        if not os.path.exists(img_path):
            continue

        direction = directions[i % len(directions)]
        img_array = np.array(__import__("PIL").Image.open(img_path).convert("RGB").resize(resolution, __import__("PIL").Image.LANCZOS))

        clip = ImageClip(img_path).set_duration(duration).resize(resolution)
        clip = clip.fl(lambda gf, t, d=duration, s=scale, di=direction, arr=img_array:
                       _ken_burns_frame(arr, t, d, s, di))

        if i > 0:
            clip = fadein(clip, 0.4)
        if i < len(image_paths) - 1:
            clip = fadeout(clip, 0.4)

        clips.append(clip)

    if not clips:
        raise RuntimeError("No video clips could be generated")

    final = concatenate_videoclips(clips, method="compose")
    audio = AudioFileClip(combined_audio_path)

    min_dur = min(audio.duration, final.duration)
    final = final.subclip(0, min_dur)
    audio = audio.subclip(0, min_dur)
    final = final.set_audio(audio)

    final.write_videofile(
        output_path,
        fps=fps,
        codec=settings["video"]["codec"],
        audio_codec=settings["video"]["audio_codec"],
        verbose=False,
        logger=None,
        threads=settings["video"].get("threads", 4),
    )

    for c in clips:
        c.close()
    audio.close()

    return output_path
