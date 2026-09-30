"""Security and Privacy Automated Test Suite.
Verifies all findings documented in SECURITY_AUDIT.md.
"""
import pytest
from pydantic import ValidationError
from app.config import Settings
from app.schemas.camera import FrameDetectionRequest
from app.schemas.mood import MoodAnalysisRequest
from app.schemas.emotion import EmotionAnalyzeRequest
from app.api.v1.preferences import UserFeedbackActionRequest
from app.services.rate_limiter import InMemoryRateLimiter


def test_production_secret_key_validation():
    """SEC-01: Verifies that production rejects the insecure default SECRET_KEY."""
    # Production with default key should fail
    with pytest.raises(ValueError, match="Production deployment requires a secure"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="moodtune-dev-insecure-secret-key-change-in-prod"
        )

    # Production with short key should fail
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="too-short-secret"
        )

    # Production with strong 32+ char key should succeed
    valid_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a-very-long-and-cryptographically-secure-secret-key-12345"
    )
    assert valid_settings.ENVIRONMENT == "production"


def test_cors_wildcard_filtering():
    """SEC-03: Verifies that wildcard '*' is stripped when credentials are used."""
    settings = Settings(
        CORS_ORIGINS=["*", "http://localhost:5173"]
    )
    assert "*" not in settings.CORS_ORIGINS
    assert "http://localhost:5173" in settings.CORS_ORIGINS


def test_base64_payload_size_rejection():
    """SEC-04: Verifies rejection of unbounded base64 strings (> 7MB)."""
    oversized_payload = "A" * 7_000_001

    with pytest.raises(ValidationError):
        FrameDetectionRequest(image_base64=oversized_payload)

    with pytest.raises(ValidationError):
        MoodAnalysisRequest(image_base64=oversized_payload)

    with pytest.raises(ValidationError):
        EmotionAnalyzeRequest(image_base64=oversized_payload)


def test_feedback_action_validation():
    """SEC-06: Verifies validation of allowed user feedback actions."""
    # Valid actions
    for action in ["like", "dislike", "skip", "play", "complete"]:
        req = UserFeedbackActionRequest(track_id="t1", action=action)
        assert req.action == action

    # Invalid action should fail validation
    with pytest.raises(ValidationError):
        UserFeedbackActionRequest(track_id="t1", action="invalid_action_payload")


def test_rate_limiter():
    """SEC-09: Verifies that in-memory rate limiter throttles excessive calls."""
    limiter = InMemoryRateLimiter(max_requests_per_second=3)
    client_ip = "192.168.1.100"

    assert limiter.check(client_ip) is True
    assert limiter.check(client_ip) is True
    assert limiter.check(client_ip) is True
    # 4th request in the same second should be throttled
    assert limiter.check(client_ip) is False


@pytest.mark.asyncio
async def test_purge_expired_sessions_enforcement():
    """SEC-05: Verifies database retention purge function execution."""
    from app.database import AsyncSessionLocal, purge_expired_sessions

    async with AsyncSessionLocal() as session:
        count = await purge_expired_sessions(session, retention_days=7)
        assert isinstance(count, int)
