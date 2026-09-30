"""Unit tests for MusicProvider Layer (Phase 7).
Tests:
- MusicProvider interface adherence (search, get_track, get_recommendations, play, pause, resume, skip)
- Metadata-driven local catalog organization
- Playback state management (play, pause, resume, skip)
- Architecture for future providers & provider registry
- Unverified third-party provider safeguard
- API endpoints for music catalog and playback controls
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.music_provider import (
    MusicProvider,
    LocalMusicProvider,
    UnverifiedThirdPartyMusicProvider,
    provider_registry,
    music_provider
)
from app.schemas.music import MusicProfile, Track, PlaybackState


@pytest.fixture
def local_provider():
    return LocalMusicProvider()


class TestMusicProviderLayer:
    def test_music_provider_interface(self, local_provider):
        """Verifies that LocalMusicProvider implements all required MusicProvider methods."""
        assert isinstance(local_provider, MusicProvider)
        methods = ["search", "get_track", "get_recommendations", "play", "pause", "resume", "skip", "get_playback_state"]
        for m in methods:
            assert hasattr(local_provider, m) and callable(getattr(local_provider, m))

    def test_metadata_driven_catalog(self, local_provider):
        """Verifies local music is organized using rich metadata instead of folder-path logic."""
        catalog = local_provider._catalog
        assert len(catalog) >= 5

        for track in catalog:
            # Metadata schema verification
            assert track.id.startswith("trk_")
            assert track.title
            assert track.artist
            assert track.profile.genre
            assert 0.0 <= track.profile.energy <= 1.0
            assert 0.0 <= track.profile.valence <= 1.0
            assert 0.0 <= track.profile.tempo <= 1.0
            assert isinstance(track.profile.mood_tags, list)
            assert len(track.profile.mood_tags) > 0

    @pytest.mark.asyncio
    async def test_search_by_query_genre_and_energy(self, local_provider):
        """Verifies searching by text query, genre, and energy ranges."""
        # Query search
        results_synth = await local_provider.search(query="Chaiyya")
        assert len(results_synth) >= 1
        assert results_synth[0].title == "Chaiyya Chaiyya"

        # Genre search
        results_ambient = await local_provider.search(genre="ambient")
        assert len(results_ambient) >= 1
        for t in results_ambient:
            assert t.profile.genre == "ambient"

        # Energy range search
        results_high_energy = await local_provider.search(min_energy=0.80)
        assert len(results_high_energy) >= 1
        for t in results_high_energy:
            assert t.profile.energy >= 0.80

    @pytest.mark.asyncio
    async def test_get_track_found_and_not_found(self, local_provider):
        """Verifies track retrieval by ID and handling of non-existent IDs."""
        track = await local_provider.get_track("trk_upbeat_01")
        assert track is not None
        assert track.title == "Chaiyya Chaiyya"

        not_found = await local_provider.get_track("trk_nonexistent_999")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_playback_controls_lifecycle(self, local_provider):
        """Tests play -> pause -> resume -> skip playback control lifecycle."""
        # 1. Play
        state1 = await local_provider.play("trk_upbeat_01", position_seconds=15.0)
        assert state1.is_playing is True
        assert state1.current_track is not None
        assert state1.current_track.id == "trk_upbeat_01"
        assert state1.position_seconds == 15.0

        # 2. Pause
        state2 = await local_provider.pause()
        assert state2.is_playing is False
        assert state2.position_seconds == 15.0

        # 3. Resume
        state3 = await local_provider.resume()
        assert state3.is_playing is True
        assert state3.current_track.id == "trk_upbeat_01"

        # 4. Skip
        state4 = await local_provider.skip(current_track_id="trk_upbeat_01", seconds_played=120.0)
        assert state4.is_playing is True
        assert state4.current_track is not None
        assert state4.current_track.id != "trk_upbeat_01"
        assert state4.position_seconds == 0.0

    @pytest.mark.asyncio
    async def test_get_recommendations(self, local_provider):
        """Verifies get_recommendations returns tracks ranked by target profile."""
        target = MusicProfile(
            genre="synthwave",
            energy=0.90,
            valence=0.80,
            tempo=0.80,
            danceability=0.85,
            mood_tags=["energetic"]
        )
        recs = await local_provider.get_recommendations(target_profile=target, limit=3)
        assert len(recs) == 3
        # Top recommendation should have high energy
        assert recs[0].profile.energy >= 0.70

    def test_future_provider_registry(self):
        """Verifies that the provider registry allows registering and retrieving new providers."""
        class MockCustomProvider(MusicProvider):
            async def search(self, *args, **kwargs): return []
            async def get_track(self, track_id: str): return None
            async def get_recommendations(self, *args, **kwargs): return []
            async def play(self, track_id: str, position_seconds: float = 0.0): return PlaybackState()
            async def pause(self): return PlaybackState()
            async def resume(self): return PlaybackState()
            async def skip(self, *args, **kwargs): return PlaybackState()
            def get_playback_state(self): return PlaybackState()

        provider_registry.register("mock_custom", MockCustomProvider)
        instance = provider_registry.get_provider("mock_custom")
        assert isinstance(instance, MockCustomProvider)

    @pytest.mark.asyncio
    async def test_unverified_third_party_constraint(self):
        """Verifies that unverified third-party providers raise clean NotImplementedError."""
        unverified = UnverifiedThirdPartyMusicProvider("spotify")
        with pytest.raises(NotImplementedError) as exc_info:
            await unverified.search(query="test")
        assert "not yet been verified" in str(exc_info.value)
        assert "Use LocalMusicProvider" in str(exc_info.value)


class TestMusicApiEndpoints:
    @pytest.mark.asyncio
    async def test_play_pause_resume_endpoints(self):
        """Tests HTTP endpoints for /api/music/play, /pause, /resume, /skip, /playback."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Play
            play_resp = await client.post("/api/music/play", json={"track_id": "trk_upbeat_01", "position_seconds": 10.0})
            assert play_resp.status_code == 200
            data_play = play_resp.json()
            assert data_play["status"] == "playing"
            assert data_play["track"]["id"] == "trk_upbeat_01"

            # Get playback state
            pb_resp = await client.get("/api/music/playback")
            assert pb_resp.status_code == 200
            data_pb = pb_resp.json()
            assert data_pb["is_playing"] is True
            assert data_pb["current_track"]["id"] == "trk_upbeat_01"

            # Pause
            pause_resp = await client.post("/api/music/pause")
            assert pause_resp.status_code == 200
            assert pause_resp.json()["status"] == "paused"

            # Resume
            resume_resp = await client.post("/api/music/resume")
            assert resume_resp.status_code == 200
            assert resume_resp.json()["status"] == "playing"

            # Skip
            skip_resp = await client.post("/api/music/skip", json={"current_track_id": "trk_upbeat_01", "seconds_played": 30.0})
            assert skip_resp.status_code == 200
            assert skip_resp.json()["status"] == "skipped"
