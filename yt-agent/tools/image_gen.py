from __future__ import annotations
import requests
from typing import Dict


def generate_dalle(
    prompt: str,
    output_path: str,
    api_key: str,
    size: str = "1792x1024",
    quality: str = "standard",
) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality=quality,
        n=1,
    )
    image_url = response.data[0].url
    img_data = requests.get(image_url, timeout=30).content
    with open(output_path, "wb") as f:
        f.write(img_data)
    return output_path


def generate_stability(prompt: str, output_path: str, api_key: str) -> str:
    url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    headers = {"authorization": f"Bearer {api_key}", "accept": "image/*"}
    data = {"prompt": prompt, "aspect_ratio": "16:9", "output_format": "png"}
    r = requests.post(url, headers=headers, files={"none": ""}, data=data, timeout=60)
    r.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(r.content)
    return output_path


def generate_image(prompt: str, output_path: str, settings: Dict, env: Dict) -> str:
    provider = settings.get("image_generator", "dall-e-3")
    if provider == "stability":
        return generate_stability(prompt, output_path, api_key=env.get("STABILITY_API_KEY", ""))
    else:
        return generate_dalle(
            prompt, output_path,
            api_key=env.get("OPENAI_API_KEY", ""),
            size=settings.get("image_size", "1792x1024"),
            quality=settings.get("image_quality", "standard"),
        )
