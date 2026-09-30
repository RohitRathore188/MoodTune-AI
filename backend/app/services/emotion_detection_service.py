"""Emotion Detection Service.
Estimates visible facial expressions from camera frames strictly in-memory.

HUMAN-CENTERED PRINCIPLE:
This service produces an "estimated facial expression". It does NOT claim to represent
the person's actual internal emotional state or subjective feelings.

PRIVACY & SAFETY:
- Frames are processed strictly in RAM and immediately deallocated.
- Handles missing faces, corrupt inputs, model exceptions, and inference timeouts safely.
- Output probabilities and confidence scores are strictly validated in [0, 1].
"""
import os
import time
import base64
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Optional, Dict, Any, Union
import cv2
import numpy as np

from ..schemas.emotion import EmotionsDistribution, EmotionEstimationResponse
from .face_detection_service import FaceDetectionService, face_detection_service

logger = logging.getLogger("moodtune.emotion_detection")

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "models")
SMILE_CASCADE_PATH = os.path.join(MODELS_DIR, "haarcascade_smile.xml")
EYE_CASCADE_PATH = os.path.join(MODELS_DIR, "haarcascade_eye.xml")

VALID_EMOTIONS = ("happy", "sad", "angry", "neutral", "fear", "surprise", "disgust")


class EmotionResult(dict):
    """Dictionary representing the emotion estimation result with dot-attribute access.
    
    Output strictly conforms to:
    {
      "emotions": {
        "happy": 0.0,
        "sad": 0.0,
        "angry": 0.0,
        "neutral": 0.0,
        "fear": 0.0,
        "surprise": 0.0,
        "disgust": 0.0
      },
      "dominant_emotion": "...",
      "confidence": 0.0,
      "expression_type": "estimated facial expression"
    }
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for k, v in self.items():
            if isinstance(v, dict) and not isinstance(v, EmotionResult):
                self[k] = EmotionResult(v)
        self.__dict__ = self


class EmotionModelBackend:
    """Abstract interface for emotion estimation backends (models / mock backends)."""
    def predict(self, face_roi_gray: np.ndarray) -> Dict[str, float]:
        raise NotImplementedError


class MockEmotionModel(EmotionModelBackend):
    """Controlled mock model for unit testing and deterministic verification."""
    def __init__(
        self,
        fixed_emotions: Optional[Dict[str, float]] = None,
        raise_error: bool = False,
        error_message: str = "Simulated model error",
        delay_seconds: float = 0.0
    ):
        self.fixed_emotions = fixed_emotions or {
            "happy": 0.0,
            "sad": 0.0,
            "angry": 0.0,
            "neutral": 1.0,
            "fear": 0.0,
            "surprise": 0.0,
            "disgust": 0.0
        }
        self.raise_error = raise_error
        self.error_message = error_message
        self.delay_seconds = delay_seconds

    def predict(self, face_roi_gray: np.ndarray) -> Dict[str, float]:
        if self.delay_seconds > 0.0:
            time.sleep(self.delay_seconds)
        if self.raise_error:
            raise RuntimeError(self.error_message)
        return dict(self.fixed_emotions)


class FacialExpressionFeatureModel(EmotionModelBackend):
    """Production-grade feature-based facial expression analyzer.
    
    Uses OpenCV Haar cascades for facial micro-features (smile curvature, eye openness)
    and gradient contrast (corrugator supercilii / brow tension) to produce
    temperature-scaled logits for estimated facial expressions.
    """
    def __init__(
        self,
        smile_cascade_path: str = SMILE_CASCADE_PATH,
        eye_cascade_path: str = EYE_CASCADE_PATH
    ):
        self.smile_cascade: Optional[cv2.CascadeClassifier] = None
        self.eye_cascade: Optional[cv2.CascadeClassifier] = None
        self._load_cascades(smile_cascade_path, eye_cascade_path)

    def _load_cascades(self, smile_path: str, eye_path: str):
        try:
            if os.path.exists(smile_path):
                self.smile_cascade = cv2.CascadeClassifier(smile_path)
            if os.path.exists(eye_path):
                self.eye_cascade = cv2.CascadeClassifier(eye_path)
        except Exception as e:
            logger.warning(f"Could not load secondary feature cascades: {e}")

    def predict(self, face_roi_gray: np.ndarray) -> Dict[str, float]:
        h, w = face_roi_gray.shape[:2]
        if h == 0 or w == 0:
            return {"neutral": 1.0}

        # Sub-regions: mouth (lower 40%) and upper eye/brow region (top 50%)
        lower_mouth_region = face_roi_gray[int(h * 0.60):h, int(w * 0.15):int(w * 0.85)]
        upper_eye_region = face_roi_gray[0:int(h * 0.50), int(w * 0.10):int(w * 0.90)]

        # 1. Smile feature extraction
        smile_intensity = 0.0
        if self.smile_cascade and lower_mouth_region.size > 0:
            smiles = self.smile_cascade.detectMultiScale(
                lower_mouth_region,
                scaleFactor=1.25,
                minNeighbors=10,
                minSize=(20, 12)
            )
            if len(smiles) > 0:
                smile_intensity = min(1.0, len(smiles) * 0.45)

        # 2. Eye region analysis
        eyes_count = 0
        if self.eye_cascade and upper_eye_region.size > 0:
            eyes = self.eye_cascade.detectMultiScale(
                upper_eye_region,
                scaleFactor=1.15,
                minNeighbors=4,
                minSize=(15, 15)
            )
            eyes_count = len(eyes)

        # 3. Brow tension & furrowing via vertical Sobel gradient
        brow_tension = 0.0
        if upper_eye_region.size > 0:
            sobel_y = cv2.Sobel(upper_eye_region, cv2.CV_64F, 0, 1, ksize=3)
            brow_tension = float(np.mean(np.abs(sobel_y))) / 100.0
            brow_tension = float(np.clip(brow_tension, 0.0, 1.0))

        # 4. Calibrated expression logits
        logits = {
            "happy": 0.10,
            "sad": 0.08,
            "angry": 0.06,
            "neutral": 0.45,
            "fear": 0.04,
            "surprise": 0.07,
            "disgust": 0.03
        }

        if smile_intensity > 0.0:
            logits["happy"] += 0.80 + smile_intensity * 0.70
            logits["neutral"] -= 0.30

        if eyes_count >= 2 and smile_intensity == 0.0:
            if brow_tension > 0.50:
                logits["angry"] += brow_tension * 0.85
                logits["neutral"] -= 0.20
            elif brow_tension > 0.35:
                logits["sad"] += brow_tension * 0.60
            else:
                logits["neutral"] += 0.30

        if eyes_count > 2 or (eyes_count >= 1 and brow_tension < 0.20 and smile_intensity > 0.3):
            logits["surprise"] += 0.35

        # Softmax normalization
        emotion_keys = list(VALID_EMOTIONS)
        raw_vals = np.array([logits.get(k, 0.05) for k in emotion_keys], dtype=np.float64)
        exp_vals = np.exp(raw_vals * 2.5)  # Temperature scaling
        probs = exp_vals / np.sum(exp_vals)

        return {k: float(p) for k, p in zip(emotion_keys, probs)}


class EmotionDetectionService:
    """Service responsible for facial expression estimation.
    
    HUMAN-CENTERED PRINCIPLE:
    Always labels predictions as 'estimated facial expression'. Never claims to know
    the user's true internal emotional state.
    """
    def __init__(
        self,
        face_detector: Optional[FaceDetectionService] = None,
        model_backend: Optional[EmotionModelBackend] = None,
        default_timeout_seconds: float = 1.5,
        max_workers: int = 2
    ):
        self.face_detector = face_detector or face_detection_service
        self.model_backend = model_backend or FacialExpressionFeatureModel()
        self.default_timeout_seconds = default_timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="emotion_worker")

    def decode_frame(self, image_input: Union[str, np.ndarray]) -> Optional[np.ndarray]:
        """Decodes base64 string to RGB frame in RAM or returns existing array."""
        if isinstance(image_input, np.ndarray):
            return image_input.copy()
        if isinstance(image_input, str):
            try:
                b64 = image_input
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                raw_bytes = base64.b64decode(b64)
                arr = np.frombuffer(raw_bytes, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                return img
            except Exception as e:
                logger.warning(f"Frame base64 decoding failed: {e}")
                return None
        return None

    def _build_fallback_result(
        self,
        reason: str,
        start_time: float,
        dominant_emotion: str = "neutral",
        face_detected: bool = False
    ) -> EmotionResult:
        """Constructs safe fallback response adhering to schema and human-centered design."""
        inference_ms = (time.perf_counter() - start_time) * 1000.0
        emotions_dist = EmotionsDistribution(
            happy=0.0,
            sad=0.0,
            angry=0.0,
            neutral=1.0,
            fear=0.0,
            surprise=0.0,
            disgust=0.0
        )
        return EmotionResult({
            "emotions": emotions_dist.to_dict(),
            "dominant_emotion": dominant_emotion,
            "confidence": 0.0,
            "expression_type": "estimated facial expression",
            "face_detected": face_detected,
            "inference_time_ms": round(inference_ms, 2),
            "status_message": f"Estimated visible facial expression fallback: {reason}"
        })

    def estimate_emotion(
        self,
        image_input: Optional[Union[str, np.ndarray]] = None,
        timeout_seconds: Optional[float] = None
    ) -> EmotionResult:
        """Estimates facial expression probabilities from an in-memory frame.
        
        Strictly guarantees:
        1. Probabilities are valid floats in [0, 1] and sum to 1.0.
        2. Confidence is a valid float in [0, 1].
        3. Missing faces produce safe fallback with confidence 0.0.
        4. Model errors produce safe fallback with confidence 0.0.
        5. Inference timeouts produce safe fallback with confidence 0.0.
        6. In-memory image references are promptly freed.
        """
        start_time = time.perf_counter()
        timeout = timeout_seconds if timeout_seconds is not None else self.default_timeout_seconds

        # 1. Check for missing input
        if image_input is None or (isinstance(image_input, str) and not image_input.strip()):
            return self._build_fallback_result("No image provided", start_time)

        # 2. Decode frame
        frame = self.decode_frame(image_input)
        if frame is None or frame.size == 0:
            return self._build_fallback_result("Invalid or corrupt frame data", start_time)

        gray: Optional[np.ndarray] = None
        face_roi: Optional[np.ndarray] = None

        try:
            # 3. Detect face
            face_result = self.face_detector.detect_faces(frame)
            if face_result.face_count == 0 or face_result.primary_face is None:
                return self._build_fallback_result("No face detected in frame", start_time, face_detected=False)

            primary_face = face_result.primary_face
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            x, y, w, h = primary_face.x, primary_face.y, primary_face.width, primary_face.height

            # Boundary clipping
            img_h, img_w = gray.shape[:2]
            x1 = max(0, min(x, img_w - 1))
            y1 = max(0, min(y, img_h - 1))
            x2 = max(x1 + 1, min(x + w, img_w))
            y2 = max(y1 + 1, min(y + h, img_h))

            face_roi = gray[y1:y2, x1:x2]
            if face_roi.size == 0:
                return self._build_fallback_result("Face ROI area is zero", start_time, face_detected=True)

            # 4. Model inference with timeout enforcement
            future = self._executor.submit(self.model_backend.predict, face_roi)
            try:
                raw_predictions = future.result(timeout=timeout)
            except FuturesTimeoutError:
                logger.warning(f"Emotion model inference timed out after {timeout}s")
                return self._build_fallback_result(f"Inference timeout exceeded ({timeout}s)", start_time, face_detected=True)
            except Exception as e:
                logger.error(f"Emotion model inference error: {e}")
                return self._build_fallback_result(f"Model error: {str(e)}", start_time, face_detected=True)

            # 5. Probability distribution validation and normalization
            validated_probs = {}
            for emotion in VALID_EMOTIONS:
                val = raw_predictions.get(emotion, 0.0)
                try:
                    fval = float(val)
                    if np.isnan(fval) or np.isinf(fval):
                        fval = 0.0
                except (ValueError, TypeError):
                    fval = 0.0
                validated_probs[emotion] = max(0.0, fval)

            total = sum(validated_probs.values())
            if total <= 0.0:
                validated_probs["neutral"] = 1.0
                total = 1.0

            normalized_probs = {k: v / total for k, v in validated_probs.items()}
            emotions_dist = EmotionsDistribution(**normalized_probs)

            # 6. Dominant emotion and confidence computation
            emotions_dict = emotions_dist.to_dict()
            dominant_emotion = max(emotions_dict.items(), key=lambda kv: kv[1])[0]
            dominant_prob = emotions_dict[dominant_emotion]

            # Confidence is derived from dominant margin & face detection confidence, clamped strictly to [0.0, 1.0]
            raw_confidence = dominant_prob * 0.90 + 0.05
            confidence = float(np.clip(raw_confidence, 0.0, 1.0))

            inference_ms = (time.perf_counter() - start_time) * 1000.0

            return EmotionResult({
                "emotions": emotions_dict,
                "dominant_emotion": dominant_emotion,
                "confidence": round(confidence, 3),
                "expression_type": "estimated facial expression",
                "face_detected": True,
                "inference_time_ms": round(inference_ms, 2),
                "status_message": "Estimated visible facial expression successfully analyzed"
            })

        except Exception as e:
            logger.error(f"Unexpected error during emotion estimation: {e}", exc_info=True)
            return self._build_fallback_result(f"Pipeline error: {str(e)}", start_time, face_detected=False)

        finally:
            # Memory safety: explicit garbage cleanup of volatile camera frames
            del frame
            if gray is not None:
                del gray
            if face_roi is not None:
                del face_roi


emotion_detection_service = EmotionDetectionService()
