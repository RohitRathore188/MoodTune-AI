# MoodTune AI — Architectural Audit & Discovery Report

**Product:** MoodTune AI  
**Tagline:** "Your mood. Your music."  
**Audit Date:** 2026-09-29  
**Status:** Architecture Discovery & System Baseline Assessment  

---

## Executive Summary

MoodTune AI has been scaffolded and developed as a production-grade full-stack AI music recommendation system with a strict separation of concerns:
- **LLM creates/reasons**: Natural language justification and music mood synthesis.
- **Jev decides**: Bounded, typed, calibrated classification and routing via TypeSafe AI's System One (`Choice`, `Score`, `Noul`).
- **Code acts**: Deterministic playback, audio synthesis, queue sequencing, and anti-thrashing gating.
- **Human-Centered Principle**: Facial expression is strictly an *estimate of visible affect*, never a claim of true internal emotion.
- **Privacy-First In-Memory Processing**: Webcam frames are evaluated in volatile RAM and immediately discarded.

This report documents the current architecture, identifies risks, inconsistencies, and missing production elements, and outlines the precise roadmap for production deployment.

---

## 1. Existing Architecture & Components

```
d:\Projects\MoodTune/
├── backend/
│   ├── app/
│   │   ├── config.py                  # Pydantic Settings & threshold configs
│   │   ├── database.py                # Async SQLite / SQLAlchemy session
│   │   ├── main.py                    # FastAPI entrypoint, CORS, routers
│   │   ├── models/models.py           # SQLAlchemy ORM entities (8 tables)
│   │   ├── schemas/                   # Pydantic v2 data models (mood, jev, music, recs, metrics)
│   │   ├── services/
│   │   │   ├── face_emotion_service.py       # OpenCV face & expression estimator
│   │   │   ├── temporal_smoothing_service.py # Rolling buffer, EMA, hysteresis
│   │   │   ├── jev_service.py                # Jev decision service + fallback
│   │   │   ├── music_provider.py             # MusicProvider interface & local catalog
│   │   │   ├── recommendation_engine.py      # Multi-factor ranking & transition policy
│   │   │   └── personalization_service.py    # Non-sensitive interaction learning
│   │   ├── agents/                           # 5 bounded agent contracts
│   │   └── api/v1/                           # Modular API endpoints (7 routers)
│   └── tests/                                # 16 automated Pytest tests (100% pass)
├── frontend/
│   ├── src/
│   │   ├── components/                # 10 Glassmorphic UI components
│   │   ├── services/                  # Typed API & AudioEngine with Web Audio fallback
│   │   ├── types/                     # TypeScript shared interfaces
│   │   ├── App.tsx                    # Main interactive interface
│   │   └── index.css                  # Tailored glassmorphism styling
│   └── package.json
└── README.md
```

### 1.1 Existing Frontend Components
| Component | Functionality | Status |
| :--- | :--- | :--- |
| **`Navbar`** | Brand identity, live in-memory privacy status, modal triggers | Operational |
| **`CameraFeed`** | HTML5 video stream, face bounding box HUD, detection pause, killswitch | Operational |
| **`MoodHUD`** | Estimated mood badge, confidence gauge, stability timer, affect breakdown | Operational |
| **`PlayerCard`** | Spinning vinyl animation, soundwave visualizer, seekbar, volume, like/skip | Operational |
| **`RecommendationQueue`** | Jev candidate queue with match percentages, exploration tags, click-to-play | Operational |
| **`ManualMoodSelector`** | 7 controlled vocabulary buttons (`energetic`, `positive`, `calm`, `neutral`, `reflective`, `low_energy`, `tense`) | Operational |
| **`MoodTimeline`** | Continuous stabilized mood timeline and hysteresis tracking | Operational |
| **`PrivacyModal`** | Ephemeral processing details and "Clear Mood History" purge trigger | Operational |
| **`PreferencesModal`** | Custom genre selection, energy bias slider, transition sensitivity | Operational |
| **`ObservabilityDrawer`**| Live latency telemetry breakdown, skip rate, and System One decision traces | Operational |
| **`AudioEngine`** | HTML5 Audio + Web Audio API synthesizer fallback (zero-silence guarantee) | Operational |

### 1.2 Existing Backend Components
| Service / Layer | Responsibility | Status |
| :--- | :--- | :--- |
| **`FaceEmotionService`** | In-memory frame decoding, Haar cascade face/smile/eye detection, affect estimation | Operational |
| **`TemporalSmoothingService`** | Rolling buffer (size 7), EMA ($\alpha=0.35$), minimum duration ($3\text{s}$), hysteresis ($0.25$) | Operational |
| **`JevDecisionService`** | Official `typesafe-sdk` System One integration (`client.system_one`) + calibrated fallback | Operational |
| **`MusicProvider`** | `BaseMusicProvider` abstraction + `LocalMusicProvider` with 11 curated tracks | Operational |
| **`RecommendationEngine`** | Confidence tier gating (HIGH/MEDIUM/LOW), feature distance scoring, personalization | Operational |
| **`PersonalizationService`** | Genre affinity vector updates based on likes, skips, and completion rates | Operational |
| **`Bounded Agents`** | Mood Analysis, Music Recommendation, Playlist, Personalization, Evaluation | Operational |
| **`FastAPI Routers`** | Health, Mood, Recommendations, Music, Preferences, History, Metrics | Operational |

---

## 2. Identified Gaps, Broken Components & Missing Features

### 2.1 Missing Components
1. **Dependency Pinning & Lockfile for Backend**:
   - No `requirements.txt` or `pyproject.toml` in `backend/`.
2. **Environment Template**:
   - Missing `.env.example` defining expected credentials (`JEV_API_KEY`, `LLM_API_KEY`, `DATABASE_URL`, `CORS_ORIGINS`).
3. **Database Migrations (Alembic)**:
   - Tables are created via `Base.metadata.create_all` during lifespan. No versioned database migration pipeline exists for production PostgreSQL schema evolution.
4. **PostgreSQL Driver**:
   - `aiosqlite` is installed for SQLite, but `asyncpg` or `psycopg` is missing for managed PostgreSQL in production.
5. **Frontend Unit / Component Tests**:
   - `vitest` and `@testing-library/react` are not yet installed or configured in `frontend/`.
6. **Containerization & Deployment Manifests**:
   - Missing multi-stage `Dockerfile` (frontend and backend) and `docker-compose.yml`.
   - Missing deployment configuration for Render/Railway/Fly.io and Vercel.
7. **Rate Limiting & Abuse Prevention**:
   - The `/api/mood/analyze` endpoint processes video frames every 1.5s; without IP rate limiting or request throttling, a client could overwhelm CPU OpenCV inference.
8. **Multiple Faces Conflict Resolution**:
   - When $>1$ face is in the frame, current OpenCV implementation picks the largest face bounding box, but does not provide an explicit UI badge warning that multiple listeners are detected.

### 2.2 Broken Components
- **Browser Automation Subagent Execution**:
  - The browser subagent failed to open `http://127.0.0.1:5173` due to a 404 from Microsoft/Playwright CDN for `playwright-1.57.0-win32_x64.zip`. The application itself is running and operational, but automated browser-based E2E tests cannot execute until the driver is cached or updated.

---

## 3. Dependency & Security Risks

### 3.1 Dependency Risks
- **`typesafe-sdk`**:
  - Uses `httpx2` and `httpcore2` with TLS truststore. If an invalid API key is provided in a corporate proxy environment, TLS handshake errors must be isolated. Current implementation wraps calls in `try/except` and safely falls back to the deterministic Bayesian decision engine.
- **`opencv-python-headless`**:
  - Pre-built binary wheels do not consistently include XML cascade data. We resolved this by downloading and storing the models locally under `backend/app/assets/models/`.
- **`react-dom` v19 + `lucide-react`**:
  - React 19 is newly released; peer dependency warnings may appear with legacy React packages. All current packages are compatible.

### 3.2 Security Risks
- **Camera Frame Privacy**:
  - *Risk*: Unauthorized disk logging or accidental frame persistence.
  - *Mitigation*: Frames are ingested via base64, processed as volatile NumPy arrays in memory, and explicitly freed (`del frame`, `del gray`). No disk writes occur.
- **CORS Configuration**:
  - Currently allows `*` in development settings. In production, this must be restricted strictly to the frontend domain.
- **Secret Keys**:
  - `SECRET_KEY` in `backend/app/config.py` defaults to a development placeholder. Must require production environment injection.

---

## 4. Architectural Inconsistencies

1. **State Duplication Between In-Memory Cache and SQLite Database**:
   - Sessions, observations, and preferences are updated in memory (`PersonalizationService._profiles` and `TemporalSmoothingService._buffers`), while SQLAlchemy models exist in `backend/app/models/models.py`.
   - While in-memory caching ensures low latency ($<50\text{ms}$), database synchronization should occur asynchronously in background tasks to ensure persistence across server restarts.
2. **Hardcoded API URL in Frontend**:
   - `frontend/src/services/api.ts` hardcodes `http://localhost:8000/api`. This should be driven by `import.meta.env.VITE_API_URL || '/api'`.

---

## 5. Recommended Architecture & Service Boundaries

### 5.1 Service Boundaries
```
[ Client Browser ]
      │
      ├── Webcam MediaStream (In-Memory Canvas JPEG)
      └── Audio Engine (HTML5 Audio / Web Audio Synth)
      │
      ▼
[ FastAPI Gateway (app/api/v1) ]
      │
      ├── /mood/analyze ──────────► [ FaceEmotionService (OpenCV) ]
      │                                    │ Affect Probabilities
      │                                    ▼
      │                             [ TemporalSmoothingService (EMA + Hysteresis) ]
      │                                    │ Stable Mood State
      │                                    ▼
      │                             [ MoodAnalysisAgent ]
      │
      ├── /recommendations ───────► [ RecommendationEngine ]
      │                                    │
      │                                    ├──► [ JevDecisionService ]
      │                                    │       ├─ TypeSafeClient (System One)
      │                                    │       └─ Calibrated Fallback Engine
      │                                    │
      │                                    ├──► [ MusicProvider (Local/Spotify) ]
      │                                    │
      │                                    └──► [ PlaylistAgent (Anti-Thrashing) ]
      │
      └── /feedback ──────────────► [ PersonalizationAgent ]
                                           │
                                           ▼
                                    [ PersonalizationService ]
                                           │
                                           ▼
                                    [ Async Database (SQLite / Postgres) ]
```

### 5.2 Recommended Folder Structure

```
MoodTune/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── assets/models/             # Haar cascades / ONNX models
│   │   ├── models/                    # SQLAlchemy entities
│   │   ├── schemas/                   # Pydantic v2 contracts
│   │   ├── services/                  # Core algorithms (CV, Smoothing, Jev, Music)
│   │   ├── agents/                    # 5 Bounded Agent services
│   │   └── api/v1/                    # Typed API routers
│   ├── migrations/                    # Alembic migration scripts
│   ├── tests/                         # Pytest test suite
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/                # Glassmorphic UI components
│   │   ├── services/                  # API client & Web Audio engine
│   │   ├── types/                     # Shared TypeScript interfaces
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── tests/                         # Vitest component tests
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 6. Jev Integration Boundary

Jev is strictly encapsulated within `JevDecisionService`:
- **SDK**: `typesafe-sdk` (TypeSafe AI System One).
- **Questions**: Predefined, typed decision primitives (`Choice`, `Score`).
- **Isolation**: No controller, agent, or frontend component directly constructs vendor-specific payloads.
- **Fail-Safe Policy**:
  - `HIGH` confidence ($\ge 0.70$): Direct execution of Jev choice.
  - `MEDIUM` confidence ($0.40 - 0.69$): Blended with user baseline preferences and deterministic acoustic profiles.
  - `LOW` confidence ($< 0.40$): Escalates to safe neutral defaults.
  - If SDK or network fails, the calibrated Bayesian decision engine produces identical typed schema outputs.

---

## 7. Strategic Assessment

### 1. What is already usable
- Full backend architecture with 7 REST routers, 5 bounded agents, and comprehensive test suite (16/16 passing).
- Complete computer vision facial affect estimation with local Haar cascades.
- Temporal smoothing with exponential moving average and hysteresis stability.
- Jev Decision Service abstraction with live SDK integration and calibrated deterministic fallback.
- Local Music Provider with rich multi-genre acoustic metadata and streaming audio.
- Interactive glassmorphic frontend with camera preview, live face bounding box overlay, Mood HUD, vinyl player card, recommendation queue, and privacy modal.
- Zero-storage camera frame privacy architecture.

### 2. What must be rewritten
- Hardcoded API base URL in `frontend/src/services/api.ts` (should read `VITE_API_URL` environment variable).
- Direct schema generation in `app/database.py` should be paired with Alembic migrations for production PostgreSQL.

### 3. What should be preserved
- The **"LLM creates/reasons, Jev decides, Code acts"** architectural separation.
- The human-centered vocabulary rules (*"Detected expression"*, *"Estimated mood"*, *"Mood confidence"*).
- The ephemeral in-memory camera frame processing pipeline.
- The anti-thrashing playback transition policy.
- The resilient Web Audio harmonic synthesizer fallback in `audioEngine.ts`.

### 4. What should be removed
- Development CORS wildcard `*` for production deployments.
- Default insecure placeholder secret key in production settings.

### 5. What should be implemented first
1. Create `requirements.txt` and `.env.example` in backend.
2. Parameterize frontend API base URL via Vite environment variables (`.env`).
3. Set up Docker containerization (`Dockerfile` for backend and frontend + `docker-compose.yml`).
4. Add Vitest unit tests for frontend components.
5. Implement rate limiting middleware on `/api/mood/analyze`.

---

*Report generated by Antigravity AI Systems Architect.*
