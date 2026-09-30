"""Temporal Smoothing and Mood Stability Service.
Applies:
- Rolling window buffer
- Exponential Moving Average (EMA)
- Minimum stable duration gating
- Hysteresis to prevent erratic jumping
"""
import time
import logging
from collections import deque
from typing import Dict, List, Optional, Tuple

from ..config import settings
from ..schemas.mood import MoodClass, MoodState, EmotionProbabilities

logger = logging.getLogger("moodtune.temporal_smoothing")


class TemporalSmoothingService:
    def __init__(
        self,
        window_size: int = settings.SMOOTHING_WINDOW_SIZE,
        ema_alpha: float = settings.SMOOTHING_EMA_ALPHA,
        min_stable_duration: float = settings.MINIMUM_STABLE_DURATION_SECONDS,
        hysteresis_margin: float = settings.HYSTERESIS_TRANSITION_THRESHOLD
    ):
        self.window_size = window_size
        self.ema_alpha = ema_alpha
        self.min_stable_duration = min_stable_duration
        self.hysteresis_margin = hysteresis_margin

        # Session-keyed state buffers
        self._buffers: Dict[str, deque] = {}
        self._ema_state: Dict[str, Dict[str, float]] = {}
        self._current_stable_mood: Dict[str, MoodClass] = {}
        self._stable_since: Dict[str, float] = {}
        self._candidate_mood: Dict[str, Optional[MoodClass]] = {}
        self._candidate_since: Dict[str, float] = {}
        self._history: Dict[str, List[dict]] = {}

    def reset_session(self, session_id: str):
        """Clears memory for a session (privacy control)."""
        self._buffers.pop(session_id, None)
        self._ema_state.pop(session_id, None)
        self._current_stable_mood.pop(session_id, None)
        self._stable_since.pop(session_id, None)
        self._candidate_mood.pop(session_id, None)
        self._candidate_since.pop(session_id, None)
        self._history.pop(session_id, None)
        logger.info(f"Cleared temporal smoothing state for session {session_id}")

    def smooth_observation(
        self,
        session_id: str,
        raw_probabilities: EmotionProbabilities,
        confidence: float,
        timestamp: Optional[float] = None,
        manual_override: Optional[MoodClass] = None
    ) -> MoodState:
        """
        Ingests instantaneous frame emotion probabilities and returns a smoothed,
        hysteresis-stabilized MoodState. Supports manual mood override.
        """
        now = timestamp or time.time()

        if manual_override is not None:
            prev = self._current_stable_mood.get(session_id, manual_override)
            transition_occurred = (prev != manual_override)
            self._current_stable_mood[session_id] = manual_override
            self._stable_since[session_id] = now
            return MoodState(
                estimated_mood=manual_override,
                mood_confidence=0.95,
                smoothed_emotion_probabilities=raw_probabilities,
                is_stable=True,
                stable_duration_seconds=5.0,
                previous_mood=prev if transition_occurred else None,
                transition_occurred=transition_occurred
            )

        if session_id not in self._buffers:
            self._buffers[session_id] = deque(maxlen=self.window_size)
            self._ema_state[session_id] = raw_probabilities.to_dict()
            initial_mood = self._map_emotions_to_mood(self._ema_state[session_id])
            self._current_stable_mood[session_id] = initial_mood
            self._stable_since[session_id] = now
            self._candidate_mood[session_id] = None
            self._candidate_since[session_id] = now
            self._history[session_id] = []

        # 1. Update Rolling Window
        buffer = self._buffers[session_id]
        raw_dict = raw_probabilities.to_dict()
        buffer.append(raw_dict)

        # 2. Update Exponential Moving Average (EMA)
        prev_ema = self._ema_state[session_id]
        curr_ema: Dict[str, float] = {}
        for key, raw_val in raw_dict.items():
            prev_val = prev_ema.get(key, raw_val)
            curr_ema[key] = (self.ema_alpha * raw_val) + ((1.0 - self.ema_alpha) * prev_val)
        self._ema_state[session_id] = curr_ema

        # 3. Determine Candidate Mood from EMA distribution
        candidate_mood, candidate_score = self._compute_dominant_mood_and_score(curr_ema)

        # 4. Hysteresis & Minimum Stable Duration Logic
        active_stable_mood = self._current_stable_mood[session_id]
        active_score = self._compute_mood_score(curr_ema, active_stable_mood)

        transition_occurred = False
        previous_mood = active_stable_mood

        # If candidate mood differs from currently established stable mood:
        if candidate_mood != active_stable_mood:
            # Check if candidate sufficiently beats active mood by hysteresis margin
            if (candidate_score - active_score) >= self.hysteresis_margin:
                # Track how long this candidate has sustained its superiority
                if self._candidate_mood[session_id] != candidate_mood:
                    self._candidate_mood[session_id] = candidate_mood
                    self._candidate_since[session_id] = now
                else:
                    duration_held = now - self._candidate_since[session_id]
                    if duration_held >= self.min_stable_duration:
                        # Commit the transition
                        logger.info(
                            f"Mood transition committed: {active_stable_mood.value} -> {candidate_mood.value} "
                            f"(Held for {duration_held:.1f}s, margin={candidate_score - active_score:.2f})"
                        )
                        self._current_stable_mood[session_id] = candidate_mood
                        self._stable_since[session_id] = now
                        self._candidate_mood[session_id] = None
                        transition_occurred = True
            else:
                # Margin not met, reset candidate
                self._candidate_mood[session_id] = None
                self._candidate_since[session_id] = now
        else:
            # Current stable mood is reaffirmed
            self._candidate_mood[session_id] = None
            self._candidate_since[session_id] = now

        current_mood = self._current_stable_mood[session_id]
        stable_duration = now - self._stable_since[session_id]

        # Computed smoothed confidence
        smoothed_confidence = float(min(0.98, max(0.2, (confidence * 0.4) + (candidate_score * 0.6))))

        # Save to session history (max 100 observations for timeline view)
        hist_entry = {
            "timestamp": now,
            "mood": current_mood.value,
            "confidence": round(smoothed_confidence, 3),
            "dominant_emotion": max(curr_ema.items(), key=lambda kv: kv[1])[0]
        }
        self._history[session_id].append(hist_entry)
        if len(self._history[session_id]) > 100:
            self._history[session_id].pop(0)

        return MoodState(
            estimated_mood=current_mood,
            mood_confidence=round(smoothed_confidence, 3),
            smoothed_emotion_probabilities=EmotionProbabilities(**{k: round(v, 4) for k, v in curr_ema.items()}),
            is_stable=(stable_duration >= self.min_stable_duration),
            stable_duration_seconds=round(stable_duration, 1),
            previous_mood=previous_mood if transition_occurred else None,
            transition_occurred=transition_occurred
        )

    def get_session_history(self, session_id: str) -> List[dict]:
        """Returns recent mood history for client visualization."""
        return self._history.get(session_id, [])

    def _compute_dominant_mood_and_score(self, ema_probs: Dict[str, float]) -> Tuple[MoodClass, float]:
        """Evaluates scores across all controlled mood classes and picks winner."""
        scores: Dict[MoodClass, float] = {
            mood: self._compute_mood_score(ema_probs, mood)
            for mood in MoodClass
        }
        best_mood = max(scores.items(), key=lambda kv: kv[1])
        return best_mood[0], best_mood[1]

    def _compute_mood_score(self, ema: Dict[str, float], mood: MoodClass) -> float:
        """Heuristic weighting of emotion distributions into controlled mood space."""
        happy = ema.get("happy", 0.0)
        neutral = ema.get("neutral", 0.0)
        surprise = ema.get("surprise", 0.0)
        sad = ema.get("sad", 0.0)
        angry = ema.get("angry", 0.0)
        fear = ema.get("fear", 0.0)
        disgust = ema.get("disgust", 0.0)

        if mood == MoodClass.ENERGETIC:
            return (happy * 0.6) + (surprise * 0.4)
        elif mood == MoodClass.POSITIVE:
            return (happy * 0.8) + (neutral * 0.2)
        elif mood == MoodClass.CALM:
            return (neutral * 0.7) + (happy * 0.3)
        elif mood == MoodClass.NEUTRAL:
            return neutral
        elif mood == MoodClass.REFLECTIVE:
            return (neutral * 0.5) + (sad * 0.5)
        elif mood == MoodClass.LOW_ENERGY:
            return (sad * 0.75) + (neutral * 0.25)
        elif mood == MoodClass.TENSE:
            return (angry * 0.5) + (fear * 0.3) + (disgust * 0.2)

        return 0.0

    def _map_emotions_to_mood(self, ema_probs: Dict[str, float]) -> MoodClass:
        best_mood, _ = self._compute_dominant_mood_and_score(ema_probs)
        return best_mood


temporal_smoothing_service = TemporalSmoothingService()
