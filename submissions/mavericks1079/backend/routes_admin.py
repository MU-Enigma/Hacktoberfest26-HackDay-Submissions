import re
from datetime import timedelta
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, iso, now, new_id, audit, notify, require_admin, public_user
from routes_items import set_status, summary
from routes_misc import compute_stats

router = APIRouter(prefix="/api/admin")


class UserActionIn(BaseModel):
    action: Literal["suspend", "ban", "reinstate", "warn"]
    reason: str = Field(min_length=5, max_length=500)
    days: Optional[int] = Field(default=7, ge=1, le=365)


class ResolveIn(BaseModel):
    status: Literal["dismissed", "actioned", "in_review"]
    note: Optional[str] = Field(default="", max_length=500)


class AppealResolveIn(BaseModel):
    decision: Literal["upheld", "overturned"]
    note: str = Field(min_length=3, max_length=500)


class LocationIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    zone: str = Field(min_length=2, max_length=40)
    is_safe_point: bool = False


class ItemCloseIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.get("/stats")
async def admin_stats(admin=Depends(require_admin)):
    s = await compute_stats()
    s.update({
        "open_reports": await db.moderation_reports.count_documents({"status": {"$in": ["open", "in_review"]}}),
        "open_claims": await db.claims.count_documents({"status": {"$in": ["pending", "verifying"]}}),
        "active_handovers": await db.handover_sessions.count_documents({"status": "active"}),
        "suspended": await db.users.count_documents({"status": "suspended"}),
        "banned": await db.users.count_documents({"status": "banned"}),
        "open_appeals": await db.appeals.count_documents({"status": "open"}),
    })
    return s


@router.get("/users")
async def users(q: Optional[str] = None, admin=Depends(require_admin)):
    query = {}
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        query = {"$or": [{"name": rx}, {"email": rx}]}
    rows = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(500)
    return [public_user(r) for r in rows]


@router.post("/users/{user_id}/action")
async def user_action(user_id: str, body: UserActionIn, admin=Depends(require_admin)):
    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(404, "User not found")
    if target["id"] == admin["id"] or target.get("role") == "admin":
        raise HTTPException(400, "Administrators cannot be moderated from this dashboard")
    update = {}
    if body.action == "suspend":
        update = {"status": "suspended", "suspended_until": (now() + timedelta(days=body.days or 7)).isoformat()}
    elif body.action == "ban":
        update = {"status": "banned", "suspended_until": None}
    elif body.action == "reinstate":
        update = {"status": "active", "suspended_until": None}
    if update:
        await db.users.update_one({"id": user_id}, {"$set": update})
    await db.moderation_actions.insert_one({"id": new_id(), "admin_id": admin["id"], "user_id": user_id, "action": body.action,
                                            "reason": body.reason, "days": body.days if body.action == "suspend" else None, "created_at": iso()})
    await audit(admin["id"], f"moderation.{body.action}", "user", user_id, {"reason": body.reason})
    msg = {"suspend": f"Your account has been suspended for {body.days} days.", "ban": "Your account has been permanently banned.",
           "reinstate": "Your account has been reinstated.", "warn": "You have received a formal warning."}[body.action]
    await notify(user_id, "moderation", "Account notice", f"{msg} Reason: {body.reason}. You may appeal from your profile.", "/profile")
    return {"ok": True}


@router.get("/moderation-actions")
async def moderation_actions(admin=Depends(require_admin)):
    return await db.moderation_actions.find({}, {"_id": 0}).sort("created_at", -1).to_list(300)


@router.get("/reports")
async def reports(status: Optional[str] = None, admin=Depends(require_admin)):
    query = {"status": status} if status else {}
    rows = await db.moderation_reports.find(query, {"_id": 0}).sort("created_at", -1).to_list(300)
    ids = {r.get("reporter_id") for r in rows} | {r.get("target_user_id") for r in rows}
    names = {u["id"]: u["name"] async for u in db.users.find({"id": {"$in": [i for i in ids if i]}}, {"_id": 0, "id": 1, "name": 1})}
    for r in rows:
        r["reporter_name"] = names.get(r.get("reporter_id"), "Automated detector" if r.get("source") == "automated" else None)
        r["target_user_name"] = names.get(r.get("target_user_id"))
    return rows


@router.post("/reports/{rid}/resolve")
async def resolve_report(rid: str, body: ResolveIn, admin=Depends(require_admin)):
    r = await db.moderation_reports.update_one({"id": rid}, {"$set": {"status": body.status, "resolution_note": body.note, "resolved_by": admin["id"], "resolved_at": iso()}})
    if not r.matched_count:
        raise HTTPException(404, "Report not found")
    await audit(admin["id"], "moderation.report_resolve", "moderation_report", rid, {"status": body.status, "note": body.note})
    return {"ok": True}


@router.get("/claims")
async def claims(status: Optional[str] = None, admin=Depends(require_admin)):
    query = {"status": status} if status else {}
    rows = await db.claims.find(query, {"_id": 0}).sort("created_at", -1).to_list(300)
    for r in rows:
        it = await db.items.find_one({"id": r["item_id"]}, {"_id": 0})
        r["item"] = summary(it) if it else None
    return rows


@router.get("/handovers")
async def handovers(admin=Depends(require_admin)):
    rows = await db.handover_sessions.find({}, {"_id": 0, "token_hash": 0, "code_hash": 0}).sort("created_at", -1).to_list(300)
    for r in rows:
        it = await db.items.find_one({"id": r["item_id"]}, {"_id": 0})
        r["item"] = summary(it) if it else None
    return rows


@router.get("/audit")
async def audit_logs(q: Optional[str] = None, admin=Depends(require_admin)):
    query = {"action": {"$regex": re.escape(q), "$options": "i"}} if q else {}
    return await db.audit_logs.find(query, {"_id": 0}).sort("created_at", -1).to_list(300)


@router.get("/items")
async def items(type: Optional[str] = None, status: Optional[str] = None, admin=Depends(require_admin)):
    query = {}
    if type:
        query["type"] = type
    if status:
        query["status"] = status
    rows = await db.items.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [{**summary(r), "owner_id": r["owner_id"], "is_deleted": r.get("is_deleted")} for r in rows]


@router.post("/items/{item_id}/close")
async def close_item(item_id: str, body: ItemCloseIn, admin=Depends(require_admin)):
    it = await db.items.find_one({"id": item_id}, {"_id": 0})
    if not it:
        raise HTTPException(404, "Item not found")
    await set_status(item_id, "CLOSED", admin["id"], f"Closed by administrator: {body.reason}")
    await audit(admin["id"], "item.admin_close", "item", item_id, {"reason": body.reason})
    await notify(it["owner_id"], "moderation", "Report closed by administrator", f"'{it['title']}' was closed. Reason: {body.reason}", f"/items/{item_id}")
    return {"ok": True}


@router.post("/locations")
async def add_location(body: LocationIn, admin=Depends(require_admin)):
    if await db.locations.find_one({"name": body.name}):
        raise HTTPException(409, "Location already exists")
    loc = {**body.model_dump(), "id": new_id(), "created_at": iso()}
    await db.locations.insert_one(dict(loc))
    await audit(admin["id"], "location.create", "location", loc["id"], {"name": body.name})
    loc.pop("_id", None)
    return loc


@router.delete("/locations/{lid}")
async def delete_location(lid: str, admin=Depends(require_admin)):
    r = await db.locations.delete_one({"id": lid})
    if not r.deleted_count:
        raise HTTPException(404, "Location not found")
    await audit(admin["id"], "location.delete", "location", lid)
    return {"ok": True}


@router.get("/appeals")
async def appeals(admin=Depends(require_admin)):
    rows = await db.appeals.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    for r in rows:
        u = await db.users.find_one({"id": r["user_id"]}, {"_id": 0, "name": 1, "email": 1, "status": 1})
        r["user"] = u
    return rows


@router.post("/appeals/{aid}/resolve")
async def resolve_appeal(aid: str, body: AppealResolveIn, admin=Depends(require_admin)):
    ap = await db.appeals.find_one({"id": aid}, {"_id": 0})
    if not ap or ap["status"] != "open":
        raise HTTPException(404, "Open appeal not found")
    await db.appeals.update_one({"id": aid}, {"$set": {"status": body.decision, "note": body.note, "resolved_by": admin["id"], "resolved_at": iso()}})
    if body.decision == "overturned":
        await db.users.update_one({"id": ap["user_id"]}, {"$set": {"status": "active", "suspended_until": None}})
        await db.moderation_actions.insert_one({"id": new_id(), "admin_id": admin["id"], "user_id": ap["user_id"], "action": "reinstate",
                                                "reason": f"Appeal overturned: {body.note}", "created_at": iso()})
    await audit(admin["id"], f"appeal.{body.decision}", "appeal", aid, {"note": body.note})
    await notify(ap["user_id"], "moderation", "Appeal decision", f"Your appeal was {body.decision}. {body.note}", "/profile")
    return {"ok": True}
