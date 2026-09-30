"""Camera and Real-Time Face Detection Router."""
from fastapi import APIRouter, Depends
from ...schemas.camera import (
    FrameDetectionRequest,
    FaceDetectionResult,
    CameraStatusResponse
)
from ...services.face_detection_service import face_detection_service
from ...services.rate_limiter import check_rate_limit

router = APIRouter(prefix="/camera", tags=["Camera & Vision"])


@router.post("/detect", response_model=FaceDetectionResult, dependencies=[Depends(check_rate_limit)])
async def detect_faces_in_frame(request: FrameDetectionRequest):
    """
    Ingests an in-memory frame and returns bounding boxes, count, and face state.
    STRICT PRIVACY GUARANTEE: Memory buffer is freed immediately after inference.
    """
    return face_detection_service.detect_faces(image_input=request.image_base64)


@router.get("/status", response_model=CameraStatusResponse)
async def get_camera_service_status():
    """Returns camera vision subsystem status and storage guarantee."""
    return CameraStatusResponse(
        status="ready",
        storage_policy="in_memory_only (never saved to disk/db)",
        models_loaded=(face_detection_service.classifier is not None)
    )
