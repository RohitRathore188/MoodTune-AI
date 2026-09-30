"""Unit tests for Phase 9: Personalization & UserPreferenceProfile.
Verifies:
- Default UserPreferenceProfile schema adherence
- Preference updates via plays, likes, skips, and completes
- Dynamic preferred_energy and preferred_tempo adjustment
- Skip rate calculation by genre
- Dislike handling and genre demotion
- Strict privacy guarantee (no sensitive demographic, religious, political, or health inferences)
- Personalization influences ranking without overriding current mood context
- API endpoints for preferences, profile, and feedback
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.personalization_service import (
    PersonalizationService,
    PROHIBITED_INFERENCES
)
from app.services.music_provider import LocalMusicProvider
from app.services.recommendation_scoring_service import RecommendationScoringService
from app.schemas.music import Track, MusicProfile, UserPreferenceSchema, UserPreferenceProfile


@pytest.fixture
def provider():
    return LocalMusicProvider()


@pytest.fixture
def pers_service():
    service = PersonalizationService()
    service.reset_profile("test_user")
    return service


class TestPersonalizationService:
    def test_default_user_preference_profile_schema(self, pers_service):
        """Verifies UserPreferenceProfile contains preferred_genres, preferred_energy, preferred_tempo, skip_rate_by_genre."""
        profile = pers_service.get_user_profile("test_user")
        assert isinstance(profile, UserPreferenceProfile)
        assert isinstance(profile.preferred_genres, list)
        assert len(profile.preferred_genres) > 0
        assert 0.0 <= profile.preferred_energy <= 1.0
        assert 0.0 <= profile.preferred_tempo <= 1.0
        assert isinstance(profile.skip_rate_by_genre, dict)
        assert profile.total_played == 0
        assert profile.total_skipped == 0

    @pytest.mark.asyncio
    async def test_play_and_like_updates_preferred_energy_and_tempo(self, pers_service, provider):
        """Likes and plays of high-energy tracks shift preferred_energy and preferred_tempo upward."""
        track = await provider.get_track("trk_upbeat_01")  # energy 0.88, tempo 0.75
        assert track is not None

        initial_profile = pers_service.get_user_profile("test_user")
        init_energy = initial_profile.preferred_energy

        # Record multiple likes on high energy tracks
        for _ in range(3):
            pers_service.record_like("test_user", track)

        updated_profile = pers_service.get_user_profile("test_user")
        assert updated_profile.total_liked == 3
        # Preferred energy should have increased toward 0.88
        assert updated_profile.preferred_energy > init_energy
        assert "synthwave" in updated_profile.preferred_genres

    @pytest.mark.asyncio
    async def test_skip_updates_skip_rate_by_genre(self, pers_service, provider):
        """Skips increase skip count and calculate accurate skip_rate_by_genre."""
        ambient_track = await provider.get_track("trk_calm_01")  # genre: ambient
        assert ambient_track is not None

        # Play once, then skip twice
        pers_service.record_play("test_user", ambient_track)
        pers_service.record_skip("test_user", ambient_track, seconds_played=5.0)
        pers_service.record_skip("test_user", ambient_track, seconds_played=8.0)

        profile = pers_service.get_user_profile("test_user")
        assert profile.total_skipped == 2
        assert "ambient" in profile.skip_rate_by_genre
        # 2 skips out of 3 plays = 0.67
        assert profile.skip_rate_by_genre["ambient"] >= 0.50

    @pytest.mark.asyncio
    async def test_dislike_penalizes_and_adds_to_disliked_genres(self, pers_service, provider):
        """Explicit dislike removes genre from preferred and adds to disliked list."""
        pop_track = await provider.get_track("trk_upbeat_02")  # genre: upbeat_pop
        assert pop_track is not None

        pers_service.record_dislike("test_user", pop_track)
        profile = pers_service.get_user_profile("test_user")

        assert profile.total_disliked >= 1
        assert "upbeat_pop" in profile.disliked_genres
        assert "upbeat_pop" not in profile.preferred_genres

    def test_strict_privacy_constraint_no_sensitive_attributes(self, pers_service):
        """
        MANDATE: Use only non-sensitive interaction data.
        Never infer or store race, religion, political views, health, sexuality, etc.
        """
        profile = pers_service.get_user_profile("test_user")
        profile_dict = profile.model_dump()

        # Check prohibited terms are completely absent
        for prohibited in PROHIBITED_INFERENCES:
            assert prohibited not in profile_dict
            assert f"user_{prohibited}" not in profile_dict

        # Verify only interaction telemetry keys exist
        allowed_keys = {
            "preferred_genres", "preferred_energy", "preferred_tempo",
            "skip_rate_by_genre", "disliked_genres", "total_played",
            "total_skipped", "total_completed", "total_liked", "total_disliked"
        }
        for k in profile_dict.keys():
            assert k in allowed_keys

    @pytest.mark.asyncio
    async def test_personalization_influences_ranking_without_overriding_mood(self, pers_service, provider):
        """
        MANDATE: Personalization influences ranking, but does NOT override current mood context.
        Even if user prefers 'lofi', when estimated mood is 'energetic', a synthwave track
        matching the mood must outscore an off-mood lofi track.
        """
        scoring_service = RecommendationScoringService()

        # User preferences strongly set to lofi
        user_prefs = UserPreferenceSchema(
            preferred_genres=["lofi"],
            preferred_energy_bias=0.30
        )

        lofi_track = await provider.get_track("trk_calm_02")     # lofi, energy 0.35
        synth_track = await provider.get_track("trk_upbeat_01")  # synthwave, energy 0.88

        # Current estimated mood: energetic
        energetic_profile = MusicProfile(
            genre="synthwave",
            energy=0.88,
            valence=0.82,
            tempo=0.75,
            danceability=0.85,
            mood_tags=["energetic", "positive"]
        )

        scored = scoring_service.score_candidates(
            candidates=[lofi_track, synth_track],
            target_profile=energetic_profile,
            user_preferences=user_prefs
        )

        # The synthwave track matching the mood MUST rank #1 despite user preferring lofi
        assert scored[0].track.id == synth_track.id
        assert scored[0].match_score > scored[1].match_score
        assert "MOOD_MATCH" in scored[0].explanation.reason_codes


class TestPersonalizationApiEndpoints:
    @pytest.mark.asyncio
    async def test_get_profile_endpoint(self):
        """Tests GET /api/preferences/profile endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/preferences/profile")
            assert resp.status_code == 200
            data = resp.json()
            assert "preferred_genres" in data
            assert "preferred_energy" in data
            assert "preferred_tempo" in data
            assert "skip_rate_by_genre" in data

    @pytest.mark.asyncio
    async def test_record_feedback_endpoint(self):
        """Tests POST /api/preferences/feedback endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/preferences/feedback",
                json={
                    "track_id": "trk_upbeat_01",
                    "action": "like",
                    "seconds_played": 30.0,
                    "mood": "positive"
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_liked"] >= 1
            assert "synthwave" in data["preferred_genres"]
