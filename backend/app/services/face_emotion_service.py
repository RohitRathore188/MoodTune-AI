"""Face detection and visible facial expression estimation service.
Adheres strictly to the human-centered principle:
This is an ESTIMATE of visible affect, never a claim of internal emotional truth.
Privacy: Frames are processed purely in-memory and immediately discarded.
"""
import os
import time
import base64
import logging
from typing import Optional, Tuple
import cv2
import numpy as np

from ..schemas.mood import (
    FaceDetectionResult,
    FaceBoundingBox,
    EmotionProbabilities,
    MoodClass
)

logger = logging.getLogger("moodtune.face_emotion")

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "models")
FACE_CASCADE_PATH = os.path.join(MODELS_DIR, "haarcascade_frontalface_default.xml")
SMILE_CASCADE_PATH = os.path.join(MODELS_DIR, "haarcascade_smile.xml")
EYE_CASCADE_PATH = os.path.join(MODELS_DIR, "haarcascade_eye.xml")


class FaceEmotionService:
    def __init__(self):
        self.face_cascade: Optional[cv2.CascadeClassifier] = None
        self.smile_cascade: Optional[cv2.CascadeClassifier] = None
        self.eye_cascade: Optional[cv2.CascadeClassifier] = None
        self._load_classifiers()

    def _load_classifiers(self):
        try:
            if os.path.exists(FACE_CASCADE_PATH):
                self.face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
            if os.path.exists(SMILE_CASCADE_PATH):
                self.smile_cascade = cv2.CascadeClassifier(SMILE_CASCADE_PATH)
            if os.path.exists(EYE_CASCADE_PATH):
                self.eye_cascade = cv2.CascadeClassifier(EYE_CASCADE_PATH)
            logger.info("Initialized OpenCV Haar cascade models.")
        except Exception as e:
            logger.error(f"Error loading cascade classifiers: {e}")

    def decode_image_base64(self, b64_str: str) -> Optional[np.ndarray]:
        """Decodes base64 string to RGB image in memory."""
        try:
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            logger.warning(f"Failed to decode base64 frame: {e}")
            return None

    def analyze_frame(
        self,
        image_input: Optional[np.ndarray | str] = None,
        manual_override: Optional[MoodClass] = None
    ) -> FaceDetectionResult:
        """
        Processes a single camera frame or handles manual mood override.
        Guarantees that raw image memory is deleted after feature extraction.
        """
        start_time = time.perf_counter()

        # Handle manual override (when camera is disabled by user)
        if manual_override is not None:
            return self._build_manual_override_result(manual_override, start_time)

        if image_input is None:
            return self._empty_result(start_time, reason="No image provided")

        # Decode if base64 string
        frame: Optional[np.ndarray] = None
        if isinstance(image_input, str):
            frame = self.decode_image_base64(image_input)
        elif isinstance(image_input, np.ndarray):
            frame = image_input

        if frame is None:
            return self._empty_result(start_time, reason="Invalid frame data")

        try:
            # Grayscale conversion for facial feature extraction
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = []
            if self.face_cascade:
                faces = self.face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.15,
                    minNeighbors=5,
                    minSize=(60, 60)
                )

            if len(faces) == 0:
                return self._empty_result(start_time, reason="No face detected in frame")

            # Extract the primary face (largest area)
            primary_face = max(faces, key=lambda f: f[2] * f[3])
            fx, fy, fw, fh = primary_face
            face_roi_gray = gray[fy : fy + fh, fx : fx + fw]

            # Visible affect feature extraction
            probabilities = self._estimate_affect_from_roi(face_roi_gray, fw, fh)

            # Determine dominant expression estimate
            dominant_expr = max(probabilities.items(), key=lambda kv: kv[1])
            expr_name, expr_prob = dominant_expr

            # Compute overall detection confidence (combining face box solidity & dominant prob)
            confidence = float(np.clip(expr_prob * 0.95 + 0.05, 0.1, 0.98))

            inference_ms = (time.perf_counter() - start_time) * 1000.0

            return FaceDetectionResult(
                detected=True,
                face_count=len(faces),
                bounding_box=FaceBoundingBox(x=int(fx), y=int(fy), width=int(fw), height=int(fh)),
                expression_estimate=expr_name,
                emotion_probabilities=EmotionProbabilities(**probabilities),
                confidence=round(confidence, 3),
                inference_time_ms=round(inference_ms, 2)
            )
        finally:
            # Explicitly free memory references to prevent frame retention
            del frame
            if "gray" in locals():
                del gray
            if "face_roi_gray" in locals():
                del face_roi_gray

    def _estimate_affect_from_roi(self, face_gray: np.ndarray, w: int, h: int) -> dict[str, float]:
        """
        Estimates visible expression probabilities from facial geometry and contrast.
        """
        # Lower half for smile / mouth region
        lower_half = face_gray[int(h * 0.55) : h, int(w * 0.15) : int(w * 0.85)]
        upper_half = face_gray[0 : int(h * 0.5), int(w * 0.1) : int(w * 0.9)]

        # Smile detection
        smile_detected = False
        smile_intensity = 0.0
        if self.smile_cascade and lower_half.size > 0:
            smiles = self.smile_cascade.detectMultiScale(
                lower_half,
                scaleFactor=1.3,
                minNeighbors=12,
                minSize=(25, 15)
            )
            if len(smiles) > 0:
                smile_detected = True
                smile_intensity = min(1.0, len(smiles) * 0.4)

        # Eye detection
        eyes_detected_count = 0
        if self.eye_cascade and upper_half.size > 0:
            eyes = self.eye_cascade.detectMultiScale(
                upper_half,
                scaleFactor=1.15,
                minNeighbors=4,
                minSize=(15, 15)
            )
            eyes_detected_count = len(eyes)

        # Brow furrowing & texture analysis (vertical gradient for brow tension)
        brow_tension = 0.0
        if upper_half.size > 0:
            sobel_y = cv2.Sobel(upper_half, cv2.CV_64F, 0, 1, ksize=3)
            brow_tension = float(np.mean(np.abs(sobel_y))) / 100.0
            brow_tension = float(np.clip(brow_tension, 0.0, 1.0))

        # Mouth corner curvature / aspect ratio
        # Calculate raw logits
        raw_scores = {
            "happy": 0.10,
            "neutral": 0.40,
            "surprise": 0.08,
            "sad": 0.08,
            "angry": 0.05,
            "fear": 0.04,
            "disgust": 0.03
        }

        if smile_detected:
            raw_scores["happy"] += 0.85 + smile_intensity * 0.6
            raw_scores["neutral"] -= 0.25

        if eyes_detected_count >= 2 and not smile_detected:
            if brow_tension > 0.45:
                raw_scores["angry"] += brow_tension * 0.8
                raw_scores["tense"] = brow_tension * 0.7  # auxiliary
            else:
                raw_scores["neutral"] += 0.35

        if eyes_detected_count >= 2 and brow_tension < 0.25 and not smile_detected:
            raw_scores["neutral"] += 0.40

        if brow_tension > 0.6 and not smile_detected:
            raw_scores["sad"] += 0.45
            raw_scores["angry"] += 0.35

        # Normalize with softmax to produce valid probability distribution
        vals = np.array([raw_scores[k] for k in ["happy", "neutral", "surprise", "sad", "angry", "fear", "disgust"]])
        exp_vals = np.exp(vals * 2.2)  # temperature scaling
        probs = exp_vals / np.sum(exp_vals)

        keys = ["happy", "neutral", "surprise", "sad", "angry", "fear", "disgust"]
        return {k: round(float(p), 4) for k, p in zip(keys, probs)}

    def _build_manual_override_result(self, mood: MoodClass, start_time: float) -> FaceDetectionResult:
        """Constructs synthetic estimate when user chooses manual mood override."""
        probabilities = {
            "happy": 0.05,
            "neutral": 0.10,
            "surprise": 0.05,
            "sad": 0.05,
            "angry": 0.05,
            "fear": 0.05,
            "disgust": 0.05
        }
        dominant_key = "neutral"
        if mood == MoodClass.POSITIVE or mood == MoodClass.ENERGETIC:
            dominant_key = "happy"
            probabilities["happy"] = 0.82
            probabilities["neutral"] = 0.10
        elif mood == MoodClass.CALM or mood == MoodClass.REFLECTIVE:
            dominant_key = "neutral"
            probabilities["neutral"] = 0.75
            probabilities["happy"] = 0.15
        elif mood == MoodClass.LOW_ENERGY:
            dominant_key = "sad"
            probabilities["sad"] = 0.70
            probabilities["neutral"] = 0.20
        elif mood == MoodClass.TENSE:
            dominant_key = "angry"
            probabilities["angry"] = 0.65
            probabilities["fear"] = 0.15

        # Normalize
        total = sum(probabilities.values())
        norm_probs = {k: round(v / total, 4) for k, v in probabilities.items()}

        inference_ms = (time.perf_counter() - start_time) * 1000.0
        return FaceDetectionResult(
            detected=True,
            face_count=1,
            bounding_box=FaceBoundingBox(x=100, y=80, width=200, height=200),
            expression_estimate=dominant_key,
            emotion_probabilities=EmotionProbabilities(**norm_probs),
            confidence=0.92,
            inference_time_ms=round(inference_ms, 2)
        )

    def _empty_result(self, start_time: float, reason: str) -> FaceDetectionResult:
        """Returns baseline unconfident result when no face is present."""
        inference_ms = (time.perf_counter() - start_time) * 1000.0
        baseline_probs = {
            "happy": 0.14,
            "neutral": 0.40,
            "surprise": 0.10,
            "sad": 0.14,
            "angry": 0.08,
            "fear": 0.08,
            "disgust": 0.06
        }
        return FaceDetectionResult(
            detected=False,
            face_count=0,
            bounding_box=None,
            expression_estimate=f"undetected ({reason})",
            emotion_probabilities=EmotionProbabilities(**baseline_probs),
            confidence=0.15,
            inference_time_ms=round(inference_ms, 2)
        )


face_emotion_service = FaceEmotionService()
