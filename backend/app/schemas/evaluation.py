"""Evaluation & Auditing Schemas (Phase 12: AI Evaluation Dashboard).

Adheres strictly to the human-centered mandate:
Visible affect metrics measure computer vision inference stability and temporal smoothing
performance only. They do NOT represent or prove that the AI understands the user's
internal emotional truth.

Clearly separates:
- MODEL PERFORMANCE (Emotion & Mood)
- RECOMMENDATION PERFORMANCE (Recommendation & Playback)
- SYSTEM PERFORMANCE (Jev, Fallbacks, API latency)
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from .metrics import LatencyStats


class ConfidenceDistribution(BaseModel):
    high: float = Field(default=0.0, description="Percentage of frames with confidence >= 0.70")
    medium: float = Field(default=0.0, description="Percentage of frames with confidence 0.40 - 0.69")
    low: float = Field(default=0.0, description="Percentage of frames with confidence < 0.40")
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0


class EmotionMetrics(BaseModel):
    inference_latency_ms: float = Field(default=0.0, description="Average CV emotion inference latency in ms")
    confidence_distribution: ConfidenceDistribution = Field(default_factory=ConfidenceDistribution)
    no_face_rate: float = Field(default=0.0, description="Ratio of frames with no face detected")
    total_frames: int = 0
    no_face_frames: int = 0


class MoodMetrics(BaseModel):
    stability_score: float = Field(default=1.0, description="Index of temporal stability (0.0 to 1.0)")
    average_stability_duration_sec: float = Field(default=0.0, description="Average seconds mood remains stable")
    transition_frequency_per_10m: float = Field(default=0.0, description="Transitions per 10 minutes")
    total_transitions: int = 0
    low_confidence_rate: float = Field(default=0.0, description="Rate of smoothed mood frames below confidence threshold")


class ModelPerformanceMetrics(BaseModel):
    emotion: EmotionMetrics = Field(default_factory=EmotionMetrics)
    mood: MoodMetrics = Field(default_factory=MoodMetrics)
    overall_model_health: str = "Optimal"


class RecommendationEngineMetrics(BaseModel):
    acceptance_rate: float = Field(default=0.0, description="Percentage of recommended candidates clicked/played")
    skip_rate: float = Field(default=0.0, description="Ratio of tracks skipped before 30 seconds")
    completion_rate: float = Field(default=0.0, description="Ratio of tracks played to completion")
    diversity_score: float = Field(default=0.85, description="Catalog diversity score (0.0 to 1.0)")
    total_recommendations_shown: int = 0
    total_recommendations_accepted: int = 0


class PlaybackMetrics(BaseModel):
    average_listening_duration_sec: float = Field(default=0.0, description="Average seconds listened per track")
    skip_frequency_per_10m: float = Field(default=0.0, description="Skip actions per 10 minutes")
    transition_frequency_per_10m: float = Field(default=0.0, description="Playback song transitions per 10 minutes")
    total_songs_played: int = 0
    total_songs_skipped: int = 0
    total_songs_completed: int = 0


class RecommendationPerformanceMetrics(BaseModel):
    recommendation: RecommendationEngineMetrics = Field(default_factory=RecommendationEngineMetrics)
    playback: PlaybackMetrics = Field(default_factory=PlaybackMetrics)
    overall_recommendation_health: str = "Optimal"


class SystemPerformanceMetrics(BaseModel):
    jev_latency_ms: float = Field(default=0.0, description="Average Jev decision latency in ms")
    jev_failures_count: int = Field(default=0, description="Count of Jev call timeouts or errors")
    jev_success_count: int = Field(default=0, description="Count of successful Jev bounded calls")
    fallback_frequency: float = Field(default=0.0, description="Percentage of decisions using deterministic fallback")
    fallback_count: int = 0
    api_failures_count: int = 0
    api_total_calls: int = 0
    api_failure_rate: float = 0.0
    latencies: LatencyStats = Field(default_factory=LatencyStats)
    system_uptime_seconds: float = 0.0
    overall_system_health: str = "Operational"


class EvaluationDashboardResponse(BaseModel):
    model_performance: ModelPerformanceMetrics
    recommendation_performance: RecommendationPerformanceMetrics
    system_performance: SystemPerformanceMetrics
    disclaimer: str = Field(
        default=(
            "Visible affect metrics measure computer vision inference stability and temporal smoothing performance only. "
            "They do NOT represent or prove that the AI understands the user's true internal emotional state."
        )
    )
    evaluation_timestamp: float
    health_verdict: str = "Healthy"
    actionable_recommendations: List[str] = Field(default_factory=list)
