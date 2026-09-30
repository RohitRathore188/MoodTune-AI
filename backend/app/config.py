"""MoodTune AI Application Configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "MoodTune AI"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security & DB
    SECRET_KEY: str = "moodtune-dev-insecure-secret-key-change-in-prod"
    DATABASE_URL: str = "sqlite+aiosqlite:///./moodtune.db"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    # AI & Jev Provider (Phase 5)
    JEV_API_KEY: Optional[str] = Field(default=None, alias="TYPESAFE_API_KEY")
    JEV_BASE_URL: Optional[str] = None
    JEV_MODEL: str = "jev-latest"
    JEV_TIMEOUT: float = 3.0
    JEV_MAX_RETRIES: int = 2
    LLM_API_KEY: Optional[str] = None

    # Music Provider
    MUSIC_PROVIDER_TYPE: str = "local"  # "local", "spotify", etc.
    MUSIC_PROVIDER_API_KEY: Optional[str] = None
    MUSIC_PROVIDER_SECRET: Optional[str] = None

    # Confidence Thresholds
    CONFIDENCE_HIGH_THRESHOLD: float = 0.70
    CONFIDENCE_MEDIUM_THRESHOLD: float = 0.40
    # Decisions below CONFIDENCE_MEDIUM_THRESHOLD fall back to safe default recommendations

    # Temporal Smoothing & Stability (Phase 4)
    MOOD_WINDOW_SIZE: int = 5
    MOOD_MIN_STABLE_DURATION: float = 3.0
    MOOD_CHANGE_THRESHOLD: float = 0.25
    MOOD_CONFIDENCE_THRESHOLD: float = 0.60

    # Legacy/compatibility aliases
    SMOOTHING_WINDOW_SIZE: int = 5
    SMOOTHING_EMA_ALPHA: float = 0.35
    MINIMUM_STABLE_DURATION_SECONDS: float = 3.0
    HYSTERESIS_TRANSITION_THRESHOLD: float = 0.25

    # Music Transition Anti-Thrashing Guardrails
    MIN_PLAY_SECONDS_BEFORE_TRANSITION: int = 30
    FORCE_TRANSITION_PLAY_RATIO: float = 0.85
    MAX_RECENT_TRANSITIONS_PER_WINDOW: int = 3
    TRANSITION_COOLDOWN_SECONDS: float = 30.0
    COMPATIBILITY_THRESHOLD: float = 0.55

    # Recommendation Scoring Weights (Phase 6 - Configurable, experimental)
    REC_WEIGHT_MOOD_MATCH: float = 0.35
    REC_WEIGHT_ENERGY_MATCH: float = 0.25
    REC_WEIGHT_PREFERENCE_MATCH: float = 0.20
    REC_WEIGHT_DIVERSITY: float = 0.10
    REC_WEIGHT_FRESHNESS: float = 0.10
    REC_PENALTY_RECENT_SKIP: float = 0.30

    # Privacy Controls
    STORE_RAW_FRAMES: bool = False  # Hard default: NEVER store raw webcam frames
    RETENTION_DAYS_MOOD_HISTORY: int = 7

    # Rate Limiting & Admin Security
    RATE_LIMIT_REQUESTS_PER_SECOND: int = 10
    ADMIN_TOKEN: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        # Guardrail: Never allow insecure default secret key in production
        if self.ENVIRONMENT.lower() == "production":
            if self.SECRET_KEY == "moodtune-dev-insecure-secret-key-change-in-prod" or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "Production deployment requires a secure, high-entropy SECRET_KEY with at least 32 characters."
                )

        # Guardrail: Prohibit wildcard CORS origin when credentials are enabled
        if "*" in self.CORS_ORIGINS:
            # Filter out wildcard to avoid credentialed CORS exploit/browser reject
            self.CORS_ORIGINS = [orig for orig in self.CORS_ORIGINS if orig != "*"]
            if not self.CORS_ORIGINS:
                self.CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

        return self


settings = Settings()
