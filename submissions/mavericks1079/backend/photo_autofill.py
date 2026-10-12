"""Photo autofill: ImageNet MobileNetV2 labels -> Back2U category, plus dominant named colour."""
import io
from pathlib import Path

import numpy as np
from PIL import Image

from image_ml import _session, _MEAN, _STD

LABELS = (Path(__file__).parent / "models" / "imagenet_classes.txt").read_text().splitlines()

LABEL_TO_CATEGORY = {
    "electronics": ["hand-held computer", "notebook", "laptop", "cellular telephone", "dial telephone", "ipod", "mouse", "remote control", "modem",
                    "joystick", "monitor", "screen", "computer keyboard", "space bar", "hard disc", "loudspeaker", "radio", "tape player", "cd player",
                    "desktop computer", "printer", "projector", "television", "digital clock"],
    "bags": ["backpack", "mailbag", "plastic bag"],
    "wallets": ["wallet", "purse"],
    "books": ["binder", "book jacket", "comic book", "pencil box", "pencil sharpener", "ballpoint", "fountain pen", "rubber eraser", "rule", "envelope", "packet"],
    "clothing": ["sweatshirt", "jersey", "cardigan", "jean", "sunglasses", "sunglass", "umbrella", "cowboy hat", "sombrero", "running shoe", "sandal",
                 "loafer", "sock", "mitten", "stole", "trench coat", "lab coat", "bow tie", "windsor tie", "digital watch", "suit", "poncho", "bonnet"],
    "bottles": ["water bottle", "pop bottle", "beer bottle", "wine bottle", "pill bottle", "water jug", "coffee mug", "cup", "beaker", "measuring cup"],
    "jewelry": ["necklace"],
}
_INDEX = {}
for cat, names in LABEL_TO_CATEGORY.items():
    for n in names:
        for i, lab in enumerate(LABELS):
            if lab.lower() == n:
                _INDEX[i] = cat

PALETTE = {
    "black": (25, 25, 25), "white": (240, 240, 240), "grey": (128, 128, 128), "silver": (190, 190, 195), "red": (200, 35, 35),
    "orange": (240, 140, 30), "yellow": (240, 215, 50), "green": (50, 140, 70), "blue": (40, 90, 200), "navy": (25, 35, 90),
    "purple": (120, 55, 160), "pink": (235, 120, 180), "brown": (120, 75, 40), "beige": (215, 195, 160),
}
_NAMES = list(PALETTE)
_RGB = np.array([PALETTE[n] for n in _NAMES], dtype=np.float32)
CATEGORY_MIN = 0.30


def _nearest(pixels):
    d = ((pixels[:, None, :] - _RGB[None, :, :]) ** 2).sum(-1)
    return np.bincount(d.argmin(1), minlength=len(_NAMES)).astype(np.float32)


def dominant_colors(img: Image.Image, top=2):
    a = np.asarray(img.resize((64, 64)), dtype=np.float32)
    center = a[16:48, 16:48].reshape(-1, 3)
    border = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3), a[:, :6].reshape(-1, 3), a[:, -6:].reshape(-1, 3)])
    c = _nearest(center) / len(center)
    b = _nearest(border) / len(border)
    score = np.clip(c - 0.5 * b, 0, None)
    order = np.argsort(score)[::-1]
    return [_NAMES[i] for i in order[:top] if score[i] >= 0.12]


def suggest_from_photo(data: bytes) -> dict:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    x = np.asarray(img.resize((224, 224)), dtype=np.float32) / 255.0
    x = ((x - _MEAN) / _STD).transpose(2, 0, 1)[None].astype(np.float32)
    logits = _session.run(None, {"input": x})[0][0]
    p = np.exp(logits - logits.max())
    p = p / p.sum()
    cats = {}
    for i, cat in _INDEX.items():
        cats[cat] = cats.get(cat, 0.0) + float(p[i])
    best = max(cats, key=cats.get) if cats else None
    conf = cats.get(best, 0.0)
    top = [{"label": LABELS[i], "probability": round(float(p[i]), 3)} for i in np.argsort(p)[::-1][:3]]
    return {"category": best if conf >= CATEGORY_MIN else None, "confidence": round(conf, 3), "uncertain": conf < CATEGORY_MIN,
            "image_labels": top, "colors": dominant_colors(img), "model": "MobileNetV2 (ImageNet) labels mapped to Back2U categories + palette colour analysis"}
