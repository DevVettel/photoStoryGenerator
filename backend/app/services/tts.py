from gtts import gTTS
import os


def generate_audio(text: str, output_path: str) -> str:
    language = "tr"

    if output_path.endswith(".mp3"):
        pass
    else:
        output_path = output_path.replace(".wav", ".mp3")

    tts = gTTS(text=text, lang=language, slow=False)
    tts.save(output_path)

    return output_path
