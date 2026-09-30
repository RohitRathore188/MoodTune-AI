"""Observability & Telemetry Schemas."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class LatencyStats(BaseModel):
    cv_inference_ms: float = 0.0
    temporal_smoothing_ms: float = 0.0
    jev_decision_ms: float = 0.0
    recommendation_scoring_ms: float = 0.0
    total_pipeline_ms: float = 0.0


class SystemHealthMetrics(BaseModel):
    uptime_seconds: float
    total_frames_analyzed: int
    faces_detected_count: int
    jev_calls_count: int
    fallback_decisions_count: int
    songs_played_count: int
    songs_skipped_count: int
    skip_rate: float
    average_mood_stability_duration_sec: float
    current_mood: str
    latencies: LatencyStats
    active_music_provider: str


class AuditLogItem(BaseModel):
    timestamp: float
    event_type: str
    summary: str
    details: Dict[str, str] = Field(default_factory=dict)
