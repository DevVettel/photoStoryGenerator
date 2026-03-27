# CLAUDE.md — PhotoStory YT Video Generator

> Bu dosya projenin tek kaynak of truth'udur. Tech stack, mimari kararlar, veritabanı şeması, sprint planı ve görev dağılımları burada yaşar. Her sprint başında güncellenir.

---

## 1. Proje Özeti

**PhotoStory**, bir konuyu alıp uçtan uca YouTube videosu üreten, tamamen open-source ve locally çalışan bir AI pipeline sistemidir.

```
Konu girişi
  → LLM ile hikaye/metin üretimi
  → TTS ile seslendirme
  → Stable Diffusion ile görsel üretimi (min 3)
  → FFmpeg ile video assembly
  → Ses + görsel + efektlerle birleşik MP4 çıktısı
```

İleride Google Trends entegrasyonu ile viral konu tespiti ve YouTube'a otomatik upload desteği eklenecektir.

**Ekip:** 2 kişi  
**Sprint süresi:** 2 hafta  
**Toplam planlı sprint:** 6 (12 hafta)  
**Deployment hedefi:** Local (geliştirme), cloud migration Sprint 6 sonrasında değerlendirilecek

---

## 2. Tech Stack

### 2.1 Frontend

| Katman | Teknoloji | Sürüm | Açıklama |
|---|---|---|---|
| Framework | Next.js | 14 (App Router) | SSR + API routes, ileriki server-side iş mantığı için |
| UI Kit | shadcn/ui + Tailwind CSS | latest | Hızlı komponent geliştirme |
| State | Zustand | latest | Client-side global state |
| Async data | React Query (TanStack) | v5 | Server state, polling, cache |
| Real-time | Server-Sent Events (SSE) | — | Job durum güncellemeleri |

### 2.2 Backend

| Katman | Teknoloji | Sürüm | Açıklama |
|---|---|---|---|
| API | FastAPI | latest | Async REST + SSE endpoint'leri |
| Task queue | Celery | latest | AI pipeline adımlarını async çalıştırır |
| Message broker | Redis | 7 | Celery broker + job durum cache |
| ORM | SQLAlchemy + Alembic | latest | DB erişimi + migration yönetimi |
| DB (dev) | SQLite | — | Geliştirme ortamı |
| DB (prod) | PostgreSQL | 16 | Sprint 6 sonrası geçiş |

### 2.3 AI Pipeline

| Adım | Teknoloji | Açıklama |
|---|---|---|
| Metin üretimi | Ollama + Llama 3.1 / Mistral | Konu → hikaye/senaryo metni |
| Ses sentezi | Kokoro TTS | Metin → .wav ses dosyası (ücretsiz, local) |
| Görsel üretimi | Stable Diffusion (AUTOMATIC1111 API) | Metin → min 3 görsel |
| Video assembly | FFmpeg | Görseller + ses + efektler → .mp4 |

> **Not:** Görsel kalitesi yetersiz kalırsa geçici olarak Replicate API (SDXL) kullanılabilir — backend'de provider soyutlaması yapılacak.

### 2.4 Storage

| Katman | Teknoloji | Açıklama |
|---|---|---|
| Dosya depolama | MinIO | Local S3-uyumlu object storage |
| Bucket yapısı | `audio/`, `images/`, `videos/` | Job ID prefix ile organize |
| Cloud geçişi | AWS S3 / GCS | Sadece endpoint değişimi gerekir |

### 2.5 DevOps

| Katman | Teknoloji | Açıklama |
|---|---|---|
| Konteynerizasyon | Docker + Docker Compose | Tüm servisler tek komutla ayağa kalkar |
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
│   Broker + cache    │    │     Async task runner     │
└─────────────────────┘    └──────────┬───────────────┘
                                      │ task chain
           ┌──────────────────────────▼───────────────────────────┐
           │                   AI Pipeline (sıralı)                │
           │                                                       │
           │  ① Metin       ② Ses          ③ Görseller  ④ Video  │
           │  Ollama    →  Kokoro TTS  →  Stable Diff  →  FFmpeg  │
           │  Llama 3.1                   (min 3 img)             │
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
- **Dosyalar:** MinIO presigned URL ile frontend'e servis edilir

### 3.2 Job Yaşam Döngüsü

```
PENDING → RUNNING (metin) → RUNNING (ses) → RUNNING (görseller) → RUNNING (video) → COMPLETED
                                                                                   → FAILED
```

---

## 4. Veritabanı Mimarisi

### 4.1 Tablolar

#### `jobs`
```sql
CREATE TABLE jobs (
    id          TEXT PRIMARY KEY,        -- UUID
    topic       TEXT NOT NULL,           -- Kullanıcının girdiği konu
    language    TEXT DEFAULT 'tr',       -- 'tr' | 'en'
    status      TEXT DEFAULT 'pending',  -- pending | running | completed | failed
    current_step TEXT,                   -- text | audio | images | video
    error_msg   TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
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

#### `prompts` (Sprint 1)
```sql
CREATE TABLE prompts (
    id          TEXT PRIMARY KEY,
    job_id      TEXT NOT NULL REFERENCES jobs(id),
    step        TEXT NOT NULL,           -- 'story' | 'image_1' | 'image_2' | 'image_3'
    prompt_text TEXT NOT NULL,
    model_used  TEXT NOT NULL,           -- 'llama3.1' | 'mistral' vs.
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### `trends` (Sprint 5)
```sql
CREATE TABLE trends (
    id          TEXT PRIMARY KEY,
    topic       TEXT NOT NULL,
    score       REAL,                    -- Trend skoru
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

## 5. Sprint Planı ve Görev Dağılımı

> Renk kodları: 🟣 Sprint 1 · 🟢 Sprint 2 · 🟡 Sprint 3 · 🔴 Sprint 4 · 🔵 Sprint 5 · 🟩 Sprint 6

---

### Sprint 1 — Proje İskeleti + Local AI Kurulumu
**Hafta 1–2 | Hedef: Konu gir → Llama 3 metin üretsin → response gel**

#### Kişi A (Backend)
- [ ] Docker Compose: FastAPI + Redis + Celery servisleri
- [ ] FastAPI proje yapısı (`routers/`, `models/`, `services/`, `workers/`)
- [ ] Ollama kurulum + Llama 3.1 model pull
- [ ] `/api/jobs` POST endpoint → Celery task enqueue
- [ ] Celery worker temel konfigürasyonu + Redis bağlantısı
- [ ] Metin üretimi Celery task'i (`generate_story`)

#### Kişi B (Frontend + DB)
- [ ] Next.js 14 init + Tailwind CSS + shadcn/ui kurulum
- [ ] Konu girişi formu komponenti (dil seçimi dahil)
- [ ] FastAPI'ye POST isteği + response gösterimi
- [ ] SQLite schema: `jobs`, `outputs`, `prompts` tabloları
- [ ] Alembic migration setup + ilk migration

#### Sprint 1 Sonu Kriterleri
- `POST /api/jobs {"topic": "Mars kolonisi", "language": "tr"}` çalışır
- Celery task kuyruğa girer, Llama 3.1 metin üretir
- Frontend formu submit eder, job ID alır

---

### Sprint 2 — TTS + Görsel Üretimi
**Hafta 3–4 | Hedef: Pipeline çalışsın, ses çalınsın, görseller görünsün**

#### Kişi A (Backend)
- [ ] Kokoro TTS kurulum + Python wrapper servisi
- [ ] Stable Diffusion AUTOMATIC1111 API bağlantısı
- [ ] Celery `chain()`: `generate_story` → `generate_audio` → `generate_images`
- [ ] Her adımda job status güncelleme (Redis cache + SQLite)
- [ ] Minimum 3 görsel için ayrı prompt üretimi mantığı

#### Kişi B (Frontend)
- [ ] Job durumu polling (2 sn interval, React Query)
- [ ] Progress bar + adım göstergesi (metin / ses / görseller / video)
- [ ] Ses dosyası önizleme player komponenti
- [ ] Görseller grid view + lightbox (MinIO presigned URL)
- [ ] SSE altyapısı hazırlığı (polling'den geçiş için)

#### Sprint 2 Sonu Kriterleri
- Pipeline metin → ses → 3 görsel üretir
- Dashboard'da ses çalar, görseller görünür
- Job status ekranda canlı güncellenir

---

### Sprint 3 — Video Assembly + MinIO
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
- [ ] Job detay sayfası (`/jobs/[id]`)

#### Sprint 3 Sonu Kriterleri (MVP)
- Uçtan uca tam video üretimi çalışır
- Video dashboard'da izlenir ve indirilir
- **Bu sprint tamamlanmadan Sprint 4'e geçilmez**

---

### Sprint 4 — Kalite + Efekt Katmanı
**Hafta 7–8 | Hedef: Videolar efektlerle zenginleşmiş, production-ready**

#### Kişi A (Backend)
- [ ] FFmpeg: geçiş animasyonları (fade, dissolve)
- [ ] FFmpeg: arka plan müziği ekleme (ses seviyesi ayarı)
- [ ] FFmpeg: ses efektleri (intro/outro)
- [ ] Prompt mühendisliği iyileştirme (görsel kalitesi için)
- [ ] Pipeline hata yönetimi + retry mekanizması

#### Kişi B (Frontend)
- [ ] Ayar paneli: ses seviyesi, geçiş efekti seçimi, video süresi
- [ ] Hata durumu UI'ları (failed job, retry butonu)
- [ ] Loading skeleton'lar ve animasyonlar
- [ ] Mobil responsive düzenleme
- [ ] Genel UI polish turu

#### Sprint 4 Sonu Kriterleri
- Videolar geçiş animasyonu ve müzikle çıkar
- Kullanıcı efekt ayarlarını değiştirebilir
- Hata durumları kullanıcıya açıkça gösterilir

---

### Sprint 5 — Google Trends + Otomasyon
**Hafta 9–10 | Hedef: Sistem trending topic'leri alıp otomatik video üretsin**

#### Kişi A (Backend)
- [ ] `pytrends` ile Google Trends API entegrasyonu
- [ ] Günlük trend çekme + `trends` tablosuna kayıt
- [ ] Topic skorlama ve filtreleme algoritması
- [ ] APScheduler ile zamanlanmış pipeline tetikleme
- [ ] Otomatik mod / manuel mod ayrımı

#### Kişi B (Frontend)
- [ ] Trend dashboard sayfası (`/trends`)
- [ ] Trending topic listesi + skor görünümü
- [ ] Zamanlama ayarları UI (günde kaç video, saat)
- [ ] Otomatik / manuel mod toggle
- [ ] Toplu job durumu görünümü

#### Sprint 5 Sonu Kriterleri
- Sistem trending topic'leri çeker ve listeler
- Zamanlama ayarlandığında otomatik video üretimi başlar

---

### Sprint 6 — YouTube Upload + Monitoring
**Hafta 11–12 | Hedef: Trending topic → video → YouTube upload, tamamen otomatik**

#### Kişi A (Backend)
- [ ] YouTube Data API v3 OAuth2 kurulumu
- [ ] Otomatik title + description + tag üretimi (LLM ile)
- [ ] Video upload servisi + upload queue
- [ ] Upload retry mekanizması
- [ ] SQLite → PostgreSQL migration (Alembic)

#### Kişi B (Frontend)
- [ ] YouTube kanal bağlama sayfası (OAuth flow)
- [ ] Upload geçmişi + YouTube performans ekranı
- [ ] Kanal ayarları (varsayılan kategori, gizlilik)
- [ ] Genel bug fix + polish turu
- [ ] Kullanıcı dokümantasyonu (README güncelleme)

#### Sprint 6 Sonu Kriterleri
- Sistem trending topic → video → YouTube upload zincirini otomatik tamamlar
- PostgreSQL'e geçiş sorunsuz çalışır

---

## 6. Dizin Yapısı

```
photostory/
├── backend/
│   ├── app/
│   │   ├── routers/         # FastAPI route'ları
│   │   │   ├── jobs.py
│   │   │   └── trends.py
│   │   ├── models/          # SQLAlchemy modelleri
│   │   │   └── job.py
│   │   ├── services/        # İş mantığı
│   │   │   ├── llm.py       # Ollama wrapper
│   │   │   ├── tts.py       # Kokoro wrapper
│   │   │   ├── image.py     # SD wrapper
│   │   │   ├── video.py     # FFmpeg wrapper
│   │   │   └── storage.py   # MinIO wrapper
│   │   ├── workers/
│   │   │   └── tasks.py     # Celery task chain
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Ana sayfa (konu girişi)
│   │   ├── jobs/
│   │   │   ├── page.tsx     # Job listesi
│   │   │   └── [id]/
│   │   │       └── page.tsx # Job detay + önizleme
│   │   └── trends/
│   │       └── page.tsx     # Trend dashboard
│   ├── components/
│   ├── lib/
│   └── package.json
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── CLAUDE.md                # Bu dosya
```

---

## 7. Environment Variables

```bash
# .env.example

# FastAPI
SECRET_KEY=changeme
DEBUG=true

# Database
DATABASE_URL=sqlite:///./photostory.db
# Sprint 6: DATABASE_URL=postgresql://user:pass@localhost/photostory

# Redis
REDIS_URL=redis://localhost:6379/0

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# Stable Diffusion
SD_API_URL=http://localhost:7860
SD_STEPS=20
SD_CFG_SCALE=7

# Kokoro TTS
KOKORO_MODEL_PATH=./models/kokoro

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=photostory

# Sprint 5+
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
TRENDS_REGION=TR
TRENDS_SCHEDULE_HOUR=9
```

---

## 8. Docker Compose Servisleri

```yaml
# docker-compose.yml (özet)
services:
  api:          # FastAPI — port 8000
  worker:       # Celery worker
  redis:        # Redis — port 6379
  minio:        # MinIO — port 9000 (API), 9001 (console)
  ollama:       # Ollama — port 11434
  sd:           # Stable Diffusion AUTOMATIC1111 — port 7860
  frontend:     # Next.js — port 3000
```

Tüm servisler `docker-compose up -d` ile ayağa kalkar.

---

## 9. Geliştirme Kuralları

### Git workflow
- `main` branch'i korumalı — direkt push yasak
- Feature branch: `feature/sprint1-api-setup`
- Commit mesajı formatı: `feat(backend): add Celery task chain`
- Her sprint sonunda `main`'e merge + tag (`v0.1.0`, `v0.2.0` ...)

### Code review
- Her PR en az 1 approval gerektirir
- Sprint içi küçük fix'ler approve olmadan merge edilebilir
- Büyük mimari değişiklikler önce bu dosyada belgelenir

### WIP limiti
- "Yapılıyor" kolonunda maksimum 2 kart
- Bloklu kart varsa önce o çözülür, yeni kart alınmaz

### Test zorunluluğu
- Backend servis katmanı: birim test zorunlu
- API endpoint'leri: entegrasyon test zorunlu
- Frontend: kritik flow'lar için Vitest testi

---

## 10. Riskler ve Notlar

| Risk | Olasılık | Etki | Önlem |
|---|---|---|---|
| SD görsel kalitesi düşük | Orta | Orta | Replicate API fallback hazır tut |
| Kokoro TTS Türkçe kalitesi | Yüksek | Yüksek | Sprint 2'de erken test et, gerekirse Coqui TTS dene |
| Celery task chain hata yönetimi | Orta | Yüksek | Her task'e retry + dead letter queue ekle |
| FFmpeg sync sorunları | Düşük | Orta | Ses süresini temel al, görselleri buna göre uzat |
| Sprint 3 gecikmesi | Orta | Yüksek | Sprint 3 MVP'dir — efekt özelliği Sprint 4'e atılabilir |

---

*Son güncelleme: Sprint 0 — Mimari ve planlama aşaması*  
*Sonraki güncelleme: Sprint 1 tamamlandığında*
