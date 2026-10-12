"""Photo autofill tests for Back2U — POST /api/ml/photo-suggest.

Covers auth 401, ownership 404, response schema, mapped-category confidence,
category-null for unmappable classes (e.g., keys/ID cards), red-colour detection.

Run: pytest /app/backend/tests/test_photo_autofill.py -v --tb=short -o addopts=''
"""
import io
import os
import pytest
import requests
from PIL import Image, ImageDraw

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://back2u.preview.emergentagent.com").rstrip("/") + "/api"


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


def _png(color=(255, 0, 0), size=(224, 224)):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _red_on_white():
    img = Image.new("RGB", (256, 256), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([80, 80, 176, 176], fill=(220, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def alice():
    r = requests.post(f"{BASE}/auth/demo-login", json={"email": "alice@campus.edu"})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def bob():
    r = requests.post(f"{BASE}/auth/demo-login", json={"email": "bob@campus.edu"})
    assert r.status_code == 200, r.text
    return r.json()


def _upload(token, data, ctype="image/png", name="x.png"):
    files = {"file": (name, io.BytesIO(data), ctype)}
    r = requests.post(f"{BASE}/uploads", headers=_hdr(token), files=files)
    assert r.status_code == 200, r.text
    return r.json()["path"]


def _fetch_url(url, ctype="image/jpeg"):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.content, ctype


class TestAuth:
    def test_requires_login(self):
        r = requests.post(f"{BASE}/ml/photo-suggest", json={"path": "whatever"})
        assert r.status_code == 401

    def test_ownership_404_for_unknown_path(self, alice):
        r = requests.post(f"{BASE}/ml/photo-suggest", headers=_hdr(alice["token"]), json={"path": "does-not-exist"})
        assert r.status_code == 404

    def test_ownership_404_for_other_users_file(self, alice, bob):
        path = _upload(alice["token"], _png((10, 200, 10)))
        r = requests.post(f"{BASE}/ml/photo-suggest", headers=_hdr(bob["token"]), json={"path": path})
        assert r.status_code == 404


class TestSchema:
    def test_response_schema_has_all_keys(self, alice):
        path = _upload(alice["token"], _red_on_white())
        r = requests.post(f"{BASE}/ml/photo-suggest", headers=_hdr(alice["token"]), json={"path": path})
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("category", "label", "confidence", "uncertain", "image_labels", "colors", "model"):
            assert k in d, f"missing key {k}"
        assert isinstance(d["image_labels"], list) and len(d["image_labels"]) == 3
        for il in d["image_labels"]:
            assert "label" in il and "probability" in il
        assert isinstance(d["colors"], list)
        assert isinstance(d["confidence"], (int, float))
        assert isinstance(d["uncertain"], bool)


class TestColorDetection:
    def test_red_square_on_white(self, alice):
        path = _upload(alice["token"], _red_on_white())
        r = requests.post(f"{BASE}/ml/photo-suggest", headers=_hdr(alice["token"]), json={"path": path})
        assert r.status_code == 200
        colors = r.json()["colors"]
        assert "red" in colors, f"expected 'red' in colors, got {colors}"


class TestCategoryMapping:
    def test_bottle_photo_maps_to_bottles(self, alice):
        # Use the exact bottle test image mentioned in the review request
        url = "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.content
        except Exception as e:
            pytest.skip(f"Could not fetch test bottle photo: {e}")
        path = _upload(alice["token"], data, ctype="image/jpeg", name="bottle.jpg")
        r = requests.post(f"{BASE}/ml/photo-suggest", headers=_hdr(alice["token"]), json={"path": path})
        assert r.status_code == 200
        d = r.json()
        assert d["category"] == "bottles", f"expected bottles, got {d['category']} (labels={d['image_labels']}, conf={d['confidence']})"
        assert d["uncertain"] is False
        assert d["label"]  # human label present
        assert d["confidence"] >= 0.30

    def test_backpack_photo_maps_to_bags(self, alice):
        url = "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.content
        except Exception as e:
            pytest.skip(f"Could not fetch test backpack photo: {e}")
        path = _upload(alice["token"], data, ctype="image/jpeg", name="bag.jpg")
        r = requests.post(f"{BASE}/ml/photo-suggest", headers=_hdr(alice["token"]), json={"path": path})
        assert r.status_code == 200
        d = r.json()
        assert d["category"] == "bags", f"expected bags, got {d['category']} (labels={d['image_labels']})"

    def test_low_confidence_returns_null_and_uncertain(self, alice):
        # A plain red square has no mapped ImageNet class — mapped category confidence should be <0.30.
        path = _upload(alice["token"], _red_on_white())
        r = requests.post(f"{BASE}/ml/photo-suggest", headers=_hdr(alice["token"]), json={"path": path})
        assert r.status_code == 200
        d = r.json()
        assert d["category"] is None
        assert d["uncertain"] is True
        assert d["confidence"] < 0.30
        assert d["label"] is None
