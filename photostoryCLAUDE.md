# CLAUDE.md — PhotoStory YT Video Generator

> Bu dosya projenin tek kaynak of truth'udur. Tech stack, mimari kararlar, veritabanı şeması, sprint planı ve görev dağılımları burada yaşar. Her sprint başında güncellenir.

---

## 1. Proje Özeti

**PhotoStory**, bir konuyu alıp uçtan uca YouTube videosu üreten, tamamen API tabanlı bir AI pipeline sistemidir.

```
Konu girişi
  → Groq (Llama 3.3 70B) ile hikaye/metin üretimi
  → gTTS ile seslendirme
  → Pillow ile placeholder görsel üretimi (Sprint 3'te AI görsellere geçilecek)
  → FFmpeg ile video assembly (Sprint 3)
  → Ses + görsel + efektlerle birleşik MP4 çıktısı
```

İleride Google Trends entegrasyonu ile viral konu tespiti ve YouTube'a otomatik upload desteği eklenecektir.

**Ekip:** 2 kişi (DevVettel + okantao)
**Sprint süresi:** 2 hafta
**Toplam planlı sprint:** 6 (12 hafta)
**Repo:** https://github.com/DevVettel/photoStoryGenerator
**Deployment hedefi:** Local (geliştirme), cloud migration Sprint 6 sonrasında değerlendirilecek

---

## 2. Tech Stack

### 2.1 Frontend

| Katman | Teknoloji | Sürüm | Açıklama |
|---|---|---|---|
| Framework | Next.js | 14 (App Router) | SSR + API routes |
| UI Kit | shadcn/ui + Tailwind CSS | latest | Hızlı komponent geliştirme |
| State | Zustand | latest | Client-side global state |
| Async data | React Query (TanStack) | v5 | Server state, polling, cache |
| Real-time | Server-Sent Events (SSE) | — | Job durum güncellemeleri |

### 2.2 Backend

| Katman | Teknoloji | Sürüm | Açıklama |
|---|---|---|---|
| API | FastAPI | 0.115.0 | Async REST + SSE endpoint'leri |
| Task queue | Celery | 5.4.0 | AI pipeline adımlarını async çalıştırır |
| Message broker | Redis | 7 (Alpine) | Celery broker — port 6380 (host) / 6379 (container) |
| ORM | SQLAlchemy + Alembic | latest | DB erişimi + migration yönetimi |
| DB (dev) | SQLite | — | Geliştirme ortamı |
| DB (prod) | PostgreSQL | 16 | Sprint 6 sonrası geçiş |

### 2.3 AI Pipeline

| Adım | Servis | Model | Maliyet | Durum |
|---|---|---|---|---|
| Metin üretimi | Groq API | Llama 3.3 70B Versatile | Ücretsiz (30 req/dk) | ✅ Çalışıyor |
| Ses sentezi | gTTS | Google TTS (library) | Ücretsiz | ✅ Çalışıyor |
| Görsel üretimi | Pillow (placeholder) | — | Ücretsiz | ✅ Sprint 3'te AI'a geçilecek |
| Video assembly | FFmpeg | — | Ücretsiz | 📋 Sprint 3 |

> **Görsel üretimi geçmişi:**
> - HuggingFace Inference API → SDXL modeli kaldırıldı (410 Gone)
> - FLUX.1-schnell → kaldırıldı (410 Gone)
> - Pollinations.ai → API key zorunlu hale geldi (401)
> - Google Gemini Image API → free tier quota 0 (bölgesel kısıt)
> - **Karar:** Sprint 3'te Replicate API ile gerçek AI görselleri ($0.003/img)

### 2.4 Storage

| Katman | Teknoloji | Açıklama |
|---|---|---|
| Geçici dosya | Docker named volume (`outputs_data`) | api ve worker arasında shared |
| Kalıcı depolama | MinIO | Sprint 3'te eklenecek |
| Cloud geçişi | AWS S3 / GCS | Sadece endpoint değişimi gerekir |

### 2.5 DevOps

| Katman | Teknoloji | Açıklama |
|---|---|---|
| Konteynerizasyon | Docker + Docker Compose | api, worker, redis servisleri |
| CI/CD | GitHub Actions | Lint, test, build pipeline |
| Linting | Ruff (Python), ESLint (JS) | Kod kalitesi |
| Test | pytest (backend), Vitest (frontend) | Birim + entegrasyon testleri |

---

## 3. Sistem Mimarisi

```
┌─────────────────────────────────────────────────────┐
│                   Next.js Dashboard                  │
│         Konu gir · Job takip · Önizle · İndir        │
└──────────────────────┬──────────────────────────────┘
                       │ REST / SSE
┌──────────────────────▼──────────────────────────────┐
│                     FastAPI                          │
│            REST endpoints · SSE stream               │
└──────────┬───────────────────────────────────────────┘
           │ enqueue task
┌──────────▼──────────┐    ┌──────────────────────────┐
│        Redis        │───▶│        Celery Worker      │
│  port 6380 (host)   │    │     Async task runner     │
│  port 6379 (docker) │    └──────────┬───────────────┘
└─────────────────────┘               │ task chain
           ┌──────────────────────────▼───────────────────────────┐
           │                   AI Pipeline (sıralı)                │
           │                                                       │
           │  ① Metin      ② Ses       ③ Görseller    ④ Video    │
           │  Groq API →  gTTS    →  Pillow (ph.) →  FFmpeg      │
           │  Llama 3.3                Sprint 3'te    Sprint 3    │
           └──────────────────────────────────────────────────────┘
                  │ status updates        │ file outputs
           ┌──────▼──────────┐    ┌───────▼─────────────────────┐
           │     SQLite      │    │   outputs_data (Docker vol) │
           │  Job metadata   │    │   audio/ images/ (shared)   │
           └─────────────────┘    └─────────────────────────────┘
```

### 3.1 API Endpoint'leri

| Endpoint | Method | Açıklama |
|---|---|---|
| `/health` | GET | Sağlık kontrolü |
| `/api/jobs` | POST | Yeni pipeline başlat |
| `/api/jobs/{id}` | GET | Job durumu sorgula |
| `/api/jobs/{id}/stream` | GET | SSE ile gerçek zamanlı takip |
| `/api/jobs/{id}/files` | GET | Üretilen dosyaların URL listesi |
| `/api/jobs/{id}/download/audio` | GET | Ses dosyası indir |
| `/api/jobs/{id}/download/images/{filename}` | GET | Görsel indir |

### 3.2 Job Yaşam Döngüsü

```
PENDING → RUNNING (text) → RUNNING (audio) → RUNNING (images) → COMPLETED
                                                               → FAILED
```

---

## 4. Veritabanı Mimarisi

### 4.1 Tablolar

#### `jobs`
```sql
CREATE TABLE jobs (
    id           TEXT PRIMARY KEY,
    topic        TEXT NOT NULL,
    language     TEXT DEFAULT 'tr',
    status       TEXT DEFAULT 'pending',
    current_step TEXT,
    result_text  TEXT,
    error_msg    TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `outputs`
```sql
CREATE TABLE outputs (
    id          TEXT PRIMARY KEY,
    job_id      TEXT NOT NULL REFERENCES jobs(id),
    type        TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    metadata    TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `prompts`
```sql
CREATE TABLE prompts (
    id          TEXT PRIMARY KEY,
    job_id      TEXT NOT NULL REFERENCES jobs(id),
    step        TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    model_used  TEXT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `trends` (Sprint 5)
```sql
CREATE TABLE trends (
    id          TEXT PRIMARY KEY,
    topic       TEXT NOT NULL,
    score       REAL,
    category    TEXT,
    region      TEXT DEFAULT 'TR',
    fetched_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    used        BOOLEAN DEFAULT FALSE
);
```

---

## 5. Environment Variables

```bash
# backend/.env (git'e gitmez — .gitignore'da)

DATABASE_URL=sqlite:///./photostory.db
REDIS_URL=redis://redis:6379/0
OUTPUT_DIR=/app/outputs
DEBUG=true

# Groq (ücretsiz) — https://console.groq.com
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# HuggingFace (şimdilik kullanılmıyor, Sprint 3'te Replicate'e geçilecek)
HUGGINGFACE_API_KEY=your_hf_api_key

# Sprint 3+
REPLICATE_API_KEY=
MINIO_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=photostory

# Sprint 5+
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
TRENDS_REGION=TR
TRENDS_SCHEDULE_HOUR=9
```

---

## 6. Docker Compose Servisleri

```yaml
services:
  api:     # FastAPI — port 8000
  worker:  # Celery worker
  redis:   # Redis — port 6380 (host) → 6379 (container)

volumes:
  outputs_data:  # api ve worker arasında shared dosya depolama
```

> **NOT:** Redis host portu 6380 — 6379 portu `fariva` projesi tarafından kullanılıyor.
> **NOT:** `outputs_data` named volume api ve worker container'ları arasında paylaşılıyor.
> Dosyalar `/app/outputs/{job_id}/` altında saklanıyor.

---

## 7. Dizin Yapısı

```
photoStoryGenerator/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   └── jobs.py       # REST + SSE + download endpoints
│   │   ├── models/
│   │   │   └── job.py        # SQLAlchemy modelleri
│   │   ├── services/
│   │   │   ├── llm.py        # Groq wrapper
│   │   │   ├── tts.py        # gTTS wrapper
│   │   │   ├── image.py      # Pillow placeholder (Sprint 3'te Replicate)
│   │   │   └── video.py      # FFmpeg wrapper (Sprint 3)
│   │   ├── workers/
│   │   │   └── tasks.py      # Celery chain: story→audio→images
│   │   └── main.py
│   ├── alembic/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── jobs/[id]/page.tsx
│   │   └── trends/page.tsx
│   ├── components/ui/
│   │   └── TopicForm.tsx
│   └── package.json
│
├── docker-compose.yml
├── .gitignore
├── README.md
└── CLAUDE.md
```

---

## 8. Sprint Planı ve Görev Dağılımı

---

### ✅ Sprint 1 — Proje İskeleti + API Entegrasyonları
**Hafta 1–2 | TAMAMLANDI**

#### Kişi A (Backend) ✅
- [x] Docker Compose: FastAPI + Redis + Celery
- [x] FastAPI proje yapısı
- [x] Groq API + Llama 3.3 70B metin üretimi
- [x] `/api/jobs` POST endpoint → Celery task enqueue
- [x] Celery worker + Redis bağlantısı
- [x] `generate_story` Celery task'i

#### Kişi B (Frontend + DB) ✅
- [x] Next.js 14 + Tailwind + shadcn/ui
- [x] `TopicForm.tsx` konu girişi formu
- [x] FastAPI'ye POST isteği
- [x] SQLite schema + Alembic migration

#### Kararlar
- Ollama → Groq API (local model çok ağır)
- Kokoro TTS → gTTS (ElevenLabs free tier devre dışı)
- Stable Diffusion local → placeholder (Sprint 3'te Replicate)
- Redis host portu 6380 (6379 başka projede)

---

### ✅ Sprint 2 — TTS + Görsel + Pipeline Chain
**Hafta 3–4 | TAMAMLANDI**

#### Kişi A (Backend) ✅
- [x] gTTS entegrasyonu (`tts.py`)
- [x] Pillow placeholder görsel üretimi (`image.py`)
- [x] Celery `chain()`: `generate_story` → `generate_audio` → `generate_images`
- [x] Her adımda job status güncelleme
- [x] SSE stream endpoint (`/jobs/{id}/stream`)
- [x] Dosya download endpoint'leri (`/files`, `/download/audio`, `/download/images/{f}`)
- [x] Docker named volume (`outputs_data`) — api/worker shared storage
- [x] `/files` endpoint bug fix

#### Kişi B (Frontend) — Devam ediyor
- [ ] Job durumu polling (React Query)
- [ ] Progress bar + adım göstergesi
- [ ] Ses önizleme player
- [ ] Görseller grid view
- [ ] Job detay sayfası (`/jobs/[id]`)

#### Sprint 2 Sonu Kriterleri ✅ (Backend)
- `POST /api/jobs` → Celery chain başlar
- `text → audio → images` sırayla çalışır
- `status: completed` görünür
- `/files` endpoint audio + 3 görsel URL döner
- Download endpoint'leri çalışır

#### Kararlar
- HuggingFace SDXL → kaldırıldı (410 Gone)
- FLUX.1-schnell → kaldırıldı (410 Gone)
- Pollinations.ai → API key zorunlu (401)
- Google Gemini Image → free tier quota 0 (bölgesel)
- **Sprint 3'te Replicate API ile gerçek görsel ($0.003/img)**

---

### 🔄 Sprint 3 — Video Assembly + MinIO + Gerçek Görseller
**Hafta 5–6 | Hedef: İlk tam video — uçtan uca çalışır, indirilebilir**

#### Kişi A (Backend)
- [ ] Replicate API entegrasyonu (SDXL/Flux) — gerçek AI görseller
- [ ] FFmpeg: görseller → slideshow video (her görsel ~5 sn)
- [ ] Ses + video sync (duration matching)
- [ ] Pipeline'a `assemble_video` Celery task'i ekleme
- [ ] MinIO Docker servisi + bucket yapısı
- [ ] Tüm dosyaların MinIO'ya upload

#### Kişi B (Frontend)
- [ ] MinIO presigned URL ile video player
- [ ] SSE ile gerçek zamanlı job takibi
- [ ] Video indirme butonu
- [ ] Geçmiş işler listesi (`/jobs`)

#### Sprint 3 Sonu Kriterleri (MVP)
- Uçtan uca tam video (AI görsel + ses + müzik) üretilir
- Video dashboard'da izlenir ve indirilir
- **Bu sprint tamamlanmadan Sprint 4'e geçilmez**

---

### 📋 Sprint 4 — Kalite + Efekt Katmanı
**Hafta 7–8**

#### Kişi A
- [ ] FFmpeg geçiş animasyonları (fade, dissolve)
- [ ] Arka plan müziği ekleme
- [ ] Prompt mühendisliği iyileştirme
- [ ] Pipeline retry mekanizması

#### Kişi B
- [ ] Ayar paneli (efekt, ses seviyesi)
- [ ] Hata durumu UI'ları
- [ ] Loading skeleton'lar
- [ ] Mobil responsive

---

### 📋 Sprint 5 — Google Trends + Otomasyon
**Hafta 9–10**

#### Kişi A
- [ ] pytrends entegrasyonu
- [ ] APScheduler otomatik pipeline
- [ ] Topic skorlama algoritması

#### Kişi B
- [ ] Trend dashboard (`/trends`)
- [ ] Zamanlama ayarları UI
- [ ] Otomatik / manuel mod toggle

---

### 📋 Sprint 6 — YouTube Upload + Monitoring
**Hafta 11–12**

#### Kişi A
- [ ] YouTube Data API OAuth2
- [ ] Otomatik title/description üretimi
- [ ] SQLite → PostgreSQL migration

#### Kişi B
- [ ] YouTube kanal bağlama sayfası
- [ ] Upload geçmişi ekranı
- [ ] Genel polish + bug fix

---

## 9. Geliştirme Kuralları

### Git workflow
- `main` branch korumalı — direkt push yasak
- Feature branch: `feature/sprint3-replicate-images`
- Commit formatı: `feat(backend): Replicate API görsel üretimi`
- Her sprint sonunda tag: `v0.1.0`, `v0.2.0` ...

### WIP limiti
- "Yapılıyor" kolonunda max 2 kart
- Bloklu kart varsa önce o çözülür

---

## 10. Riskler ve Notlar

| Risk | Olasılık | Etki | Önlem |
|---|---|---|---|
| Replicate görsel kalitesi | Düşük | Orta | SDXL veya Flux modeli seç |
| gTTS Türkçe kalitesi robotik | Yüksek | Orta | Sprint 4'te OpenAI TTS ile değiştir |
| FFmpeg sync sorunları | Düşük | Orta | Ses süresini temel al |
| Sprint 3 gecikmesi | Orta | Yüksek | Video efekti Sprint 4'e atılabilir |
| MinIO kurulum karmaşıklığı | Orta | Düşük | Önce local filesystem, sonra MinIO |

---

*Son güncelleme: Sprint 2 tamamlandı (Backend) — 28 Mart 2026*
*Sonraki güncelleme: Sprint 2 Frontend + Sprint 3 başlangıcında*
