"""Comprehensive feature tests for SideQuest."""

import io
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import database as db  # noqa: E402
import year_utils  # noqa: E402
from app import app  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def make_test_image_bytes():
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color=(255, 183, 206))
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ── Study Year Calculation ─────────────────────────────────────────────


def test_study_year_calculation_2026_academic_year():
    # In academic year 2026 (e.g. October 2026):
    now_oct_2026 = datetime(2026, 10, 15)

    y26 = year_utils.study_year_from_email("se26uecm024@sdheeraj.is-cool.dev", now=now_oct_2026)
    assert y26["cohort_year"] == 2026
    assert y26["study_year"] == 1
    assert y26["study_year_label"] == "First Year"
    assert y26["branch_code"] == "ecm"
    assert y26["branch_name"] == "ECM"
    assert y26["badge_label"] == "First Year · ECM"

    y25 = year_utils.study_year_from_email("se25ucse100@sdheeraj.is-cool.dev", now=now_oct_2026)
    assert y25["cohort_year"] == 2025
    assert y25["study_year"] == 2
    assert y25["study_year_label"] == "Second Year"
    assert y25["branch_name"] == "CSE"
    assert y25["badge_label"] == "Second Year · CSE"

    y24 = year_utils.study_year_from_email("se24umech006@sdheeraj.is-cool.dev", now=now_oct_2026)
    assert y24["cohort_year"] == 2024
    assert y24["study_year"] == 3
    assert y24["study_year_label"] == "Third Year"
    assert y24["branch_name"] == "Mechanical"
    assert y24["badge_label"] == "Third Year · Mechanical"

    y23 = year_utils.study_year_from_email("se23ucse005@sdheeraj.is-cool.dev", now=now_oct_2026)
    assert y23["cohort_year"] == 2023
    assert y23["study_year"] == 4
    assert y23["study_year_label"] == "Fourth Year"
    assert y23["badge_label"] == "Fourth Year · CSE"


def test_study_year_edge_cases():
    now_oct_2026 = datetime(2026, 10, 15)

    # Graduated cohort (>4 years)
    y22 = year_utils.study_year_from_email("se22ucse005@sdheeraj.is-cool.dev", now=now_oct_2026)
    assert y22["cohort_year"] == 2022
    assert y22["study_year"] is None
    assert y22["study_year_label"] is None

    # Unrecognized cohort prefix
    staff = year_utils.study_year_from_email("faculty@sdheeraj.is-cool.dev", now=now_oct_2026)
    assert staff["recognized"] is False
    assert staff["cohort_year"] is None
    assert staff["study_year_label"] is None

    # Configurable start month: in May 2026, if start_month=7 (July), academic year is 2025
    now_may_2026 = datetime(2026, 5, 10)
    y_may = year_utils.study_year_from_email("se25ucse100@sdheeraj.is-cool.dev", now=now_may_2026, start_month=7)
    assert y_may["study_year"] == 1  # 2025 - 2025 + 1 = 1


# ── Auth Flow ─────────────────────────────────────────────────────────


def test_registration_validation(client):
    # Reject non-university domain
    bad_domain = client.post(
        "/api/auth/register",
        json={
            "email": "test@gmail.com",
            "password": "password123",
            "display_name": "Test User",
        },
    )
    assert bad_domain.status_code == 400
    assert "email" in bad_domain.get_json()["fields"]

    # Reject short password
    short_pw = client.post(
        "/api/auth/register",
        json={
            "email": "se26ucse999@sdheeraj.is-cool.dev",
            "password": "123",
            "display_name": "Newbie",
        },
    )
    assert short_pw.status_code == 400
    assert "password" in short_pw.get_json()["fields"]


def test_register_login_logout_flow(client):
    unique_email = f"se26ucse_{datetime.now().strftime('%M%S%f')}@sdheeraj.is-cool.dev"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": unique_email,
            "password": "securepassword",
            "display_name": "Tara Test",
            "gender": "woman",
            "connection_preference": "friends",
            "profile_visibility": "first_name_only",
            "interests": ["reading", "board games"],
        },
    )
    assert reg.status_code == 201
    reg_data = reg.get_json()
    assert reg_data["user"]["display_name"] == "Tara Test"
    assert reg_data["study_year"]["study_year_label"] == "First Year"
    assert reg_data["user"]["profile_visibility"] == "first_name_only"

    # Current user is now logged in
    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.get_json()["email"] == unique_email

    # Logout
    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200

    # Login again
    login = client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": "securepassword"},
    )
    assert login.status_code == 200
    assert login.get_json()["user"]["email"] == unique_email


def test_otp_and_forgot_password(client):
    # Valid OTP verification in demo mode
    otp_res = client.post(
        "/api/auth/verify-otp",
        json={"email": "se26uecm024@sdheeraj.is-cool.dev", "otp": "123456"},
    )
    assert otp_res.status_code == 200
    assert otp_res.get_json()["verified"] is True

    # Bad OTP code
    bad_otp = client.post(
        "/api/auth/verify-otp",
        json={"email": "se26uecm024@sdheeraj.is-cool.dev", "otp": "999999"},
    )
    assert bad_otp.status_code == 400

    # Forgot password simulated demo
    fp = client.post(
        "/api/auth/forgot-password",
        json={"email": "se25ucse100@sdheeraj.is-cool.dev"},
    )
    assert fp.status_code == 200
    assert "demo_mode" in fp.get_json()


def test_demo_login_and_switcher(client):
    # Default demo login (Aanya)
    res1 = client.post("/api/auth/demo", json={})
    assert res1.status_code == 200
    assert res1.get_json()["user"]["display_name"] == "Aanya Kapoor"

    # Specific demo student (Rohan Mehta)
    res2 = client.post(
        "/api/auth/demo",
        json={"email": "se24ucse002@sdheeraj.is-cool.dev"},
    )
    assert res2.status_code == 200
    assert res2.get_json()["user"]["display_name"] == "Rohan Mehta"


# ── Profile & Avatar ──────────────────────────────────────────────────


def test_profile_update_and_avatar_upload(client):
    # Log in as Dev Patel
    client.post("/api/auth/demo", json={"email": "se25uaid004@sdheeraj.is-cool.dev"})

    # Update profile fields including visibility
    patch = client.patch(
        "/api/me",
        json={
            "display_name": "Dev P.",
            "bio": "Updating my bio for hackathon test",
            "connection_preference": "either",
            "profile_visibility": "first_name_only",
            "interests": ["coffee", "synthwave"],
            "preferred_categories": ["Coffee", "Music"],
        },
    )
    assert patch.status_code == 200
    data = patch.get_json()
    assert data["display_name"] == "Dev P."
    assert data["profile_visibility"] == "first_name_only"
    assert "synthwave" in data["interests"]

    # Upload avatar image
    img_bytes = make_test_image_bytes()
    upload = client.post(
        "/api/me/avatar",
        data={"avatar": (img_bytes, "profile.png")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200
    assert upload.get_json()["avatar_url"] is not None
    avatar_url = upload.get_json()["avatar_url"]

    # File can be fetched
    get_file = client.get(avatar_url)
    assert get_file.status_code == 200

    # Remove avatar
    remove = client.delete("/api/me/avatar")
    assert remove.status_code == 200
    assert remove.get_json()["avatar_url"] is None


# ── Gender and Activity Eligibility ────────────────────────────────────


def test_gender_eligibility_enforcement(client):
    # Log in as Aanya (Woman) to host the activity
    client.post("/api/auth/demo", json={"email": "se25ucse100@sdheeraj.is-cool.dev"})

    # Create a women-only activity
    tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    create = client.post(
        "/api/activities",
        json={
            "title": "Women in Tech Tea",
            "description": "Tea and chatting about coding projects",
            "category": "Tech",
            "date": tomorrow,
            "start_time": "16:00",
            "venue": "Innovation Courtyard",
            "capacity": 5,
            "connection_type": "friends",
            "invite_policy": "women",
            "interest_tags": ["tech", "tea"],
        },
    )
    assert create.status_code == 201
    act_id = create.get_json()["id"]

    # Log in as Rohan (Man)
    client.post("/api/auth/demo", json={"email": "se24ucse002@sdheeraj.is-cool.dev"})

    # Rohan (Man) tries to join -> ineligibility 409
    rohan_join = client.post(f"/api/activities/{act_id}/join")
    assert rohan_join.status_code == 409
    assert rohan_join.get_json()["error"] == "ineligible"

    # Log in as Sara (Woman)
    client.post("/api/auth/demo", json={"email": "se26uecm024@sdheeraj.is-cool.dev"})
    sara_join = client.post(f"/api/activities/{act_id}/join")
    assert sara_join.status_code == 200
    assert sara_join.get_json()["message"] == "joined"

    # Duplicate join returns 409
    dup_join = client.post(f"/api/activities/{act_id}/join")
    assert dup_join.status_code == 409
    assert dup_join.get_json()["error"] == "already_joined"

    # Sara leaves
    leave = client.delete(f"/api/activities/{act_id}/join")
    assert leave.status_code == 200


def test_custom_guest_list_eligibility(client):
    # Create activity inviting non-binary only
    tomorrow = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    client.post("/api/auth/demo", json={"email": "se25ucse100@sdheeraj.is-cool.dev"})

    create = client.post(
        "/api/activities",
        json={
            "title": "Non-binary Hangout Circle",
            "description": "Chill coffee session",
            "category": "Coffee",
            "date": tomorrow,
            "start_time": "15:00",
            "venue": "Courtyard Bench",
            "capacity": 4,
            "connection_type": "friends",
            "invite_policy": "non_binary",
            "interest_tags": ["coffee"],
        },
    )
    assert create.status_code == 201
    act_id = create.get_json()["id"]

    # Aanya (Woman) -> ineligible
    assert client.post(f"/api/activities/{act_id}/join").status_code == 409

    # Maya Sharma (Non-binary) -> eligible
    client.post("/api/auth/demo", json={"email": "se23ucse005@sdheeraj.is-cool.dev"})
    assert client.post(f"/api/activities/{act_id}/join").status_code == 200


# ── Public Profile & Privacy ───────────────────────────────────────────


def test_public_user_profile(client):
    # Fetch public profile API
    res = client.get("/api/users/1")
    assert res.status_code == 200
    data = res.get_json()["user"]
    assert "first_name" in data
    assert "badge_label" in data

    # HTML page route exists
    page = client.get("/user/1")
    assert page.status_code == 200
    assert b"SideQuest Profile" in page.data


# ── Reporting and Admin Panel ──────────────────────────────────────────


def test_reporting_activity(client):
    client.post("/api/auth/demo", json={"email": "se25ucse100@sdheeraj.is-cool.dev"})
    rep = client.post(
        "/api/activities/1/report",
        json={"reason": "Spam activity title posted repeatedly"},
    )
    assert rep.status_code == 201
    assert rep.get_json()["status"] == "open"


def test_admin_access_control_and_operations(client):
    # Regular user is forbidden from admin APIs
    client.post("/api/auth/demo", json={"email": "se25ucse100@sdheeraj.is-cool.dev"})
    assert client.get("/api/admin/stats").status_code == 403
    assert client.get("/api/admin/users").status_code == 403

    # Authenticate as admin (meldhee or custom admin)
    admin_email = "meldhee@sdheeraj.is-cool.dev"
    with db.db() as conn:
        admin_row = conn.execute("SELECT id FROM users WHERE email = ? AND role = 'admin'", (admin_email,)).fetchone()
        if not admin_row:
            conn.execute(
                """
                INSERT OR REPLACE INTO users (
                    email, password_hash, display_name, role, is_demo, created_at
                ) VALUES (?, 'fakehash', 'Campus Moderator', 'admin', 0, '2026-10-12T00:00:00')
                """,
                (admin_email,),
            )
            admin_row = conn.execute("SELECT id FROM users WHERE email = ?", (admin_email,)).fetchone()
        admin_id = admin_row["id"]

    with client.session_transaction() as sess:
        sess["user_id"] = admin_id

    # Admin stats accessible
    stats = client.get("/api/admin/stats")
    assert stats.status_code == 200
    assert "users" in stats.get_json()

    users = client.get("/api/admin/users")
    assert users.status_code == 200
    assert len(users.get_json()["users"]) > 0

    # Suspend user 5
    susp = client.post("/api/admin/users/5/suspend")
    assert susp.status_code == 200
    assert susp.get_json()["is_suspended"] is True

    # Unsuspend user 5
    unsusp = client.post("/api/admin/users/5/unsuspend")
    assert unsusp.status_code == 200
    assert unsusp.get_json()["is_suspended"] is False

    # Admin updates a user's details
    patch_user = client.patch(
        "/api/admin/users/2",
        json={
            "display_name": "Rohan M. (Updated)",
            "bio": "Admin updated bio",
            "profile_visibility": "first_name_only",
        },
    )
    assert patch_user.status_code == 200
    assert patch_user.get_json()["user"]["display_name"] == "Rohan M. (Updated)"

    # Mass reset rejection without confirmation
    bad_reset = client.post("/api/admin/reset", json={})
    assert bad_reset.status_code == 400

    # Mass reset execution with confirmation "RESET"
    good_reset = client.post("/api/admin/reset", json={"confirmation": "RESET"})
    assert good_reset.status_code == 200
    assert good_reset.get_json()["status"] == "ok"

