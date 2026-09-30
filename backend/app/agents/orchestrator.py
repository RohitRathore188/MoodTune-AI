"""Agent Orchestration Pipeline (Phase 10: AI Agent Orchestration).
Coordinates the structured agent pipeline:
    Emotion Model -> Mood Analysis Agent -> JEV Decision Layer -> Recommendation Agent -> Music Provider -> Playback Manager

CORE PRINCIPLES:
- LLM is used for language/reasoning tasks (e.g. human explanation).
- JEV handles bounded decisions (mood_class, music_energy, transition_decision, recommendation_strategy).
- Code executes final deterministic actions (playback, queue sequencing).
- Strictly prevents arbitrary code execution from any AI or model component.
"""
import time
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from ..schemas.mood import EmotionProbabilities, MoodState, MoodClass
from ..schemas.music import Track, PlaybackState, TransitionDecisionResult
from ..schemas.jev import JevDecisionBundle
from ..schemas.recommendation import ScoredTrack
from ..schemas.metrics import LatencyStats

from .mood_analysis_agent import mood_analysis_agent, MoodAnalysisAgentInput
from .music_recommendation_agent import recommendation_agent, RecommendationAgentInput
from .playlist_agent import playlist_agent, PlaylistAgentInput
from .personalization_agent import personalization_agent
from .evaluation_agent import evaluation_agent, EvaluationAgentInput
from ..services.jev_service import jev_decision_service, JevDecisionService
from ..services.playback_manager import playback_manager, PlaybackManager

logger = logging.getLogger("moodtune.orchestrator")


class OrchestrationCycleResult(BaseModel):
    """Structured result of one end-to-end agent orchestration cycle."""
    success: bool
    mood_state: MoodState
    jev_decision: JevDecisionBundle
    recommendations: List[ScoredTrack]
    transition_result: TransitionDecisionResult
    playback_state: PlaybackState
    explanation: str
    cycle_latency_ms: float
    pipeline_stages: Dict[str, float] = Field(default_factory=dict)


class AgentOrchestrator:
    """Orchestrates bounded AI agents, Jev decision layer, and code execution."""

    def __init__(
        self,
        jev_service: Optional[JevDecisionService] = None,
        playback_mgr: Optional[PlaybackManager] = None
    ):
        self.jev = jev_service or jev_decision_service
        self.playback = playback_mgr or playback_manager
        self.mood_agent = mood_analysis_agent
        self.rec_agent = recommendation_agent
        self.playlist_agent = playlist_agent
        self.pers_agent = personalization_agent
        self.eval_agent = evaluation_agent

    async def run_pipeline(
        self,
        emotion_probabilities: EmotionProbabilities,
        emotion_confidence: float = 0.85,
        session_id: str = "default_session",
        user_id: str = "default_user",
        manual_mood_override: Optional[MoodClass] = None,
        auto_execute_playback: bool = True
    ) -> OrchestrationCycleResult:
        """
        Executes one full cycle of the MoodTune architecture:
        1. Emotion Model output -> Mood Analysis Agent
        2. Mood Analysis Agent -> JEV Decision Layer
        3. JEV Decision Layer -> Recommendation Agent
        4. Recommendation Agent -> Music Provider (candidate retrieval & scoring)
        5. Music Provider -> Playback Manager (anti-thrashing evaluation & deterministic execution)
        """
        cycle_start = time.perf_counter()
        stage_latencies: Dict[str, float] = {}

        # ---------------------------------------------------------------------
        # Stage 1: Mood Analysis Agent
        # ---------------------------------------------------------------------
        s1_start = time.perf_counter()
        mood_input = MoodAnalysisAgentInput(
            session_id=session_id,
            emotion_probabilities=emotion_probabilities,
            confidence=emotion_confidence,
            timestamp=time.time(),
            manual_override=manual_mood_override
        )
        mood_exec = await self.mood_agent.run(mood_input)
        stage_latencies["mood_analysis_agent_ms"] = round((time.perf_counter() - s1_start) * 1000.0, 2)
        mood_state = mood_exec.proposal.mood_state

        # ---------------------------------------------------------------------
        # Stage 2: JEV Decision Layer (Bounded Decisions Only)
        # ---------------------------------------------------------------------
        s2_start = time.perf_counter()
        cur_playback = self.playback.get_playback_state()
        cur_track = cur_playback.current_track

        current_song_dict = None
        if cur_track:
            current_song_dict = {
                "id": cur_track.id,
                "title": cur_track.title,
                "genre": cur_track.profile.genre,
                "energy": cur_track.profile.energy,
                "seconds_played": cur_playback.position_seconds,
                "duration": float(cur_track.duration_seconds)
            }

        jev_state = {
            "smoothed_mood": mood_state.estimated_mood.value,
            "mood_confidence": mood_state.mood_confidence,
            "emotion_probabilities": mood_state.smoothed_emotion_probabilities.to_dict(),
            "current_song": current_song_dict,
            "seconds_played": cur_playback.position_seconds
        }

        # Jev bounded decisions: mood_class, music_energy, transition_decision, recommendation_strategy
        jev_decision = self.jev.decide(jev_state)
        stage_latencies["jev_decision_ms"] = round((time.perf_counter() - s2_start) * 1000.0, 2)
        self.eval_agent.record_decision(jev_decision.decision_source)

        # ---------------------------------------------------------------------
        # Stage 3: Recommendation Agent (Music Provider Layer Integration)
        # ---------------------------------------------------------------------
        s3_start = time.perf_counter()
        rec_input = RecommendationAgentInput(
            mood_state=mood_state,
            playback_state=cur_playback,
            user_id=user_id,
            limit=5,
            force_transition=(jev_decision.transition.value == "transition")
        )
        rec_exec = await self.rec_agent.run(rec_input)
        stage_latencies["recommendation_agent_ms"] = round((time.perf_counter() - s3_start) * 1000.0, 2)
        recommendations = rec_exec.proposal.recommendations

        # ---------------------------------------------------------------------
        # Stage 4: Playback Manager (Intelligent Transition & Code Execution)
        # ---------------------------------------------------------------------
        s4_start = time.perf_counter()
        # Evaluate transition through multi-factor anti-thrashing guardrails
        transition_result = await self.playback.evaluate_transition(
            current_mood=mood_state.estimated_mood.value,
            mood_confidence=mood_state.mood_confidence,
            mood_stability=mood_state.stable_duration_seconds,
            is_stable=mood_state.is_stable,
            current_track_progress=cur_playback.position_seconds,
            auto_execute=auto_execute_playback
        )

        # Replenish queue if low
        if len(self.playback.queue) < 3 and recommendations:
            candidate_raw_tracks = [st.track for st in recommendations]
            for trk in candidate_raw_tracks:
                self.playback.add_to_queue(trk)

        stage_latencies["playback_manager_ms"] = round((time.perf_counter() - s4_start) * 1000.0, 2)
        final_playback_state = self.playback.get_playback_state()

        # ---------------------------------------------------------------------
        # Stage 5: Evaluation Agent Audit
        # ---------------------------------------------------------------------
        total_latency = (time.perf_counter() - cycle_start) * 1000.0
        latencies = LatencyStats(
            face_detection_ms=10.0,
            temporal_smoothing_ms=stage_latencies.get("mood_analysis_agent_ms", 5.0),
            jev_decision_ms=stage_latencies.get("jev_decision_ms", 15.0),
            recommendation_ms=stage_latencies.get("recommendation_agent_ms", 20.0),
            total_pipeline_ms=total_latency
        )
        await self.eval_agent.run(
            EvaluationAgentInput(current_mood=mood_state.estimated_mood.value, last_latencies=latencies)
        )

        # Human-centered explanation (LLM reasoning without arbitrary execution)
        human_explanation = (
            f"Estimated mood: {mood_state.estimated_mood.value} (confidence: {mood_state.mood_confidence:.0%}). "
            f"Transition action: {transition_result.action}. {transition_result.reason}"
        )

        return OrchestrationCycleResult(
            success=True,
            mood_state=mood_state,
            jev_decision=jev_decision,
            recommendations=recommendations,
            transition_result=transition_result,
            playback_state=final_playback_state,
            explanation=human_explanation,
            cycle_latency_ms=round(total_latency, 2),
            pipeline_stages=stage_latencies
        )


# Global orchestrator singleton
agent_orchestrator = AgentOrchestrator()
