"""Music and Track Schemas."""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, model_validator


class MusicProfile(BaseModel):
    genre: str
    energy: float = Field(default=0.5, ge=0.0, le=1.0)
    valence: float = Field(default=0.5, ge=0.0, le=1.0)
    tempo: float = Field(default=0.5, ge=0.0)
    danceability: float = Field(default=0.5, ge=0.0, le=1.0)
    instrumental: float = Field(default=0.0, ge=0.0, le=1.0)
    mood_tags: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any):
        if isinstance(data, dict):
            # Handle boolean instrumental
            inst = data.get("instrumental", 0.0)
            if isinstance(inst, bool):
                data["instrumental"] = 1.0 if inst else 0.0
        return data


class Track(BaseModel):
    id: str
    title: str
    artist: str
    album: Optional[str] = "MoodTune Essentials"
    duration_seconds: int = 180
    audio_url: str
    cover_art_url: str
    profile: MusicProfile
    provider: str = "local"
    external_url: Optional[str] = None


class PlaybackState(BaseModel):
    current_track: Optional[Track] = None
    is_playing: bool = False
    position_seconds: float = 0.0
    volume: float = 0.8
    repeat_mode: str = "all"  # off, one, all
    shuffle: bool = False
    queue: List[Track] = Field(default_factory=list)
    manual_pause: bool = False
    last_transition_timestamp: Optional[float] = None


class TransitionDecisionResult(BaseModel):
    action: str  # "continue", "transition", "replenish_queue"
    reason: str
    current_track: Optional[Track] = None
    next_track: Optional[Track] = None
    compatibility_score: float = 1.0
    is_compatible: bool = True
    jev_decision: Optional[str] = None
    cooldown_remaining_seconds: float = 0.0
    transition_executed: bool = False


class UserPreferenceSchema(BaseModel):
    preferred_genres: List[str] = Field(default_factory=lambda: ["lofi", "ambient", "synthwave", "indie_folk"])
    preferred_energy_bias: float = Field(default=0.5, ge=0.0, le=1.0)
    transition_sensitivity: float = Field(default=0.6, ge=0.0, le=1.0)
    disliked_genres: List[str] = Field(default_factory=list)
    auto_play_on_mood_shift: bool = True


class UserPreferenceProfile(BaseModel):
    """User preference profile generated from non-sensitive interaction telemetry."""
    preferred_genres: List[str] = Field(default_factory=lambda: ["pop", "lofi"])
    preferred_energy: float = Field(default=0.50, ge=0.0, le=1.0)
    preferred_tempo: float = Field(default=0.50, ge=0.0)
    skip_rate_by_genre: Dict[str, float] = Field(default_factory=dict)
    disliked_genres: List[str] = Field(default_factory=list)
    total_played: int = 0
    total_skipped: int = 0
    total_completed: int = 0
    total_liked: int = 0
    total_disliked: int = 0
