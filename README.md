# MoodTune AI — "Your mood. Your music."

MoodTune AI is a production-grade, privacy-first intelligent music recommendation and playback system.

It estimates visible facial expressions via webcam, applies temporal smoothing with exponential moving average (EMA) and hysteresis, consults a bounded AI decision layer (**Jev** / TypeSafe AI System One with calibrated deterministic fallback), and dynamically curates tracks from a decoupled music provider while learning non-sensitive personalization signals.

---

## Core Architectural Philosophy

```
  ┌─────────────────────────────────────────────────────────────┐
  │                 LLM creates/reasons                         │
  │                     Jev decides                             │
  │                      Code acts                              │
  └─────────────────────────────────────────────────────────────┘
```

1. **Computer Vision / ML Service**:
   - Detects face and estimates facial expression probabilities (`happy`, `neutral`, `surprise`, `sad`, `angry`, `fear`, `disgust`).
   - Uses OpenCV Haar cascade classifiers (`haarcascade_frontalface_default.xml`, `haarcascade_smile.xml`, `haarcascade_eye.xml`) stored locally.
   - **Strict Privacy**: Camera frames are processed strictly in RAM and immediately discarded. Never persisted to disk or database.

2. **Temporal Smoothing & Hysteresis Engine**:
   - Rolling window buffer (size = 7) and Exponential Moving Average (`alpha = 0.35`).
   - Minimum stable duration threshold (3.0s) and hysteresis margin (`0.25`) to prevent rapid flipping or noise spikes.
   - Maps affect distributions into controlled mood classes: `energetic`, `positive`, `calm`, `neutral`, `reflective`, `low_energy`, `tense`.

3. **Jev Bounded Decision Layer**:
   - Native integration with **TypeSafe AI's System One** Python SDK (`typesafe-sdk`).
   - Typed questions: `Choice` (mood, strategy, transition action) and `Score` (energy level).
   - High calibration: Confidence tiers (**HIGH**, **MEDIUM**, **LOW**) dictate recommendation escalation.
   - Resilient Fallback Engine: Deterministic Bayesian/heuristic decision rules guarantee zero downtime when offline or when no `TYPESAFE_API_KEY` is provided.

4. **Music Provider & Recommendation Engine**:
   - `BaseMusicProvider` abstraction decoupling third-party services from application code.
   - Built-in `LocalMusicProvider` with rich multi-genre catalog (`synthwave`, `upbeat_pop`, `ambient`, `lofi`, `meditation`, `indie_folk`, `classical`).
   - Multi-factor candidate ranking (acoustic distance, genre compatibility, personalization affinity, exploration factor).
   - Anti-thrashing guardrails holding transitions until songs reach minimum duration (30s) or completion.

5. **Personalization Engine**:
   - Learns from explicit (`like`, `dislike`) and implicit (`skip`, `complete`) listening signals.
   - Adapts genre affinities and mood-genre affinity matrices.

6. **Bounded Agent Contracts**:
   - `MoodAnalysisAgent`: Affect probabilities + temporal context → `MoodProposal`.
   - `MusicRecommendationAgent`: Mood state + music profile + user preferences → `MusicRecommendationProposal`.
   - `PlaylistAgent`: Anti-thrashing validation & queue sequencing → `PlaylistProposal`.
   - `PersonalizationAgent`: Interaction signals → `PersonalizationProposal`.
   - `EvaluationAgent`: End-to-end latency budget audit & skip-rate monitoring → `EvaluationProposal`.

---

## Human-Centered Principles

- **Affect is only an Estimate**: The application always uses careful human-centered language:
  - *"Detected expression"*
  - *"Estimated mood"*
  - *"Mood confidence"*
- Never claims to know a user's internal emotional truth.
- Manual mood override is permanently available on the main interface.

---

## Project Structure

```
MoodTune/
├── backend/
│   ├── app/
│   │   ├── config.py                  # Pydantic Settings & threshold configs
│   │   ├── database.py                # Async SQLite / SQLAlchemy session
│   │   ├── main.py                    # FastAPI entrypoint, CORS, routers
│   │   ├── models/models.py           # SQLAlchemy ORM entities
│   │   ├── schemas/                   # Pydantic v2 data models
│   │   ├── services/
│   │   │   ├── face_emotion_service.py       # OpenCV face & expression estimator
│   │   │   ├── temporal_smoothing_service.py # Rolling buffer, EMA, hysteresis
│   │   │   ├── jev_service.py                # Jev decision service + fallback
│   │   │   ├── music_provider.py             # MusicProvider interface & local catalog
│   │   │   ├── recommendation_engine.py      # Multi-factor ranking & transition policy
│   │   │   └── personalization_service.py    # Non-sensitive interaction learning
│   │   ├── agents/                           # 5 bounded agent contracts
│   │   └── api/v1/                           # Modular API endpoints
│   └── tests/                                # 16 automated Pytest tests
├── frontend/
│   ├── src/
│   │   ├── components/                # Glassmorphic UI components
│   │   ├── services/                  # Typed API & AudioEngine with Web Audio fallback
│   │   ├── types/                     # TypeScript shared interfaces
│   │   ├── App.tsx                    # Main interactive interface
│   │   └── index.css                  # Tailored glassmorphism styling
│   └── package.json
└── README.md
```

---

## Getting Started

### 1. Environment Variables
Create a `.env` file in `backend/`:
```env
JEV_API_KEY=your_typesafe_api_key_here
LLM_API_KEY=your_llm_api_key_here
DATABASE_URL=sqlite+aiosqlite:///./moodtune.db
MUSIC_PROVIDER_TYPE=local
```
*(If `JEV_API_KEY` is omitted, the system seamlessly uses its calibrated deterministic fallback engine.)*

### 2. Run Backend
```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
Health Check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 3. Run Backend Tests
```powershell
cd backend
python -m pytest tests -v
```

### 4. Run Frontend
```powershell
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.
