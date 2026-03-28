# CLAUDE.md — PhotoStory YT Video Generator

> Bu dosya projenin tek kaynak of truth'udur. Tech stack, mimari kararlar, veritabanı şeması, sprint planı ve görev dağılımları burada yaşar. Her sprint başında güncellenir.

---

## 1. Proje Özeti

**PhotoStory**, bir konuyu alıp uçtan uca YouTube videosu üreten, tamamen API tabanlı bir AI pipeline sistemidir.

```
Konu girişi
  → Groq (Llama 3.3 70B) ile hikaye/metin üretimi
  → ElevenLabs ile seslendirme
  → HuggingFace (SDXL) ile görsel üretimi (min 3)
  → FFmpeg ile video assembly
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

### 2.3 AI Pipeline (API Tabanlı — GPU/Local Model Gerekmez)

| Adım | Servis | Model | Maliyet |
|---|---|---|---|
| Metin üretimi | Groq API | Llama 3.3 70B Versatile | Ücretsiz (30 req/dk) |
| Ses sentezi | ElevenLabs | Multilingual v2 | Ücretsiz (10K char/ay) |
| Görsel üretimi | HuggingFace Inference API | Stable Diffusion XL | Ücretsiz |
| Video assembly | FFmpeg (local binary) | — | Ücretsiz |

> **Mimari karar:** Local model yaklaşımı (Ollama, Stable Diffusion, Kokoro TTS) terk edildi.
> Sebep: GPU gerektiriyor, CPU'da çok yavaş, Docker image'ları çok büyük (~34GB toplam).
> API tabanlı yaklaşımla geliştirme hızlandı, sprint boyunca maliyet sıfıra yakın.

### 2.4 Storage

| Katman | Teknoloji | Açıklama |
|---|---|---|
| Dosya depolama | MinIO | Local S3-uyumlu object storage (Sprint 3'te eklenecek) |
| Bucket yapısı | `audio/`, `images/`, `videos/` | Job ID prefix ile organize |
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
           │  ① Metin      ② Ses          ③ Görseller  ④ Video   │
           │  Groq API → ElevenLabs  →  HuggingFace  →  FFmpeg   │
           │  Llama 3.3   Multilingual   SDXL                     │
           └──────────────────────────────────────────────────────┘
                  │ status updates                  │ file outputs
           ┌──────▼──────────┐           ┌──────────▼────────────┐
           │     SQLite      │           │        MinIO           │
           │  Job metadata   │           │  audio/ images/ video/ │
           └─────────────────┘           └───────────────────────┘

- - - - - - - - - - - Sprint 5+ - - - - - - - - - - - - - - - - -

   Google Trends  →  APScheduler  →  [Pipeline]  →  YouTube API
   (pytrends)        (cron job)                      (auto upload)
```

### 3.1 Servis İletişimi

- **Dashboard → FastAPI:** REST (POST /jobs, GET /jobs/{id})
- **FastAPI → Celery:** Redis broker üzerinden task enqueue
- **Celery → Dashboard:** SSE stream (FastAPI /jobs/{id}/stream endpoint'i)
- **Pipeline adımları:** Celery `chain()` ile sıralı, her adım öncekinin çıktısını alır
- **Dosyalar:** MinIO presigned URL ile frontend'e servis edilir (Sprint 3)

### 3.2 Job Yaşam Döngüsü

```
PENDING → RUNNING (text) → RUNNING (audio) → RUNNING (images) → RUNNING (video) → COMPLETED
                                                                                 → FAILED
```

---

## 4. Veritabanı Mimarisi

### 4.1 Tablolar

#### `jobs`
```sql
CREATE TABLE jobs (
    id           TEXT PRIMARY KEY,        -- UUID
    topic        TEXT NOT NULL,           -- Kullanıcının girdiği konu
    language     TEXT DEFAULT 'tr',       -- 'tr' | 'en'
    status       TEXT DEFAULT 'pending',  -- pending | running | completed | failed
    current_step TEXT,                    -- text | audio | images | video
    result_text  TEXT,                    -- Groq'tan gelen senaryo metni
    error_msg    TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `outputs`
```sql
CREATE TABLE outputs (
    id          TEXT PRIMARY KEY,        -- UUID
    job_id      TEXT NOT NULL REFERENCES jobs(id),
    type        TEXT NOT NULL,           -- 'text' | 'audio' | 'image' | 'video'
    storage_key TEXT NOT NULL,           -- MinIO object key
    metadata    TEXT,                    -- JSON (duration, resolution, prompt vs.)
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `prompts`
```sql
CREATE TABLE prompts (
    id          TEXT PRIMARY KEY,
    job_id      TEXT NOT NULL REFERENCES jobs(id),
    step        TEXT NOT NULL,           -- 'story' | 'image_1' | 'image_2' | 'image_3'
    prompt_text TEXT NOT NULL,
    model_used  TEXT NOT NULL,           -- 'llama-3.3-70b-versatile' vs.
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

### 4.2 İndeksler

```sql
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_outputs_job_id ON outputs(job_id);
CREATE INDEX idx_trends_fetched_at ON trends(fetched_at);
```

### 4.3 Migration Stratejisi

- Geliştirme: SQLite + Alembic migration'ları
- Sprint 6 öncesi: Alembic ile PostgreSQL'e geçiş (connection string değişimi yeterli)
- MinIO bucket yapısı: `{job_id}/audio/output.wav`, `{job_id}/images/img_1.png`, `{job_id}/video/final.mp4`

---

## 5. Environment Variables

```bash
# backend/.env (git'e gitmez — .gitignore'da)

DATABASE_URL=sqlite:///./photostory.db
REDIS_URL=redis://redis:6379/0
DEBUG=true

# Groq (ücretsiz) — https://console.groq.com
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# ElevenLabs (ücretsiz tier) — https://elevenlabs.io
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=pNInz6obpgDQGcFmaJgB

# HuggingFace (ücretsiz) — https://huggingface.co/settings/tokens
HUGGINGFACE_API_KEY=your_hf_api_key
HF_IMAGE_MODEL=stabilityai/stable-diffusion-xl-base-1.0

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
           # NOT: 6379 host portu fariva projesi tarafından kullanılıyor
```

Başlatmak için:
```bash
docker-compose up -d --build
```

---

## 7. Dizin Yapısı

```
photoStoryGenerator/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   └── jobs.py
│   │   ├── models/
│   │   │   └── job.py
│   │   ├── services/
│   │   │   ├── llm.py       # Groq wrapper
│   │   │   ├── tts.py       # ElevenLabs wrapper
│   │   │   ├── image.py     # HuggingFace wrapper
│   │   │   └── video.py     # FFmpeg wrapper (Sprint 3)
│   │   ├── workers/
│   │   │   └── tasks.py     # Celery task chain
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Ana sayfa (konu girişi)
│   │   ├── jobs/
│   │   │   ├── page.tsx      # Job listesi
│   │   │   └── [id]/
│   │   │       └── page.tsx  # Job detay + önizleme
│   │   └── trends/
│   │       └── page.tsx      # Trend dashboard (Sprint 5)
│   ├── components/
│   │   └── ui/
│   │       └── TopicForm.tsx
│   ├── lib/
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

#### Kişi A (Backend) — ✅
- [x] Docker Compose: FastAPI + Redis + Celery servisleri
- [x] FastAPI proje yapısı (`routers/`, `models/`, `services/`, `workers/`)
- [x] Groq API entegrasyonu + Llama 3.3 70B metin üretimi
- [x] `/api/jobs` POST endpoint → Celery task enqueue
- [x] Celery worker konfigürasyonu + Redis bağlantısı
- [x] `generate_story` Celery task'i
- [x] ElevenLabs TTS servisi (`tts.py`)
- [x] HuggingFace görsel servisi (`image.py`)

#### Kişi B (Frontend + DB) — ✅
- [x] Next.js 14 init + Tailwind CSS + shadcn/ui kurulum
- [x] `TopicForm.tsx` konu girişi formu (dil seçimi dahil)
- [x] FastAPI'ye POST isteği + job ID alma
- [x] SQLite schema: `jobs`, `outputs`, `prompts` tabloları
- [x] Alembic migration setup + ilk migration

#### Sprint 1 Sonu Kriterleri — ✅ Karşılandı
- `POST /api/jobs {"topic": "Mars kolonisi", "language": "tr"}` → `status: completed`
- Groq Llama 3.3 70B Türkçe senaryo üretiyor
- Frontend iskelet + form komponenti hazır
- Repo: https://github.com/DevVettel/photoStoryGenerator

#### Sprint 1 Notları
- Ollama (local LLM) → Groq API
- Kokoro TTS → ElevenLabs
- Stable Diffusion local → HuggingFace Inference API
- Redis host portu 6380 (6379 başka proje tarafından kullanılıyor)

---

### 🔄 Sprint 2 — TTS + Görsel Üretimi + Frontend Bağlantısı
**Hafta 3–4 | Hedef: Pipeline çalışsın, ses çalınsın, görseller görünsün**

#### Kişi A (Backend)
- [ ] ElevenLabs task'ini Celery chain'e ekle (`generate_audio`)
- [ ] HuggingFace görsel task'ini Celery chain'e ekle (`generate_images`)
- [ ] Celery `chain()`: `generate_story` → `generate_audio` → `generate_images`
- [ ] Her adımda job status güncelleme (SQLite)
- [ ] Üretilen dosyaları geçici olarak local filesystem'e kaydet

#### Kişi B (Frontend)
- [ ] Job durumu polling (2 sn interval, React Query)
- [ ] Progress bar + adım göstergesi (metin / ses / görseller / video)
- [ ] Ses dosyası önizleme player komponenti
- [ ] Görseller grid view + lightbox
- [ ] Job detay sayfası (`/jobs/[id]`)

#### Sprint 2 Sonu Kriterleri
- Pipeline metin → ses → 3 görsel üretir
- Dashboard'da ses çalar, görseller görünür
- Job status ekranda polling ile güncellenir

---

### 📋 Sprint 3 — Video Assembly + MinIO
**Hafta 5–6 | Hedef: İlk tam video — uçtan uca çalışır, indirilebilir**

#### Kişi A (Backend)
- [ ] FFmpeg: görseller → slideshow video (her görsel ~5 sn)
- [ ] Ses + video sync (duration matching)
- [ ] Pipeline'a `assemble_video` Celery task'i ekleme
- [ ] MinIO Docker servisi + bucket yapısı kurulumu
- [ ] Tüm dosyaların MinIO'ya upload mantığı

#### Kişi B (Frontend)
- [ ] MinIO presigned URL ile video stream player
- [ ] SSE ile gerçek zamanlı job takibine geçiş (polling kaldır)
- [ ] Video indirme butonu
- [ ] Geçmiş işler listesi sayfası (`/jobs`)

#### Sprint 3 Sonu Kriterleri (MVP)
- Uçtan uca tam video üretimi çalışır
- Video dashboard'da izlenir ve indirilir
- **Bu sprint tamamlanmadan Sprint 4'e geçilmez**

---

### 📋 Sprint 4 — Kalite + Efekt Katmanı
**Hafta 7–8 | Hedef: Videolar efektlerle zenginleşmiş, production-ready**

#### Kişi A (Backend)
- [ ] FFmpeg: geçiş animasyonları (fade, dissolve)
- [ ] FFmpeg: arka plan müziği ekleme
- [ ] Prompt mühendisliği iyileştirme
- [ ] Pipeline hata yönetimi + retry mekanizması

#### Kişi B (Frontend)
- [ ] Ayar paneli: ses seviyesi, geçiş efekti seçimi
- [ ] Hata durumu UI'ları (failed job, retry butonu)
- [ ] Loading skeleton'lar ve animasyonlar
- [ ] Mobil responsive düzenleme

---

### 📋 Sprint 5 — Google Trends + Otomasyon
**Hafta 9–10 | Hedef: Sistem trending topic'leri alıp otomatik video üretsin**

#### Kişi A (Backend)
- [ ] `pytrends` ile Google Trends API entegrasyonu
- [ ] Günlük trend çekme + `trends` tablosuna kayıt
- [ ] APScheduler ile zamanlanmış pipeline tetikleme
- [ ] Otomatik mod / manuel mod ayrımı

#### Kişi B (Frontend)
- [ ] Trend dashboard sayfası (`/trends`)
- [ ] Trending topic listesi + skor görünümü
- [ ] Zamanlama ayarları UI
- [ ] Otomatik / manuel mod toggle

---

### 📋 Sprint 6 — YouTube Upload + Monitoring
**Hafta 11–12 | Hedef: Trending topic → video → YouTube upload, tamamen otomatik**

#### Kişi A (Backend)
- [ ] YouTube Data API v3 OAuth2 kurulumu
- [ ] Otomatik title + description + tag üretimi (LLM ile)
- [ ] Video upload servisi + retry mekanizması
- [ ] SQLite → PostgreSQL migration

#### Kişi B (Frontend)
- [ ] YouTube kanal bağlama sayfası (OAuth flow)
- [ ] Upload geçmişi + performans ekranı
- [ ] Genel bug fix + polish turu

---

## 9. Geliştirme Kuralları

### Git workflow
- `main` branch'i korumalı — direkt push yasak
- Feature branch: `feature/sprint2-tts-pipeline`
- Commit mesajı formatı: `feat(backend): ElevenLabs TTS Celery chain'e eklendi`
- Her sprint sonunda `main`'e merge + tag (`v0.1.0`, `v0.2.0` ...)

### Code review
- Her PR en az 1 approval gerektirir
- Sprint içi küçük fix'ler approve olmadan merge edilebilir
- Büyük mimari değişiklikler önce bu dosyada belgelenir

### WIP limiti
- "Yapılıyor" kolonunda maksimum 2 kart
- Bloklu kart varsa önce o çözülür, yeni kart alınmaz

---

## 10. Riskler ve Notlar

| Risk | Olasılık | Etki | Önlem |
|---|---|---|---|
| ElevenLabs 10K char limiti dolması | Orta | Orta | OpenAI TTS fallback hazırla |
| HuggingFace model loading (503) | Yüksek | Düşük | Kodda 3x retry var, otomatik bekler |
| Celery task chain hata yönetimi | Orta | Yüksek | Her task'e retry + dead letter queue ekle |
| FFmpeg sync sorunları | Düşük | Orta | Ses süresini temel al, görselleri buna göre uzat |
| Sprint 3 gecikmesi | Orta | Yüksek | Sprint 3 MVP'dir — efekt özelliği Sprint 4'e atılabilir |

---

*Son güncelleme: Sprint 1 tamamlandı — 28 Mart 2026*
*Sonraki güncelleme: Sprint 2 tamamlandığında*
