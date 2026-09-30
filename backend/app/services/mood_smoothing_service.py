"""Mood Smoothing Service (Phase 4: Temporal Mood Engine).
Stabilizes fluctuating emotion predictions over time to produce a robust,
hysteresis-stabilized, and anti-thrashing mood state.

Core Pipeline:
1. Rolling window buffer
2. Dual-stage probability smoothing (window averaging + EMA)
3. Confidence calculation (frame confidence + score margin + stability bonus)
4. Minimum stability duration gating
5. Hysteresis (change threshold) to prevent rapid oscillation
6. Transition detection with previous state history
7. Graceful handling of missing faces, noisy predictions, sudden outliers, and recovery
"""
import time
import logging
from collections import deque
from typing import Dict, List, Optional, Tuple, Union, Any

from ..config import settings
from ..schemas.mood import MoodClass

logger = logging.getLogger("moodtune.mood_smoothing")

# Canonical mood mapping scores
# Maps smoothed facial expression probabilities into human-centered mood states
def evaluate_mood_scores(emotions: Dict[str, float]) -> Dict[str, float]:
    h = emotions.get("happy", 0.0)
    n = emotions.get("neutral", 0.0)
    su = emotions.get("surprise", 0.0)
    sa = emotions.get("sad", 0.0)
    a = emotions.get("angry", 0.0)
    f = emotions.get("fear", 0.0)
    d = emotions.get("disgust", 0.0)

    return {
        "positive": (h * 0.85) + (n * 0.15),
        "energetic": (h * 0.55) + (su * 0.45),
        "calm": (n * 0.70) + (h * 0.30),
        "neutral": n,
        "reflective": (n * 0.50) + (sa * 0.50),
        "low_energy": (sa * 0.80) + (n * 0.20),
        "tense": (a * 0.50) + (f * 0.30) + (d * 0.20),
    }


class StableMoodState(dict):
    """Dictionary representing the stable mood state with attribute access."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for k, v in self.items():
            if isinstance(v, dict) and not isinstance(v, StableMoodState):
                self[k] = StableMoodState(v)
        self.__dict__ = self


class SessionState:
    """Tracks state and history for a specific listening session."""
    def __init__(self, window_size: int, initial_mood: str = "neutral", initial_time: float = 0.0):
        self.window: deque = deque(maxlen=window_size)
        self.ema_emotions: Dict[str, float] = {
            "happy": 0.0, "sad": 0.0, "angry": 0.0, "neutral": 1.0,
            "fear": 0.0, "surprise": 0.0, "disgust": 0.0
        }
        self.current_mood: str = initial_mood
        self.current_confidence: float = 0.80
        self.stable_since: float = initial_time
        self.candidate_mood: Optional[str] = None
        self.candidate_since: Optional[float] = None
        self.consecutive_no_face_count: int = 0
        self.last_valid_face_timestamp: Optional[float] = initial_time
        self.frozen_stable_duration: float = 0.0
        self.history: List[dict] = []


class MoodSmoothingService:
    """Service responsible for temporal mood stabilization."""
    def __init__(
        self,
        mood_window_size: Optional[int] = None,
        mood_min_stable_duration: Optional[float] = None,
        mood_change_threshold: Optional[float] = None,
        mood_confidence_threshold: Optional[float] = None,
        ema_alpha: float = 0.35
    ):
        # Configurable parameters (never hard-coded inside business logic)
        self.mood_window_size = (
            mood_window_size if mood_window_size is not None
            else getattr(settings, "MOOD_WINDOW_SIZE", 5)
        )
        self.mood_min_stable_duration = (
            mood_min_stable_duration if mood_min_stable_duration is not None
            else getattr(settings, "MOOD_MIN_STABLE_DURATION", 3.0)
        )
        self.mood_change_threshold = (
            mood_change_threshold if mood_change_threshold is not None
            else getattr(settings, "MOOD_CHANGE_THRESHOLD", 0.25)
        )
        self.mood_confidence_threshold = (
            mood_confidence_threshold if mood_confidence_threshold is not None
            else getattr(settings, "MOOD_CONFIDENCE_THRESHOLD", 0.60)
        )
        self.ema_alpha = ema_alpha

        # Session memory store
        self._sessions: Dict[str, SessionState] = {}

    def reset_session(self, session_id: str):
        """Clears memory for a session (privacy control)."""
        self._sessions.pop(session_id, None)
        logger.info(f"Cleared mood smoothing session: {session_id}")

    def _get_or_create_session(self, session_id: str, now: float, initial_probs: Dict[str, float]) -> SessionState:
        if session_id not in self._sessions:
            scores = evaluate_mood_scores(initial_probs)
            initial_mood = max(scores.items(), key=lambda kv: kv[1])[0]
            sess = SessionState(self.mood_window_size, initial_mood=initial_mood, initial_time=now)
            sess.ema_emotions = dict(initial_probs)
            self._sessions[session_id] = sess
        return self._sessions[session_id]

    def process_observation(
        self,
        emotion_probabilities: Union[Dict[str, float], Any],
        confidence: float = 0.85,
        face_detected: bool = True,
        timestamp: Optional[float] = None,
        session_id: str = "default_session"
    ) -> StableMoodState:
        """
        Ingests instantaneous emotion probabilities and outputs a stable mood state.

        Guarantees:
        - Outliers & jitter are smoothed out over the rolling window.
        - Hysteresis avoids flickering between close states.
        - Changes only commit once candidate is held stably for MOOD_MIN_STABLE_DURATION.
        - No-face frames maintain the existing mood safely with gradual confidence decay.
        """
        now = timestamp if timestamp is not None else time.time()

        # Sanitize incoming probabilities into dict
        if hasattr(emotion_probabilities, "model_dump"):
            raw_dict = emotion_probabilities.model_dump()
        elif hasattr(emotion_probabilities, "to_dict"):
            raw_dict = emotion_probabilities.to_dict()
        elif isinstance(emotion_probabilities, dict):
            raw_dict = dict(emotion_probabilities)
        else:
            raw_dict = {"neutral": 1.0}

        sess = self._get_or_create_session(session_id, now, raw_dict)

        # -------------------------------------------------------------
        # 1. Handle No-Face State & Recovery
        # -------------------------------------------------------------
        if not face_detected or confidence <= 0.0:
            sess.consecutive_no_face_count += 1
            # If no face, do NOT abruptly change the mood.
            # Maintain previous stable mood, decay confidence gradually.
            decay_factor = max(0.20, 1.0 - (sess.consecutive_no_face_count * 0.15))
            decayed_conf = round(float(sess.current_confidence * decay_factor), 3)

            # Freeze or clamp stability duration
            stable_seconds = round(max(0.0, now - sess.stable_since), 1)

            return StableMoodState({
                "mood": sess.current_mood,
                "confidence": decayed_conf,
                "stable_for_seconds": stable_seconds,
                "is_stable": (stable_seconds >= self.mood_min_stable_duration),
                "transition_detected": False,
                "previous_mood": None,
                "smoothed_emotions": {k: round(v, 4) for k, v in sess.ema_emotions.items()},
                "face_detected": False,
                "status_message": f"Face absent: safely maintaining stable mood '{sess.current_mood}'."
            })

        # Recovery after no-face
        is_recovery = (sess.consecutive_no_face_count > 0)
        sess.consecutive_no_face_count = 0
        sess.last_valid_face_timestamp = now

        # -------------------------------------------------------------
        # 2. Rolling Window & Dual-Stage Smoothing (Window Mean + EMA)
        # -------------------------------------------------------------
        # Weight frame by confidence: low confidence frames are damped
        confidence_weight = 1.0
        if confidence < self.mood_confidence_threshold:
            # Dampen influence of low-confidence frames
            confidence_weight = max(0.25, confidence / self.mood_confidence_threshold)

        sess.window.append(raw_dict)

        # Window average
        all_emotions = ("happy", "sad", "angry", "neutral", "fear", "surprise", "disgust")
        window_avg: Dict[str, float] = {}
        for emo in all_emotions:
            vals = [w.get(emo, 0.0) for w in sess.window]
            window_avg[emo] = sum(vals) / len(vals)

        # Update EMA with confidence weighting
        effective_alpha = self.ema_alpha * confidence_weight
        curr_ema: Dict[str, float] = {}
        for emo in all_emotions:
            raw_v = raw_dict.get(emo, 0.0)
            prev_v = sess.ema_emotions.get(emo, raw_v)
            curr_ema[emo] = (effective_alpha * raw_v) + ((1.0 - effective_alpha) * prev_v)

        # Blend window mean and EMA (50/50)
        blended_emotions: Dict[str, float] = {}
        for emo in all_emotions:
            blended_emotions[emo] = (0.5 * curr_ema[emo]) + (0.5 * window_avg[emo])

        # Normalize blended distribution
        total_p = sum(blended_emotions.values())
        if total_p > 0:
            blended_emotions = {k: v / total_p for k, v in blended_emotions.items()}
        else:
            blended_emotions["neutral"] = 1.0

        sess.ema_emotions = blended_emotions

        # -------------------------------------------------------------
        # 3. Evaluate Mood Scores & Candidate Determination
        # -------------------------------------------------------------
        mood_scores = evaluate_mood_scores(blended_emotions)
        candidate_mood = max(mood_scores.items(), key=lambda kv: kv[1])[0]
        candidate_score = mood_scores[candidate_mood]
        active_score = mood_scores.get(sess.current_mood, 0.0)

        # Compute runner-up score for margin
        sorted_scores = sorted(mood_scores.values(), reverse=True)
        score_margin = (sorted_scores[0] - sorted_scores[1]) if len(sorted_scores) > 1 else 0.5

        # -------------------------------------------------------------
        # 4. Hysteresis & Minimum Stability Duration Gating
        # -------------------------------------------------------------
        transition_detected = False
        previous_mood = None

        if candidate_mood != sess.current_mood:
            # Check 1: Must exceed active mood score by MOOD_CHANGE_THRESHOLD (hysteresis)
            # Check 2: Low-confidence frames cannot trigger transition
            hysteresis_satisfied = (
                (candidate_score - active_score) >= self.mood_change_threshold
                and confidence >= self.mood_confidence_threshold
            )

            if hysteresis_satisfied:
                if sess.candidate_mood != candidate_mood:
                    # New candidate has crossed hysteresis margin
                    sess.candidate_mood = candidate_mood
                    sess.candidate_since = now
                else:
                    # Candidate continues to sustain superiority
                    held_duration = now - (sess.candidate_since or now)
                    if held_duration >= self.mood_min_stable_duration:
                        # COMMIT TRANSITION!
                        logger.info(
                            f"Mood transition committed: {sess.current_mood} -> {candidate_mood} "
                            f"(held for {held_duration:.1f}s, margin={candidate_score - active_score:.2f})"
                        )
                        previous_mood = sess.current_mood
                        sess.current_mood = candidate_mood
                        sess.stable_since = now
                        sess.candidate_mood = None
                        sess.candidate_since = None
                        transition_detected = True
            else:
                # Hysteresis not met: candidate rejected or reset
                sess.candidate_mood = None
                sess.candidate_since = None
        else:
            # Active mood reaffirmed
            sess.candidate_mood = None
            sess.candidate_since = None

        # -------------------------------------------------------------
        # 5. Stability Duration & Confidence Calculation
        # -------------------------------------------------------------
        stable_for_seconds = round(max(0.0, now - sess.stable_since), 1)
        is_stable = (stable_for_seconds >= self.mood_min_stable_duration)

        # Confidence calculation:
        # Blends raw frame confidence, mood score margin, and stability bonus
        stability_bonus = min(0.20, (stable_for_seconds / self.mood_min_stable_duration) * 0.20)
        calculated_conf = (
            (confidence * 0.45) +
            (score_margin * 0.35) +
            stability_bonus
        )
        # If low confidence input, clamp accordingly
        if confidence < self.mood_confidence_threshold:
            calculated_conf = min(calculated_conf, confidence + 0.10)

        final_confidence = round(float(min(0.98, max(0.10, calculated_conf))), 2)
        sess.current_confidence = final_confidence

        # Save to session history (capped at 50)
        history_entry = {
            "timestamp": now,
            "mood": sess.current_mood,
            "confidence": final_confidence,
            "stable_for_seconds": stable_for_seconds,
            "transition": transition_detected
        }
        sess.history.append(history_entry)
        if len(sess.history) > 50:
            sess.history.pop(0)

        status_msg = (
            f"Mood '{sess.current_mood}' stable for {stable_for_seconds}s"
            if is_stable else f"Stabilizing mood '{sess.current_mood}' ({stable_for_seconds}s)"
        )
        if transition_detected:
            status_msg = f"Mood transitioned from '{previous_mood}' to '{sess.current_mood}'."
        elif is_recovery:
            status_msg = f"Recovered tracking: mood maintained as '{sess.current_mood}'."

        return StableMoodState({
            "mood": sess.current_mood,
            "confidence": final_confidence,
            "stable_for_seconds": stable_for_seconds,
            "is_stable": is_stable,
            "transition_detected": transition_detected,
            "previous_mood": previous_mood,
            "smoothed_emotions": {k: round(v, 4) for k, v in blended_emotions.items()},
            "face_detected": True,
            "status_message": status_msg
        })

    def get_current_mood(self, session_id: str = "default_session") -> StableMoodState:
        """Returns the current stable mood for the given session."""
        if session_id not in self._sessions:
            return StableMoodState({
                "mood": "neutral",
                "confidence": 0.50,
                "stable_for_seconds": 0.0,
                "is_stable": False,
                "transition_detected": False,
                "previous_mood": None,
                "smoothed_emotions": {"neutral": 1.0},
                "face_detected": False,
                "status_message": "Session not initialized yet"
            })

        sess = self._sessions[session_id]
        now = time.time()
        stable_seconds = round(max(0.0, now - sess.stable_since), 1)
        return StableMoodState({
            "mood": sess.current_mood,
            "confidence": sess.current_confidence,
            "stable_for_seconds": stable_seconds,
            "is_stable": (stable_seconds >= self.mood_min_stable_duration),
            "transition_detected": False,
            "previous_mood": None,
            "smoothed_emotions": {k: round(v, 4) for k, v in sess.ema_emotions.items()},
            "face_detected": (sess.consecutive_no_face_count == 0),
            "status_message": f"Active mood '{sess.current_mood}'"
        })

    def get_session_history(self, session_id: str = "default_session") -> List[dict]:
        """Returns recent history for visualization."""
        if session_id in self._sessions:
            return list(self._sessions[session_id].history)
        return []


mood_smoothing_service = MoodSmoothingService()
