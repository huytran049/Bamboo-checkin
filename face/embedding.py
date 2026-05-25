import threading
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
import onnxruntime

from .vision import detect_faces_from_bgr, vision_face_helper_available

_RECOGNITION_MODEL_PATH = Path("models/face/w600k_r50.onnx")
_ARCFACE_TEMPLATE = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)

_ENGINE = None
_ENGINE_LOCK = threading.Lock()


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm <= 1e-12:
        return vec.astype(np.float32)
    return (vec / norm).astype(np.float32)


class FaceEmbeddingEngine:
    def __init__(
        self,
        recognition_model_path: Path = _RECOGNITION_MODEL_PATH,
    ) -> None:
        self.recognition_model_path = Path(recognition_model_path)
        self._session: Optional[onnxruntime.InferenceSession] = None
        self._input_name: Optional[str] = None
        self._output_name: Optional[str] = None
        self._lock = threading.Lock()

    def is_ready(self) -> bool:
        return vision_face_helper_available() and self.recognition_model_path.exists()

    def _ensure_session(self) -> onnxruntime.InferenceSession:
        if self._session is None:
            if not self.recognition_model_path.exists():
                raise FileNotFoundError(
                    f"Recognition model not found: {self.recognition_model_path}"
                )
            session = onnxruntime.InferenceSession(
                str(self.recognition_model_path),
                providers=["CPUExecutionProvider"],
            )
            self._session = session
            self._input_name = session.get_inputs()[0].name
            self._output_name = session.get_outputs()[0].name
        return self._session

    def detect_primary_face(self, image_bgr: np.ndarray) -> dict[str, Any]:
        payload = detect_faces_from_bgr(image_bgr)
        faces = payload.get("faces") or []
        if not faces:
            raise ValueError("No face detected")

        best = max(
            faces,
            key=lambda item: float(item.get("area") or 0.0),
        )
        landmarks = np.asarray(best.get("arcface_landmarks") or [], dtype=np.float32)
        if landmarks.shape != (5, 2):
            raise ValueError("Apple Vision did not return the 5 landmarks required for ArcFace alignment")

        bbox_payload = best.get("bbox") or {}
        x = int(round(float(bbox_payload.get("x", 0.0))))
        y = int(round(float(bbox_payload.get("y", 0.0))))
        w = int(round(float(bbox_payload.get("w", 0.0))))
        h = int(round(float(bbox_payload.get("h", 0.0))))

        return {
            "bbox": [x, y, x + w, y + h],
            "landmarks": landmarks,
            "confidence": float(best.get("confidence", 0.0)),
            "area": int(round(float(best.get("area", 0.0)))),
            "backend": "apple_vision",
        }

    def align_face(
        self,
        image_bgr: np.ndarray,
        landmarks: np.ndarray,
        output_size: tuple[int, int] = (112, 112),
    ) -> np.ndarray:
        if landmarks.shape != (5, 2):
            raise ValueError("Expected 5 facial landmarks")
        target = _ARCFACE_TEMPLATE.copy()
        if output_size != (112, 112):
            scale_x = output_size[0] / 112.0
            scale_y = output_size[1] / 112.0
            target[:, 0] *= scale_x
            target[:, 1] *= scale_y
        matrix, _ = cv2.estimateAffinePartial2D(
            landmarks.astype(np.float32),
            target.astype(np.float32),
            method=cv2.LMEDS,
        )
        if matrix is None:
            raise ValueError("Failed to estimate face alignment transform")
        return cv2.warpAffine(
            image_bgr,
            matrix,
            output_size,
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )

    def preprocess(self, aligned_bgr: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(aligned_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)
        rgb = (rgb - 127.5) / 128.0
        chw = np.transpose(rgb, (2, 0, 1))
        return np.expand_dims(chw, axis=0).astype(np.float32)

    def infer_embedding(self, aligned_bgr: np.ndarray) -> np.ndarray:
        session = self._ensure_session()
        blob = self.preprocess(aligned_bgr)
        outputs = session.run([self._output_name], {self._input_name: blob})
        return _l2_normalize(outputs[0][0].astype(np.float32))

    def image_quality_score(
        self,
        image_bgr: np.ndarray,
        aligned_bgr: np.ndarray,
        face_info: dict[str, Any],
    ) -> float:
        bbox = face_info["bbox"]
        h, w = image_bgr.shape[:2]
        face_area_ratio = (max(0, bbox[2] - bbox[0]) * max(0, bbox[3] - bbox[1])) / max(1, w * h)
        sharpness = float(cv2.Laplacian(aligned_bgr, cv2.CV_64F).var())
        sharpness_score = min(1.0, sharpness / 500.0)
        confidence = min(1.0, max(0.0, float(face_info.get("confidence", 0.0))))
        return round((face_area_ratio * 0.45) + (sharpness_score * 0.35) + (confidence * 0.20), 4)

    def extract(self, image_bgr: np.ndarray) -> dict[str, Any]:
        with self._lock:
            face_info = self.detect_primary_face(image_bgr)
            aligned = self.align_face(image_bgr, face_info["landmarks"])
            embedding = self.infer_embedding(aligned)
            quality_score = self.image_quality_score(image_bgr, aligned, face_info)
        return {
            "embedding": embedding,
            "bbox": face_info["bbox"],
            "landmarks": face_info["landmarks"].tolist(),
            "confidence": face_info["confidence"],
            "quality_score": quality_score,
            "aligned_face": aligned,
            "detector_backend": face_info.get("backend", "apple_vision"),
        }

    def extract_from_bytes(self, image_bytes: bytes) -> dict[str, Any]:
        arr = np.frombuffer(image_bytes, np.uint8)
        image_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image_bgr is None:
            raise ValueError("Failed to decode image")
        return self.extract(image_bgr)

    def extract_from_path(self, image_path: str | Path) -> dict[str, Any]:
        image_bgr = cv2.imread(str(image_path))
        if image_bgr is None:
            raise ValueError(f"Failed to load image: {image_path}")
        return self.extract(image_bgr)


def get_face_embedding_engine() -> FaceEmbeddingEngine:
    global _ENGINE
    if _ENGINE is None:
        with _ENGINE_LOCK:
            if _ENGINE is None:
                _ENGINE = FaceEmbeddingEngine()
    return _ENGINE


def extract_face_embedding(image_path: str | Path) -> dict[str, Any]:
    return get_face_embedding_engine().extract_from_path(image_path)


def extract_face_embedding_from_bytes(image_bytes: bytes) -> dict[str, Any]:
    return get_face_embedding_engine().extract_from_bytes(image_bytes)
