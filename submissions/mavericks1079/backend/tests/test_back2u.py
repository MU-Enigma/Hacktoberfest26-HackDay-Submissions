"""Basic tests: python -m pytest backend/tests -q (ML/matching are pure; API tests hit the running backend)."""
import os
import uuid

import pytest
import requests

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import ml  # noqa: E402

BASE = os.environ.get("BACK2U_API", "http://localhost:8001/api")


def test_categorizer_predicts_keys():
    p = ml.predict_category("hostel room key", "silver key on ring")
    assert p["category"] == "keys" and 0 <= p["confidence"] <= 1


def test_categorizer_uncertain_fallback():
    p = ml.predict_category("zzqx", "")
    assert p["uncertain"] is (p["confidence"] < ml.UNCERTAIN_THRESHOLD)


def test_match_score_ranks_similar_higher():
    lost = {"title": "white earbuds case", "description": "white wireless earbuds", "category": "electronics", "color": "white", "location": "Library", "occurred_at": "2026-01-01T10:00:00+00:00"}
    good = {**lost, "title": "earbuds in charging case", "occurred_at": "2026-01-01T15:00:00+00:00"}
    bad = {"title": "green bottle", "description": "steel bottle", "category": "bottles", "color": "green", "location": "Gymnasium", "occurred_at": "2025-12-01T10:00:00+00:00"}
    assert ml.score_pair(lost, good, {})["score"] > ml.score_pair(lost, bad, {})["score"]
    assert 0 <= ml.score_pair(lost, bad, {})["score"] <= 100


def test_verify_claim_scores():
    clues = "blue star sticker inside lid, chip on left earbud"
    assert ml.verify_claim("there is a blue star sticker in the lid and a chipped left earbud", clues) > ml.verify_claim("it is white", clues)


def test_image_similarity_and_weights():
    import io
    from PIL import Image
    from image_ml import embed_image, image_similarity

    def img(color):
        buf = io.BytesIO()
        Image.new("RGB", (120, 120), color).save(buf, "PNG")
        return embed_image(buf.getvalue())

    red, red2, blue = img((220, 20, 20)), img((210, 30, 25)), img((20, 40, 220))
    assert image_similarity(red, red2) > image_similarity(red, blue)
    a = {"title": "bottle", "description": "red bottle", "category": "bottles", "location": "Gymnasium", "_img": [red]}
    b = {**a, "_img": [red2]}
    res = ml.score_pair(a, b, {})
    assert "image" in res["breakdown"] and abs(sum(res["weights"].values()) - 1) < 1e-6
    assert "image" not in ml.score_pair({**a, "_img": []}, b, {})["breakdown"]


def test_photo_autofill_colors():
    import io
    from PIL import Image
    from photo_autofill import suggest_from_photo
    im = Image.new("RGB", (200, 200), (245, 245, 245))
    im.paste((200, 35, 35), (60, 60, 140, 140))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    res = suggest_from_photo(buf.getvalue())
    assert "red" in res["colors"] and (res["category"] is None) == res["uncertain"]


def _api_up():
    try:
        return requests.get(f"{BASE}/", timeout=3).ok
    except requests.RequestException:
        return False


@pytest.mark.skipif(not _api_up(), reason="backend not running")
def test_admin_routes_require_admin():
    r = requests.post(f"{BASE}/auth/demo-login", json={"email": "alice@campus.edu"}).json()
    h = {"Authorization": f"Bearer {r['token']}"}
    assert requests.get(f"{BASE}/admin/stats", headers=h).status_code == 403
    assert requests.get(f"{BASE}/admin/stats").status_code == 401


@pytest.mark.skipif(not _api_up(), reason="backend not running")
def test_register_requires_policy():
    r = requests.post(f"{BASE}/auth/register", json={"name": "TEST user", "email": f"test_{uuid.uuid4().hex[:6]}@campus.edu", "password": "Passw0rd!", "accept_policy": False, "policy_version": "1.0"})
    assert r.status_code == 400
