import os
from PIL import Image, ImageDraw, ImageFont
import time


def build_image_prompts(story_text: str, topic: str, count: int = 3) -> list[str]:
    sentences = [s.strip() for s in story_text.split(".") if len(s.strip()) > 30]
    step = max(1, len(sentences) // count)
    selected = [sentences[i * step] for i in range(count) if i * step < len(sentences)]

    prompts = []
    for sentence in selected[:count]:
        prompts.append(sentence[:100])

    while len(prompts) < count:
        prompts.append(f"{topic} - sahne {len(prompts) + 1}")

    return prompts


def generate_image(prompt: str, output_path: str, index: int = 1) -> str:
    colors = ["#1a1a2e", "#16213e", "#0f3460"]
    color = colors[index % len(colors)]

    img = Image.new("RGB", (1024, 576), color=color)
    draw = ImageDraw.Draw(img)

    draw.rectangle([40, 40, 984, 536], outline="#e94560", width=2)

    text = prompt[:80] + "..." if len(prompt) > 80 else prompt
    draw.text((512, 288), text, fill="#ffffff", anchor="mm")

    img.save(output_path, "PNG")
    return output_path


def generate_images(story_text: str, topic: str, output_dir: str, count: int = 3) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    prompts = build_image_prompts(story_text, topic, count)
    paths = []

    for i, prompt in enumerate(prompts):
        output_path = os.path.join(output_dir, f"image_{i+1}.png")
        generate_image(prompt, output_path, index=i)
        paths.append(output_path)

    return paths
