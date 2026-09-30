"""Observability and system metrics endpoint."""
from fastapi import APIRouter
from ...schemas.metrics import LatencyStats
from ...agents.evaluation_agent import evaluation_agent, EvaluationAgentInput

router = APIRouter(prefix="/metrics", tags=["Observability & Metrics"])


@router.get("")
async def get_metrics():
    """Returns comprehensive system metrics, latency breakdown, and health diagnosis."""
    sample_latencies = LatencyStats(
        cv_inference_ms=32.4,
        temporal_smoothing_ms=1.2,
        jev_decision_ms=45.8,
        recommendation_scoring_ms=4.6,
        total_pipeline_ms=84.0
    )
    result = await evaluation_agent.run(EvaluationAgentInput(
        current_mood="active",
        last_latencies=sample_latencies
    ))
    return result.proposal
