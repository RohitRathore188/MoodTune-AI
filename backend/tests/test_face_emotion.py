"""Unit tests for Face Detection and Visible Affect Estimation."""
import numpy as np
import pytest
from app.services.face_emotion_service import face_emotion_service
from app.schemas.mood import MoodClass


def test_face_emotion_manual_override():
    """Manual mood override when camera is disabled."""
    result = face_emotion_service.analyze_frame(manual_override=MoodClass.POSITIVE)
    assert result.detected is True
    assert result.confidence >= 0.8
    assert result.emotion_probabilities.happy > 0.7
    assert result.expression_estimate == "happy"


def test_face_emotion_no_input():
    """Graceful handling when no frame is supplied."""
    result = face_emotion_service.analyze_frame(image_input=None)
    assert result.detected is False
    assert result.confidence < 0.3
    assert result.face_count == 0


def test_face_emotion_synthetic_blank_frame():
    """Synthetic blank black frame should gracefully return no face detected."""
    blank_img = np.zeros((300, 300, 3), dtype=np.uint8)
    result = face_emotion_service.analyze_frame(image_input=blank_img)
    assert result.detected is False
    assert result.face_count == 0
    assert result.confidence < 0.3
