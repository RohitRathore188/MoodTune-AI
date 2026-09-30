# MoodTune AI — Phase 1 System Architecture Specification

## 1. Architectural Philosophy
MoodTune AI follows the core operating principle:
- **LLM creates/reasons**: Generates human-centered justifications and musical explanations.
- **Jev decides**: Performs bounded, typed, calibrated classification and routing via TypeSafe AI System One (`Choice`, `Score`, `Noul`).
- **Code acts**: Executes deterministic operations (playback, audio synthesis, queue management, anti-thrashing).
- **Human-Centered Principle**: Facial expression is strictly an *estimate of visible affect*, never a claim of internal emotional truth.
- **Privacy by Default**: Ephemeral in-memory frame processing in RAM; raw camera frames are discarded immediately after analysis.

## 2. Directory Layout
```
MoodTune/
├── backend/
│   ├── app/
│   │   ├── api/v1/health.py           # Health & diagnostic router
│   │   ├── config.py                  # Pydantic Settings & threshold management
│   │   ├── database.py                # Database connection & session factory
│   │   ├── main.py                    # FastAPI entrypoint, CORS, global error handling
│   │   ├── models/                    # ORM entities
│   │   ├── schemas/                   # Pydantic validation schemas
│   │   └── services/                  # Business logic services
│   ├── tests/                         # Pytest test suite
│   ├── requirements.txt               # Pinned Python dependencies
│   ├── pytest.ini                     # Pytest configuration
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/                # Glassmorphic UI components
│   │   ├── services/api.ts            # Typed API client with environment base URL
│   │   ├── types/                     # TypeScript definitions
│   │   ├── App.tsx                    # Main UI
│   │   └── main.tsx                   # Entrypoint
│   ├── tests/                         # Vitest component/unit tests
│   ├── vite.config.ts                 # Vite & Vitest configuration
│   ├── package.json
│   └── .env.example
├── docs/                              # Architecture and API documentation
├── tests/                             # Root end-to-end and integration tests
├── .env.example                       # Root environment template
└── README.md
```
