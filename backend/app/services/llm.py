import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

STORY_PROMPT_TR = """Sen bir YouTube içerik yazarısın. Aşağıdaki konu için ilgi çekici, bilgilendirici ve akıcı bir video senaryosu yaz.

KURALLAR:
- Senaryo 300-400 kelime olsun
- Doğal konuşma diline uygun olsun
- İzleyiciyi baştan sona meşgul etsin
- Sadece senaryo metnini yaz, başlık veya açıklama ekleme
- YALNIZCA Türkçe yaz. Tek bir İngilizce, Çince, Arapça veya başka yabancı dil kelimesi kullanma
- Yabancı kelime kullanmak istersen Türkçe karşılığını kullan (örn: "not only" yerine "sadece değil", "private" yerine "özel")"""

STORY_PROMPT_EN = """You are a YouTube content writer. Write an engaging, informative and fluid video script for the following topic.

RULES:
- Script should be 300-400 words
- Use natural conversational language
- Keep the audience engaged from start to finish
- Write only the script text, no title or description
- Use ONLY English and Latin characters
- Never use Chinese, Arabic, Vietnamese or any non-Latin characters"""


def generate_story(topic: str, language: str = "tr") -> str:
    prompt = STORY_PROMPT_TR if language == "tr" else STORY_PROMPT_EN

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Konu: {topic}"}
            ],
            max_tokens=800,
            temperature=0.7
        )

        content = response.choices[0].message.content

        # Yabancı karakterleri temizle — sadece Latin, Türkçe, noktalama ve boşluk bırak
        content = re.sub(r'[^\x00-\x7FÀ-ɏĞğİıŞşÖöÜüÇç\s]', '', content)
        content = re.sub(r' +', ' ', content).strip()

        return content
    except Exception as e:
        print(f"Groq Hatası: {str(e)}")
        raise e
