"""Unit tests for MoodSmoothingService (Phase 4: Temporal Mood Engine).
Tests:
- Configurable parameters (MOOD_WINDOW_SIZE, MOOD_MIN_STABLE_DURATION, MOOD_CHANGE_THRESHOLD, MOOD_CONFIDENCE_THRESHOLD)
- Stable mood progression & stability duration
- Noisy predictions dampening & user example verification
- Sudden changes & outlier rejection vs persistent transition
- Low confidence observation handling
- No face handling (graceful hold & confidence decay)
- Recovery after no face
- API endpoints: POST /api/mood/smooth and GET /api/mood/current
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.mood_smoothing_service import MoodSmoothingService
from app.schemas.mood import MoodSmoothRequest, StableMoodResponse


@pytest.fixture
def smoothing_service():
    """Provides a fresh service instance with controlled parameters."""
    return MoodSmoothingService(
        mood_window_size=5,
        mood_min_stable_duration=3.0,
        mood_change_threshold=0.25,
        mood_confidence_threshold=0.60,
        ema_alpha=0.35
    )


class TestMoodSmoothingService:
    def test_configurable_parameters(self):
        """Verifies parameters are fully configurable and not hardcoded."""
        custom_svc = MoodSmoothingService(
            mood_window_size=12,
            mood_min_stable_duration=5.5,
            mood_change_threshold=0.35,
            mood_confidence_threshold=0.75
        )
        assert custom_svc.mood_window_size == 12
        assert custom_svc.mood_min_stable_duration == 5.5
        assert custom_svc.mood_change_threshold == 0.35
        assert custom_svc.mood_confidence_threshold == 0.75

    def test_stable_mood(self, smoothing_service):
        """Consistent emotion observations establish stable mood and increment stable duration."""
        session_id = "test_stable"
        t0 = 100.0

        # Step through 5 seconds of consistent happy emotions
        for i in range(6):
            t = t0 + i
            res = smoothing_service.process_observation(
                emotion_probabilities={"happy": 0.85, "neutral": 0.15},
                confidence=0.90,
                timestamp=t,
                session_id=session_id
            )

        assert res.mood == "positive"
        assert res["mood"] == "positive"
        assert res.stable_for_seconds == 5.0
        assert res.is_stable is True
        assert res.confidence >= 0.70
        assert res.transition_detected is False

    def test_noisy_predictions_and_user_example(self, smoothing_service):
        """Validates the prompt's exact scenario:
        Frame 1: happy 0.80, neutral 0.10
        Next:    happy 0.70, neutral 0.20
        Next:    neutral 0.55, happy 0.40
        The system should NOT immediately switch to neutral.
        """
        session_id = "test_noisy_example"

        # Frame 1: happy 0.80, neutral 0.10
        f1 = smoothing_service.process_observation(
            {"happy": 0.80, "neutral": 0.10},
            confidence=0.88,
            timestamp=100.0,
            session_id=session_id
        )
        assert f1.mood == "positive"

        # Frame 2: happy 0.70, neutral 0.20
        f2 = smoothing_service.process_observation(
            {"happy": 0.70, "neutral": 0.20},
            confidence=0.85,
            timestamp=101.0,
            session_id=session_id
        )
        assert f2.mood == "positive"

        # Frame 3: neutral 0.55, happy 0.40
        f3 = smoothing_service.process_observation(
            {"neutral": 0.55, "happy": 0.40},
            confidence=0.82,
            timestamp=102.0,
            session_id=session_id
        )
        # CRITICAL ASSERTION: The system should NOT immediately switch to neutral
        assert f3.mood == "positive", f"Expected 'positive' to hold, but got '{f3.mood}'"
        assert f3.transition_detected is False

    def test_sudden_changes_and_eventual_transition(self, smoothing_service):
        """A single outlier frame is rejected; a sustained shift commits after min stable duration."""
        session_id = "test_sudden"

        # Establish positive mood
        for i in range(4):
            smoothing_service.process_observation(
                {"happy": 0.85, "neutral": 0.15},
                confidence=0.90,
                timestamp=100.0 + i,
                session_id=session_id
            )

        # 1. Sudden single-frame outlier (sharp sad spike)
        outlier = smoothing_service.process_observation(
            {"sad": 0.90, "happy": 0.05},
            confidence=0.88,
            timestamp=104.0,
            session_id=session_id
        )
        # Must NOT abruptly flip to low_energy on a single frame
        assert outlier.mood == "positive"
        assert outlier.transition_detected is False

        # 2. Next frame returns to happy
        returned = smoothing_service.process_observation(
            {"happy": 0.80, "neutral": 0.15},
            confidence=0.90,
            timestamp=105.0,
            session_id=session_id
        )
        assert returned.mood == "positive"

        # 3. Now simulate persistent, sustained shift to sad
        # Need to feed enough frames so window fills, passes hysteresis, and holds for >= 3.0s
        transition_found = False
        final_state = None
        for step in range(12):
            t = 106.0 + step
            s = smoothing_service.process_observation(
                {"sad": 0.90, "neutral": 0.08},
                confidence=0.90,
                timestamp=t,
                session_id=session_id
            )
            if s.transition_detected:
                transition_found = True
                assert s.previous_mood == "positive"
                assert s.mood == "low_energy"
            final_state = s

        assert transition_found is True
        assert final_state.mood == "low_energy"
        assert final_state.is_stable is True

    def test_low_confidence(self, smoothing_service):
        """Low confidence frames are damped and cannot trigger mood transitions."""
        session_id = "test_low_conf"

        # Establish positive mood with high confidence
        smoothing_service.process_observation(
            {"happy": 0.85, "neutral": 0.15},
            confidence=0.90,
            timestamp=100.0,
            session_id=session_id
        )

        # Feed frames with very low confidence (e.g. 0.25 < 0.60 threshold)
        for i in range(5):
            res = smoothing_service.process_observation(
                {"angry": 0.95, "neutral": 0.05},
                confidence=0.25,
                timestamp=101.0 + i,
                session_id=session_id
            )
            # Low confidence frames must NOT cause a transition to 'tense'
            assert res.mood == "positive"
            assert res.transition_detected is False
            assert res.confidence <= 0.60

    def test_no_face_handling(self, smoothing_service):
        """When face is absent, previous mood is preserved while confidence decays gracefully."""
        session_id = "test_no_face"

        # Establish positive mood
        for i in range(4):
            smoothing_service.process_observation(
                {"happy": 0.85, "neutral": 0.15},
                confidence=0.90,
                timestamp=100.0 + i,
                session_id=session_id
            )

        # Camera frame without face
        no_face_res = smoothing_service.process_observation(
            {"neutral": 1.0},
            confidence=0.0,
            face_detected=False,
            timestamp=104.0,
            session_id=session_id
        )
        assert no_face_res.mood == "positive"
        assert no_face_res.face_detected is False
        assert no_face_res.transition_detected is False
        assert "Face absent" in no_face_res.status_message

    def test_recovery_after_no_face(self, smoothing_service):
        """When face is re-detected after absence, tracking resumes smoothly."""
        session_id = "test_recovery"

        # Establish positive mood
        for i in range(3):
            smoothing_service.process_observation(
                {"happy": 0.85, "neutral": 0.15},
                confidence=0.90,
                timestamp=100.0 + i,
                session_id=session_id
            )

        # Face absent for 2 frames
        smoothing_service.process_observation(
            {"neutral": 1.0},
            confidence=0.0,
            face_detected=False,
            timestamp=103.0,
            session_id=session_id
        )
        smoothing_service.process_observation(
            {"neutral": 1.0},
            confidence=0.0,
            face_detected=False,
            timestamp=104.0,
            session_id=session_id
        )

        # Re-detect face with happy expression
        rec_res = smoothing_service.process_observation(
            {"happy": 0.80, "neutral": 0.20},
            confidence=0.92,
            face_detected=True,
            timestamp=105.0,
            session_id=session_id
        )

        assert rec_res.mood == "positive"
        assert rec_res.face_detected is True
        assert rec_res.confidence >= 0.70
        assert "Recovered tracking" in rec_res.status_message or "stable" in rec_res.status_message.lower()


class TestMoodApiEndpoints:
    @pytest.mark.asyncio
    async def test_smooth_mood_api_endpoint(self):
        """POST /api/mood/smooth returns the stabilized mood format."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "emotions": {"happy": 0.85, "neutral": 0.15},
                "confidence": 0.90,
                "face_detected": True,
                "session_id": "api_test_sess"
            }
            resp = await client.post("/api/mood/smooth", json=payload)
            assert resp.status_code == 200
            data = resp.json()

            assert "mood" in data
            assert data["mood"] == "positive"
            assert "confidence" in data
            assert 0.0 <= data["confidence"] <= 1.0
            assert "stable_for_seconds" in data
            assert isinstance(data["stable_for_seconds"], (int, float))

    @pytest.mark.asyncio
    async def test_get_current_mood_api_endpoint(self):
        """GET /api/mood/current returns the latest stable state for the session."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/mood/current?session_id=api_test_sess")
            assert resp.status_code == 200
            data = resp.json()
            assert "mood" in data
            assert "confidence" in data
            assert "stable_for_seconds" in data
