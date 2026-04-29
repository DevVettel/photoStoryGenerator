import os
import time
import httpx
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
REPLICATE_API_URL = "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions"

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def generate_image_prompts_with_llm(story_text: str, topic: str, count: int = 3) -> list[str]:
    """Groq ile hikayeye uygun İngilizce görsel promptları üretir."""
    prompt = f"""You are a visual director for YouTube videos. Based on the following video script, generate exactly {count} short, vivid image generation prompts in English.

Rules:
- Each prompt must be in English
- Each prompt should visually represent a key moment from the script
- Keep each prompt under 20 words
- Add "cinematic, 4k, high quality, photorealistic" to each prompt
- Return ONLY the prompts, one per line, no numbering, no extra text

Video script topic: {topic}

Video script:
{story_text[:1000]}

Generate {count} image prompts:"""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300,
    )

    raw = response.choices[0].message.content.strip()
    prompts = [line.strip() for line in raw.split("\n") if line.strip()][:count]

    # Yeterli prompt yoksa fallback ekle
    while len(prompts) < count:
        prompts.append(f"{topic}, cinematic, 4k, high quality, photorealistic")

    return prompts


def generate_image(prompt: str, output_path: str) -> str:
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }

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

    poll_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
    for _ in range(40):
        time.sleep(3)
        poll = httpx.get(poll_url, headers=headers, timeout=30.0)
        poll.raise_for_status()
        result = poll.json()

        if result["status"] == "succeeded":
            image_url = result["output"][0]
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

    # Groq ile İngilizce prompt üret
    prompts = generate_image_prompts_with_llm(story_text, topic, count)

    paths = []
    for i, prompt in enumerate(prompts):
        output_path = os.path.join(output_dir, f"image_{i+1}.png")

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

        if i < count - 1:
            time.sleep(15)

    return paths
