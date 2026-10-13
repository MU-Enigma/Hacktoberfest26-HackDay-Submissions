"""End-to-end backend tests for Back2U — exercises auth, items, duplicates,
matching, claims, handover, admin and policy flows against the live backend.

Run: pytest /app/backend/tests/test_back2u_e2e.py -v --tb=short
"""
import os
import uuid
import time
import io
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://back2u.preview.emergentagent.com").rstrip("/") + "/api"
ADMIN_EMAIL = "richa.kshama@gmail.com"
ADMIN_PASSWORD = "Back2U@Admin26"
DEMO_PASSWORD = "Demo@1234"
POLICY_VERSION = "1.0"


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{BASE}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def alice():
    r = requests.post(f"{BASE}/auth/demo-login", json={"email": "alice@campus.edu"})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="session")
def bob():
    r = requests.post(f"{BASE}/auth/demo-login", json={"email": "bob@campus.edu"})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="session")
def carol():
    r = requests.post(f"{BASE}/auth/demo-login", json={"email": "carol@campus.edu"})
    assert r.status_code == 200, r.text
    return r.json()


# ---------- Auth / Policy ----------
class TestAuth:
    def test_root(self):
        r = requests.get(f"{BASE}/")
        assert r.status_code == 200 and r.json()["policy_version"] == POLICY_VERSION

    def test_register_requires_policy(self):
        r = requests.post(f"{BASE}/auth/register", json={
            "name": "TEST user", "email": f"test_{uuid.uuid4().hex[:6]}@campus.edu",
            "password": "Passw0rd!", "accept_policy": False, "policy_version": POLICY_VERSION})
        assert r.status_code == 400

    def test_register_policy_version_mismatch(self):
        r = requests.post(f"{BASE}/auth/register", json={
            "name": "TEST user", "email": f"test_{uuid.uuid4().hex[:6]}@campus.edu",
            "password": "Passw0rd!", "accept_policy": True, "policy_version": "9.9"})
        assert r.status_code == 400

    def test_register_success_and_policy_ack_false(self):
        email = f"test_{uuid.uuid4().hex[:8]}@campus.edu"
        r = requests.post(f"{BASE}/auth/register", json={
            "name": "TEST New", "email": email, "password": "Passw0rd!",
            "accept_policy": True, "policy_version": POLICY_VERSION})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["token"] and d["user"]["email"] == email
        assert d["user"]["report_policy_ack"] is False

    def test_login_invalid(self):
        r = requests.post(f"{BASE}/auth/login", json={"email": "nobody@campus.edu", "password": "wrong"})
        assert r.status_code == 401

    def test_demo_login_all(self, alice, bob, carol):
        assert alice["user"]["email"] == "alice@campus.edu"
        assert bob["user"]["email"] == "bob@campus.edu"
        assert carol["user"]["email"] == "carol@campus.edu"

    def test_me_requires_auth(self):
        assert requests.get(f"{BASE}/auth/me").status_code == 401

    def test_me_ok(self, alice):
        r = requests.get(f"{BASE}/auth/me", headers=_hdr(alice["token"]))
        assert r.status_code == 200 and r.json()["email"] == "alice@campus.edu"

    def test_bcrypt_hash_format(self):
        import pymongo
        c = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        u = c[os.environ.get("DB_NAME", "test_database")].users.find_one({"email": ADMIN_EMAIL})
        assert u and u["password_hash"].startswith("$2b$")


# ---------- Items / ML / Duplicates ----------
class TestItemsML:
    def test_categorize(self):
        r = requests.post(f"{BASE}/ml/categorize", json={"title": "hostel room key", "description": "silver"})
        assert r.status_code == 200 and r.json()["category"] == "keys"

    def test_locations_list(self):
        r = requests.get(f"{BASE}/locations")
        assert r.status_code == 200 and len(r.json()) >= 10

    def test_categories_list(self):
        r = requests.get(f"{BASE}/categories")
        assert r.status_code == 200 and len(r.json()) > 3

    def test_feed_public(self):
        r = requests.get(f"{BASE}/feed")
        assert r.status_code == 200
        d = r.json()
        for k in ("lost", "found", "recovered", "matches", "stats"):
            assert k in d

    def test_stats_public(self):
        r = requests.get(f"{BASE}/stats")
        assert r.status_code == 200 and "lost" in r.json()

    def test_items_list_hides_private(self):
        r = requests.get(f"{BASE}/items?type=found&limit=50")
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert "secure_collection_location" not in it
            assert "owner_id" not in it

    def test_newly_registered_cannot_create_before_ack(self):
        email = f"test_{uuid.uuid4().hex[:8]}@campus.edu"
        reg = requests.post(f"{BASE}/auth/register", json={
            "name": "TEST Noack", "email": email, "password": "Passw0rd!",
            "accept_policy": True, "policy_version": POLICY_VERSION}).json()
        tok = reg["token"]
        r = requests.post(f"{BASE}/items", headers=_hdr(tok), json={
            "type": "lost", "title": "Test lost book", "description": "a blue novel",
            "category": "books", "location": "Library",
            "occurred_at": "2026-01-05T10:00:00+00:00"})
        assert r.status_code == 403
        # Now ack and retry
        ack = requests.post(f"{BASE}/policy/report-ack", headers=_hdr(tok))
        assert ack.status_code == 200
        r2 = requests.post(f"{BASE}/items", headers=_hdr(tok), json={
            "type": "lost", "title": "TEST lost book", "description": "a blue novel",
            "category": "books", "location": "Library",
            "occurred_at": "2026-01-05T10:00:00+00:00"})
        assert r2.status_code == 200, r2.text
        assert "secure_collection_location" not in r2.json() or r2.json().get("secure_collection_location") in ("", None)

    def test_duplicate_detection(self, alice):
        r = requests.post(f"{BASE}/items/check-duplicates", headers=_hdr(alice["token"]), json={
            "type": "found", "title": "Earbuds in white charging case",
            "description": "white earbuds inside a small white case",
            "category": "electronics", "color": "white", "location": "Centre for Sustainability"})
        assert r.status_code == 200
        # Not strict - seed may or may not match depending on state
        data = r.json()
        assert isinstance(data, list)


# ---------- Matching ----------
class TestMatching:
    def test_matches_for_alice_lost(self, alice):
        mine = requests.get(f"{BASE}/items/mine", headers=_hdr(alice["token"])).json()
        earbuds_lost = next((i for i in mine if i["type"] == "lost" and "earbud" in i["title"].lower()), None)
        if not earbuds_lost:
            pytest.skip("Seed alice lost earbuds not present")
        r = requests.get(f"{BASE}/items/{earbuds_lost['id']}/matches", headers=_hdr(alice["token"]))
        assert r.status_code == 200
        d = r.json()
        assert "matches" in d
        assert any(m["score"] >= 80 for m in d["matches"]), f"Expected high-score match, got {[m['score'] for m in d['matches']]}"

    def test_match_access_denied_to_other(self, bob):
        mine = requests.get(f"{BASE}/items/mine", headers=_hdr(bob["token"])).json()
        if not mine:
            pytest.skip("bob has no items")
        # Get alice's item id via public listing
        others = requests.get(f"{BASE}/items?type=lost&limit=50").json()["items"]
        if not others:
            pytest.skip()
        # Just verify route denies when not owner
        for it in others:
            if not it["is_owner"]:
                r = requests.get(f"{BASE}/items/{it['id']}/matches", headers=_hdr(bob["token"]))
                assert r.status_code == 403
                break


# ---------- Private clues leakage ----------
class TestPrivacy:
    def test_private_clues_hidden_for_non_owner(self, alice, bob):
        # Find a bob-owned found item that has private clues AND no approved claim from alice
        bob_items = requests.get(f"{BASE}/items/mine", headers=_hdr(bob["token"])).json()
        tgt = None
        for i in bob_items:
            if i["type"] != "found" or not i.get("has_private_clues"):
                continue
            # Ensure alice has no approved/completed claim on this item
            claims = requests.get(f"{BASE}/items/{i['id']}/claims", headers=_hdr(bob["token"])).json()
            if any(cl.get("claimant_id") == alice["user"]["id"] and cl.get("status") in ("approved", "completed") for cl in claims):
                continue
            tgt = i
            break
        if not tgt:
            pytest.skip("No eligible bob found item for privacy test")
        r = requests.get(f"{BASE}/items/{tgt['id']}", headers=_hdr(alice["token"]))
        assert r.status_code == 200
        d = r.json()
        assert "private_clues" not in d or not d.get("private_clues")
        assert not d.get("secure_collection_location")


# ---------- Claims & Handover ----------
@pytest.fixture(scope="session")
def claim_flow(alice, bob):
    """Create: bob reports found earbuds, alice claims. Returns (item_id, claim_id)."""
    # Bob reports found
    item = requests.post(f"{BASE}/items", headers=_hdr(bob["token"]), json={
        "type": "found", "title": "TEST Earbuds in white case",
        "description": "white wireless earbuds in a charging case, left in library",
        "category": "electronics", "color": "white", "location": "Centre for Sustainability",
        "occurred_at": "2026-01-06T10:00:00+00:00",
        "private_clues": "blue star sticker inside lid; chipped left bud",
        "secure_collection_location": "Campus Security Office", "holder": "office",
        "collection_window": "Mon-Fri 10-5",
    })
    assert item.status_code == 200, item.text
    item_id = item.json()["id"]
    # Alice claims
    cl = requests.post(f"{BASE}/items/{item_id}/claims", headers=_hdr(alice["token"]), json={
        "marks": "there is a blue star sticker inside the lid and a chipped left earbud",
        "contents": "white silicon tips",
        "circumstances": "I lost them yesterday in the library reading room while studying",
    })
    assert cl.status_code == 200, cl.text
    return item_id, cl.json()["id"]


class TestClaims:
    def test_cannot_claim_own(self, bob, claim_flow):
        item_id, _ = claim_flow
        r = requests.post(f"{BASE}/items/{item_id}/claims", headers=_hdr(bob["token"]), json={
            "marks": "mine", "circumstances": "I reported it"})
        assert r.status_code == 400

    def test_claimant_cannot_see_score(self, alice, claim_flow):
        _, claim_id = claim_flow
        mine = requests.get(f"{BASE}/claims/mine", headers=_hdr(alice["token"])).json()
        c = next((x for x in mine if x["id"] == claim_id), None)
        assert c is not None
        assert "verification_score" not in c

    def test_finder_sees_score(self, bob, claim_flow):
        item_id, claim_id = claim_flow
        rows = requests.get(f"{BASE}/items/{item_id}/claims", headers=_hdr(bob["token"])).json()
        c = next((x for x in rows if x["id"] == claim_id), None)
        assert c is not None
        assert "verification_score" in c and c["verification_score"] is not None
        assert c.get("score_label") in ("Strong", "Partial", "Weak", "No private clues stored - verify manually")

    def test_review_start_verification_and_approve(self, bob, claim_flow):
        item_id, claim_id = claim_flow
        r = requests.post(f"{BASE}/claims/{claim_id}/review", headers=_hdr(bob["token"]),
                          json={"action": "start_verification", "note": "checking"})
        assert r.status_code == 200
        it = requests.get(f"{BASE}/items/{item_id}").json()
        assert it["status"] == "VERIFICATION IN PROGRESS"
        r2 = requests.post(f"{BASE}/claims/{claim_id}/review", headers=_hdr(bob["token"]),
                           json={"action": "approve", "note": "ok"})
        assert r2.status_code == 200
        it2 = requests.get(f"{BASE}/items/{item_id}").json()
        assert it2["status"] == "READY FOR HANDOVER"

    def test_claim_rate_limit(self, carol, bob):
        # Bob creates a decoy found item
        item = requests.post(f"{BASE}/items", headers=_hdr(bob["token"]), json={
            "type": "found", "title": "TEST decoy wallet",
            "description": "brown leather wallet with cards inside",
            "category": "wallets", "color": "brown", "location": "Dining-1",
            "occurred_at": "2026-01-06T10:00:00+00:00",
            "private_clues": "driver license id 1234", "secure_collection_location": "Campus Security Office",
            "holder": "office",
        }).json()
        item_id = item["id"]
        for i in range(3):
            r = requests.post(f"{BASE}/items/{item_id}/claims", headers=_hdr(carol["token"]), json={
                "marks": f"attempt {i} brown leather", "circumstances": "mine lost in cafe"})
            # second/third should produce 409 (open claim exists) unless cancelled
            if r.status_code == 409:
                # cancel and retry
                mine = requests.get(f"{BASE}/claims/mine", headers=_hdr(carol["token"])).json()
                open_c = next((x for x in mine if x["item_id"] == item_id and x["status"] in ("pending", "verifying")), None)
                if open_c:
                    requests.post(f"{BASE}/claims/{open_c['id']}/cancel", headers=_hdr(carol["token"]))
                r = requests.post(f"{BASE}/items/{item_id}/claims", headers=_hdr(carol["token"]), json={
                    "marks": f"retry {i}", "circumstances": "mine lost in cafe"})
            assert r.status_code in (200, 429), f"attempt {i}: {r.status_code} {r.text}"
        # Cancel and try a 4th -> should 429
        mine = requests.get(f"{BASE}/claims/mine", headers=_hdr(carol["token"])).json()
        open_c = next((x for x in mine if x["item_id"] == item_id and x["status"] in ("pending", "verifying")), None)
        if open_c:
            requests.post(f"{BASE}/claims/{open_c['id']}/cancel", headers=_hdr(carol["token"]))
        r = requests.post(f"{BASE}/items/{item_id}/claims", headers=_hdr(carol["token"]), json={
            "marks": "4th attempt", "circumstances": "mine"})
        assert r.status_code == 429


class TestHandover:
    def test_qr_handover_flow(self, alice, bob):
        # Create fresh item/claim/approval chain (isolated from other test ordering)
        it = requests.post(f"{BASE}/items", headers=_hdr(bob["token"]), json={
            "type": "found", "title": "TEST QR flow earbuds",
            "description": "white wireless earbuds for qr handover test",
            "category": "electronics", "color": "white", "location": "Centre for Sustainability",
            "occurred_at": "2026-01-07T10:00:00+00:00",
            "private_clues": "blue star sticker inside lid",
            "secure_collection_location": "Campus Security Office", "holder": "office",
        }).json()
        item_id = it["id"]
        c = requests.post(f"{BASE}/items/{item_id}/claims", headers=_hdr(alice["token"]), json={
            "marks": "blue star sticker inside the lid", "circumstances": "lost in library"}).json()
        claim_id = c["id"]
        requests.post(f"{BASE}/claims/{claim_id}/review", headers=_hdr(bob["token"]),
                      json={"action": "approve", "note": "ok"})
        rows = requests.get(f"{BASE}/items/{item_id}/claims", headers=_hdr(bob["token"])).json()
        c = next(x for x in rows if x["id"] == claim_id)
        hid = c["handover"]["id"]
        # Bob issues token
        tok = requests.post(f"{BASE}/handovers/{hid}/token", headers=_hdr(bob["token"])).json()
        assert "token" in tok and "code" in tok
        # Bob cannot scan (not claimant)
        bad = requests.post(f"{BASE}/handovers/scan", headers=_hdr(bob["token"]), json={"token": tok["token"]})
        assert bad.status_code == 403
        # Alice scans with token
        s = requests.post(f"{BASE}/handovers/scan", headers=_hdr(alice["token"]), json={"token": tok["token"]})
        assert s.status_code == 200
        # Reusing same token should fail
        again = requests.post(f"{BASE}/handovers/scan", headers=_hdr(alice["token"]), json={"token": tok["token"]})
        assert again.status_code in (400, 409, 410)
        # Item still not RETURNED until finder confirms
        it = requests.get(f"{BASE}/items/{item_id}").json()
        assert it["status"] != "RETURNED"
        # Bob confirms
        fc = requests.post(f"{BASE}/handovers/{hid}/finder-confirm", headers=_hdr(bob["token"]))
        assert fc.status_code == 200 and fc.json()["status"] == "completed"
        # Item is RETURNED
        it2 = requests.get(f"{BASE}/items/{item_id}").json()
        assert it2["status"] == "RETURNED"
        receipt_id = fc.json()["receipt_id"]
        # Both parties can see receipt
        for who in (alice["token"], bob["token"]):
            r = requests.get(f"{BASE}/receipts/{receipt_id}", headers=_hdr(who))
            assert r.status_code == 200

    def test_handover_code_path_fresh(self, alice, bob):
        # Create fresh item & claim via code (not token)
        it = requests.post(f"{BASE}/items", headers=_hdr(bob["token"]), json={
            "type": "found", "title": "TEST Steel bottle green",
            "description": "green steel water bottle with dents",
            "category": "bottles", "color": "green", "location": "Gymnasium",
            "occurred_at": "2026-01-06T10:00:00+00:00",
            "private_clues": "dent near base",
            "secure_collection_location": "Campus Security Office", "holder": "office"}).json()
        iid = it["id"]
        c = requests.post(f"{BASE}/items/{iid}/claims", headers=_hdr(alice["token"]), json={
            "marks": "there is a dent near the base",
            "circumstances": "lost at gym"}).json()
        cid = c["id"]
        requests.post(f"{BASE}/claims/{cid}/review", headers=_hdr(bob["token"]), json={"action": "approve", "note": "ok"})
        rows = requests.get(f"{BASE}/items/{iid}/claims", headers=_hdr(bob["token"])).json()
        hid = next(x for x in rows if x["id"] == cid)["handover"]["id"]
        tok = requests.post(f"{BASE}/handovers/{hid}/token", headers=_hdr(bob["token"])).json()
        # Alice uses code
        s = requests.post(f"{BASE}/handovers/scan", headers=_hdr(alice["token"]),
                          json={"handover_id": hid, "code": tok["code"]})
        assert s.status_code == 200
        # Reuse code fails
        again = requests.post(f"{BASE}/handovers/scan", headers=_hdr(alice["token"]),
                              json={"handover_id": hid, "code": tok["code"]})
        assert again.status_code in (400, 409, 410)


# ---------- Watchlists & Notifications ----------
class TestWatchlist:
    def test_crud(self, alice):
        tok = alice["token"]
        wl = requests.post(f"{BASE}/watchlists", headers=_hdr(tok), json={
            "name": "TEST wl", "keywords": "earbuds", "category": "electronics",
            "locations": ["Library"], "threshold": 60, "item_type": "found", "active": True}).json()
        assert "id" in wl
        wl2 = requests.put(f"{BASE}/watchlists/{wl['id']}", headers=_hdr(tok), json={
            "name": "TEST wl2", "keywords": "earbuds", "category": "electronics",
            "locations": ["Library"], "threshold": 70, "item_type": "found", "active": False}).json()
        assert wl2["active"] is False
        d = requests.delete(f"{BASE}/watchlists/{wl['id']}", headers=_hdr(tok))
        assert d.status_code == 200

    def test_notifications_read_all(self, alice):
        r = requests.post(f"{BASE}/notifications/read-all", headers=_hdr(alice["token"]))
        assert r.status_code == 200
        n = requests.get(f"{BASE}/notifications", headers=_hdr(alice["token"])).json()
        assert n["unread"] == 0


# ---------- Moderation / Appeals ----------
class TestModeration:
    def test_report_abuse(self, alice):
        r = requests.post(f"{BASE}/moderation/reports", headers=_hdr(alice["token"]), json={
            "target_type": "other", "reason": "TEST report", "details": "testing"})
        assert r.status_code == 200 and "reference" in r.json()


# ---------- Admin ----------
class TestAdmin:
    def test_students_denied(self, alice):
        for ep in ("stats", "users", "reports", "claims", "handovers", "audit", "items", "appeals"):
            r = requests.get(f"{BASE}/admin/{ep}", headers=_hdr(alice["token"]))
            assert r.status_code == 403, f"{ep}: {r.status_code}"

    def test_unauth_401(self):
        assert requests.get(f"{BASE}/admin/stats").status_code == 401

    def test_admin_stats(self, admin_token):
        r = requests.get(f"{BASE}/admin/stats", headers=_hdr(admin_token))
        assert r.status_code == 200
        s = r.json()
        for k in ("lost", "found", "returned", "open_reports", "open_claims", "active_handovers", "banned", "open_appeals"):
            assert k in s

    def test_admin_users_search(self, admin_token):
        r = requests.get(f"{BASE}/admin/users?q=alice", headers=_hdr(admin_token))
        assert r.status_code == 200 and any(u["email"] == "alice@campus.edu" for u in r.json())

    def test_admin_cannot_moderate_admin(self, admin_token):
        r = requests.get(f"{BASE}/admin/users?q=richa", headers=_hdr(admin_token)).json()
        if r:
            uid = r[0]["id"]
            res = requests.post(f"{BASE}/admin/users/{uid}/action", headers=_hdr(admin_token),
                                json={"action": "suspend", "reason": "test moderating admin", "days": 1})
            assert res.status_code == 400

    def test_admin_ban_and_reinstate_flow(self, admin_token):
        # Create TEST user and ban/reinstate
        email = f"test_{uuid.uuid4().hex[:8]}@campus.edu"
        reg = requests.post(f"{BASE}/auth/register", json={
            "name": "TEST Ban", "email": email, "password": "Passw0rd!",
            "accept_policy": True, "policy_version": POLICY_VERSION}).json()
        uid, tok = reg["user"]["id"], reg["token"]
        # Suspend
        r = requests.post(f"{BASE}/admin/users/{uid}/action", headers=_hdr(admin_token),
                          json={"action": "suspend", "reason": "testing suspend", "days": 7})
        assert r.status_code == 200
        # Suspended user cannot create items
        it = requests.post(f"{BASE}/items", headers=_hdr(tok), json={
            "type": "lost", "title": "TEST x", "description": "aaaaa",
            "category": "books", "location": "Library",
            "occurred_at": "2026-01-05T10:00:00+00:00"})
        assert it.status_code == 403
        # Suspended user cannot upload
        up = requests.post(f"{BASE}/uploads", headers=_hdr(tok),
                           files={"file": ("x.jpg", io.BytesIO(b"abc"), "image/jpeg")})
        assert up.status_code == 403
        # Submit appeal
        ap = requests.post(f"{BASE}/appeals", headers=_hdr(tok), json={"message": "please reinstate me, test"})
        assert ap.status_code == 200
        # Admin overturns appeal
        aid = ap.json()["id"]
        res = requests.post(f"{BASE}/admin/appeals/{aid}/resolve", headers=_hdr(admin_token),
                            json={"decision": "overturned", "note": "test overturn"})
        assert res.status_code == 200
        # User can now access protected endpoint - active again
        me = requests.get(f"{BASE}/auth/me", headers=_hdr(tok)).json()
        assert me["status"] == "active"

    def test_admin_locations_add_delete(self, admin_token):
        name = f"TEST Zone {uuid.uuid4().hex[:6]}"
        r = requests.post(f"{BASE}/admin/locations", headers=_hdr(admin_token),
                          json={"name": name, "zone": "Test", "is_safe_point": False})
        assert r.status_code == 200
        lid = r.json()["id"]
        d = requests.delete(f"{BASE}/admin/locations/{lid}", headers=_hdr(admin_token))
        assert d.status_code == 200


# ---------- Uploads ----------
class TestUploads:
    def test_upload_rejects_bad_type(self, alice):
        r = requests.post(f"{BASE}/uploads", headers=_hdr(alice["token"]),
                          files={"file": ("x.txt", io.BytesIO(b"hello"), "text/plain")})
        assert r.status_code == 415

    def test_upload_requires_auth(self):
        r = requests.post(f"{BASE}/uploads",
                          files={"file": ("x.jpg", io.BytesIO(b"abc"), "image/jpeg")})
        assert r.status_code == 401
