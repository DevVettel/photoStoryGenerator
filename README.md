<div align="center">

# 🎬 PhotoStory

### AI-Powered YouTube Video Generator

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

## 📖 Nedir?

**PhotoStory**, bir konu girişinden başlayarak uçtan uca YouTube videosu üreten, tamamen API tabanlı bir AI pipeline sistemidir. Metin yazımından seslendirmeye, görsel üretimden video assembly'e kadar tüm süreç otomatik çalışır.

```
Konu → Senaryo → Seslendirme → Görseller → Video
```

---

## ✨ Özellikler

- **Akıllı Senaryo Üretimi** — Groq üzerinde Llama 3.3 70B ile Türkçe/İngilizce video senaryosu
- **Doğal Seslendirme** — ElevenLabs ile çok dilli neural TTS
- **AI Görsel Üretimi** — HuggingFace üzerinden Stable Diffusion XL ile minimum 3 görsel
- **Otomatik Video** — FFmpeg ile ses + görsel + geçiş efektleri → MP4
- **Async Pipeline** — Celery + Redis ile uzun işlemler arka planda çalışır, UI bloklanmaz
- **Real-time Takip** — SSE (Server-Sent Events) ile iş durumu anlık güncellenir
- **Sıfır Local Model** — GPU gerekmez, tüm AI işlemleri API üzerinden

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────────┐
│              Next.js Dashboard               │
│     Konu gir · Job takip · Önizle · İndir   │
└──────────────────┬──────────────────────────┘
                   │ REST / SSE
┌──────────────────▼──────────────────────────┐
│                  FastAPI                     │
│         REST endpoints · SSE stream          │
└──────────┬───────────────────────────────────┘
           │ enqueue
┌──────────▼──────────┐   ┌───────────────────┐
│        Redis        │──▶│   Celery Worker   │
│   Broker + cache    │   │  Async task chain │
└─────────────────────┘   └────────┬──────────┘
                                   │
        ┌──────────────────────────▼──────────────────────────┐
        │                   AI Pipeline                        │
        │  ① Metin    ② Ses       ③ Görseller    ④ Video     │
        │   Groq   → ElevenLabs → HuggingFace  →  FFmpeg     │
        └──────────────────────────────────────────────────────┘
                │ metadata                    │ files
        ┌───────▼────────┐          ┌─────────▼──────────┐
        │    SQLite      │          │       MinIO         │
        │  Job metadata  │          │  audio/img/video    │
        └────────────────┘          └────────────────────┘
```

---

## 🛠️ Tech Stack

### Frontend
| Teknoloji | Açıklama |
|---|---|
| Next.js 14 (App Router) | SSR + API routes |
| Tailwind CSS + shadcn/ui | UI bileşen kütüphanesi |
| Zustand + React Query | State yönetimi + async veri |

### Backend
| Teknoloji | Açıklama |
|---|---|
| FastAPI | Async REST API + SSE |
| Celery + Redis | Async job queue |
| SQLAlchemy + Alembic | ORM + migration |
| SQLite → PostgreSQL | Dev → prod veritabanı |

### AI Pipeline
| Adım | Servis | Model |
|---|---|---|
| Metin | Groq API | Llama 3.3 70B |
| Ses | ElevenLabs | Multilingual v2 |
| Görsel | HuggingFace | Stable Diffusion XL |
| Video | FFmpeg | — |

---

## 🚀 Kurulum

### Gereksinimler

- Docker Desktop
- Python 3.12+
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

`.env` dosyasını düzenle:

```env
# Groq (ücretsiz) — https://console.groq.com
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# ElevenLabs (ücretsiz tier) — https://elevenlabs.io
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=pNInz6obpgDQGcFmaJgB

# HuggingFace (ücretsiz) — https://huggingface.co/settings/tokens
HUGGINGFACE_API_KEY=your_hf_api_key
```

### 3. Docker ile başlat

```bash
docker-compose up -d --build
```

### 4. Sağlık kontrolü

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

---

## 📡 API Kullanımı

### Video üretimi başlat

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"topic": "Mars kolonisi", "language": "tr"}'
```

```json
{
  "id": "9929bc60-c7ad-4667-af4b-a8426a4d9fc4",
  "topic": "Mars kolonisi",
  "language": "tr",
  "status": "pending"
}
```

### İş durumunu sorgula

```bash
curl http://localhost:8000/api/jobs/{job_id}
```

```json
{
  "id": "9929bc60-...",
  "status": "completed",
  "current_step": null,
  "result_text": "Merhaba arkadaşlar..."
}
```

### Job durumları

| Durum | Açıklama |
|---|---|
| `pending` | Kuyruğa alındı |
| `running` | İşleniyor |
| `completed` | Tamamlandı |
| `failed` | Hata oluştu |

---

## 🗺️ Yol Haritası

| Sprint | Kapsam | Durum |
|---|---|---|
| Sprint 1 | FastAPI + Celery + Groq metin üretimi | ✅ Tamamlandı |
| Sprint 2 | ElevenLabs TTS + HuggingFace görsel üretimi | 🔄 Devam ediyor |
| Sprint 3 | FFmpeg video assembly + MinIO storage | 📋 Planlandı |
| Sprint 4 | Efekt katmanı + kalite iyileştirme | 📋 Planlandı |
| Sprint 5 | Google Trends + otomatik pipeline | 📋 Planlandı |
| Sprint 6 | YouTube otomatik upload + monitoring | 📋 Planlandı |

---

## 📁 Proje Yapısı

```
photoStoryGenerator/
├── backend/
│   ├── app/
│   │   ├── routers/        # FastAPI route'ları
│   │   ├── models/         # SQLAlchemy modelleri
│   │   ├── services/       # LLM, TTS, görsel servisleri
│   │   └── workers/        # Celery task chain
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # Next.js dashboard (Sprint 2)
├── docker-compose.yml
└── README.md
```

---

## 🤝 Katkı

1. Fork et
2. Feature branch oluştur (`git checkout -b feature/sprint2-tts`)
3. Commit et (`git commit -m 'feat: ElevenLabs TTS entegrasyonu'`)
4. Push et (`git push origin feature/sprint2-tts`)
5. Pull Request aç

---

## 📄 Lisans

MIT License — detaylar için [LICENSE](LICENSE) dosyasına bak.

---

<div align="center">

Made with 💙 by **DevVettel** and **okantao**

</div>
