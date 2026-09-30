"""Unit and Integration Tests for Real-Time Face Detection Pipeline (Phase 2)."""
import os
import numpy as np
import pytest
from unittest.mock import MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.face_detection_service import FaceDetectionService
from app.schemas.camera import FaceDetectionState


@pytest.fixture
def mock_detection_service():
    """Provides FaceDetectionService with mocked OpenCV cascade detection."""
    service = FaceDetectionService()
    return service


def test_camera_detection_no_face(mock_detection_service):
    """Test 1: No face state (blank image produces 0 faces)."""
    blank_frame = np.zeros((360, 480, 3), dtype=np.uint8)
    res = mock_detection_service.detect_faces(blank_frame)

    assert res.state == FaceDetectionState.NO_FACE
    assert res.face_count == 0
    assert res.primary_face is None
    assert "No face detected" in res.status_message


def test_camera_detection_none_input(mock_detection_service):
    """Test 2: Null frame input gracefully returns NO_FACE."""
    res = mock_detection_service.detect_faces(None)
    assert res.state == FaceDetectionState.NO_FACE
    assert res.face_count == 0


def test_camera_detection_corrupt_input(mock_detection_service):
    """Test 3: Corrupt base64 string returns ERROR state."""
    res = mock_detection_service.detect_faces("not_a_valid_image_base64")
    assert res.state == FaceDetectionState.ERROR
    assert res.error_message is not None


def test_camera_detection_single_face(monkeypatch):
    """Test 4: Exactly one face state."""
    service = FaceDetectionService()
    # Mock classifier to simulate 1 face detected
    mock_classifier = MagicMock()
    mock_classifier.detectMultiScale.return_value = np.array([[100, 100, 80, 80]])
    monkeypatch.setattr(service, "classifier", mock_classifier)

    dummy_frame = np.ones((360, 480, 3), dtype=np.uint8) * 128
    res = service.detect_faces(dummy_frame)

    assert res.state == FaceDetectionState.SINGLE_FACE
    assert res.face_count == 1
    assert res.primary_face is not None
    assert res.primary_face.x == 100
    assert res.primary_face.width == 80
    assert res.confidence >= 0.85
    assert "Single face detected" in res.status_message


def test_camera_detection_multiple_faces(monkeypatch):
    """Test 5: Multiple faces state with primary face prioritization."""
    service = FaceDetectionService()
    # Mock classifier to simulate 3 faces of varying sizes
    mock_classifier = MagicMock()
    mock_classifier.detectMultiScale.return_value = np.array([
        [50, 50, 60, 60],     # area = 3600
        [180, 120, 110, 110], # area = 12100 (largest / primary)
        [320, 60, 55, 55]     # area = 3025
    ])
    monkeypatch.setattr(service, "classifier", mock_classifier)

    dummy_frame = np.ones((360, 480, 3), dtype=np.uint8) * 128
    res = service.detect_faces(dummy_frame)

    assert res.state == FaceDetectionState.MULTIPLE_FACES
    assert res.face_count == 3
    assert len(res.all_faces) == 3
    assert res.primary_face is not None
    # Primary face should be the largest area one (x=180, w=110)
    assert res.primary_face.x == 180
    assert res.primary_face.width == 110
    assert "Multiple faces detected (3)" in res.status_message


def test_camera_in_memory_privacy_guarantee(mock_detection_service):
    """Test 6: Validates that frames are processed in-memory and never written to disk."""
    dummy_frame = np.zeros((200, 200, 3), dtype=np.uint8)
    initial_files = set(os.listdir("."))

    mock_detection_service.detect_faces(dummy_frame)

    current_files = set(os.listdir("."))
    # No new image files or temp dumps created
    assert current_files == initial_files


@pytest.mark.asyncio
async def test_camera_detect_api_endpoint():
    """Test 7: POST /api/camera/detect integration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send empty frame request
        res = await client.post("/api/camera/detect", json={"image_base64": None})
        assert res.status_code == 200
        data = res.json()
        assert data["state"] == "no_face"
        assert data["face_count"] == 0


@pytest.mark.asyncio
async def test_camera_status_api_endpoint():
    """Test 8: GET /api/camera/status integration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/camera/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert "in_memory_only" in data["storage_policy"]
