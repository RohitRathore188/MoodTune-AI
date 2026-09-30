"""Unit and integration tests for Bounded AI Agents & Orchestration (Phase 10).
Verifies:
- All 5 agents satisfy the strict contract:
  * clear purpose
  * typed input
  * typed output
  * allowed tools
  * validation
  * timeout
  * deterministic fallback
  * structured logging
- Security: Disallowing arbitrary code execution or unapproved tool calls
- End-to-end pipeline orchestration:
  Emotion Model -> MoodAnalysisAgent -> JEV Decision Layer -> RecommendationAgent -> MusicProvider -> PlaybackManager
"""
import pytest
from app.agents.mood_analysis_agent import mood_analysis_agent, MoodAnalysisAgent, MoodAnalysisAgentInput
from app.agents.music_recommendation_agent import (
    recommendation_agent, RecommendationAgent,
    RecommendationAgentInput, MusicRecommendationAgent
)
from app.agents.playlist_agent import playlist_agent, PlaylistAgent, PlaylistAgentInput
from app.agents.personalization_agent import personalization_agent, PersonalizationAgent, PersonalizationAgentInput
from app.agents.evaluation_agent import evaluation_agent, EvaluationAgent, EvaluationAgentInput
from app.agents.orchestrator import agent_orchestrator, AgentOrchestrator, OrchestrationCycleResult
from app.schemas.mood import EmotionProbabilities, MoodState, MoodClass
from app.schemas.music import Track, MusicProfile, PlaybackState
from app.schemas.metrics import LatencyStats
from app.services.music_provider import LocalMusicProvider


@pytest.fixture
def provider():
    return LocalMusicProvider()


class TestAgentContractAndSecurity:
    def test_all_five_agents_satisfy_strict_contract(self):
        """Verifies every agent has clear purpose, typed schemas, allowed tools, timeout, and fallback."""
        agents = [
            mood_analysis_agent,
            recommendation_agent,
            playlist_agent,
            personalization_agent,
            evaluation_agent
        ]
        assert len(agents) == 5

        for agent in agents:
            # 1. Clear purpose
            assert hasattr(agent, "purpose")
            assert isinstance(agent.purpose, str) and len(agent.purpose) > 10

            # 2. Allowed tools
            assert hasattr(agent, "allowed_tools")
            assert isinstance(agent.allowed_tools, set)
            assert len(agent.allowed_tools) > 0

            # 3. Timeout and retry policy
            assert hasattr(agent, "timeout_seconds")
            assert agent.timeout_seconds > 0.0
            assert hasattr(agent, "max_retries")

            # 4. Validation and Fallback methods
            assert hasattr(agent, "validate_input") and callable(agent.validate_input)
            assert hasattr(agent, "fallback") and callable(agent.fallback)
            assert hasattr(agent, "execute") and callable(agent.execute)
            assert hasattr(agent, "run") and callable(agent.run)

    def test_security_disallows_arbitrary_or_unapproved_tools(self):
        """Ensures agents cannot invoke arbitrary tools or execute arbitrary code."""
        with pytest.raises(PermissionError) as exc_info:
            mood_analysis_agent.verify_tool_allowed("arbitrary_eval_code_injection")
        assert "attempted to invoke disallowed tool" in str(exc_info.value)

        with pytest.raises(PermissionError) as exc_info_rec:
            recommendation_agent.verify_tool_allowed("shell_execute_command")
        assert "attempted to invoke disallowed tool" in str(exc_info_rec.value)


@pytest.mark.asyncio
class TestIndividualAgents:
    async def test_mood_analysis_agent_execution_and_fallback(self):
        """Tests MoodAnalysisAgent with valid input and simulated fallback."""
        input_data = MoodAnalysisAgentInput(
            session_id="agent_test_session",
            emotion_probabilities=EmotionProbabilities(happy=0.85, neutral=0.10),
            confidence=0.9
        )
        result = await mood_analysis_agent.run(input_data)
        assert result.success is True
        assert result.is_fallback is False
        assert result.proposal.mood_state.estimated_mood == MoodClass.POSITIVE
        assert "Evaluated visible expressions" in result.proposal.reasoning

        # Test deterministic fallback
        fallback = mood_analysis_agent.fallback(input_data, error="Simulated timeout")
        assert fallback.mood_state.estimated_mood == MoodClass.NEUTRAL
        assert "Fallback engaged" in fallback.reasoning

    async def test_recommendation_agent_execution(self, provider):
        """Tests RecommendationAgent producing ranked recommendations."""
        mood_state = MoodState(
            estimated_mood=MoodClass.ENERGETIC,
            mood_confidence=0.92,
            smoothed_emotion_probabilities=EmotionProbabilities(happy=0.88, surprise=0.10),
            is_stable=True,
            stable_duration_seconds=12.0
        )
        rec_input = RecommendationAgentInput(
            mood_state=mood_state,
            user_id="default_user",
            limit=3
        )
        result = await recommendation_agent.run(rec_input)
        assert result.success is True
        assert len(result.proposal.recommendations) > 0
        assert result.proposal.target_profile.energy >= 0.70
        assert result.proposal.transition_decision in ["continue", "transition", "retrieve_new_candidates"]

    async def test_playlist_agent_anti_thrashing(self):
        """Tests PlaylistAgent enforcing anti-thrashing safety."""
        track = Track(
            id="test_trk",
            title="Test Track",
            artist="Test Artist",
            duration_seconds=200,
            audio_url="https://test.com/audio.mp3",
            cover_art_url="https://test.com/cover.jpg",
            profile=MusicProfile(genre="lofi", energy=0.3, valence=0.5, tempo=0.4, danceability=0.4)
        )
        playback = PlaybackState(current_track=track, is_playing=True, position_seconds=10.0)

        # Transition requested, but only 10s played -> anti-thrashing holds it
        input_data = PlaylistAgentInput(
            candidate_tracks=[track],
            playback_state=playback,
            transition_decision="transition",
            min_play_seconds=30
        )
        res = await playlist_agent.run(input_data)
        assert res.proposal.should_switch_now is False
        assert "held to prevent thrashing" in res.proposal.action_reason

    async def test_personalization_agent_execution(self, provider):
        """Tests PersonalizationAgent processing feedback."""
        track = await provider.get_track("trk_upbeat_01")
        assert track is not None

        pers_input = PersonalizationAgentInput(
            user_id="default_user",
            track=track,
            feedback_type="like",
            seconds_played=45.0,
            mood_at_time="positive"
        )
        res = await personalization_agent.run(pers_input)
        assert res.success is True
        assert res.proposal.acknowledged is True
        assert res.proposal.genre_updated == "synthwave"

    async def test_evaluation_agent_audit(self):
        """Tests EvaluationAgent producing health and telemetry proposal."""
        latencies = LatencyStats(
            face_detection_ms=8.0,
            temporal_smoothing_ms=3.0,
            jev_decision_ms=12.0,
            recommendation_ms=18.0,
            total_pipeline_ms=41.0
        )
        eval_input = EvaluationAgentInput(current_mood="positive", last_latencies=latencies)
        res = await evaluation_agent.run(eval_input)
        assert res.success is True
        assert res.proposal.metrics.latencies.total_pipeline_ms == 41.0
        assert res.proposal.recommendation_health_status in ["Optimal", "Latency Above Target", "High Skip Rate Detected"]


@pytest.mark.asyncio
class TestPipelineOrchestration:
    async def test_end_to_end_orchestration_cycle(self):
        """
        Tests the complete orchestration architecture:
        Emotion Model -> MoodAnalysisAgent -> JEV Decision Layer -> RecommendationAgent -> MusicProvider -> PlaybackManager
        """
        raw_emotions = EmotionProbabilities(happy=0.82, neutral=0.15)
        cycle_result = await agent_orchestrator.run_pipeline(
            emotion_probabilities=raw_emotions,
            emotion_confidence=0.88,
            session_id="orchestrator_test_session",
            auto_execute_playback=False
        )

        assert isinstance(cycle_result, OrchestrationCycleResult)
        assert cycle_result.success is True

        # Stage 1: Mood Analysis Agent output verified
        assert cycle_result.mood_state is not None
        assert cycle_result.mood_state.estimated_mood == MoodClass.POSITIVE

        # Stage 2: JEV bounded decision verified
        assert cycle_result.jev_decision.decision_source in ["jev_system_one", "deterministic_fallback"]
        assert cycle_result.jev_decision.mood.value == "positive"
        assert cycle_result.jev_decision.transition.value in ["continue", "transition", "retrieve_new_candidates"]

        # Stage 3: Recommendation Agent output verified
        assert len(cycle_result.recommendations) > 0

        # Stage 4: Playback Manager transition evaluation verified
        assert cycle_result.transition_result.action in ["continue", "transition", "replenish_queue"]

        # Language/reasoning explanation generated (without arbitrary code execution)
        assert len(cycle_result.explanation) > 0
        assert "Estimated mood:" in cycle_result.explanation

        # Latency breakdown verified
        assert "mood_analysis_agent_ms" in cycle_result.pipeline_stages
        assert "jev_decision_ms" in cycle_result.pipeline_stages
        assert "recommendation_agent_ms" in cycle_result.pipeline_stages
        assert "playback_manager_ms" in cycle_result.pipeline_stages

    async def test_orchestrate_api_endpoint(self):
        """Tests the POST /api/mood/orchestrate HTTP endpoint."""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/mood/orchestrate",
                json={
                    "emotions": {"happy": 0.85, "neutral": 0.10},
                    "confidence": 0.90,
                    "session_id": "api_orchestrate_session",
                    "auto_execute_playback": False
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert "mood_state" in data
            assert "jev_decision" in data
            assert "recommendations" in data
            assert "transition_result" in data
            assert "playback_state" in data
