"""Unit tests for EmotionDetectionService (Phase 3).
Tests:
- Output schema conforms to required keys (emotions, dominant_emotion, confidence)
- Human-centered assertion: "estimated facial expression"
- Probabilities validity (in [0, 1] and sums to 1.0)
- Confidence validity (in [0, 1])
- Missing faces handled gracefully
- Corrupt/empty frames handled gracefully
- Model errors handled gracefully
- Inference timeouts handled gracefully
- Controlled/mock model outputs for all 7 emotions
- API endpoint /api/v1/emotion/detect
"""
import base64
import numpy as np
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.camera import FaceDetectionResult, FaceDetectionState, BoundingBox
from app.schemas.emotion import EmotionsDistribution, EmotionEstimationResponse
from app.services.emotion_detection_service import (
    EmotionDetectionService,
    MockEmotionModel,
    VALID_EMOTIONS,
    FacialExpressionFeatureModel,
    EmotionResult
)


class MockFaceDetector:
    """Configurable mock for FaceDetectionService."""
    def __init__(self, has_face: bool = True, face_count: int = 1):
        self.has_face = has_face
        self.face_count = face_count

    def detect_faces(self, frame) -> FaceDetectionResult:
        if not self.has_face:
            return FaceDetectionResult(
                state=FaceDetectionState.NO_FACE,
                face_count=0,
                confidence=0.0,
                status_message="No face detected in test"
            )
        return FaceDetectionResult(
            state=FaceDetectionState.SINGLE_FACE if self.face_count == 1 else FaceDetectionState.MULTIPLE_FACES,
            face_count=self.face_count,
            primary_face=BoundingBox(x=10, y=10, width=80, height=80),
            confidence=0.95,
            status_message="Test face detected"
        )


@pytest.fixture
def dummy_frame():
    return np.zeros((120, 120, 3), dtype=np.uint8)


class TestEmotionDetectionService:
    def test_output_schema_structure(self, dummy_frame):
        """Verify the exact output structure matches Phase 3 specification."""
        service = EmotionDetectionService()
        result = service.estimate_emotion(dummy_frame)

        # Core required fields
        assert "emotions" in result
        assert "dominant_emotion" in result
        assert "confidence" in result

        # Verify 7 emotions
        for emo in ("happy", "sad", "angry", "neutral", "fear", "surprise", "disgust"):
            assert emo in result["emotions"]

        # Human-centered wording
        assert result["expression_type"] == "estimated facial expression"

    def test_probabilities_are_valid_and_normalized(self, dummy_frame):
        """All probabilities must be between 0 and 1, and sum to 1.0."""
        mock_model = MockEmotionModel({
            "happy": 0.40,
            "sad": 0.10,
            "angry": 0.10,
            "neutral": 0.20,
            "fear": 0.05,
            "surprise": 0.10,
            "disgust": 0.05
        })
        service = EmotionDetectionService(
            face_detector=MockFaceDetector(has_face=True),
            model_backend=mock_model
        )
        res = service.estimate_emotion(dummy_frame)

        prob_sum = 0.0
        for emo, prob in res["emotions"].items():
            assert 0.0 <= prob <= 1.0, f"Probability for {emo} out of bounds: {prob}"
            prob_sum += prob

        assert abs(prob_sum - 1.0) < 0.002, f"Probabilities do not sum to 1.0: {prob_sum}"

    def test_confidence_bounded_zero_to_one(self, dummy_frame):
        """Confidence score must strictly remain in [0.0, 1.0]."""
        mock_model = MockEmotionModel({"happy": 0.99, "neutral": 0.01})
        service = EmotionDetectionService(
            face_detector=MockFaceDetector(has_face=True),
            model_backend=mock_model
        )
        res = service.estimate_emotion(dummy_frame)
        assert 0.0 <= res["confidence"] <= 1.0
        assert 0.0 <= res.confidence <= 1.0

    def test_missing_face_handled_gracefully(self, dummy_frame):
        """When no face is detected, confidence is 0.0 and safe neutral fallback is returned."""
        service = EmotionDetectionService(
            face_detector=MockFaceDetector(has_face=False)
        )
        res = service.estimate_emotion(dummy_frame)

        assert res["face_detected"] is False
        assert res["confidence"] == 0.0
        assert res["dominant_emotion"] == "neutral"
        assert res["emotions"]["neutral"] == 1.0
        assert res["expression_type"] == "estimated facial expression"

    def test_none_and_empty_inputs_handled(self):
        """None or empty string input must return safe fallback without crashing."""
        service = EmotionDetectionService()

        res_none = service.estimate_emotion(None)
        assert res_none["confidence"] == 0.0
        assert res_none["dominant_emotion"] == "neutral"

        res_empty = service.estimate_emotion("")
        assert res_empty["confidence"] == 0.0
        assert res_empty["dominant_emotion"] == "neutral"

        res_corrupt = service.estimate_emotion("not-a-valid-base64-image-content!!")
        assert res_corrupt["confidence"] == 0.0
        assert res_corrupt["dominant_emotion"] == "neutral"

    def test_model_errors_handled_gracefully(self, dummy_frame):
        """Exceptions in model inference are caught and safely return fallback."""
        mock_broken_model = MockEmotionModel(raise_error=True, error_message="Fatal GPU OOM")
        service = EmotionDetectionService(
            face_detector=MockFaceDetector(has_face=True),
            model_backend=mock_broken_model
        )
        res = service.estimate_emotion(dummy_frame)

        assert res["confidence"] == 0.0
        assert res["dominant_emotion"] == "neutral"
        assert "Model error" in res["status_message"]

    def test_inference_timeout_handled(self, dummy_frame):
        """Inference taking longer than timeout threshold is aborted and returns fallback."""
        slow_model = MockEmotionModel(delay_seconds=0.3)
        service = EmotionDetectionService(
            face_detector=MockFaceDetector(has_face=True),
            model_backend=slow_model,
            default_timeout_seconds=0.05
        )
        res = service.estimate_emotion(dummy_frame, timeout_seconds=0.05)

        assert res["confidence"] == 0.0
        assert res["dominant_emotion"] == "neutral"
        assert "timeout" in res["status_message"].lower()

    @pytest.mark.parametrize("target_emotion", [
        "happy", "sad", "angry", "neutral", "fear", "surprise", "disgust"
    ])
    def test_controlled_mock_model_outputs(self, dummy_frame, target_emotion):
        """Verify each of the 7 emotions behaves deterministically under controlled mock."""
        mock_probs = {e: 0.05 for e in VALID_EMOTIONS}
        mock_probs[target_emotion] = 0.70

        mock_model = MockEmotionModel(fixed_emotions=mock_probs)
        service = EmotionDetectionService(
            face_detector=MockFaceDetector(has_face=True),
            model_backend=mock_model
        )
        res = service.estimate_emotion(dummy_frame)

        assert res["dominant_emotion"] == target_emotion
        assert res["emotions"][target_emotion] > 0.50
        assert 0.0 <= res["confidence"] <= 1.0

    def test_emotions_distribution_sanitization(self):
        """EmotionsDistribution Pydantic model sanitizes unnormalized values."""
        dist = EmotionsDistribution(happy=2.0, sad=1.0)
        dumped = dist.to_dict()
        assert abs(sum(dumped.values()) - 1.0) < 0.001
        assert dumped["happy"] > dumped["sad"]


class TestEmotionApiEndpoint:
    @pytest.mark.asyncio
    async def test_detect_emotion_no_face_endpoint(self):
        """POST /api/v1/emotion/detect with empty frame returns safe fallback."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/emotion/detect", json={"image_base64": None})
            assert resp.status_code == 200
            data = resp.json()
            assert "emotions" in data
            assert data["dominant_emotion"] == "neutral"
            assert data["confidence"] == 0.0
            assert data["expression_type"] == "estimated facial expression"

    @pytest.mark.asyncio
    async def test_detect_emotion_valid_base64_endpoint(self):
        """POST /api/v1/emotion/detect with valid encoded frame returns structured response."""
        # Create small test black PNG image
        import cv2
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buffer = cv2.imencode(".jpg", img)
        b64 = base64.b64encode(buffer).decode("utf-8")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/emotion/detect", json={"image_base64": b64})
            assert resp.status_code == 200
            data = resp.json()
            assert "emotions" in data
            assert "dominant_emotion" in data
            assert 0.0 <= data["confidence"] <= 1.0
            assert data["expression_type"] == "estimated facial expression"
