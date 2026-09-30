"""Unit tests for JevDecisionService (Phase 5: Jev Decision Layer).
Tests:
- successful Jev decision
- low confidence
- timeout
- invalid response
- API failure
- fallback
- malformed input
- server-side security (JEV_API_KEY never in frontend)
"""
import os
import pytest
from app.services.jev_service import JevDecisionService
from app.schemas.jev import (
    JevDecisionState,
    JevCurrentSongState,
    ConfidenceTier,
    EnergyChoice,
    TransitionChoice,
    RecommendationStrategyChoice
)
from typesafe_sdk import SystemOneResponse, ChoiceAnswer, ScoreAnswer


class MockTypesafeClient:
    """Mock client simulating diverse Jev System One response and failure states."""
    def __init__(self, mode: str = "success"):
        self.mode = mode

    def system_one(self, state, questions, model=None, timeout=None):
        if self.mode == "timeout":
            raise TimeoutError("Live Jev API timeout simulated")
        elif self.mode == "api_failure":
            raise RuntimeError("503 Service Unavailable: upstream connection lost")
        elif self.mode == "invalid_response":
            return "string_instead_of_system_one_response"
        elif self.mode == "empty_answers":
            return SystemOneResponse(model="jev-latest", usage={}, answers={})
        elif self.mode == "low_confidence":
            return SystemOneResponse(
                model="jev-latest",
                usage={"prompt_tokens": 12, "completion_tokens": 4},
                answers={
                    "mood_class": ChoiceAnswer(choice="neutral", confidence=0.25, probabilities={"neutral": 0.25}),
                    "music_energy": ChoiceAnswer(choice="low", confidence=0.30, probabilities={"low": 0.30}),
                    "transition_decision": ChoiceAnswer(choice="continue", confidence=0.35, probabilities={"continue": 0.35}),
                    "recommendation_strategy": ChoiceAnswer(choice="safe_default", confidence=0.25, probabilities={"safe_default": 0.25})
                }
            )

        # Default success response
        return SystemOneResponse(
            model="jev-latest",
            usage={"prompt_tokens": 15, "completion_tokens": 4},
            answers={
                "mood_class": ChoiceAnswer(choice="positive", confidence=0.92, probabilities={"positive": 0.92, "neutral": 0.08}),
                "music_energy": ChoiceAnswer(choice="medium", confidence=0.88, probabilities={"low": 0.10, "medium": 0.88, "high": 0.02}),
                "transition_decision": ChoiceAnswer(choice="continue", confidence=0.85, probabilities={"continue": 0.85, "transition": 0.15}),
                "recommendation_strategy": ChoiceAnswer(choice="mood_match", confidence=0.90, probabilities={"mood_match": 0.90, "safe_default": 0.10})
            }
        )


class TestJevDecisionService:
    def test_successful_jev_decision(self):
        """Validates that a live/mocked Jev client returns typed decision bundle."""
        client = MockTypesafeClient(mode="success")
        service = JevDecisionService(client=client)

        state = JevDecisionState(
            emotion_probabilities={"happy": 0.85, "neutral": 0.15},
            smoothed_mood="positive",
            mood_confidence=0.88,
            recent_skips=0,
            recent_likes=2,
            seconds_played=45.0
        )

        bundle = service.decide(state)

        assert bundle.decision_source == "jev_system_one"
        assert bundle.confidence_tier == ConfidenceTier.HIGH
        assert bundle.mood.value == "positive"
        assert bundle.mood_class.value == "positive"
        assert bundle.energy.value == "medium"
        assert bundle.music_energy.value == "medium"
        assert bundle.transition.value == "continue"
        assert bundle.transition_decision.value == "continue"
        assert bundle.strategy.value == "mood_match"
        assert bundle.recommendation_strategy.value == "mood_match"
        assert bundle.latency_ms >= 0.0

    def test_low_confidence_handling(self):
        """Low confidence responses safely enforce safe_default strategy and LOW tier."""
        # 1. Live Jev low confidence
        client = MockTypesafeClient(mode="low_confidence")
        service = JevDecisionService(client=client)
        bundle = service.decide({"smoothed_mood": "neutral", "mood_confidence": 0.25})

        assert bundle.decision_source == "jev_system_one"
        assert bundle.confidence_tier == ConfidenceTier.LOW
        assert bundle.strategy.value == "safe_default"

        # 2. Deterministic fallback low confidence
        fallback_service = JevDecisionService(client=None, api_key=None)
        fallback_bundle = fallback_service.decide({"smoothed_mood": "neutral", "mood_confidence": 0.20})

        assert fallback_bundle.decision_source == "deterministic_fallback"
        assert fallback_bundle.confidence_tier == ConfidenceTier.LOW
        assert fallback_bundle.strategy.value == "safe_default"

    def test_timeout_handling(self):
        """Inference exceeding timeout threshold triggers calibrated deterministic fallback."""
        client = MockTypesafeClient(mode="timeout")
        service = JevDecisionService(client=client, timeout=0.1)

        bundle = service.decide({"smoothed_mood": "positive", "mood_confidence": 0.85})

        assert bundle.decision_source == "deterministic_fallback"
        assert bundle.error_message is not None
        assert "Timeout" in bundle.error_message
        assert bundle.mood.value == "positive"

    def test_invalid_response_handling(self):
        """Invalid response schemas trigger graceful fallback without crashing."""
        # A: Non-dict / string response
        client_str = MockTypesafeClient(mode="invalid_response")
        service_str = JevDecisionService(client=client_str)
        bundle_str = service_str.decide({"smoothed_mood": "positive", "mood_confidence": 0.85})

        assert bundle_str.decision_source == "deterministic_fallback"
        assert "Invalid SystemOneResponse" in bundle_str.error_message

        # B: Empty answers dict
        client_empty = MockTypesafeClient(mode="empty_answers")
        service_empty = JevDecisionService(client=client_empty)
        bundle_empty = service_empty.decide({"smoothed_mood": "positive", "mood_confidence": 0.85})

        assert bundle_empty.decision_source == "deterministic_fallback"

    def test_api_failure_handling(self):
        """HTTP errors or network exceptions trigger graceful fallback."""
        client = MockTypesafeClient(mode="api_failure")
        service = JevDecisionService(client=client)

        bundle = service.decide({"smoothed_mood": "positive", "mood_confidence": 0.85})

        assert bundle.decision_source == "deterministic_fallback"
        assert "API failure" in bundle.error_message

    def test_deterministic_fallback_anti_thrashing(self):
        """Fallback engine satisfies song duration and skip anti-thrashing rules."""
        service = JevDecisionService(client=None, api_key=None)

        # Song played for only 5 seconds -> must CONTINUE
        current_song = JevCurrentSongState(
            id="track_123",
            title="Calm Waters",
            genre="ambient",
            energy=0.2,
            seconds_played=5.0,
            duration=180.0
        )
        state_early = JevDecisionState(
            emotion_probabilities={"happy": 0.9},
            smoothed_mood="energetic",
            mood_confidence=0.90,
            current_song=current_song,
            seconds_played=5.0
        )
        bundle_early = service.decide(state_early)
        assert bundle_early.transition.value == TransitionChoice.CONTINUE.value

        # High skips -> must RETRIEVE_NEW_CANDIDATES
        state_skips = JevDecisionState(
            emotion_probabilities={"happy": 0.9},
            smoothed_mood="positive",
            mood_confidence=0.85,
            recent_skips=3,
            current_song=current_song,
            seconds_played=40.0
        )
        bundle_skips = service.decide(state_skips)
        assert bundle_skips.transition.value == TransitionChoice.RETRIEVE_NEW_CANDIDATES.value

    def test_malformed_input_handling(self):
        """Malformed input data types are sanitized into safe defaults without unhandled exceptions."""
        service = JevDecisionService()

        # Non-dict, non-pydantic input
        res1 = service.decide("not_a_valid_state_object")
        assert res1.decision_source == "deterministic_fallback"
        assert res1.mood.value == "neutral"

        # Out-of-bounds confidence
        res2 = service.decide({"smoothed_mood": "positive", "mood_confidence": 99.9})
        assert res2.mood.value == "positive"
        assert 0.0 <= res2.mood.confidence <= 1.0

    def test_server_side_only_api_key_security(self):
        """Verifies that JEV_API_KEY / TYPESAFE_API_KEY is never exposed to frontend code."""
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "src")
        
        # Scan all frontend source files
        found_leaks = []
        if os.path.exists(frontend_dir):
            for root, _, files in os.walk(frontend_dir):
                for f in files:
                    if f.endswith((".ts", ".tsx", ".js", ".jsx", ".html")):
                        path = os.path.join(root, f)
                        with open(path, "r", encoding="utf-8") as fl:
                            content = fl.read()
                            if "JEV_API_KEY" in content or "TYPESAFE_API_KEY" in content:
                                found_leaks.append(f)

        assert len(found_leaks) == 0, f"Secret leak found in frontend files: {found_leaks}"
