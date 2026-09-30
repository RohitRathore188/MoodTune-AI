"""System Foundation Integration Test."""
import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from app.config import settings


@pytest.mark.asyncio
async def test_foundation_health_check():
    """Validates that GET /api/health returns healthy with expected structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == settings.PROJECT_NAME
        assert "ai_providers" in data
        assert data["ai_providers"]["camera_cv"]["storage_policy"].startswith("in_memory_only")


@pytest.mark.asyncio
async def test_root_metadata_endpoint():
    """Validates root endpoint contains project tagline and health link."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["tagline"] == "Your mood. Your music."
        assert "/api/health" in data["health"]
