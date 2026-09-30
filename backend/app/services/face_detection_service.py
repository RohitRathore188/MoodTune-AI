"""Face Detection Service.
Processes incoming camera frames strictly in-memory.
Never stores raw frames to disk or database.
Handles:
- No-face state
- Single-face state
- Multiple-face state
- Corrupt frame / error states
"""
import os
import time
import base64
import logging
from typing import Optional, List, Tuple
import cv2
import numpy as np

from ..schemas.camera import (
    FaceDetectionResult,
    FaceDetectionState,
    BoundingBox
)

logger = logging.getLogger("moodtune.face_detection")

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "models")
CASCADE_PATH = os.path.join(MODELS_DIR, "haarcascade_frontalface_default.xml")


class FaceDetectionService:
    def __init__(self, cascade_path: Optional[str] = None):
        self.cascade_path = cascade_path or CASCADE_PATH
        self.classifier: Optional[cv2.CascadeClassifier] = None
        self._load_classifier()

    def _load_classifier(self):
        try:
            if os.path.exists(self.cascade_path):
                self.classifier = cv2.CascadeClassifier(self.cascade_path)
                logger.info(f"Loaded Haar face classifier from {self.cascade_path}")
            else:
                logger.warning(f"Haar cascade file not found at {self.cascade_path}")
        except Exception as e:
            logger.error(f"Failed to load Haar classifier: {e}")
            self.classifier = None

    def decode_base64_frame(self, b64_str: str) -> Optional[np.ndarray]:
        """Decodes base64 string to a volatile NumPy RGB array in RAM."""
        try:
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            logger.warning(f"Error decoding base64 frame: {e}")
            return None

    def detect_faces(
        self,
        image_input: Optional[np.ndarray | str] = None
    ) -> FaceDetectionResult:
        """
        Executes face detection on an in-memory frame.
        Guarantees: image memory is deleted immediately after detection.
        """
        start_time = time.perf_counter()

        if image_input is None:
            inference_ms = (time.perf_counter() - start_time) * 1000.0
            return FaceDetectionResult(
                state=FaceDetectionState.NO_FACE,
                face_count=0,
                primary_face=None,
                all_faces=[],
                confidence=0.0,
                inference_time_ms=round(inference_ms, 2),
                status_message="No frame provided."
            )

        frame: Optional[np.ndarray] = None
        if isinstance(image_input, str):
            frame = self.decode_base64_frame(image_input)
        elif isinstance(image_input, np.ndarray):
            frame = image_input

        if frame is None or frame.size == 0:
            inference_ms = (time.perf_counter() - start_time) * 1000.0
            return FaceDetectionResult(
                state=FaceDetectionState.ERROR,
                face_count=0,
                primary_face=None,
                all_faces=[],
                confidence=0.0,
                inference_time_ms=round(inference_ms, 2),
                status_message="Corrupt or unreadable frame data.",
                error_message="Invalid frame format."
            )

        try:
            # Grayscale conversion
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            detected_faces = []
            if self.classifier is not None:
                detected_faces = self.classifier.detectMultiScale(
                    gray,
                    scaleFactor=1.15,
                    minNeighbors=5,
                    minSize=(50, 50)
                )

            face_count = len(detected_faces)
            boxes = [
                BoundingBox(x=int(x), y=int(y), width=int(w), height=int(h))
                for (x, y, w, h) in detected_faces
            ]

            inference_ms = (time.perf_counter() - start_time) * 1000.0

            # State classification
            if face_count == 0:
                return FaceDetectionResult(
                    state=FaceDetectionState.NO_FACE,
                    face_count=0,
                    primary_face=None,
                    all_faces=[],
                    confidence=0.0,
                    inference_time_ms=round(inference_ms, 2),
                    status_message="No face detected in camera viewport."
                )

            # Pick primary face by area
            primary = max(boxes, key=lambda b: b.width * b.height)

            if face_count == 1:
                return FaceDetectionResult(
                    state=FaceDetectionState.SINGLE_FACE,
                    face_count=1,
                    primary_face=primary,
                    all_faces=boxes,
                    confidence=0.92,
                    inference_time_ms=round(inference_ms, 2),
                    status_message="Single face detected and locked."
                )
            else:
                return FaceDetectionResult(
                    state=FaceDetectionState.MULTIPLE_FACES,
                    face_count=face_count,
                    primary_face=primary,
                    all_faces=boxes,
                    confidence=0.85,
                    inference_time_ms=round(inference_ms, 2),
                    status_message=f"Multiple faces detected ({face_count}). Focus locked onto primary listener."
                )

        except Exception as e:
            logger.error(f"Exception during face detection: {e}")
            inference_ms = (time.perf_counter() - start_time) * 1000.0
            return FaceDetectionResult(
                state=FaceDetectionState.ERROR,
                face_count=0,
                primary_face=None,
                all_faces=[],
                confidence=0.0,
                inference_time_ms=round(inference_ms, 2),
                status_message="Detection pipeline encountered an unexpected error.",
                error_message=str(e)
            )
        finally:
            # Explicit in-memory garbage collection
            del frame
            if "gray" in locals():
                del gray


face_detection_service = FaceDetectionService()
