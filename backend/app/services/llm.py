import os
import httpx
from groq import Groq
from dotenv import load_dotenv

# .env dosyasındaki GROQ_API_KEY ve diğer değişkenleri yükler
load_dotenv()

# Manuel testte çalışan bağlantı yapısını buraya kuruyoruz
# verify=False: SSL sertifika hatalarını atlayarak bağlantıyı zorlar
custom_client = httpx.Client(
    verify=False,
    timeout=60.0,
    trust_env=True
)

client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
    http_client=custom_client
)

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

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