import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Güvenli client başlatma
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

STORY_PROMPT_TR = """Sen bir YouTube içerik yazarısın. Aşağıdaki konu için ilgi çekici, 
bilgilendirici ve akıcı bir video senaryosu yaz. Senaryo 300-400 kelime olsun, 
doğal konuşma diline uygun olsun ve izleyiciyi baştan sona meşgul etsin."""

def generate_story(topic: str, language: str = "tr") -> str:
    """
    Groq API kullanarak verilen konuya göre bir hikaye/senaryo oluşturur.
    """
    prompt = STORY_PROMPT_TR if language == "tr" else "Write an engaging story about: "
    
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
        return response.choices[0].message.content
    except Exception as e:
        print(f"Groq Hatası: {str(e)}")
        raise e