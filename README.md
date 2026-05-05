<div align="center">

# PhotoStory

### AI-Powered Video Generator

*Bir konu ver — senaryo, ses, görsel ve video otomatik üretilsin.*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org)
[![Celery](https://img.shields.io/badge/Celery-5.4-37814A?style=flat-square&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## Nedir?

**PhotoStory**, bir konu girişinden başlayarak uçtan uca video üreten, tamamen API tabanlı bir AI pipeline sistemidir. Metin üretiminden seslendir meye, görsel oluşturmadan video montajına kadar tüm süreç otomatik çalışır — yerel GPU veya model gerektirmez.

```
Konu → Senaryo (Groq) → Ses (MiniMax) → Görseller (Flux) → Video (FFmpeg)
```

---

## Özellikler

- **Senaryo Üretimi** — Groq üzerinde Llama 3.3 70B ile Türkçe/İngilizce video senaryosu (300–400 kelime)
- **Doğal Seslendirme** — Replicate üzerinden MiniMax Speech 2.8 HD ile yüksek kaliteli neural TTS
- **AI Görsel Üretimi** — Replicate üzerinden Flux Schnell ile otomatik prompt mühendisliği + 3 adet 16:9 görsel
- **Profesyonel Video Montajı** — FFmpeg ile Ken Burns efektleri, xfade geçişleri, otomatik SRT altyazılar → MP4
- **Async Pipeline** — Celery + Redis ile uzun işlemler arka planda; UI bloklanmaz
- **Gerçek Zamanlı Takip** — SSE (Server-Sent Events) ile iş durumu anlık akışı
- **Test Modu** — Görsel üretimini atlayan ve placeholder kullanan `skip_images` seçeneği (API kredisi harcamaz)
- **Sıfır Lokal Model** — Tüm AI işlemleri API üzerinden; GPU gerekmez

---

## Mimari

```
┌───────────────────────────────────────────┐
│             Next.js Dashboard              │
│   Konu gir · Job takip · İndir · Önizle   │
└─────────────────┬─────────────────────────┘
                  │ REST / SSE
┌─────────────────▼─────────────────────────┐
│                 FastAPI                    │
│        REST endpoints · SSE stream        │
└──────────┬────────────────────────────────┘
           │ enqueue
┌──────────▼──────────┐  ┌──────────────────────┐
│        Redis        │─▶│    Celery Worker     │
│  Broker + Backend   │  │   Async task chain   │
└─────────────────────┘  └──────────┬───────────┘
                                    │
        ┌───────────────────────────▼──────────────────────────┐
        │                    AI Pipeline                        │
        │  ① Senaryo    ② Ses         ③ Görseller   ④ Video  │
        │   Groq LLM → MiniMax TTS → Flux Schnell → FFmpeg    │
        └───────────────────────────────────────────────────────┘
                │ metadata                    │ dosyalar
        ┌───────▼────────┐        ┌───────────▼──────────┐
        │    SQLite      │        │   Docker Volume      │
        │  Job metadata  │        │  audio / img / video │
        └────────────────┘        └──────────────────────┘
```

---

## Tech Stack

### Frontend

| Teknoloji | Versiyon | Açıklama |
|---|---|---|
| Next.js (App Router) | 14.2 | SSR + dosya tabanlı routing |
| React | 18 | UI bileşenleri |
| TypeScript | 5 | Tip güvenliği |
| Tailwind CSS | 3.4 | Utility-first stil |
| TanStack React Query | 5 | Async state yönetimi |

### Backend

| Teknoloji | Versiyon | Açıklama |
|---|---|---|
| FastAPI | 0.115 | Async REST API + SSE streaming |
| Celery | 5.4 | Dağıtık task queue |
| Redis | 7 | Broker + sonuç backend |
| SQLAlchemy | 2.0 | ORM |
| SQLite | — | Job metadata (geliştirme) |
| Python | 3.12 | Runtime |

### AI Pipeline

| Adım | Sağlayıcı | Model |
|---|---|---|
| Senaryo | Groq API | Llama 3.3 70B Versatile |
| Ses | Replicate (MiniMax) | Speech 2.8 HD |
| Görseller | Replicate (Black Forest Labs) | Flux Schnell |
| Video montajı | FFmpeg | — |

---

## Video Montaj Detayları

FFmpeg `filter_complex` zinciri ile tam otomatik video üretimi:

- **Ken Burns efektleri** — zoom-in, zoom-out, pan-right, pan-left, pan-up (rotasyonlu)
- **xfade geçişleri** — dissolve, fadeblack, smoothleft, smoothright, fade (rotasyonlu)
- **Altyazılar** — Hikaye metni cümlelere ayrılır, eşit süre paylaştırılır, SRT olarak oluşturulur
- **Çıktı** — H.264 (CRF 20) + AAC 192k, 25 FPS, 1280×720

---

## Kurulum

### Gereksinimler

- Docker Desktop
- Node.js 18+

### 1. Repo'yu klonla

```bash
git clone https://github.com/DevVettel/photoStoryGenerator.git
cd photoStoryGenerator
```

### 2. Environment değişkenlerini ayarla

```bash
cp backend/.env.example backend/.env
```

`backend/.env` dosyasını düzenle:

```env
# Groq — https://console.groq.com (ücretsiz tier mevcut)
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# Replicate — https://replicate.com (TTS + görsel üretimi)
REPLICATE_API_TOKEN=your_replicate_api_token

# Altyapı (varsayılanlar Docker Compose ile çalışır)
DATABASE_URL=sqlite:///./photostory.db
REDIS_URL=redis://redis:6379/0
OUTPUT_DIR=/app/outputs
```

### 3. Docker ile başlat

```bash
docker-compose up -d --build
```

Servisler:
- **API** → `http://localhost:8000`
- **Frontend** → `http://localhost:3000`
- **Redis** → `localhost:6380`

### 4. Sağlık kontrolü

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

---

## API Referansı

### Video üretimi başlat

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"topic": "Mars kolonisi", "language": "tr", "skip_images": false}'
```

```json
{
  "id": "9929bc60-c7ad-4667-af4b-a8426a4d9fc4",
  "topic": "Mars kolonisi",
  "language": "tr",
  "status": "pending",
  "current_step": null
}
```

### İş durumunu sorgula

```bash
curl http://localhost:8000/api/jobs/{job_id}
```

### Gerçek zamanlı durum akışı (SSE)

```bash
curl -N http://localhost:8000/api/jobs/{job_id}/stream
```

### Tüm işleri listele

```bash
curl http://localhost:8000/api/jobs
```

### Çıktı dosyalarını al

```bash
curl http://localhost:8000/api/jobs/{job_id}/files
# → {"audio": "...", "images": [...], "video": "..."}
```

### Dosya indir

```bash
curl -O http://localhost:8000/api/jobs/{job_id}/download/video
curl -O http://localhost:8000/api/jobs/{job_id}/download/audio
```

### İş durumları

| Durum | Açıklama |
|---|---|
| `pending` | Kuyruğa alındı |
| `running` (step: `text`) | Senaryo üretiliyor |
| `running` (step: `audio`) | Seslendirme yapılıyor |
| `running` (step: `images`) | Görseller oluşturuluyor |
| `running` (step: `video`) | Video montajı yapılıyor |
| `completed` | Tamamlandı, dosyalar hazır |
| `failed` | Hata oluştu (`error_msg` dolu) |

---

## Proje Yapısı

```
photoStoryGenerator/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI uygulama başlangıcı
│   │   ├── routers/
│   │   │   └── jobs.py         # Tüm job endpoint'leri
│   │   ├── models/
│   │   │   └── job.py          # SQLAlchemy Job modeli
│   │   ├── services/
│   │   │   ├── llm.py          # Groq senaryo üretimi
│   │   │   ├── tts.py          # MiniMax TTS (Replicate)
│   │   │   ├── image.py        # Flux Schnell görsel üretimi (Replicate)
│   │   │   └── video.py        # FFmpeg montaj + Ken Burns + SRT
│   │   └── workers/
│   │       └── tasks.py        # Celery task chain tanımları
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.tsx            # Ana form sayfası
│   │   ├── layout.tsx          # Root layout
│   │   └── jobs/
│   │       ├── page.tsx        # Job listesi
│   │       └── [id]/page.tsx   # Job detay ve izleme
│   ├── package.json
│   └── .env.local
├── docker-compose.yml
└── README.md
```

---

## Geliştirme

### Worker'ı yeniden başlat

```bash
docker-compose up -d --force-recreate worker
```

### Logları izle

```bash
docker-compose logs -f worker
docker-compose logs -f api
```

### Test modu

Frontend'deki **Test modu** toggle'ı `skip_images: true` parametresini gönderir. Görsel üretimini atlayıp PIL ile placeholder görsel oluşturur — Replicate kredisi harcamadan tüm pipeline'ı test etmeye yarar.

---

## Lisans

MIT License — detaylar için [LICENSE](LICENSE) dosyasına bak.

---

<div align="center">

Made by **DevVettel** and **okantao**

</div>
