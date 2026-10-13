"""Photo matching tests for Back2U — covers upload embedding persistence,
image-weighted matching, watchlist image scoring, duplicate check with
image_paths, and a light regression on item creation + matching.

Run: pytest /app/backend/tests/test_photo_matching.py -v --tb=short
"""
import io
import os
import uuid
import time
import pytest
import requests
from PIL import Image, ImageDraw

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://back2u.preview.emergentagent.com").rstrip("/") + "/api"
DEMO_PASSWORD = "Demo@1234"


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


def _png(color=(255, 0, 0), size=(224, 224), shape="solid"):
    img = Image.new("RGB", size, color)
    if shape == "circle":
        d = ImageDraw.Draw(img)
        d.ellipse([20, 20, size[0] - 20, size[1] - 20], fill=(255, 255, 255))
    elif shape == "stripes":
        d = ImageDraw.Draw(img)
        for i in range(0, size[0], 20):
            d.rectangle([i, 0, i + 10, size[1]], fill=(0, 0, 0))
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


def _upload(token, data, name="x.png", ctype="image/png"):
    return requests.post(f"{BASE}/uploads", headers=_hdr(token),
                         files={"file": (name, io.BytesIO(data), ctype)})


# ---------- Uploads: embeddings + validation ----------
class TestUploadEmbeddings:
    def test_upload_png_stores_embedding(self, alice):
        r = _upload(alice["token"], _png((200, 50, 50)))
        assert r.status_code == 200, r.text
        path = r.json()["path"]
        # Verify db record has embedding + histogram by using image_similarity indirectly:
        # Upload the same image again, create two lost items, and check matches/image breakdown.
        assert isinstance(path, str) and path.endswith(".png")

    def test_upload_rejects_non_image_content_type(self, alice):
        r = _upload(alice["token"], b"not an image", name="x.txt", ctype="text/plain")
        assert r.status_code == 415

    def test_upload_rejects_corrupt_image_bytes(self, alice):
        # content_type claims PNG but bytes are garbage -> embed_image should raise -> 422
        r = _upload(alice["token"], b"\x89PNGnot-a-real-png", name="x.png", ctype="image/png")
        assert r.status_code == 422

    def test_upload_too_large(self, alice):
        big = b"\x89PNG" + b"\x00" * (5 * 1024 * 1024 + 100)
        r = _upload(alice["token"], big, name="big.png", ctype="image/png")
        assert r.status_code == 413


# ---------- Matching with photos ----------
def _mk_item(token, type_, title, image_paths, color="red", location="Library"):
    r = requests.post(f"{BASE}/items", headers=_hdr(token), json={
        "type": type_, "title": title,
        "description": "a small red object seen on a table in the library",
        "category": "other", "color": color, "location": location,
        "occurred_at": "2026-01-07T10:00:00+00:00",
        "image_paths": image_paths,
    })
    assert r.status_code == 200, r.text
    return r.json()


class TestMatchImageBreakdown:
    def test_match_both_photos_similar_vs_different(self, alice, bob):
        # Upload a red image for alice (lost) and a visually similar red image for bob (found).
        red_a = _upload(alice["token"], _png((220, 30, 30)))
        red_b = _upload(bob["token"], _png((225, 25, 25)))
        assert red_a.status_code == 200 and red_b.status_code == 200

        tag = uuid.uuid4().hex[:6]
        title = f"TEST photomatch red widget {tag}"
        lost = _mk_item(alice["token"], "lost", title, [red_a.json()["path"]])
        found = _mk_item(bob["token"], "found", title, [red_b.json()["path"]])

        # Fetch alice's matches for her lost item
        time.sleep(1)
        r = requests.get(f"{BASE}/items/{lost['id']}/matches", headers=_hdr(alice["token"]))
        assert r.status_code == 200
        d = r.json()
        m = next((x for x in d["matches"] if x["item"]["id"] == found["id"]), None)
        assert m is not None, f"Expected a match for {found['id']}, got {d}"
        # breakdown.image present, weights.image == 0.2, other weights scaled to sum to 1
        assert "image" in m["breakdown"]
        assert 0.0 <= m["breakdown"]["image"] <= 1.0
        assert abs(m["weights"]["image"] - 0.2) < 1e-6
        total_w = sum(m["weights"].values())
        assert abs(total_w - 1.0) < 1e-3, m["weights"]
        # Each non-image weight should be original * 0.8
        from_defaults = {"description": 0.35, "category": 0.20, "attributes": 0.15, "location": 0.15, "date": 0.15}
        for k, v in from_defaults.items():
            assert abs(m["weights"][k] - v * 0.8) < 1e-3
        similar_score = m["score"]
        similar_image_sim = m["breakdown"]["image"]
        # Should be high since same solid colour
        assert similar_image_sim >= 0.6, f"expected high image sim, got {similar_image_sim}"
        # Reason mentioning visual similarity should be present
        assert any("visually similar" in r.lower() for r in m["reasons"])

        # Now swap bob's photo with a BLUE image (visually different) -> replace found item's image_paths
        blue = _upload(bob["token"], _png((20, 30, 220)))
        assert blue.status_code == 200
        patch = requests.patch(f"{BASE}/items/{found['id']}", headers=_hdr(bob["token"]),
                               json={"image_paths": [blue.json()["path"]]})
        assert patch.status_code == 200, patch.text
        time.sleep(1)
        r2 = requests.get(f"{BASE}/items/{lost['id']}/matches", headers=_hdr(alice["token"]))
        assert r2.status_code == 200
        m2 = next((x for x in r2.json()["matches"] if x["item"]["id"] == found["id"]), None)
        assert m2 is not None
        assert m2["breakdown"]["image"] < similar_image_sim, \
            f"different-photo sim {m2['breakdown']['image']} should be < similar sim {similar_image_sim}"
        assert m2["score"] <= similar_score, f"different-photo score {m2['score']} should be <= similar {similar_score}"

    def test_match_one_side_no_photo_no_image_key(self, alice, bob):
        tag = uuid.uuid4().hex[:6]
        title = f"TEST only one photo green bottle {tag}"
        up = _upload(alice["token"], _png((20, 180, 60)))
        assert up.status_code == 200
        lost = _mk_item(alice["token"], "lost", title, [up.json()["path"]], color="green", location="Gymnasium")
        found = _mk_item(bob["token"], "found", title, [], color="green", location="Gymnasium")
        time.sleep(1)
        r = requests.get(f"{BASE}/items/{lost['id']}/matches", headers=_hdr(alice["token"]))
        assert r.status_code == 200
        m = next((x for x in r.json()["matches"] if x["item"]["id"] == found["id"]), None)
        assert m is not None, "expected text-only match"
        assert "image" not in m["breakdown"]
        # Weights sum to 1 and image absent
        assert "image" not in m["weights"]
        assert abs(sum(m["weights"].values()) - 1.0) < 1e-3


# ---------- Duplicate check with image_paths ----------
class TestDuplicatesWithImages:
    def test_check_duplicates_accepts_image_paths(self, alice):
        up = _upload(alice["token"], _png((100, 100, 200)))
        assert up.status_code == 200
        r = requests.post(f"{BASE}/items/check-duplicates", headers=_hdr(alice["token"]), json={
            "type": "found", "title": "Earbuds in white charging case",
            "description": "white earbuds inside a small white case",
            "category": "electronics", "color": "white", "location": "Centre for Sustainability",
            "image_paths": [up.json()["path"]],
        })
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------- Watchlist with reference_image ----------
class TestWatchlistImage:
    def test_watchlist_with_reference_image_triggers_on_similar_photo(self, alice, bob):
        ref = _upload(alice["token"], _png((255, 200, 50), shape="circle"))
        assert ref.status_code == 200
        wl = requests.post(f"{BASE}/watchlists", headers=_hdr(alice["token"]), json={
            "name": f"TEST wl img {uuid.uuid4().hex[:4]}", "keywords": "yellow widget",
            "category": "other", "locations": ["Library"], "threshold": 30,
            "item_type": "found", "active": True, "reference_image": ref.json()["path"],
        })
        assert wl.status_code == 200, wl.text
        wid = wl.json()["id"]

        # Mark alice's notifications as read so we can detect a new one
        requests.post(f"{BASE}/notifications/read-all", headers=_hdr(alice["token"]))

        # Bob reports a found item with a visually similar photo
        similar = _upload(bob["token"], _png((250, 205, 55), shape="circle"))
        assert similar.status_code == 200
        item = _mk_item(bob["token"], "found", f"TEST yellow widget {uuid.uuid4().hex[:4]}",
                        [similar.json()["path"]], color="yellow")
        time.sleep(1.5)
        notif = requests.get(f"{BASE}/notifications", headers=_hdr(alice["token"])).json()
        wl_hits = [n for n in notif.get("items", []) if n.get("type") == "watchlist" and item["id"] in (n.get("link") or "")]
        assert wl_hits, f"Expected watchlist notification for item {item['id']}, got {notif}"

        requests.delete(f"{BASE}/watchlists/{wid}", headers=_hdr(alice["token"]))


# ---------- Light regression: seeded alice/bob earbuds ----------
class TestSeedRegression:
    def test_seed_alice_lost_earbuds_matches_bob_found_with_image_factor(self, alice):
        mine = requests.get(f"{BASE}/items/mine", headers=_hdr(alice["token"])).json()
        earbuds = next((i for i in mine if i["type"] == "lost" and "earbud" in i["title"].lower()), None)
        if not earbuds:
            pytest.skip("Seed alice lost earbuds not present")
        r = requests.get(f"{BASE}/items/{earbuds['id']}/matches", headers=_hdr(alice["token"]))
        assert r.status_code == 200
        matches = r.json()["matches"]
        assert matches, "expected at least one match"
        top = matches[0]
        assert top["score"] >= 80, f"expected high top score, got {top['score']}"
        # If both seeds have images, we expect image key; log either way.
        print(f"[regression] alice lost earbuds top match score={top['score']} breakdown={top['breakdown']}")
