"""SideQuest — campus social discovery for Mahindra University."""

from __future__ import annotations

import os
import re
import secrets
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
)
from PIL import Image
from werkzeug.utils import secure_filename

import database as db
from year_utils import study_year_from_email

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "sidequest-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

UNIVERSITY_EMAIL_DOMAIN = os.getenv(
    "UNIVERSITY_EMAIL_DOMAIN", "sdheeraj.is-cool.dev"
).lower()
UPLOAD_DIR = db.UPLOAD_DIR
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}

CATEGORIES = db.CATEGORIES
CONNECTION_TYPES = db.CONNECTION_TYPES
GENDER_OPTIONS = db.GENDER_OPTIONS
INVITE_POLICIES = db.INVITE_POLICIES


def err(message: str, code: int = 400, **extra: Any):
    return jsonify({"error": message, **extra}), code


def current_user_id() -> Optional[int]:
    uid = session.get("user_id")
    if not uid and app.config.get("TESTING") and os.getenv("DEMO_USER_ID"):
        try:
            return int(os.getenv("DEMO_USER_ID"))
        except (ValueError, TypeError):
            return None
    return int(uid) if uid else None


def current_user() -> Optional[dict[str, Any]]:
    uid = current_user_id()
    if not uid:
        return None
    user = db.get_user(uid)
    if not user or user.get("is_suspended"):
        session.clear()
        return None
    return user


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user_id():
            return err("login required", 401)
        user = current_user()
        if not user:
            return err("login required", 401)
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user.get("role") != "admin":
            return err("admin only", 403)
        return fn(*args, **kwargs)

    return wrapper


@app.before_request
def ensure_db():
    db.init_db()


@app.get("/")
def index():
    return render_template(
        "index.html",
        university_domain=UNIVERSITY_EMAIL_DOMAIN,
        email_verification=False,
    )


@app.get("/login")
def login_page():
    tab = request.args.get("tab", "login")
    return render_template(
        "login.html",
        university_domain=UNIVERSITY_EMAIL_DOMAIN,
        tab=tab,
        me=current_user(),
    )


@app.get("/register")
def register_page():
    return redirect("/login?tab=register")


@app.get("/user/<int:user_id>")
def user_profile_page(user_id: int):
    profile = db.get_user_public_profile(user_id)
    if not profile:
        return redirect("/?not_found=1")
    return render_template(
        "user_profile.html",
        profile=profile,
        me=current_user(),
        university_domain=UNIVERSITY_EMAIL_DOMAIN,
    )


@app.get("/admin")
def admin_page():
    user = current_user()
    if not user or user.get("role") != "admin":
        return redirect("/?next=admin")
    return render_template("admin.html", me=user)


@app.get("/uploads/<path:filename>")
def uploaded_file(filename: str):
    safe = secure_filename(filename)
    return send_from_directory(UPLOAD_DIR, safe)


@app.get("/api/health")
def health():
    return jsonify(
        {
            "ok": True,
            "app": "SideQuest",
            "email_domain": UNIVERSITY_EMAIL_DOMAIN,
            "email_verification": False,
        }
    )


@app.get("/api/config")
def api_config():
    return jsonify(
        {
            "university_email_domain": UNIVERSITY_EMAIL_DOMAIN,
            "email_verification_implemented": False,
            "categories": CATEGORIES,
            "genders": GENDER_OPTIONS,
            "invite_policies": INVITE_POLICIES,
            "connection_types": CONNECTION_TYPES,
            "authenticated": current_user_id() is not None,
        }
    )


# ── Auth ─────────────────────────────────────────────────────────────


def validate_university_email(email: str) -> Optional[str]:
    email = email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return "that email looks scrambled."
    domain = email.split("@", 1)[1]
    if domain != UNIVERSITY_EMAIL_DOMAIN:
        return f"use your @{UNIVERSITY_EMAIL_DOMAIN} university email."
    return None


@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    display_name = str(data.get("display_name") or "").strip()
    gender = str(data.get("gender") or "prefer_not_to_say")
    gender_self = str(data.get("gender_self_describe") or "").strip()[:80]
    connection_preference = str(data.get("connection_preference") or "either")
    interests = data.get("interests") or []

    problems: dict[str, str] = {}
    email_err = validate_university_email(email)
    if email_err:
        problems["email"] = email_err
    if len(password) < 6:
        problems["password"] = "password needs at least 6 characters."
    if len(display_name) < 2:
        problems["display_name"] = "display name needs at least 2 characters."
    if gender not in GENDER_OPTIONS:
        problems["gender"] = "pick a gender option (or prefer not to say)."
    if connection_preference not in CONNECTION_TYPES:
        problems["connection_preference"] = "choose friendship, dating, or either."
    if not isinstance(interests, list):
        problems["interests"] = "interests should be a list."
        interests = []
    else:
        interests = [str(i).strip()[:40] for i in interests if str(i).strip()][:12]

    profile_visibility = str(data.get("profile_visibility") or "public")
    if profile_visibility not in ("public", "first_name_only", "minimal"):
        profile_visibility = "public"

    if problems:
        return jsonify({"error": "validation_failed", "fields": problems}), 400

    if db.get_user_by_email(email):
        return err("an account with that email already exists.", 409)

    user = db.create_user(
        email=email,
        password=password,
        display_name=display_name,
        gender=gender,
        gender_self_describe=gender_self if gender == "self_describe" else "",
        connection_preference=connection_preference,
        interests=interests,
        profile_visibility=profile_visibility,
    )
    session["user_id"] = user["id"]
    session.permanent = True
    year = study_year_from_email(email)
    return jsonify(
        {
            "user": user,
            "message": "welcome aboard! email verification is not implemented in this prototype.",
            "study_year": year,
        }
    ), 201


@app.post("/api/auth/verify-otp")
def verify_otp():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    otp = str(data.get("otp") or "").strip()
    if not email:
        return err("university email is required.")
    email_err = validate_university_email(email)
    if email_err:
        return err(email_err)
    if otp != "123456":
        return err("Invalid OTP code. In this evaluation prototype demo, use OTP code: 123456", 400)
    return jsonify({
        "ok": True,
        "verified": True,
        "message": "OTP verified successfully (Demo Mode)",
    })


@app.post("/api/auth/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    if not email:
        return err("please enter your university email.")
    email_err = validate_university_email(email)
    if email_err:
        return err(email_err)
    return jsonify({
        "ok": True,
        "demo_mode": True,
        "message": "Demo Mode / Coming Soon: Campus email password reset is simulated in this prototype. You can log in using any demo account or use password 'demo1234'.",
    })


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    result = db.authenticate(email, password)
    if result and result.get("__error__") == "suspended":
        return err("this account is suspended. ask an admin if that seems wrong.", 403)
    if not result:
        return err("email or password didn't match. try again?", 401)
    session["user_id"] = result["id"]
    session.permanent = True
    return jsonify({"user": result})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.post("/api/auth/demo")
def demo_login():
    """One-click explore as seeded demo student Aanya, or specify a demo user."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    if not email:
        email = f"se25ucse100@{UNIVERSITY_EMAIL_DOMAIN}"

    user = db.authenticate(email, "demo1234")
    if not user or user.get("__error__"):
        # fallback: check if user exists without password check for demo users
        user_row = db.get_user_by_email(email)
        if user_row and user_row.get("is_demo") and not user_row.get("is_suspended"):
            session["user_id"] = user_row["id"]
            session.permanent = True
            return jsonify({"user": user_row, "demo": True})
        # fallback: first demo non-admin
        users = [u for u in db.list_users() if u.get("is_demo") and u.get("role") != "admin"]
        if not users:
            return err("demo user missing — reseed the database", 500)
        session["user_id"] = users[0]["id"]
        session.permanent = True
        return jsonify({"user": db.get_user(users[0]["id"]), "demo": True})
    session["user_id"] = user["id"]
    session.permanent = True
    return jsonify({"user": user, "demo": True})


@app.get("/api/me")
@login_required
def api_me():
    return jsonify(current_user())


@app.get("/api/users/<int:user_id>")
def api_user_profile(user_id: int):
    profile = db.get_user_public_profile(user_id)
    if not profile:
        return err("student profile not found", 404)
    return jsonify({"user": profile, **profile})


@app.patch("/api/me")
@login_required
def api_me_update():
    data = request.get_json(silent=True) or {}
    if "connection_preference" in data and data["connection_preference"] not in CONNECTION_TYPES:
        return err("connection_preference must be friends, dating, or either")
    if "gender" in data and data["gender"] not in GENDER_OPTIONS:
        return err("invalid gender option")
    if "interests" in data and not isinstance(data["interests"], list):
        return err("interests must be a list of strings")
    if "preferred_categories" in data and not isinstance(data["preferred_categories"], list):
        return err("preferred_categories must be a list")
    if "profile_visibility" in data and data["profile_visibility"] not in ("public", "first_name_only", "minimal"):
        return err("profile_visibility must be public, first_name_only, or minimal")
    if "display_name" in data:
        name = str(data["display_name"]).strip()
        if len(name) < 2:
            return err("display name needs at least 2 characters")
        data["display_name"] = name
    if "bio" in data:
        data["bio"] = str(data["bio"]).strip()[:280]
    if "gender_self_describe" in data:
        data["gender_self_describe"] = str(data["gender_self_describe"]).strip()[:80]
    if "default_avatar" in data and data["default_avatar"] not in db.DEFAULT_AVATARS:
        return err("unknown default avatar")
    user = db.update_user(current_user_id(), data)  # type: ignore[arg-type]
    return jsonify(user)


@app.post("/api/me/avatar")
@login_required
def upload_avatar():
    if "avatar" not in request.files:
        return err("no file uploaded")
    file = request.files["avatar"]
    if not file or not file.filename:
        return err("no file selected")

    original = secure_filename(file.filename)
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        return err("only JPEG, PNG, or WebP please.")

    # Validate image content
    try:
        file.stream.seek(0)
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)
        img = Image.open(file.stream)
        img = img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img
        # Resize large images
        img.thumbnail((512, 512))
    except Exception:
        return err("that file doesn't look like a valid image.")

    uid = current_user_id()
    name = f"user{uid}_{uuid.uuid4().hex[:10]}.webp"
    dest = UPLOAD_DIR / name
    img.save(dest, format="WEBP", quality=85)

    # Remove previous upload if any
    prev = db.get_user(uid)  # type: ignore[arg-type]
    if prev and prev.get("avatar_url"):
        old = UPLOAD_DIR / Path(prev["avatar_url"]).name
        if old.exists() and old.name.startswith(f"user{uid}_"):
            try:
                old.unlink()
            except OSError:
                pass

    user = db.update_user(uid, {"avatar_path": name})  # type: ignore[arg-type]
    return jsonify(user)


@app.delete("/api/me/avatar")
@login_required
def remove_avatar():
    uid = current_user_id()
    prev = db.get_user(uid)  # type: ignore[arg-type]
    if prev and prev.get("avatar_url"):
        old = UPLOAD_DIR / Path(prev["avatar_url"]).name
        if old.exists() and old.name.startswith(f"user{uid}_"):
            try:
                old.unlink()
            except OSError:
                pass
    user = db.update_user(uid, {"clear_avatar": True})  # type: ignore[arg-type]
    return jsonify(user)


# ── Activities ────────────────────────────────────────────────────────


@app.get("/api/activities")
@login_required
def api_activities():
    category = request.args.get("category") or None
    intention = request.args.get("intention") or request.args.get("connection_type")
    include_past = request.args.get("include_past") == "1"
    viewer = current_user_id()
    activities = db.list_activities(
        category=category,
        connection_type=intention,
        include_past=include_past,
        viewer_id=viewer,
    )
    user = current_user()
    if user:
        for activity in activities:
            activity["recommendation"] = db.score_activity(user, activity)
        activities.sort(key=lambda a: (-a["recommendation"]["score"], a["starts_at"]))
    return jsonify({"activities": activities})


@app.get("/api/activities/<int:activity_id>")
@login_required
def api_activity(activity_id: int):
    viewer = current_user_id()
    activity = db.get_activity(activity_id, viewer)
    if not activity:
        return err("quest not found", 404)
    user = current_user() or {}
    ice = db.icebreaker_for(user, activity)
    if user:
        activity["recommendation"] = db.score_activity(user, activity)
    activity["icebreaker"] = ice
    return jsonify(activity)


@app.post("/api/activities")
@login_required
def api_create_activity():
    data = request.get_json(silent=True) or {}
    validated, problems = validate_activity_payload(data)
    if problems:
        return jsonify({"error": "validation_failed", "fields": problems}), 400
    activity = db.create_activity(current_user_id(), validated)  # type: ignore[arg-type]
    return jsonify(activity), 201


@app.post("/api/activities/<int:activity_id>/join")
@login_required
def api_join(activity_id: int):
    ok, reason, activity = db.join_activity(activity_id, current_user_id())  # type: ignore[arg-type]
    if not ok:
        messages = {
            "quest_not_found": "that quest wandered off the map.",
            "cancelled": "this quest got cancelled.",
            "past": "this adventure already happened.",
            "already_joined": "you're already in this quest!",
            "full": "nooo, this quest is packed. the plot demands another adventure.",
            "ineligible": (activity or {}).get("eligibility_message")
            or "you're not eligible for this quest's guest list.",
            "suspended": "your account is suspended.",
        }
        status = 404 if reason == "quest_not_found" else 409
        return jsonify(
            {
                "error": reason,
                "message": messages.get(reason, reason),
                "activity": activity,
            }
        ), status
    return jsonify({"message": "joined", "activity": activity})


@app.delete("/api/activities/<int:activity_id>/join")
@login_required
def api_leave(activity_id: int):
    ok, reason, activity = db.leave_activity(activity_id, current_user_id())  # type: ignore[arg-type]
    if not ok:
        messages = {
            "quest_not_found": "that quest wandered off the map.",
            "host_cannot_leave": "hosts stay with the plot — you created this one!",
            "not_joined": "you're not in this quest.",
        }
        status = 404 if reason == "quest_not_found" else 409
        return jsonify(
            {
                "error": reason,
                "message": messages.get(reason, reason),
                "activity": activity,
            }
        ), status
    return jsonify({"message": "left", "activity": activity})


@app.get("/api/my-quests")
@login_required
def api_my_quests():
    return jsonify(db.my_quests(current_user_id()))  # type: ignore[arg-type]


@app.post("/api/activities/<int:activity_id>/report")
@login_required
def api_report(activity_id: int):
    data = request.get_json(silent=True) or {}
    reason = str(data.get("reason") or "").strip()
    if len(reason) < 5:
        return err("tell us a bit more about why you're reporting this.")
    activity = db.get_activity(activity_id)
    if not activity:
        return err("quest not found", 404)
    report = db.create_report(current_user_id(), activity_id, reason)  # type: ignore[arg-type]
    return jsonify(report), 201


# ── Admin API ─────────────────────────────────────────────────────────


@app.get("/api/admin/stats")
@login_required
@admin_required
def admin_stats():
    return jsonify(db.admin_stats())


@app.get("/api/admin/users")
@login_required
@admin_required
def admin_users():
    q = (request.args.get("q") or "").lower().strip()
    users = db.list_users()
    if q:
        users = [
            u
            for u in users
            if q in (u.get("email") or "").lower()
            or q in (u.get("display_name") or "").lower()
        ]
    return jsonify({"users": users})


@app.post("/api/admin/users/<int:user_id>/suspend")
@login_required
@admin_required
def admin_suspend(user_id: int):
    if user_id == current_user_id():
        return err("you can't suspend yourself. dramatic, but no.")
    user = db.set_user_suspended(user_id, True)
    if not user:
        return err("user not found", 404)
    return jsonify(user)


@app.post("/api/admin/users/<int:user_id>/unsuspend")
@login_required
@admin_required
def admin_unsuspend(user_id: int):
    user = db.set_user_suspended(user_id, False)
    if not user:
        return err("user not found", 404)
    return jsonify(user)


@app.patch("/api/admin/users/<int:user_id>")
@login_required
@admin_required
def admin_patch_user(user_id: int):
    data = request.get_json(silent=True) or {}
    updated = db.admin_update_user(user_id, data)
    if not updated:
        return err("user not found", 404)
    return jsonify({"user": updated, **updated})


@app.post("/api/admin/reset")
@login_required
@admin_required
def admin_reset_database():
    data = request.get_json(silent=True) or {}
    confirmation = str(data.get("confirmation") or "").strip().upper()
    if confirmation != "RESET":
        return err("Confirmation 'RESET' is required to perform mass database reset.", 400)
    db.reset_database_to_default()
    return jsonify({
        "ok": True,
        "status": "ok",
        "message": "Database successfully reset to pristine defaults. Admin account preserved.",
    })


@app.get("/api/admin/activities")
@login_required
@admin_required
def admin_activities():
    q = (request.args.get("q") or "").lower().strip()
    activities = db.list_activities(include_past=True, include_removed=True)
    if q:
        activities = [
            a
            for a in activities
            if q in a["title"].lower()
            or q in a["category"].lower()
            or q in (a.get("host", {}).get("display_name") or "").lower()
        ]
    return jsonify({"activities": activities})


@app.delete("/api/admin/activities/<int:activity_id>")
@login_required
@admin_required
def admin_remove_activity(activity_id: int):
    activity = db.cancel_activity(activity_id)
    if not activity:
        return err("quest not found", 404)
    return jsonify(activity)


@app.get("/api/admin/reports")
@login_required
@admin_required
def admin_reports():
    status = request.args.get("status")
    return jsonify({"reports": db.list_reports(status)})


@app.post("/api/admin/reports/<int:report_id>")
@login_required
@admin_required
def admin_resolve_report(report_id: int):
    data = request.get_json(silent=True) or {}
    status = str(data.get("status") or "reviewed")
    if status not in ("open", "reviewed", "dismissed"):
        return err("status must be open, reviewed, or dismissed")
    report = db.set_report_status(report_id, status)
    if not report:
        return err("report not found", 404)
    return jsonify(report)


def validate_activity_payload(
    data: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    problems: dict[str, str] = {}
    title = str(data.get("title") or "").strip()
    description = str(data.get("description") or "").strip()
    category = str(data.get("category") or "").strip()
    venue = str(data.get("venue") or "").strip()
    connection_type = str(data.get("connection_type") or "").strip()
    invite_policy = str(data.get("invite_policy") or "everyone").strip()
    invite_genders = data.get("invite_genders") or []
    date = str(data.get("date") or "").strip()
    start_time = str(data.get("start_time") or "").strip()
    end_time = str(data.get("end_time") or "").strip()
    capacity_raw = data.get("capacity")
    tags = data.get("interest_tags") or data.get("tags") or []

    if not title:
        problems["title"] = "tiny plot twist: we need a title before this quest can exist."
    elif len(title) > 80:
        problems["title"] = "title is getting novel-length — keep it under 80 characters."

    if not description:
        problems["description"] = "give us a little lore (description required)."
    elif len(description) > 500:
        problems["description"] = "description max is 500 characters."

    if category not in CATEGORIES:
        problems["category"] = "pick a real category from the list."

    if not venue:
        problems["venue"] = "where's the side quest happening?"
    elif len(venue) > 120:
        problems["venue"] = "venue is too long."

    if connection_type not in CONNECTION_TYPES:
        problems["connection_type"] = "choose friends, dating, or either."

    if invite_policy not in INVITE_POLICIES:
        problems["invite_policy"] = "pick who is invited."
    if invite_policy == "custom":
        if not isinstance(invite_genders, list) or not invite_genders:
            problems["invite_genders"] = "custom invites need at least one gender option."
        else:
            invite_genders = [
                g for g in invite_genders if g in GENDER_OPTIONS and g != "prefer_not_to_say"
            ]
            if not invite_genders:
                problems["invite_genders"] = "custom guest list is empty."
    else:
        invite_genders = []

    starts_at = None
    ends_at = None
    if not date or not start_time:
        problems["starts_at"] = "date and start time are required."
    else:
        try:
            starts_at = datetime.fromisoformat(f"{date}T{start_time}")
            if starts_at < datetime.now():
                problems["starts_at"] = "time travel denied — pick a future date/time."
        except ValueError:
            problems["starts_at"] = "that date/time looks scrambled."

    if end_time and date and "starts_at" not in problems:
        try:
            ends_at = datetime.fromisoformat(f"{date}T{end_time}")
            if starts_at and ends_at <= starts_at:
                problems["ends_at"] = "end time must be after start time."
        except ValueError:
            problems["ends_at"] = "end time looks invalid."

    try:
        capacity = int(capacity_raw)
        if capacity < 2:
            problems["capacity"] = "need at least 2 people for a quest."
        elif capacity > 50:
            problems["capacity"] = "capacity max is 50 for this prototype."
    except (TypeError, ValueError):
        problems["capacity"] = "capacity must be a positive whole number."
        capacity = 0

    if not isinstance(tags, list):
        problems["interest_tags"] = "tags should be a list."
        tags = []
    else:
        tags = [str(t).strip()[:40] for t in tags if str(t).strip()][:8]

    if problems:
        return {}, problems

    assert starts_at is not None
    return {
        "title": title,
        "description": description,
        "category": category,
        "starts_at": starts_at.replace(microsecond=0).isoformat(),
        "ends_at": ends_at.replace(microsecond=0).isoformat() if ends_at else None,
        "venue": venue,
        "capacity": capacity,
        "connection_type": connection_type,
        "invite_policy": invite_policy,
        "invite_genders": invite_genders,
        "interest_tags": tags,
    }, {}


if __name__ == "__main__":
    db.init_db()
    port = int(os.getenv("PORT", "5050"))
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1", host="0.0.0.0", port=port)
