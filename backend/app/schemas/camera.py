"""Camera and Face Detection Schemas."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class CameraState(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    OFF = "off"
    PERMISSION_DENIED = "permission_denied"
    HARDWARE_ERROR = "hardware_error"


class FaceDetectionState(str, Enum):
    NO_FACE = "no_face"
    SINGLE_FACE = "single_face"
    MULTIPLE_FACES = "multiple_faces"
    PROCESSING = "processing"
    ERROR = "error"


class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class FaceDetectionResult(BaseModel):
    state: FaceDetectionState
    face_count: int = 0
    primary_face: Optional[BoundingBox] = None
    all_faces: List[BoundingBox] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    inference_time_ms: float = 0.0
    status_message: str
    error_message: Optional[str] = None


class FrameDetectionRequest(BaseModel):
    image_base64: Optional[str] = Field(default=None, max_length=7_000_000, description="In-memory base64 frame (max ~5MB)")
    timestamp: Optional[float] = None


class CameraStatusResponse(BaseModel):
    status: str = "ready"
    storage_policy: str = "in_memory_only"
    models_loaded: bool = True
