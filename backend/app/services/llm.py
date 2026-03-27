from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

STORY_PROMPT_TR = """Sen bir YouTube içerik yazarısın. Aşağıdaki konu için ilgi çekici,
bilgilendirici ve akıcı bir video senaryosu yaz. Senaryo 300-400 kelime olsun,
doğal konuşma diline uygun olsun ve izleyiciyi baştan sona meşgul etsin.

Konu: {topic}

Sadece senaryo metnini yaz, başlık veya açıklama ekleme."""

STORY_PROMPT_EN = """You are a YouTube content writer. Write an engaging, informative
and fluid video script for the following topic. The script should be 300-400 words,
in natural conversational language, and keep the audience engaged from start to finish.

Topic: {topic}

Write only the script text, no title or description."""


def generate_story(topic: str, language: str = "tr") -> str:
    prompt = STORY_PROMPT_TR if language == "tr" else STORY_PROMPT_EN
    prompt = prompt.format(topic=topic)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=800,
    )
    return response.choices[0].message.content
