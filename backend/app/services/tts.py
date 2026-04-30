import os
import time
import httpx

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
MINIMAX_TTS_URL = "https://api.replicate.com/v1/models/minimax/speech-2.8-hd/predictions"

VOICE_MAP = {
    "tr": "Friendly_Person",
    "en": "Friendly_Person",
}


def generate_audio(text: str, output_path: str, language: str = "tr") -> str:
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    voice = VOICE_MAP.get(language, "Friendly_Person")

    response = httpx.post(
        MINIMAX_TTS_URL,
        headers=headers,
        json={
            "input": {
                "text": text,
                "voice": voice,
                "speed": 1.0,
            }
        },
        timeout=30.0,
    )
    response.raise_for_status()
    prediction = response.json()
    prediction_id = prediction["id"]

    poll_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
    for _ in range(60):
        time.sleep(3)
        poll = httpx.get(poll_url, headers=headers, timeout=30.0)
        poll.raise_for_status()
        result = poll.json()

        if result["status"] == "succeeded":
            audio_url = result["output"]
            if isinstance(audio_url, list):
                audio_url = audio_url[0]

            audio_response = httpx.get(audio_url, timeout=60.0)
            audio_response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(audio_response.content)
            return output_path

        elif result["status"] == "failed":
            raise RuntimeError(f"MiniMax TTS failed: {result.get('error')}")

    raise RuntimeError("MiniMax TTS timeout — 180 saniye içinde tamamlanamadı")
