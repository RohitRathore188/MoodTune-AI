"""Jev Decision Service (Phase 5: Jev Decision Layer).
Wraps TypeSafe AI's System One model (typesafe-sdk) behind an internal typed interface.

PRINCIPLES & CONSTRAINTS:
1. Keeps Jev vendor-specific SDK details behind JevDecisionService.
2. Uses Jev for BOUNDED decisions only:
   - mood_class (Choice)
   - music_energy (Score/Choice)
   - transition_decision (Choice)
   - recommendation_strategy (Choice)
3. Passes only the MINIMUM useful state (no raw frames, no image arrays, no prose generation).
4. Does NOT allow Jev to directly control playback; application code executes decisions.
5. Implements timeout, retry policy, confidence tiering, and graceful deterministic fallback.
6. Server-side only: JEV_API_KEY is never exposed to browser or client code.
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional, Union, Tuple

from ..config import settings
from ..schemas.jev import (
    JevDecisionState,
    JevDecisionBundle,
    DecisionResultItem,
    ConfidenceTier,
    EnergyChoice,
    TransitionChoice,
    RecommendationStrategyChoice,
    JevCurrentSongState
)

logger = logging.getLogger("moodtune.jev")

# Import official typesafe-sdk
try:
    from typesafe_sdk import (
        TypeSafeClient,
        Choice,
        Score,
        RetryPolicy,
        SystemOneResponse,
        ChoiceAnswer,
        ScoreAnswer,
        TypeSafeError,
        TypeSafeAPITimeoutError,
        TypeSafeAPIConnectionError,
        TypeSafeAuthenticationError
    )
    HAS_TYPESAFE_SDK = True
except ImportError:
    HAS_TYPESAFE_SDK = False
    logger.warning("typesafe-sdk not available in python environment; deterministic fallback engine active.")


class JevDecisionService:
    """Bounded AI Decision Service wrapping Jev System One."""
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        client: Optional[Any] = None
    ):
        self.api_key = api_key or settings.JEV_API_KEY or os.environ.get("TYPESAFE_API_KEY") or os.environ.get("JEV_API_KEY")
        self.model = model or getattr(settings, "JEV_MODEL", "jev-latest")
        self.timeout = timeout if timeout is not None else getattr(settings, "JEV_TIMEOUT", 3.0)
        self.max_retries = max_retries if max_retries is not None else getattr(settings, "JEV_MAX_RETRIES", 2)
        self.client = client

        # Initialize live client if not injected and credentials exist
        if self.client is None and HAS_TYPESAFE_SDK and self.api_key:
            try:
                # Set environment variable expected by typesafe-sdk
                if not os.environ.get("TYPESAFE_API_KEY"):
                    os.environ["TYPESAFE_API_KEY"] = self.api_key

                retry_policy = RetryPolicy(
                    max_retries=self.max_retries,
                    backoff_initial=0.5,
                    backoff_max=2.0
                )
                self.client = TypeSafeClient(
                    api_key=self.api_key,
                    model=self.model,
                    timeout=self.timeout,
                    retry=retry_policy
                )
                logger.info(f"Initialized live TypeSafeClient for Jev (model={self.model}, timeout={self.timeout}s)")
            except Exception as e:
                logger.error(f"Failed to instantiate TypeSafeClient: {e}. Fallback active.")
                self.client = None

    def decide(
        self,
        state: Union[JevDecisionState, Dict[str, Any]],
        questions: Optional[Dict[str, Any]] = None
    ) -> JevDecisionBundle:
        """
        Typed internal interface: executes bounded decisions on the provided state.

        Guarantees:
        - Never sends raw images to Jev.
        - Falls back gracefully to deterministic logic on timeout, network failure, or invalid response.
        - Logs structured diagnostics.
        """
        start_time = time.perf_counter()

        # 1. Normalize and sanitize input state to minimal useful dictionary
        clean_state, parse_error = self._sanitize_input_state(state)
        if parse_error:
            logger.warning(f"Malformed input state provided to JevDecisionService: {parse_error}. Engaging fallback.")
            return self._evaluate_deterministic_fallback(clean_state, start_time, error_message=f"Malformed input: {parse_error}")

        # 2. Build questions if not provided
        decision_questions = questions or self._build_standard_questions()

        # 3. Attempt live Jev call if client is available
        if self.client is not None and HAS_TYPESAFE_SDK:
            try:
                state_json_str = json.dumps(clean_state)
                logger.debug(f"Calling Jev System One (model={self.model}) with minimal state...")

                response = self.client.system_one(
                    state=state_json_str,
                    questions=decision_questions,
                    model=self.model,
                    timeout=self.timeout
                )

                bundle = self._parse_typesafe_response(response, start_time, clean_state)
                logger.info(
                    f"Jev decision succeeded in {bundle.latency_ms}ms "
                    f"[mood={bundle.mood.value}, energy={bundle.energy.value}, transition={bundle.transition.value}, tier={bundle.confidence_tier.value}]"
                )
                return bundle

            except (TypeSafeAPITimeoutError, TimeoutError) as te:
                logger.warning(f"Jev inference timed out after {self.timeout}s: {te}. Engaging calibrated fallback.")
                return self._evaluate_deterministic_fallback(clean_state, start_time, error_message=f"Timeout ({self.timeout}s): {te}")
            except Exception as e:
                logger.warning(f"Jev API call failed ({type(e).__name__}: {e}). Engaging calibrated fallback.")
                return self._evaluate_deterministic_fallback(clean_state, start_time, error_message=f"API failure: {str(e)}")

        # 4. Fallback when live client is unconfigured or offline
        return self._evaluate_deterministic_fallback(clean_state, start_time)

    def _sanitize_input_state(self, state: Union[JevDecisionState, Dict[str, Any]]) -> Tuple[Dict[str, Any], Optional[str]]:
        """Extracts strictly the minimal useful state. Strips any extraneous or raw data."""
        try:
            if isinstance(state, JevDecisionState):
                raw = state.model_dump()
            elif isinstance(state, dict):
                raw = dict(state)
            else:
                return {"smoothed_mood": "neutral", "mood_confidence": 0.5}, "Invalid state type"

            # Filter and sanitize strictly bounded fields
            smoothed_mood = str(raw.get("smoothed_mood", "neutral")).lower()
            try:
                mood_conf = float(raw.get("mood_confidence", 0.5))
                if mood_conf < 0.0 or mood_conf > 1.0:
                    mood_conf = max(0.0, min(1.0, mood_conf))
            except (ValueError, TypeError):
                mood_conf = 0.5

            current_song_data = raw.get("current_song")
            sanitized_song = None
            if isinstance(current_song_data, dict):
                sanitized_song = {
                    "id": current_song_data.get("id"),
                    "title": current_song_data.get("title"),
                    "genre": current_song_data.get("genre"),
                    "energy": current_song_data.get("energy", 0.5),
                    "seconds_played": float(current_song_data.get("seconds_played", 0.0)),
                    "duration": float(current_song_data.get("duration", 180.0))
                }

            clean = {
                "smoothed_mood": smoothed_mood,
                "mood_confidence": mood_conf,
                "emotion_probabilities": raw.get("emotion_probabilities", {"neutral": 1.0}),
                "current_song": sanitized_song,
                "recent_skips": int(raw.get("recent_skips", 0)),
                "recent_likes": int(raw.get("recent_likes", 0)),
                "seconds_played": float(raw.get("seconds_played", 0.0)),
                "preferred_genres": list(raw.get("preferred_genres", []))
            }
            return clean, None

        except Exception as e:
            return {"smoothed_mood": "neutral", "mood_confidence": 0.5}, str(e)

    def _build_standard_questions(self) -> Dict[str, Any]:
        """Constructs official typesafe_sdk Question objects for bounded decisions."""
        if not HAS_TYPESAFE_SDK:
            return {}

        return {
            "mood_class": Choice(
                instructions="Determine the primary mood class from visible affect and stability.",
                criteria={
                    "energetic": None,
                    "positive": None,
                    "calm": None,
                    "neutral": None,
                    "reflective": None,
                    "low_energy": None,
                    "tense": None
                }
            ),
            "music_energy": Choice(
                instructions="What music energy level should be used?",
                criteria={
                    "low": None,
                    "medium": None,
                    "high": None
                }
            ),
            "transition_decision": Choice(
                instructions="What should the player do with the current song?",
                criteria={
                    "continue": None,
                    "transition": None,
                    "retrieve_new_candidates": None
                }
            ),
            "recommendation_strategy": Choice(
                instructions="Select the recommendation strategy for the current listener state.",
                criteria={
                    "mood_match": None,
                    "preference_match": None,
                    "exploration": None,
                    "safe_default": None
                }
            )
        }

    def _parse_typesafe_response(self, response: Any, start_time: float, clean_state: Dict[str, Any]) -> JevDecisionBundle:
        """Parses and validates SystemOneResponse into typed JevDecisionBundle."""
        answers = getattr(response, "answers", None)
        if not isinstance(answers, dict) or not answers:
            raise ValueError(f"Invalid SystemOneResponse: answers must be a non-empty dict, got {type(answers).__name__}")

        # 1. mood_class (or mood)
        mood_ans = answers.get("mood_class") or answers.get("mood")
        mood_val = getattr(mood_ans, "choice", None) or getattr(mood_ans, "value", None)
        if not mood_val:
            mood_val = clean_state.get("smoothed_mood", "neutral")
        mood_conf = float(getattr(mood_ans, "confidence", clean_state.get("mood_confidence", 0.8)))
        mood_probs = getattr(mood_ans, "probabilities", None)

        # 2. music_energy (or target_energy)
        energy_ans = answers.get("music_energy") or answers.get("target_energy")
        energy_val = getattr(energy_ans, "choice", None) or getattr(energy_ans, "score", None) or getattr(energy_ans, "value", "medium")
        energy_conf = float(getattr(energy_ans, "confidence", 0.75))
        energy_probs = getattr(energy_ans, "probabilities", None)

        # 3. transition_decision (or transition_action / transition)
        trans_ans = answers.get("transition_decision") or answers.get("transition_action") or answers.get("transition")
        trans_val = getattr(trans_ans, "choice", None) or getattr(trans_ans, "value", "continue")
        trans_conf = float(getattr(trans_ans, "confidence", 0.8))
        trans_probs = getattr(trans_ans, "probabilities", None)

        # 4. recommendation_strategy (or strategy)
        strat_ans = answers.get("recommendation_strategy") or answers.get("strategy")
        strat_val = getattr(strat_ans, "choice", None) or getattr(strat_ans, "value", "mood_match")
        strat_conf = float(getattr(strat_ans, "confidence", 0.8))
        strat_probs = getattr(strat_ans, "probabilities", None)

        # Evaluate confidence tier
        avg_conf = (mood_conf + energy_conf + trans_conf + strat_conf) / 4.0
        tier = self._compute_confidence_tier(avg_conf)

        # Confidence handling: low confidence enforces safe default
        if tier == ConfidenceTier.LOW:
            strat_val = RecommendationStrategyChoice.SAFE_DEFAULT.value

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return JevDecisionBundle(
            mood=DecisionResultItem(value=str(mood_val), confidence=round(mood_conf, 3), probabilities=mood_probs),
            energy=DecisionResultItem(value=str(energy_val), confidence=round(energy_conf, 3), probabilities=energy_probs),
            transition=DecisionResultItem(value=str(trans_val), confidence=round(trans_conf, 3), probabilities=trans_probs),
            strategy=DecisionResultItem(value=str(strat_val), confidence=round(strat_conf, 3), probabilities=strat_probs),
            confidence_tier=tier,
            decision_source="jev_system_one",
            latency_ms=round(latency_ms, 2)
        )

    def _evaluate_deterministic_fallback(
        self,
        clean_state: Dict[str, Any],
        start_time: float,
        error_message: Optional[str] = None
    ) -> JevDecisionBundle:
        """
        Calibrated deterministic fallback engine replicating Jev's bounded decision logic.
        Used when offline, in tests, without API keys, or when Jev encounters timeouts/errors.
        """
        mood_str = clean_state.get("smoothed_mood", "neutral")
        conf = clean_state.get("mood_confidence", 0.5)

        # 1. Bounded Energy Decision
        if mood_str == "energetic":
            energy_val = EnergyChoice.HIGH.value
            energy_probs = {"low": 0.05, "medium": 0.25, "high": 0.70}
        elif mood_str == "positive":
            energy_val = EnergyChoice.MEDIUM.value
            energy_probs = {"low": 0.15, "medium": 0.65, "high": 0.20}
        elif mood_str in ["calm", "reflective"]:
            energy_val = EnergyChoice.LOW.value
            energy_probs = {"low": 0.65, "medium": 0.30, "high": 0.05}
        elif mood_str == "low_energy":
            energy_val = EnergyChoice.LOW.value
            energy_probs = {"low": 0.80, "medium": 0.18, "high": 0.02}
        elif mood_str == "tense":
            # For tense expressions: select calming / low energy
            energy_val = EnergyChoice.LOW.value
            energy_probs = {"low": 0.70, "medium": 0.25, "high": 0.05}
        else:  # neutral
            energy_val = EnergyChoice.MEDIUM.value
            energy_probs = {"low": 0.30, "medium": 0.50, "high": 0.20}

        # 2. Bounded Transition Decision (Anti-thrashing rules)
        current_song = clean_state.get("current_song")
        recent_skips = clean_state.get("recent_skips", 0)

        trans_val = TransitionChoice.CONTINUE.value
        trans_probs = {"continue": 0.75, "transition": 0.20, "retrieve_new_candidates": 0.05}

        if current_song:
            song_sec = float(clean_state.get("seconds_played", current_song.get("seconds_played", 0.0)))
            duration = float(current_song.get("duration", 180.0)) or 180.0
            play_ratio = song_sec / max(1.0, duration)

            if recent_skips >= 2:
                trans_val = TransitionChoice.RETRIEVE_NEW_CANDIDATES.value
                trans_probs = {"continue": 0.05, "transition": 0.25, "retrieve_new_candidates": 0.70}
            elif play_ratio >= getattr(settings, "FORCE_TRANSITION_PLAY_RATIO", 0.85):
                trans_val = TransitionChoice.TRANSITION.value
                trans_probs = {"continue": 0.10, "transition": 0.85, "retrieve_new_candidates": 0.05}
            elif song_sec >= getattr(settings, "MIN_PLAY_SECONDS_BEFORE_TRANSITION", 30):
                song_energy = float(current_song.get("energy", 0.5))
                target_num = 0.8 if energy_val == "high" else (0.5 if energy_val == "medium" else 0.2)
                if abs(song_energy - target_num) > 0.45 and conf >= getattr(settings, "CONFIDENCE_HIGH_THRESHOLD", 0.70):
                    trans_val = TransitionChoice.TRANSITION.value
                    trans_probs = {"continue": 0.20, "transition": 0.70, "retrieve_new_candidates": 0.10}
        else:
            trans_val = TransitionChoice.RETRIEVE_NEW_CANDIDATES.value
            trans_probs = {"continue": 0.0, "transition": 0.20, "retrieve_new_candidates": 0.80}

        # 3. Bounded Strategy Decision
        recent_likes = clean_state.get("recent_likes", 0)
        tier = self._compute_confidence_tier(conf)

        if tier == ConfidenceTier.LOW:
            strat_val = RecommendationStrategyChoice.SAFE_DEFAULT.value
            strat_probs = {"mood_match": 0.15, "preference_match": 0.15, "exploration": 0.10, "safe_default": 0.60}
        elif recent_likes >= 3:
            strat_val = RecommendationStrategyChoice.PREFERENCE_MATCH.value
            strat_probs = {"mood_match": 0.35, "preference_match": 0.55, "exploration": 0.05, "safe_default": 0.05}
        elif recent_skips >= 2:
            strat_val = RecommendationStrategyChoice.EXPLORATION.value
            strat_probs = {"mood_match": 0.25, "preference_match": 0.15, "exploration": 0.55, "safe_default": 0.05}
        else:
            strat_val = RecommendationStrategyChoice.MOOD_MATCH.value
            strat_probs = {"mood_match": 0.70, "preference_match": 0.15, "exploration": 0.10, "safe_default": 0.05}

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return JevDecisionBundle(
            mood=DecisionResultItem(value=mood_str, confidence=round(conf, 3)),
            energy=DecisionResultItem(value=energy_val, confidence=round(conf * 0.9, 3), probabilities=energy_probs),
            transition=DecisionResultItem(value=trans_val, confidence=0.88, probabilities=trans_probs),
            strategy=DecisionResultItem(value=strat_val, confidence=0.85, probabilities=strat_probs),
            confidence_tier=tier,
            decision_source="deterministic_fallback",
            latency_ms=round(latency_ms, 2),
            error_message=error_message
        )

    def _compute_confidence_tier(self, confidence: float) -> ConfidenceTier:
        """Categorizes confidence into HIGH, MEDIUM, or LOW tiers."""
        high_th = getattr(settings, "CONFIDENCE_HIGH_THRESHOLD", 0.70)
        med_th = getattr(settings, "CONFIDENCE_MEDIUM_THRESHOLD", 0.40)
        if confidence >= high_th:
            return ConfidenceTier.HIGH
        elif confidence >= med_th:
            return ConfidenceTier.MEDIUM
        return ConfidenceTier.LOW


jev_decision_service = JevDecisionService()
