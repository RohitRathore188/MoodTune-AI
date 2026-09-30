"""Unit tests for Temporal Smoothing & Hysteresis."""
import pytest
from app.services.temporal_smoothing_service import TemporalSmoothingService
from app.schemas.mood import EmotionProbabilities, MoodClass


def test_temporal_smoothing_hysteresis_and_duration():
    """Validates that rapid noisy fluctuations do NOT trigger mood transitions."""
    service = TemporalSmoothingService(
        window_size=5,
        ema_alpha=0.4,
        min_stable_duration=2.0,
        hysteresis_margin=0.25
    )
    session_id = "test_smoothing_session"

    # Frame 1 to 5: Consistent Happy
    happy_probs = EmotionProbabilities(happy=0.85, neutral=0.10)
    for i in range(5):
        state = service.smooth_observation(
            session_id=session_id,
            raw_probabilities=happy_probs,
            confidence=0.9,
            timestamp=100.0 + i * 0.5
        )

    assert state.estimated_mood == MoodClass.POSITIVE
    assert state.is_stable is True

    # Frame 6: Single isolated frame of surprise/neutral (noise)
    noisy_probs = EmotionProbabilities(happy=0.1, neutral=0.85)
    noisy_state = service.smooth_observation(
        session_id=session_id,
        raw_probabilities=noisy_probs,
        confidence=0.8,
        timestamp=102.5
    )
    # Hysteresis + min duration prevents immediate mood flip
    assert noisy_state.estimated_mood == MoodClass.POSITIVE
    assert noisy_state.transition_occurred is False

    # Persistent shift across duration >= 2.0 seconds
    for j in range(6):
        persisted_state = service.smooth_observation(
            session_id=session_id,
            raw_probabilities=noisy_probs,
            confidence=0.88,
            timestamp=103.0 + j * 0.5
        )

    # After sustaining for > 2.0s, transition is committed
    assert persisted_state.estimated_mood == MoodClass.NEUTRAL
    assert persisted_state.transition_occurred is True
