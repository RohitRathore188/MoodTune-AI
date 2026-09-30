"""AI Evaluation Dashboard API Endpoints (Phase 12).

Adheres strictly to the human-centered mandate:
Visible affect metrics measure model inference and smoothing stability only;
they do NOT represent or prove that the AI understands the user's true emotions.

Provides categorized metrics for:
- MODEL PERFORMANCE
- RECOMMENDATION PERFORMANCE
- SYSTEM PERFORMANCE
"""
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from ...config import settings
from ...schemas.evaluation import EvaluationDashboardResponse
from ...services.evaluation_service import evaluation_service

router = APIRouter(prefix="/evaluation", tags=["AI Evaluation Dashboard"])


@router.get("", response_model=EvaluationDashboardResponse)
async def get_evaluation_dashboard():
    """
    Returns real-time AI evaluation metrics cleanly partitioned into:
    - MODEL PERFORMANCE (inference latency, confidence distribution, no-face rate, stability, transitions)
    - RECOMMENDATION PERFORMANCE (acceptance rate, skip rate, completion rate, diversity, listening duration)
    - SYSTEM PERFORMANCE (Jev latency, Jev failures, fallback frequency, API failures)
    """
    return evaluation_service.get_evaluation_dashboard()


@router.post("/reset")
async def reset_evaluation_metrics(x_admin_token: Optional[str] = Header(default=None)):
    """Resets evaluation telemetry buffers. Requires X-Admin-Token when ADMIN_TOKEN is configured."""
    if settings.ADMIN_TOKEN and x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing X-Admin-Token")
    evaluation_service.reset()
    return {
        "status": "reset_successful",
        "message": "Evaluation metrics buffers cleared."
    }


@router.post("/record-acceptance")
async def record_recommendation_acceptance():
    """Records that a user selected/played a recommended candidate song."""
    evaluation_service.record_recommendation_accepted()
    return {
        "status": "recorded",
        "acceptance_rate": evaluation_service.get_evaluation_dashboard().recommendation_performance.recommendation.acceptance_rate
    }
