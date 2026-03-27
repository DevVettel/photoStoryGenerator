import httpx
import os
import time

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HF_MODEL = os.getenv("HF_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

IMAGE_STYLE_SUFFIX = (
    ", cinematic, high quality, detailed, 4k, professional photography style"
)


def build_image_prompts(story_text: str, topic: str, count: int = 3) -> list[str]:
    sentences = [s.strip() for s in story_text.split(".") if len(s.strip()) > 30]
    step = max(1, len(sentences) // count)
    selected = [sentences[i * step] for i in range(count) if i * step < len(sentences)]

    prompts = []
    for sentence in selected[:count]:
        prompt = f"{sentence[:120]}{IMAGE_STYLE_SUFFIX}"
        prompts.append(prompt)

    while len(prompts) < count:
        prompts.append(f"{topic} scene, cinematic, high quality, detailed, 4k")

    return prompts


def generate_image(prompt: str, output_path: str, retries: int = 3) -> str:
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {
        "inputs": prompt,
        "parameters": {"width": 1024, "height": 576, "num_inference_steps": 25},
    }

    for attempt in range(retries):
        response = httpx.post(
            HF_API_URL,
            headers=headers,
            json=payload,
            timeout=60.0,
        )

        if response.status_code == 503:
            wait = 20 * (attempt + 1)
            time.sleep(wait)
            continue

        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

        return output_path

    raise RuntimeError(f"HuggingFace model {retries} denemede yanıt vermedi")


def generate_images(story_text: str, topic: str, output_dir: str, count: int = 3) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    prompts = build_image_prompts(story_text, topic, count)
    paths = []

    for i, prompt in enumerate(prompts):
        output_path = os.path.join(output_dir, f"image_{i+1}.png")
        generate_image(prompt, output_path)
        paths.append(output_path)

    return paths
