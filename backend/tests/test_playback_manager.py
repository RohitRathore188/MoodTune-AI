"""Unit tests for Phase 8: Intelligent Playback & PlaybackManager.
Verifies:
- Stable mood transition behavior
- Unstable mood prevention (mood changes do NOT immediately change the song)
- Compatible song continuation
- Incompatible song transition execution
- User skip handling & personalization penalty
- Manual pause suppression of auto-transitions
- Transition cooldown / anti-thrashing enforcement
- Queue management and next track sequencing
- API endpoints for playback, queue, and transition evaluation
"""
import time
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings
from app.services.playback_manager import PlaybackManager
from app.services.music_provider import LocalMusicProvider
from app.services.jev_service import JevDecisionService
from app.services.personalization_service import PersonalizationService
from app.schemas.music import Track, MusicProfile, PlaybackState


@pytest.fixture
def provider():
    return LocalMusicProvider()


@pytest.fixture
def playback_mgr(provider):
    personalization = PersonalizationService()
    jev = JevDecisionService()
    mgr = PlaybackManager(provider=provider, jev=jev, personalization=personalization)
    return mgr


@pytest.mark.asyncio
class TestPlaybackManager:
    async def test_queue_management_and_sequencing(self, playback_mgr, provider):
        """Verifies queue operations: add, set, remove, clear, next_track."""
        tracks = await provider.search(limit=3)
        assert len(tracks) >= 3

        # Add tracks
        playback_mgr.clear_queue()
        playback_mgr.add_to_queue(tracks[0])
        playback_mgr.add_to_queue(tracks[1])
        assert len(playback_mgr.get_queue()) == 2

        # Avoid duplicates
        playback_mgr.add_to_queue(tracks[0])
        assert len(playback_mgr.get_queue()) == 2

        # Remove from queue
        removed = playback_mgr.remove_from_queue(tracks[0].id)
        assert removed is not None
        assert removed.id == tracks[0].id
        assert len(playback_mgr.get_queue()) == 1

        # Advance to next track
        next_trk = await playback_mgr.next_track(reason="test")
        assert next_trk.id == tracks[1].id
        state = playback_mgr.get_playback_state()
        assert state.is_playing is True
        assert state.current_track.id == tracks[1].id

    async def test_stable_mood_with_incompatible_song_triggers_transition(self, playback_mgr, provider):
        """
        When mood has remained stable and the current song is strongly incompatible,
        playback must transition to the next track in queue.
        """
        # Current song: low energy ambient (0.18)
        calm_track = await provider.get_track("trk_low_01")
        assert calm_track is not None
        await playback_mgr.play(calm_track.id, position_seconds=40.0)

        # Queue upcoming energetic track
        energetic_track = await provider.get_track("trk_upbeat_01")
        playback_mgr.set_queue([energetic_track])

        # Allow cooldown to be inactive
        playback_mgr.last_transition_timestamp = time.time() - 60.0

        # Stable energetic mood (energy ~0.88 vs song 0.18)
        decision = await playback_mgr.evaluate_transition(
            current_mood="energetic",
            mood_confidence=0.88,
            mood_stability=15.0,  # 15s stable (> 3s threshold)
            is_stable=True,
            current_track_progress=40.0,
            auto_execute=True
        )

        assert decision.action == "transition"
        assert decision.is_compatible is False
        assert decision.transition_executed is True
        assert decision.next_track is not None
        assert decision.next_track.id == energetic_track.id

        # Verify playback state updated
        state = playback_mgr.get_playback_state()
        assert state.current_track.id == energetic_track.id
        assert state.is_playing is True

    async def test_unstable_mood_does_not_transition(self, playback_mgr, provider):
        """
        IMPORTANT: Mood changes must NOT immediately change the song!
        If mood is unstable, fluctuating, or low confidence, playback must continue.
        """
        # Current song: calm (0.22)
        calm_track = await provider.get_track("trk_calm_01")
        await playback_mgr.play(calm_track.id, position_seconds=35.0)

        # Case 1: is_stable is False
        dec1 = await playback_mgr.evaluate_transition(
            current_mood="energetic",
            mood_confidence=0.85,
            mood_stability=1.0,
            is_stable=False,
            auto_execute=True
        )
        assert dec1.action == "continue"
        assert "unstable" in dec1.reason.lower()
        assert dec1.transition_executed is False

        # Case 2: stable_duration < MOOD_MIN_STABLE_DURATION (3.0s)
        dec2 = await playback_mgr.evaluate_transition(
            current_mood="energetic",
            mood_confidence=0.85,
            mood_stability=1.5,
            is_stable=True,
            auto_execute=True
        )
        assert dec2.action == "continue"
        assert "unstable" in dec2.reason.lower()

        # Case 3: mood_confidence < MOOD_CONFIDENCE_THRESHOLD (0.60)
        dec3 = await playback_mgr.evaluate_transition(
            current_mood="energetic",
            mood_confidence=0.45,
            mood_stability=10.0,
            is_stable=True,
            auto_execute=True
        )
        assert dec3.action == "continue"
        assert "unstable" in dec3.reason.lower()

        # Verify current track is still playing unchanged
        state = playback_mgr.get_playback_state()
        assert state.current_track.id == calm_track.id

    async def test_compatible_song_continues_playback(self, playback_mgr, provider):
        """
        Example from specification:
        Current song: energy = 0.45 ("Subtle Equilibrium")
        New mood: energy = 0.75 ("positive")
        If current song is still compatible: continue
        """
        track = await provider.get_track("trk_neutral_01")
        assert track is not None
        assert track.profile.energy == 0.45
        await playback_mgr.play(track.id, position_seconds=45.0)

        # Clear cooldown
        playback_mgr.last_transition_timestamp = time.time() - 60.0

        # Stable mood shift to "positive"
        decision = await playback_mgr.evaluate_transition(
            current_mood="positive",
            mood_confidence=0.85,
            mood_stability=12.0,
            is_stable=True,
            current_track_progress=45.0,
            auto_execute=True
        )

        assert decision.action == "continue"
        assert decision.is_compatible is True
        assert decision.compatibility_score >= 0.55
        assert decision.transition_executed is False

        # Still playing the same track
        state = playback_mgr.get_playback_state()
        assert state.current_track.id == "trk_neutral_01"

    async def test_incompatible_song_triggers_transition(self, playback_mgr, provider):
        """
        Current song: meditation/ambient (energy = 0.15)
        New mood: energetic (energy = 0.88)
        If mood has remained stable and song is strongly incompatible: transition
        """
        track_tense = await provider.get_track("trk_tense_01")  # energy 0.15
        await playback_mgr.play(track_tense.id, position_seconds=50.0)

        # Queue energetic candidate
        upbeat = await provider.get_track("trk_upbeat_02")
        playback_mgr.set_queue([upbeat])
        playback_mgr.last_transition_timestamp = time.time() - 60.0

        decision = await playback_mgr.evaluate_transition(
            current_mood="energetic",
            mood_confidence=0.90,
            mood_stability=15.0,
            is_stable=True,
            current_track_progress=50.0,
            auto_execute=True
        )

        assert decision.action == "transition"
        assert decision.is_compatible is False
        assert decision.compatibility_score < 0.50
        assert decision.transition_executed is True
        assert decision.next_track.id == upbeat.id

    async def test_user_skip_immediately_advances_and_penalizes(self, playback_mgr, provider):
        """
        User skip:
        - Bypasses mood stability and compatibility checks
        - Immediately advances track
        - Records skip penalty in personalization
        """
        track1 = await provider.get_track("trk_upbeat_01")
        track2 = await provider.get_track("trk_upbeat_02")
        playback_mgr.set_queue([track2])

        await playback_mgr.play(track1.id, position_seconds=10.0)
        assert playback_mgr.get_playback_state().current_track.id == track1.id

        # User clicks skip
        state = await playback_mgr.skip(reason="user_skip")

        # Track immediately switched to track2
        assert state.current_track.id == track2.id
        assert state.is_playing is True

        # Verify skip penalty registered in personalization
        stats = playback_mgr.personalization.get_recent_stats("default_user")
        assert stats["recent_skips"] >= 1
        assert track1.id in stats["recent_skipped_ids"]

    async def test_manual_pause_suppresses_auto_transition(self, playback_mgr, provider):
        """
        When playback is manually paused by user:
        - Auto-transitions must be suppressed
        - Playback must NOT automatically resume
        """
        track = await provider.get_track("trk_calm_01")
        await playback_mgr.play(track.id, position_seconds=20.0)

        # User manually pauses
        pause_state = await playback_mgr.pause()
        assert pause_state.is_playing is False
        assert playback_mgr.manual_pause is True

        # Even with stable incompatible mood, auto-transition must be suppressed
        decision = await playback_mgr.evaluate_transition(
            current_mood="energetic",
            mood_confidence=0.95,
            mood_stability=30.0,
            is_stable=True,
            auto_execute=True
        )

        assert decision.action == "continue"
        assert "manual pause" in decision.reason.lower()
        assert decision.transition_executed is False

        # State remains paused
        state = playback_mgr.get_playback_state()
        assert state.is_playing is False

        # Resume restores playback and clears manual pause
        resume_state = await playback_mgr.resume()
        assert resume_state.is_playing is True
        assert playback_mgr.manual_pause is False

    async def test_transition_cooldown_prevents_frequent_switching(self, playback_mgr, provider):
        """
        Transition cooldown:
        Prevents frequent switching/thrashing when a transition recently occurred.
        """
        track = await provider.get_track("trk_calm_02")
        await playback_mgr.play(track.id, position_seconds=10.0)

        # Simulate that a transition happened 5 seconds ago (cooldown is 30s)
        playback_mgr.last_transition_timestamp = time.time() - 5.0

        decision = await playback_mgr.evaluate_transition(
            current_mood="energetic",
            mood_confidence=0.90,
            mood_stability=15.0,
            is_stable=True,
            auto_execute=True
        )

        assert decision.action == "continue"
        assert "cooldown" in decision.reason.lower()
        assert decision.cooldown_remaining_seconds > 0.0
        assert decision.transition_executed is False


class TestPlaybackApiEndpoints:
    @pytest.mark.asyncio
    async def test_evaluate_transition_endpoint(self):
        """Tests the POST /api/music/evaluate-transition API."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/music/evaluate-transition",
                json={
                    "current_mood": "positive",
                    "mood_confidence": 0.85,
                    "mood_stability": 8.0,
                    "is_stable": True,
                    "auto_execute": False
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "action" in data
            assert "reason" in data
            assert "compatibility_score" in data
            assert "is_compatible" in data

    @pytest.mark.asyncio
    async def test_queue_and_playback_state_endpoints(self):
        """Tests GET /api/music/queue, POST /api/music/queue/add, and GET /api/music/playback."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Add track to queue
            add_resp = await client.post(
                "/api/music/queue/add",
                json={"track_id": "trk_upbeat_01", "prepend": False}
            )
            assert add_resp.status_code == 200
            assert add_resp.json()["status"] == "added"

            # Check queue endpoint
            queue_resp = await client.get("/api/music/queue")
            assert queue_resp.status_code == 200
            queue_data = queue_resp.json()
            assert any(t["id"] == "trk_upbeat_01" for t in queue_data)

            # Check enriched playback state
            pb_resp = await client.get("/api/music/playback")
            assert pb_resp.status_code == 200
            pb_data = pb_resp.json()
            assert "queue" in pb_data
            assert "manual_pause" in pb_data
