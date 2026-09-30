"""Unit tests for Phase 6 Music Recommendation Engine.
Tests:
- MusicProfileService profile synthesis & human-centered explanation
- CandidateRetrievalService filtering & diversity
- RecommendationScoringService configurable weights, skip penalty, and scoring formula
- RecommendationExplanation structure and reason_codes
- End-to-end pipeline execution and ranking
"""
import pytest
from app.services.music_profile_service import MusicProfileService
from app.services.candidate_retrieval_service import CandidateRetrievalService
from app.services.recommendation_scoring_service import RecommendationScoringService, ScoringWeights
from app.services.recommendation_engine import recommendation_engine
from app.schemas.mood import MoodState, MoodClass, EmotionProbabilities
from app.schemas.music import MusicProfile, Track, UserPreferenceSchema
from app.schemas.jev import (
    JevDecisionBundle,
    DecisionResultItem,
    ConfidenceTier
)


@pytest.fixture
def mock_jev_bundle():
    return JevDecisionBundle(
        mood=DecisionResultItem(value="positive", confidence=0.88),
        energy=DecisionResultItem(value="medium", confidence=0.85),
        transition=DecisionResultItem(value="continue", confidence=0.80),
        strategy=DecisionResultItem(value="mood_match", confidence=0.85),
        confidence_tier=ConfidenceTier.HIGH,
        decision_source="jev_system_one"
    )


@pytest.fixture
def sample_tracks():
    return [
        Track(
            id="trk_01",
            title="Sunny Lofi",
            artist="ChillBeat",
            duration_seconds=180,
            audio_url="https://audio.example.com/1.mp3",
            cover_art_url="https://art.example.com/1.jpg",
            profile=MusicProfile(
                genre="lofi",
                energy=0.50,
                valence=0.70,
                tempo=0.50,
                danceability=0.55,
                instrumental=0.80,
                mood_tags=["relaxing", "positive", "focus"]
            )
        ),
        Track(
            id="trk_02",
            title="High Voltage",
            artist="SynthRider",
            duration_seconds=210,
            audio_url="https://audio.example.com/2.mp3",
            cover_art_url="https://art.example.com/2.jpg",
            profile=MusicProfile(
                genre="synthwave",
                energy=0.90,
                valence=0.85,
                tempo=0.85,
                danceability=0.80,
                instrumental=0.50,
                mood_tags=["energetic", "driving"]
            )
        ),
        Track(
            id="trk_03",
            title="Deep Woods",
            artist="NatureSound",
            duration_seconds=300,
            audio_url="https://audio.example.com/3.mp3",
            cover_art_url="https://art.example.com/3.jpg",
            profile=MusicProfile(
                genre="ambient",
                energy=0.20,
                valence=0.40,
                tempo=0.30,
                danceability=0.20,
                instrumental=0.95,
                mood_tags=["calm", "peaceful"]
            )
        ),
    ]


class TestMusicProfileService:
    def test_synthesize_profile_fields_and_explanation(self, mock_jev_bundle):
        """Verifies synthesized profile contains all required fields and valid phrasing."""
        service = MusicProfileService()
        profile, explanation = service.synthesize_profile(
            stable_mood="positive",
            jev_decision=mock_jev_bundle,
            user_preferences=UserPreferenceSchema(preferred_genres=["lofi"], preferred_energy_bias=0.6)
        )

        assert profile.genre in ["upbeat_pop", "lofi"]
        assert 0.0 <= profile.energy <= 1.0
        assert 0.0 <= profile.valence <= 1.0
        assert 0.0 <= profile.tempo <= 1.0
        assert 0.0 <= profile.danceability <= 1.0
        assert 0.0 <= profile.instrumental <= 1.0
        assert len(profile.mood_tags) > 0

        # Human-centered phrasing verification
        assert "matches your current estimated mood" in explanation
        assert "This song will make you happy" not in explanation


class TestCandidateRetrievalService:
    @pytest.mark.asyncio
    async def test_filter_disliked_genres(self):
        """Verifies that disliked genres are completely filtered out of retrieved candidates."""
        service = CandidateRetrievalService()
        target = MusicProfile(genre="ambient", energy=0.25, valence=0.5, tempo=0.3, danceability=0.2)
        prefs = UserPreferenceSchema(disliked_genres=["ambient"])

        candidates = await service.retrieve_candidates(target_profile=target, user_preferences=prefs, limit=5)
        for t in candidates:
            assert t.profile.genre.lower() != "ambient"


class TestRecommendationScoringService:
    def test_scoring_weights_configurable(self):
        """Verifies that scoring weights are configurable and not hardcoded."""
        custom_weights = ScoringWeights(
            mood_match=0.50,
            energy_match=0.20,
            preference_match=0.10,
            diversity=0.10,
            freshness=0.10,
            recent_skip_penalty=0.50
        )
        service = RecommendationScoringService(weights=custom_weights)
        assert service.weights.mood_match == 0.50
        assert service.weights.recent_skip_penalty == 0.50

    def test_skip_penalty_decreases_score(self, sample_tracks):
        """A recently skipped track receives a lower score due to the penalty."""
        service = RecommendationScoringService()
        target = MusicProfile(genre="lofi", energy=0.50, valence=0.70, tempo=0.50, danceability=0.50)

        # Score without skips
        normal_scores = service.score_candidates(
            candidates=sample_tracks,
            target_profile=target
        )
        track_1_normal = next(s for s in normal_scores if s.track.id == "trk_01")

        # Score with trk_01 skipped
        penalized_scores = service.score_candidates(
            candidates=sample_tracks,
            target_profile=target,
            recent_skipped_ids=["trk_01"]
        )
        track_1_penalized = next(s for s in penalized_scores if s.track.id == "trk_01")

        assert track_1_penalized.match_score < track_1_normal.match_score

    def test_recommendation_explanation_codes(self, sample_tracks):
        """Validates structured RecommendationExplanation with reason_codes."""
        service = RecommendationScoringService()
        target = MusicProfile(
            genre="lofi",
            energy=0.50,
            valence=0.70,
            tempo=0.50,
            danceability=0.50,
            mood_tags=["positive", "relaxing"]
        )
        prefs = UserPreferenceSchema(preferred_genres=["lofi"])

        scored = service.score_candidates(
            candidates=sample_tracks,
            target_profile=target,
            user_preferences=prefs
        )
        top = scored[0]

        assert hasattr(top, "explanation")
        assert len(top.explanation.reason_codes) > 0
        assert "MOOD_MATCH" in top.explanation.reason_codes or "ENERGY_MATCH" in top.explanation.reason_codes
        assert "matches your current estimated mood" in top.explanation.human_summary
        assert "will make you happy" not in top.explanation.human_summary.lower()


class TestEndToEndRecommendationEngine:
    @pytest.mark.asyncio
    async def test_recommendations_energetic_mood(self):
        """Energetic mood outputs high energy tracks ranked by match score."""
        mood_state = MoodState(
            estimated_mood=MoodClass.ENERGETIC,
            mood_confidence=0.92,
            smoothed_emotion_probabilities=EmotionProbabilities(happy=0.88, surprise=0.10),
            is_stable=True,
            stable_duration_seconds=10.0
        )
        res = await recommendation_engine.generate_recommendations(
            mood_state=mood_state,
            limit=3
        )
        assert len(res.recommendations) > 0
        top_track = res.recommendations[0].track
        assert top_track.profile.energy >= 0.60
        assert res.target_profile.energy >= 0.65
        assert res.recommendations[0].explanation.reason_codes is not None

    @pytest.mark.asyncio
    async def test_recommendations_calm_mood(self):
        """Calm mood outputs relaxing, low-energy tracks ranked by match score."""
        mood_state = MoodState(
            estimated_mood=MoodClass.CALM,
            mood_confidence=0.85,
            smoothed_emotion_probabilities=EmotionProbabilities(neutral=0.80, happy=0.15),
            is_stable=True,
            stable_duration_seconds=8.0
        )
        res = await recommendation_engine.generate_recommendations(
            mood_state=mood_state,
            limit=3
        )
        top_track = res.recommendations[0].track
        assert top_track.profile.energy <= 0.55
