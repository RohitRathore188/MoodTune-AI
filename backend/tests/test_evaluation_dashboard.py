"""Tests for Phase 12: AI Evaluation Dashboard.

Verifies:
1. Emotion metrics (inference latency, confidence distribution, no-face rate)
2. Mood metrics (stability, transition frequency, low-confidence rate)
3. Recommendation metrics (acceptance rate, skip rate, completion rate, diversity)
4. Playback metrics (average listening duration, skip frequency, transition frequency)
5. System metrics (Jev latency, Jev failures, fallback frequency, API failures)
6. Human-centered mandate (explicit disclaimer, no claims of internal emotional truth)
7. Clean partitioning into MODEL, RECOMMENDATION, and SYSTEM performance
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.evaluation_service import evaluation_service


@pytest.fixture(autouse=True)
def reset_eval_telemetry():
    """Reset evaluation telemetry before every test."""
    evaluation_service.reset()
    yield
    evaluation_service.reset()


class TestEvaluationService:
    def test_default_evaluation_metrics_structure(self):
        """Verifies clean partitioning into MODEL, RECOMMENDATION, and SYSTEM."""
        dash = evaluation_service.get_evaluation_dashboard()
        assert dash.model_performance is not None
        assert dash.recommendation_performance is not None
        assert dash.system_performance is not None
        assert "internal emotional state" in dash.disclaimer or "true emotions" in dash.disclaimer or "internal emotional truth" in dash.disclaimer

    def test_emotion_metrics_calculation(self):
        """Tests inference latency, confidence distribution, and no-face rate."""
        # Record 4 frames: 2 high conf detected, 1 med conf detected, 1 no face
        evaluation_service.record_emotion_inference(latency_ms=20.0, confidence=0.85, detected=True)
        evaluation_service.record_emotion_inference(latency_ms=30.0, confidence=0.75, detected=True)
        evaluation_service.record_emotion_inference(latency_ms=25.0, confidence=0.55, detected=True)
        evaluation_service.record_emotion_inference(latency_ms=15.0, confidence=0.00, detected=False)

        dash = evaluation_service.get_evaluation_dashboard()
        emotion = dash.model_performance.emotion

        assert emotion.inference_latency_ms > 0
        assert emotion.no_face_rate == pytest.approx(0.25, rel=1e-2)
        assert emotion.total_frames == 4
        assert emotion.confidence_distribution.high > 0
        assert emotion.confidence_distribution.medium > 0

    def test_mood_metrics_calculation(self):
        """Tests stability, transition frequency, and low-confidence rate."""
        evaluation_service.record_mood_observation(confidence=0.85, is_stable=True, duration_sec=14.0, transition_occurred=False)
        evaluation_service.record_mood_observation(confidence=0.30, is_stable=False, duration_sec=0.0, transition_occurred=False)
        evaluation_service.record_mood_observation(confidence=0.90, is_stable=True, duration_sec=20.0, transition_occurred=True)

        dash = evaluation_service.get_evaluation_dashboard()
        mood = dash.model_performance.mood

        assert mood.average_stability_duration_sec > 0
        assert mood.total_transitions == 1
        assert mood.low_confidence_rate == pytest.approx(1 / 3, rel=1e-2)
        assert 0.0 <= mood.stability_score <= 1.0

    def test_recommendation_metrics_calculation(self):
        """Tests acceptance rate, skip rate, completion rate, and diversity."""
        evaluation_service.record_recommendations_served(count=10, diversity_score=0.88)
        evaluation_service.record_recommendation_accepted()
        evaluation_service.record_recommendation_accepted()

        evaluation_service.record_playback_event(event_type="play")
        evaluation_service.record_playback_event(event_type="skip", seconds_played=15.0)
        evaluation_service.record_playback_event(event_type="complete", seconds_played=180.0)

        dash = evaluation_service.get_evaluation_dashboard()
        rec = dash.recommendation_performance.recommendation

        assert rec.acceptance_rate == pytest.approx(0.20, rel=1e-2)
        assert 0.0 <= rec.skip_rate <= 1.0
        assert 0.0 <= rec.completion_rate <= 1.0
        assert 0.0 <= rec.diversity_score <= 1.0

    def test_playback_metrics_calculation(self):
        """Tests average listening duration, skip frequency, and transition frequency."""
        evaluation_service.record_playback_event(event_type="skip", seconds_played=30.0)
        evaluation_service.record_playback_event(event_type="complete", seconds_played=150.0)
        evaluation_service.record_playback_event(event_type="transition")

        dash = evaluation_service.get_evaluation_dashboard()
        playback = dash.recommendation_performance.playback

        assert playback.average_listening_duration_sec > 0
        assert playback.skip_frequency_per_10m >= 0
        assert playback.transition_frequency_per_10m >= 0

    def test_system_metrics_calculation(self):
        """Tests Jev latency, Jev failures, fallback frequency, and API failures."""
        evaluation_service.record_jev_decision(latency_ms=45.0, success=True, is_fallback=False)
        evaluation_service.record_jev_decision(latency_ms=55.0, success=True, is_fallback=True)
        evaluation_service.record_jev_decision(latency_ms=0.0, success=False, is_fallback=True)

        evaluation_service.record_api_call(is_error=False)
        evaluation_service.record_api_call(is_error=False)
        evaluation_service.record_api_call(is_error=True)

        dash = evaluation_service.get_evaluation_dashboard()
        sys = dash.system_performance

        assert sys.jev_latency_ms == pytest.approx(50.0, rel=1e-1)
        assert sys.jev_failures_count == 1
        assert sys.fallback_frequency > 0
        assert sys.api_failures_count == 1
        assert sys.api_failure_rate == pytest.approx(1 / 3, rel=1e-2)


@pytest.mark.asyncio
class TestEvaluationApiEndpoints:
    async def test_get_evaluation_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/evaluation")
            assert res.status_code == 200
            data = res.json()
            assert "model_performance" in data
            assert "recommendation_performance" in data
            assert "system_performance" in data
            assert "disclaimer" in data

            # Check Model sub-metrics
            assert "inference_latency_ms" in data["model_performance"]["emotion"]
            assert "confidence_distribution" in data["model_performance"]["emotion"]
            assert "no_face_rate" in data["model_performance"]["emotion"]
            assert "stability_score" in data["model_performance"]["mood"]
            assert "transition_frequency_per_10m" in data["model_performance"]["mood"]
            assert "low_confidence_rate" in data["model_performance"]["mood"]

            # Check Rec sub-metrics
            assert "acceptance_rate" in data["recommendation_performance"]["recommendation"]
            assert "skip_rate" in data["recommendation_performance"]["recommendation"]
            assert "completion_rate" in data["recommendation_performance"]["recommendation"]
            assert "diversity_score" in data["recommendation_performance"]["recommendation"]
            assert "average_listening_duration_sec" in data["recommendation_performance"]["playback"]
            assert "skip_frequency_per_10m" in data["recommendation_performance"]["playback"]
            assert "transition_frequency_per_10m" in data["recommendation_performance"]["playback"]

            # Check System sub-metrics
            assert "jev_latency_ms" in data["system_performance"]
            assert "jev_failures_count" in data["system_performance"]
            assert "fallback_frequency" in data["system_performance"]
            assert "api_failures_count" in data["system_performance"]

    async def test_record_acceptance_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/evaluation/record-acceptance")
            assert res.status_code == 200
            assert res.json()["status"] == "recorded"

    async def test_reset_evaluation_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/evaluation/reset")
            assert res.status_code == 200
            assert res.json()["status"] == "reset_successful"
