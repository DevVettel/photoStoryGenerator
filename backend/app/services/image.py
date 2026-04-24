import os
import time
import httpx

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
REPLICATE_API_URL = "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions"

IMAGE_STYLE_SUFFIX = ", cinematic, high quality, detailed, 4k, professional photography style"


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


def generate_image(prompt: str, output_path: str) -> str:
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    # Prediction oluştur
    response = httpx.post(
        REPLICATE_API_URL,
        headers=headers,
        json={
            "input": {
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "num_outputs": 1,
                "output_format": "png",
            }
        },
        timeout=30.0,
    )
    response.raise_for_status()
    prediction = response.json()
    prediction_id = prediction["id"]

    # Sonucu poll et (max 120 saniye)
    poll_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
    for _ in range(40):
        time.sleep(3)
        poll = httpx.get(poll_url, headers=headers, timeout=30.0)
        poll.raise_for_status()
        result = poll.json()

        if result["status"] == "succeeded":
            image_url = result["output"][0]
            # Görseli indir
            img_response = httpx.get(image_url, timeout=60.0)
            img_response.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(img_response.content)
            return output_path

        elif result["status"] == "failed":
            raise RuntimeError(f"Replicate prediction failed: {result.get('error')}")

    raise RuntimeError("Replicate prediction timeout — 120 saniye içinde tamamlanamadı")


def generate_images(story_text: str, topic: str, output_dir: str, count: int = 3) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    prompts = build_image_prompts(story_text, topic, count)
    paths = []

    for i, prompt in enumerate(prompts):
        output_path = os.path.join(output_dir, f"image_{i+1}.png")

        # Her görsel için retry mekanizması
        for attempt in range(5):
            try:
                generate_image(prompt, output_path)
                paths.append(output_path)
                break
            except Exception as e:
                if "429" in str(e) and attempt < 4:
                    wait_time = 30 * (attempt + 1)
                    time.sleep(wait_time)
                    continue
                raise

        # Görseller arası bekleme
        if i < count - 1:
            time.sleep(15)

    return paths
