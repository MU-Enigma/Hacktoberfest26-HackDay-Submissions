import os
from datetime import timedelta
from typing import Optional, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, EmailStr

import ml
from core import (db, iso, now, new_id, audit, hash_password, verify_password, create_access_token, public_user,
                  get_current_user, require_active, parse_dt, POLICY_VERSION)
from routes_items import summary

router = APIRouter(prefix="/api")


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    accept_policy: bool
    policy_version: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    avatar_path: Optional[str] = None
    notification_prefs: Optional[dict] = None


class WatchlistIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    keywords: Optional[str] = ""
    category: Optional[str] = ""
    color: Optional[str] = ""
    locations: List[str] = []
    date_from: Optional[str] = ""
    date_to: Optional[str] = ""
    item_type: Literal["lost", "found", "any"] = "found"
    threshold: int = Field(default=50, ge=20, le=95)
    reference_image: Optional[str] = None
    active: bool = True


class ModReportIn(BaseModel):
    target_type: Literal["item", "user", "claim", "other"]
    target_id: Optional[str] = None
    reason: str = Field(min_length=3, max_length=120)
    details: Optional[str] = Field(default="", max_length=2000)


class AppealIn(BaseModel):
    message: str = Field(min_length=10, max_length=2000)


def _set_cookie(resp: Response, token: str):
    resp.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=8 * 3600, path="/")


def _allowed_domain(email: str) -> bool:
    domains = [d.strip().lower() for d in os.environ.get("ALLOWED_EMAIL_DOMAINS", "").split(",") if d.strip()]
    return not domains or email.split("@")[-1].lower() in domains


@router.get("/policy")
async def policy():
    domains = [d.strip() for d in os.environ.get("ALLOWED_EMAIL_DOMAINS", "").split(",") if d.strip()]
    return {"version": POLICY_VERSION, "allowed_domains": domains}


@router.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    if not body.accept_policy:
        raise HTTPException(400, "You must accept the Back2U Responsible Use Policy to register")
    if body.policy_version != POLICY_VERSION:
        raise HTTPException(400, "Policy version has changed. Please re-read the policy.")
    if not _allowed_domain(email):
        raise HTTPException(400, "Please register with your university email address")
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "An account with this email already exists")
    user = {"id": new_id(), "name": body.name.strip(), "email": email, "password_hash": hash_password(body.password), "role": "student",
            "status": "active", "email_verified": False, "policy_version": POLICY_VERSION, "policy_accepted_at": iso(),
            "report_policy_ack": False, "notification_prefs": {"matches": True, "claims": True, "watchlist": True}, "created_at": iso()}
    await db.users.insert_one(dict(user))
    await db.policy_acceptances.insert_one({"id": new_id(), "user_id": user["id"], "policy_version": POLICY_VERSION, "context": "registration", "accepted_at": iso()})
    await audit(user["id"], "user.register", "user", user["id"], {"policy_version": POLICY_VERSION})
    token = create_access_token(user["id"], email)
    _set_cookie(response, token)
    return {"user": public_user(user), "token": token}


@router.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "x")
    ident = f"{ip}:{email}"
    rec = await db.login_attempts.find_one({"identifier": ident})
    if rec and rec.get("count", 0) >= 5 and rec.get("last", "") > (now() - timedelta(minutes=15)).isoformat():
        raise HTTPException(429, "Too many failed login attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not verify_password(body.password, user["password_hash"]):
        await db.login_attempts.update_one({"identifier": ident}, {"$inc": {"count": 1}, "$set": {"last": iso()}}, upsert=True)
        raise HTTPException(401, "Invalid email or password")
    await db.login_attempts.delete_one({"identifier": ident})
    token = create_access_token(user["id"], email)
    _set_cookie(response, token)
    return {"user": public_user(user), "token": token}


class DemoIn(BaseModel):
    email: EmailStr


@router.post("/auth/demo-login")
async def demo_login(body: DemoIn, response: Response):
    user = await db.users.find_one({"email": body.email.lower(), "is_demo": True, "role": "student"}, {"_id": 0})
    if not user:
        raise HTTPException(404, "Demo account not found")
    token = create_access_token(user["id"], user["email"])
    _set_cookie(response, token)
    return {"user": public_user(user), "token": token}


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return public_user(user)


@router.patch("/profile")
async def update_profile(body: ProfileIn, user: dict = Depends(get_current_user)):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if "notification_prefs" in data:
        data["notification_prefs"] = {k: bool(data["notification_prefs"].get(k, True)) for k in ("matches", "claims", "watchlist")}
    if data:
        await db.users.update_one({"id": user["id"]}, {"$set": data})
    return public_user(await db.users.find_one({"id": user["id"]}, {"_id": 0}))


@router.post("/policy/report-ack")
async def report_ack(user: dict = Depends(require_active)):
    await db.users.update_one({"id": user["id"]}, {"$set": {"report_policy_ack": True}})
    await db.policy_acceptances.insert_one({"id": new_id(), "user_id": user["id"], "policy_version": POLICY_VERSION, "context": "first_report", "accepted_at": iso()})
    return {"ok": True}


# ---------- Notifications ----------
@router.get("/notifications")
async def notifications(user: dict = Depends(get_current_user)):
    rows = await db.notifications.find({"user_id": user["id"]}, {"_id": 0, "dedupe_key": 0}).sort("created_at", -1).to_list(100)
    return {"unread": sum(1 for r in rows if not r["read"]), "items": rows}


@router.post("/notifications/{nid}/read")
async def read_notification(nid: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one({"id": nid, "user_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


@router.post("/notifications/read-all")
async def read_all(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


# ---------- Watchlists ----------
@router.get("/watchlists")
async def watchlists(user: dict = Depends(get_current_user)):
    return await db.watchlists.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)


@router.post("/watchlists")
async def create_watchlist(body: WatchlistIn, user: dict = Depends(require_active)):
    if not (body.keywords or body.category or body.color or body.locations):
        raise HTTPException(422, "Add at least one keyword, category, colour or location")
    wl = {**body.model_dump(), "id": new_id(), "user_id": user["id"], "created_at": iso()}
    await db.watchlists.insert_one(dict(wl))
    wl.pop("_id", None)
    return wl


@router.put("/watchlists/{wid}")
async def update_watchlist(wid: str, body: WatchlistIn, user: dict = Depends(require_active)):
    r = await db.watchlists.update_one({"id": wid, "user_id": user["id"]}, {"$set": body.model_dump()})
    if not r.matched_count:
        raise HTTPException(404, "Watchlist not found")
    return await db.watchlists.find_one({"id": wid}, {"_id": 0})


@router.delete("/watchlists/{wid}")
async def delete_watchlist(wid: str, user: dict = Depends(get_current_user)):
    r = await db.watchlists.delete_one({"id": wid, "user_id": user["id"]})
    if not r.deleted_count:
        raise HTTPException(404, "Watchlist not found")
    return {"ok": True}


# ---------- Stats & feed ----------
async def compute_stats():
    lost = await db.items.count_documents({"type": "lost", "is_deleted": False})
    found = await db.items.count_documents({"type": "found", "is_deleted": False})
    receipts = await db.handover_receipts.find({}, {"_id": 0, "completed_at": 1, "found_reported_at": 1}).to_list(5000)
    days = []
    for r in receipts:
        try:
            days.append((parse_dt(r["completed_at"]) - parse_dt(r["found_reported_at"])).total_seconds() / 86400)
        except Exception:
            pass
    active_matches = await db.item_matches.count_documents({"feedback_irrelevant": {"$ne": True}})
    users = await db.users.count_documents({"role": "student"})
    return {"lost": lost, "found": found, "returned": len(receipts), "active_matches": active_matches, "students": users,
            "recovery_rate": round(100 * len(receipts) / found) if found else 0,
            "avg_days_to_return": round(sum(days) / len(days), 1) if days else None}


@router.get("/stats")
async def stats():
    return await compute_stats()


async def anonymized_recoveries(limit=6):
    out = []
    async for r in db.handover_receipts.find({"story_opt_out": {"$size": 0}}, {"_id": 0}).sort("completed_at", -1).limit(limit):
        out.append({"id": r["id"], "category": r["item_category"], "category_label": ml.CATEGORIES.get(r["item_category"], "Item"),
                    "location": r["item_location"], "completed_at": r["completed_at"], "found_reported_at": r["found_reported_at"]})
    return out


@router.get("/recoveries")
async def recoveries():
    return await anonymized_recoveries(8)


@router.get("/feed")
async def feed(category: Optional[str] = None, location: Optional[str] = None, q: Optional[str] = None,
               since: Optional[str] = None, sort: str = "newest"):
    base = {"is_deleted": False}
    if category:
        base["category"] = category
    if location:
        base["location"] = location
    if since:
        base["occurred_at"] = {"$gte": since}
    if q:
        import re
        rx = {"$regex": re.escape(q), "$options": "i"}
        base["$or"] = [{"title": rx}, {"description": rx}, {"location": rx}]
    d = 1 if sort == "oldest" else -1

    async def grab(extra):
        rows = await db.items.find({**base, **extra}, {"_id": 0}).sort("created_at", d).limit(12).to_list(12)
        return [summary(r) for r in rows]

    matches = []
    async for m in db.item_matches.find({"feedback_irrelevant": {"$ne": True}}, {"_id": 0}).sort("updated_at", -1).limit(6):
        a = await db.items.find_one({"id": m["lost_id"], "is_deleted": False}, {"_id": 0})
        b = await db.items.find_one({"id": m["found_id"], "is_deleted": False}, {"_id": 0})
        if a and b and a["status"] not in ("RETURNED", "CLOSED"):
            matches.append({"id": m["id"], "score": m["score"], "lost": summary(a), "found": summary(b)})
    return {
        "lost": await grab({"type": "lost", "status": {"$nin": ["RETURNED", "CLOSED"]}}),
        "found": await grab({"type": "found", "status": {"$nin": ["RETURNED", "CLOSED"]}}),
        "recovered": await grab({"status": "RETURNED"}),
        "matches": matches,
        "stories": await anonymized_recoveries(6),
        "stats": await compute_stats(),
    }


# ---------- Moderation (user-facing) ----------
@router.post("/moderation/reports")
async def report_abuse(body: ModReportIn, user: dict = Depends(get_current_user)):
    since = (now() - timedelta(hours=1)).isoformat()
    if await db.moderation_reports.count_documents({"reporter_id": user["id"], "created_at": {"$gte": since}}) >= 10:
        raise HTTPException(429, "Too many reports submitted. Please try again later.")
    target_user = None
    if body.target_type == "item" and body.target_id:
        it = await db.items.find_one({"id": body.target_id}, {"owner_id": 1})
        target_user = it["owner_id"] if it else None
    elif body.target_type == "claim" and body.target_id:
        c = await db.claims.find_one({"id": body.target_id}, {"claimant_id": 1})
        target_user = c["claimant_id"] if c else None
    elif body.target_type == "user":
        target_user = body.target_id
    rep = {**body.model_dump(), "id": new_id(), "source": "user", "reporter_id": user["id"], "target_user_id": target_user,
           "status": "open", "created_at": iso()}
    await db.moderation_reports.insert_one(dict(rep))
    await audit(user["id"], "moderation.report", body.target_type, body.target_id, {"reason": body.reason})
    return {"id": rep["id"], "reference": rep["id"][:8].upper(), "message": "Thank you. An administrator will review this report."}


@router.post("/appeals")
async def appeal(body: AppealIn, user: dict = Depends(get_current_user)):
    if await db.appeals.find_one({"user_id": user["id"], "status": "open"}):
        raise HTTPException(409, "You already have an open appeal")
    ap = {"id": new_id(), "user_id": user["id"], "message": body.message, "status": "open", "account_status": user.get("status"), "created_at": iso()}
    await db.appeals.insert_one(dict(ap))
    await audit(user["id"], "appeal.submit", "user", user["id"])
    ap.pop("_id", None)
    return ap


@router.get("/appeals/mine")
async def my_appeals(user: dict = Depends(get_current_user)):
    return await db.appeals.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
