"""Integration tests for FastAPI endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "ai_providers" in data


@pytest.mark.asyncio
async def test_mood_analyze_manual_override():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"manual_mood_override": "calm", "session_id": "test_api_sess"}
        response = await client.post("/api/mood/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["face_detection"]["detected"] is True
        assert data["mood_state"]["estimated_mood"] == "calm"
        assert "explanation" in data


@pytest.mark.asyncio
async def test_recommendations_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/recommendations?mood=energetic&confidence=0.88&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) > 0
        assert data["jev_decision"]["mood"]["value"] == "energetic"


@pytest.mark.asyncio
async def test_music_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/music/tracks")
        assert response.status_code == 200
        tracks = response.json()
        assert len(tracks) > 5


@pytest.mark.asyncio
async def test_history_clear_privacy():
    """Privacy control test: Clear history wipes data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/history/clear?session_id=test_api_sess")
        assert response.status_code == 200
        assert response.json()["status"] == "cleared"


@pytest.mark.asyncio
async def test_camera_status_and_detect_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Status
        status_res = await client.get("/api/camera/status")
        assert status_res.status_code == 200
        assert status_res.json()["storage_policy"] == "in_memory_only (never saved to disk/db)"

        # Detect
        detect_res = await client.post("/api/camera/detect", json={"image_base64": None})
        assert detect_res.status_code == 200
        assert detect_res.json()["state"] == "no_face"


@pytest.mark.asyncio
async def test_evaluation_dashboard_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/evaluation")
        assert res.status_code == 200
        data = res.json()
        assert "model_performance" in data
        assert "recommendation_performance" in data
        assert "system_performance" in data


@pytest.mark.asyncio
async def test_preferences_lifecycle_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        get_res = await client.get("/api/preferences?user_id=test_api_user")
        assert get_res.status_code == 200

        # Feedback
        fb_res = await client.post("/api/preferences/feedback?user_id=test_api_user", json={
            "track_id": "trk_upbeat_01",
            "action": "like",
            "seconds_played": 10.0
        })
        assert fb_res.status_code == 200
        assert fb_res.json()["total_liked"] >= 1
