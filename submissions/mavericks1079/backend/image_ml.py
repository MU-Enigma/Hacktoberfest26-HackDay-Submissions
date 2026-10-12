"""Image embeddings: pretrained MobileNetV2 (ONNX, ImageNet) + HSV colour histogram, computed once at upload."""
import io
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

_session = ort.InferenceSession(str(Path(__file__).parent / "models" / "mobilenetv2.onnx"), providers=["CPUExecutionProvider"])
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

CNN_WEIGHT = 0.75
HIST_WEIGHT = 0.25


def _hist(img: Image.Image) -> np.ndarray:
    hsv = np.asarray(img.convert("HSV").resize((64, 64)), dtype=np.float32)
    h, _ = np.histogramdd(hsv.reshape(-1, 3), bins=(8, 4, 4), range=((0, 256), (0, 256), (0, 256)))
    h = h.flatten()
    return h / max(h.sum(), 1)


def embed_image(data: bytes) -> dict:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    x = np.asarray(img.resize((224, 224)), dtype=np.float32) / 255.0
    x = ((x - _MEAN) / _STD).transpose(2, 0, 1)[None].astype(np.float32)
    logits = _session.run(None, {"input": x})[0][0]
    e = np.exp(logits - logits.max())
    probs = e / e.sum()
    vec = np.sqrt(probs)
    vec = vec / (np.linalg.norm(vec) or 1)
    return {"embedding": [round(float(v), 5) for v in vec], "histogram": [round(float(v), 5) for v in _hist(img)]}


def image_similarity(a: dict, b: dict) -> float:
    """0-1 visual similarity. Never proof of ownership."""
    if not a or not b or not a.get("embedding") or not b.get("embedding"):
        return None
    cnn = float(np.dot(np.array(a["embedding"]), np.array(b["embedding"])))
    hist = float(np.minimum(np.array(a["histogram"]), np.array(b["histogram"])).sum())
    return max(0.0, min(1.0, CNN_WEIGHT * cnn + HIST_WEIGHT * hist))


def best_similarity(list_a, list_b):
    scores = [s for x in list_a for y in list_b if (s := image_similarity(x, y)) is not None]
    return max(scores) if scores else None
