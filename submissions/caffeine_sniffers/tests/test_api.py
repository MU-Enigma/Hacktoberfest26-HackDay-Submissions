"""API smoke tests for SideQuest."""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Use a temp DB for tests
os.environ["DEMO_USER_ID"] = "1"
TEST_DB = ROOT / "test_sidequest.db"
if TEST_DB.exists():
    TEST_DB.unlink()

import database as db  # noqa: E402

db.DB_PATH = TEST_DB
db.init_db()

from app import app  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_me(client):
    res = client.get("/api/me")
    assert res.status_code == 200
    data = res.get_json()
    assert data["display_name"]
    assert isinstance(data["interests"], list)


def test_list_and_filter(client):
    res = client.get("/api/activities")
    assert res.status_code == 200
    activities = res.get_json()["activities"]
    assert len(activities) >= 5

    res = client.get("/api/activities?category=Coffee")
    coffee = res.get_json()["activities"]
    assert coffee
    assert all(a["category"] == "Coffee" for a in coffee)


def test_join_leave_and_capacity(client):
    res = client.get("/api/activities")
    activities = res.get_json()["activities"]
    target = next(a for a in activities if not a["joined"] and not a["is_full"])
    aid = target["id"]

    join = client.post(f"/api/activities/{aid}/join")
    assert join.status_code == 200
    assert join.get_json()["activity"]["joined"] is True

    dup = client.post(f"/api/activities/{aid}/join")
    assert dup.status_code == 409

    leave = client.delete(f"/api/activities/{aid}/join")
    # May fail if user is host — pick a non-hosted one
    if leave.status_code == 409 and leave.get_json()["error"] == "host_cannot_leave":
        other = next(
            a
            for a in activities
            if not a["joined"] and not a["is_full"] and a["host_id"] != 1
        )
        aid = other["id"]
        assert client.post(f"/api/activities/{aid}/join").status_code == 200
        assert client.delete(f"/api/activities/{aid}/join").status_code == 200
    else:
        assert leave.status_code == 200


def test_create_validation(client):
    res = client.post("/api/activities", json={})
    assert res.status_code == 400
    assert "fields" in res.get_json()

    tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    payload = {
        "title": "pytest chai circle",
        "description": "automated vibes only",
        "category": "Coffee",
        "date": tomorrow,
        "start_time": "17:30",
        "venue": "Test Courtyard",
        "capacity": 4,
        "connection_type": "friends",
        "interest_tags": ["coffee", "testing"],
    }
    created = client.post("/api/activities", json=payload)
    assert created.status_code == 201
    body = created.get_json()
    assert body["title"] == "pytest chai circle"
    assert body["joined"] is True


def test_recommendation_deterministic():
    user = db.get_user(1)
    activities = db.list_activities(viewer_id=1)
    assert user and activities
    a = activities[0]
    s1 = db.score_activity(user, a)
    s2 = db.score_activity(user, a)
    assert s1 == s2
