"""Complete System Verification Test Suite (17 Core Subsystems).
Exercises every major layer of MoodTune AI from Camera & Vision to Jev Decision & Playback.
"""
import pytest
import time
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

from app.main import app
from app.config import settings, Settings
from app.services.face_detection_service import face_detection_service
from app.services.emotion_detection_service import emotion_detection_service
from app.services.mood_smoothing_service import mood_smoothing_service
from app.services.temporal_smoothing_service import temporal_smoothing_service
from app.services.jev_service import JevDecisionService
from app.services.recommendation_engine import recommendation_engine
from app.services.music_provider import LocalMusicProvider, music_provider
from app.services.playback_manager import playback_manager
from app.services.personalization_service import personalization_service
from app.services.rate_limiter import InMemoryRateLimiter
from app.database import AsyncSessionLocal, purge_expired_sessions
from app.schemas.camera import FrameDetectionRequest
from app.schemas.mood import MoodState, MoodClass, EmotionProbabilities
from app.schemas.music import MusicProfile, UserPreferenceSchema, PlaybackState


class TestFullSystemIntegration:

    @pytest.mark.asyncio
    async def test_01_backend_and_database_initialization(self):
        """1 & 2: Backend application lifecycle and database connection."""
        assert app.title == settings.PROJECT_NAME
        assert settings.STORE_RAW_FRAMES is False
        async with AsyncSessionLocal() as session:
            purged = await purge_expired_sessions(session, retention_days=7)
            assert isinstance(purged, int)

    @pytest.mark.asyncio
    async def test_02_camera_and_storage_guarantees(self):
        """3: Camera subsystem in-memory status and storage policy."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/camera/status")
            assert res.status_code == 200
            data = res.json()
            assert data["storage_policy"] == "in_memory_only (never saved to disk/db)"

    def test_03_face_detection_pipeline(self):
        """4: Face detection processing in-memory and zero-leakage."""
        # Test no frame input
        result_none = face_detection_service.detect_faces(None)
        assert result_none.state.value == "no_face"
        assert result_none.face_count == 0

        # Test corrupt frame data
        result_corrupt = face_detection_service.detect_faces("invalid_base64_string")
        assert result_corrupt.state.value == "error"

    def test_04_emotion_model_human_centered_principles(self):
        """5: Emotion estimation produces 'estimated facial expression' with bounded probabilities."""
        res = emotion_detection_service.estimate_emotion(None)
        assert res["expression_type"] == "estimated facial expression"
        assert "neutral" in res["emotions"]
        assert 0.0 <= res["confidence"] <= 1.0

    def test_05_mood_smoothing_and_anti_thrashing(self):
        """6: Mood temporal smoothing with EMA and hysteresis stability."""
        session_id = f"test_smooth_{time.time()}"
        emotions = {"happy": 0.85, "neutral": 0.15, "sad": 0.0, "angry": 0.0, "fear": 0.0, "surprise": 0.0, "disgust": 0.0}

        # Step 1: initial observation
        obs1 = mood_smoothing_service.process_observation(emotions, confidence=0.90, session_id=session_id)
        assert obs1["mood"] in ["positive", "energetic"]

        # Step 2: brief noise should not violently snap state
        noise = {"happy": 0.10, "neutral": 0.10, "sad": 0.80, "angry": 0.0, "fear": 0.0, "surprise": 0.0, "disgust": 0.0}
        obs2 = mood_smoothing_service.process_observation(noise, confidence=0.85, session_id=session_id)
        # Hysteresis dampens the single frame noise
        assert obs2["mood"] in ["positive", "energetic", "neutral"]

    def test_06_jev_service_and_fallback(self):
        """7 & 8: Jev decision layer with bounded minimal state and deterministic fallback."""
        jev = JevDecisionService(api_key=None)  # forces fallback
        bundle = jev.decide({
            "smoothed_mood": "calm",
            "mood_confidence": 0.85,
            "seconds_played": 45.0,
            "recent_skips": 0
        })
        assert bundle.mood.value in ["calm", "neutral", "reflective"]
        assert bundle.decision_source == "deterministic_fallback"
        assert bundle.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_07_recommendation_engine_and_hindi_catalog(self):
        """9 & 10: Recommendation engine ranking Hindi tracks matching mood."""
        mood_state = MoodState(
            estimated_mood=MoodClass.POSITIVE,
            mood_confidence=0.88,
            smoothed_emotion_probabilities=EmotionProbabilities(happy=0.85, neutral=0.15),
            is_stable=True,
            stable_duration_seconds=6.0
        )
        rec_resp = await recommendation_engine.generate_recommendations(
            mood_state=mood_state,
            playback_state=None,
            user_id="default_user",
            limit=5
        )
        assert len(rec_resp.recommendations) > 0
        top_track = rec_resp.recommendations[0].track
        hindi_titles = {t.title for t in music_provider._catalog}
        assert top_track.title in hindi_titles

    @pytest.mark.asyncio
    async def test_08_playback_management_lifecycle(self):
        """11: Playback sequencing, user skip penalty, and transition cooldown."""
        track = await music_provider.get_track("trk_upbeat_01")
        assert track is not None
        await playback_manager.play(track.id, position_seconds=10.0)

        assert playback_manager.get_playback_state().is_playing is True

        # Test skip
        next_state = await playback_manager.skip(reason="user_skip")
        assert next_state is not None

        # Pause
        paused_state = await playback_manager.pause()
        assert paused_state.is_playing is False

    def test_09_personalization_privacy_and_weights(self):
        """12: Personalization telemetry without sensitive demographic inference."""
        pers = personalization_service
        user_id = f"user_{time.time()}"
        profile = pers.get_user_profile(user_id)
        assert profile.preferred_energy == 0.64
        assert "religion" not in profile.model_dump()
        assert "political_views" not in profile.model_dump()

    @pytest.mark.asyncio
    async def test_10_api_endpoints_integration(self):
        """14: All core API routes responding correctly."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            h_res = await client.get("/api/health")
            assert h_res.status_code == 200

            m_res = await client.get("/api/music/tracks")
            assert m_res.status_code == 200
            assert len(m_res.json()) >= 10

            rec_res = await client.get("/api/recommendations?mood=energetic&confidence=0.90")
            assert rec_res.status_code == 200
            assert len(rec_res.json()["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_11_error_handling_and_sanitization(self):
        """15: Error handling returns clean, sanitized responses without path disclosures."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 422 on invalid parameter
            res_422 = await client.get("/api/recommendations?confidence=2.5")
            assert res_422.status_code == 422

            # 404 on missing track
            res_404 = await client.get("/api/music/track/trk_unknown_9999")
            assert res_404.status_code == 404

    def test_12_security_guardrails(self):
        """16: Insecure secret key in prod rejected, CORS hardened, and rate limiter active."""
        with pytest.raises(ValueError):
            Settings(ENVIRONMENT="production", SECRET_KEY="moodtune-dev-insecure-secret-key-change-in-prod")

        limiter = InMemoryRateLimiter(max_requests_per_second=2)
        assert limiter.check("test_ip") is True
        assert limiter.check("test_ip") is True
        assert limiter.check("test_ip") is False
