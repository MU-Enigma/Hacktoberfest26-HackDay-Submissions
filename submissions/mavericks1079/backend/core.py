import os
import uuid
import hashlib
import logging
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
import requests
from fastapi import Request, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger("back2u")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

JWT_ALGORITHM = "HS256"
POLICY_VERSION = os.environ.get("POLICY_VERSION", "1.0")
APP_NAME = os.environ.get("APP_NAME", "back2u")


def now():
    return datetime.now(timezone.utc)


def iso(dt=None):
    return (dt or now()).isoformat()


def parse_dt(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def new_id():
    return str(uuid.uuid4())


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "type": "access", "exp": now() + timedelta(hours=8)}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def public_user(u: dict) -> dict:
    return {
        "id": u["id"], "name": u.get("name"), "email": u.get("email"), "role": u.get("role", "student"),
        "status": u.get("status", "active"), "suspended_until": u.get("suspended_until"),
        "avatar_path": u.get("avatar_path"), "email_verified": u.get("email_verified", False),
        "policy_version": u.get("policy_version"), "policy_accepted_at": u.get("policy_accepted_at"),
        "report_policy_ack": u.get("report_policy_ack", False),
        "notification_prefs": u.get("notification_prefs", {"matches": True, "claims": True, "watchlist": True}),
        "is_demo": u.get("is_demo", False), "created_at": u.get("created_at"),
    }


async def _user_from_request(request: Request):
    token = request.cookies.get("access_token")
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        return None
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired, please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    if user.get("status") == "suspended" and user.get("suspended_until"):
        until = parse_dt(user["suspended_until"])
        if until and until < now():
            await db.users.update_one({"id": user["id"]}, {"$set": {"status": "active", "suspended_until": None}})
            user["status"], user["suspended_until"] = "active", None
    return user


async def get_current_user(request: Request) -> dict:
    user = await _user_from_request(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user


async def get_optional_user(request: Request):
    try:
        return await _user_from_request(request)
    except HTTPException:
        return None


async def require_active(user: dict = Depends(get_current_user)) -> dict:
    status = user.get("status", "active")
    if status == "banned":
        raise HTTPException(403, "Your account has been permanently banned for violating the Responsible Use Policy. You may submit an appeal from your profile.")
    if status == "suspended":
        raise HTTPException(403, f"Your account is suspended until {user.get('suspended_until') or 'further review'}. You may submit an appeal from your profile.")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(403, "Administrator access required")
    return user


async def audit(actor_id, action, target_type, target_id, details=None):
    await db.audit_logs.insert_one({
        "id": new_id(), "actor_id": actor_id, "action": action, "target_type": target_type,
        "target_id": target_id, "details": details or {}, "created_at": iso(),
    })


async def notify(user_id, ntype, title, body, link=None, dedupe_key=None, pref=None):
    if pref:
        u = await db.users.find_one({"id": user_id}, {"_id": 0, "notification_prefs": 1})
        if u and not (u.get("notification_prefs") or {}).get(pref, True):
            return
    if dedupe_key and await db.notifications.find_one({"dedupe_key": dedupe_key}):
        return
    await db.notifications.insert_one({
        "id": new_id(), "user_id": user_id, "type": ntype, "title": title, "body": body,
        "link": link, "read": False, "dedupe_key": dedupe_key, "created_at": iso(),
    })


# ---------- Object storage ----------
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
_storage_key = None


def init_storage(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": os.environ.get("EMERGENT_LLM_KEY")}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    elif resp.status_code >= 500:
        resp = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    if resp.status_code >= 500:
        raise HTTPException(502, "Photo storage is temporarily unavailable. Please try again.")
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
