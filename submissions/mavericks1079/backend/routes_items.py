import re
import uuid
import asyncio
import logging
from typing import Optional, List, Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from pydantic import BaseModel, Field

import ml
from image_ml import embed_image, image_similarity
from photo_autofill import suggest_from_photo
from core import db, iso, new_id, audit, notify, require_active, get_optional_user, get_current_user, put_object, get_object, APP_NAME, POLICY_VERSION

router = APIRouter(prefix="/api")

BASE_STATUS = {"lost": "LOST", "found": "FOUND"}
INACTIVE = ["RETURNED", "CLOSED"]
EARLY = ["LOST", "FOUND", "MATCH FOUND"]
PRIVATE_FIELDS = ("secure_collection_location", "owner_id", "_id")


def public_item(item: dict, viewer=None) -> dict:
    out = {k: v for k, v in item.items() if k not in PRIVATE_FIELDS}
    out["is_owner"] = bool(viewer and viewer["id"] == item.get("owner_id"))
    return out


def summary(item: dict) -> dict:
    keys = ("id", "type", "title", "category", "location", "occurred_at", "status", "image_paths", "color", "created_at")
    return {k: item.get(k) for k in keys}


async def zones() -> dict:
    return {l["name"]: l.get("zone") for l in await db.locations.find({}, {"_id": 0}).to_list(500)}


async def attach_images(items: list, field: str = "image_paths"):
    """Attach precomputed photo embeddings (from db.files) as transient `_img` for scoring."""
    paths = {p for it in items for p in (it.get(field) or [])}
    if not paths:
        return items
    emb = {f["storage_path"]: f async for f in db.files.find({"storage_path": {"$in": list(paths)}, "embedding": {"$exists": True}},
                                                           {"_id": 0, "storage_path": 1, "embedding": 1, "histogram": 1})}
    for it in items:
        it["_img"] = [emb[p] for p in (it.get(field) or []) if p in emb]
    return items


async def set_status(item_id, status, actor_id, note=""):
    await db.items.update_one({"id": item_id}, {
        "$set": {"status": status, "updated_at": iso()},
        "$push": {"status_history": {"status": status, "at": iso(), "by": actor_id, "note": note}},
    })


async def reset_status(item_id, actor_id, note=""):
    item = await db.items.find_one({"id": item_id}, {"_id": 0})
    if not item or item["status"] in INACTIVE:
        return
    field = "lost_id" if item["type"] == "lost" else "found_id"
    has = await db.item_matches.find_one({field: item_id, "feedback_irrelevant": {"$ne": True}})
    target = "MATCH FOUND" if has else BASE_STATUS[item["type"]]
    if item["status"] != target:
        await set_status(item_id, target, actor_id, note)


async def recompute_matches(item: dict):
    if item.get("is_deleted") or item["status"] in INACTIVE:
        return
    z = await zones()
    opp = "found" if item["type"] == "lost" else "lost"
    candidates = await db.items.find({"type": opp, "is_deleted": False, "status": {"$nin": INACTIVE}, "owner_id": {"$ne": item["owner_id"]}}, {"_id": 0}).to_list(1000)
    item = dict(item)
    await attach_images([item, *candidates])
    touched = []
    for c in candidates:
        lost, found = (item, c) if item["type"] == "lost" else (c, item)
        res = ml.score_pair(lost, found, z)
        key = {"lost_id": lost["id"], "found_id": found["id"]}
        if res["score"] >= ml.MATCH_THRESHOLD:
            r = await db.item_matches.update_one(key, {
                "$set": {"score": res["score"], "breakdown": res["breakdown"], "reasons": res["reasons"], "weights": res["weights"], "updated_at": iso()},
                "$setOnInsert": {"id": new_id(), "created_at": iso(), "feedback": {}},
            }, upsert=True)
            if r.upserted_id:
                for owner, mine, other in ((lost["owner_id"], lost, found), (found["owner_id"], found, lost)):
                    await notify(owner, "match", "Potential match found",
                                 f"Your report '{mine['title']}' may match a {other['type']} item ({res['score']}% match).",
                                 f"/items/{mine['id']}", f"match:{lost['id']}:{found['id']}:{owner}", pref="matches")
        else:
            await db.item_matches.delete_one({**key, "feedback": {}})
        touched.append(c["id"])
    for iid in [item["id"], *touched]:
        await reset_status(iid, "system", "Match recalculation")


async def run_watchlists(item: dict):
    z = await zones()
    item = dict(item)
    await attach_images([item])
    wls = await db.watchlists.find({"active": True, "user_id": {"$ne": item["owner_id"]}}, {"_id": 0}).to_list(1000)
    for wl in wls:
        wl["ref_paths"] = [wl["reference_image"]] if wl.get("reference_image") else []
    await attach_images(wls, "ref_paths")
    for wl in wls:
        if wl.get("item_type") in ("lost", "found") and wl["item_type"] != item["type"]:
            continue
        occ = item.get("occurred_at") or ""
        if wl.get("date_from") and occ[:10] < wl["date_from"][:10]:
            continue
        if wl.get("date_to") and occ[:10] > wl["date_to"][:10]:
            continue
        score = ml.watchlist_score(wl, item, z)
        if score >= int(wl.get("threshold") or 50):
            await notify(wl["user_id"], "watchlist", f"Watchlist alert: {wl['name']}",
                         f"A new {item['type']} report '{item['title']}' at {item['location']} matches your watchlist ({score}%).",
                         f"/items/{item['id']}", f"wl:{wl['id']}:{item['id']}", pref="watchlist")


class ItemIn(BaseModel):
    type: Literal["lost", "found"]
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5, max_length=2000)
    category: str
    predicted_category: Optional[str] = None
    prediction_confidence: Optional[float] = None
    color: Optional[str] = ""
    attributes: Optional[str] = ""
    location: str = Field(min_length=2, max_length=120)
    occurred_at: str
    image_paths: List[str] = []
    private_clues: Optional[str] = Field(default="", max_length=1000)
    reward: Optional[str] = ""
    contact_pref: Optional[str] = "in_app"
    collection_pref: Optional[str] = ""
    secure_collection_location: Optional[str] = ""
    collection_window: Optional[str] = ""
    holder: Optional[Literal["finder", "office"]] = "finder"
    notes_for_owner: Optional[str] = ""


class ItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, min_length=5, max_length=2000)
    category: Optional[str] = None
    color: Optional[str] = None
    attributes: Optional[str] = None
    location: Optional[str] = None
    occurred_at: Optional[str] = None
    image_paths: Optional[List[str]] = None
    private_clues: Optional[str] = Field(default=None, max_length=1000)
    reward: Optional[str] = None
    secure_collection_location: Optional[str] = None
    collection_window: Optional[str] = None
    holder: Optional[Literal["finder", "office"]] = None
    notes_for_owner: Optional[str] = None


class CategorizeIn(BaseModel):
    title: str
    description: Optional[str] = ""


class DuplicateIn(BaseModel):
    type: Literal["lost", "found"]
    title: str
    description: Optional[str] = ""
    category: Optional[str] = None
    color: Optional[str] = ""
    attributes: Optional[str] = ""
    location: Optional[str] = ""
    occurred_at: Optional[str] = None
    image_paths: List[str] = []


class FeedbackIn(BaseModel):
    relevant: bool


class PhotoSuggestIn(BaseModel):
    path: str


@router.post("/ml/photo-suggest")
async def photo_suggest(body: PhotoSuggestIn, user: dict = Depends(get_current_user)):
    rec = await db.files.find_one({"storage_path": body.path, "owner_id": user["id"], "is_deleted": False})
    if not rec:
        raise HTTPException(404, "Photo not found")
    loop = asyncio.get_running_loop()
    data, _ = await loop.run_in_executor(None, get_object, body.path)
    res = await loop.run_in_executor(None, suggest_from_photo, data)
    res["label"] = ml.CATEGORIES.get(res["category"]) if res["category"] else None
    return res


@router.post("/ml/categorize")
async def categorize(body: CategorizeIn):
    return ml.predict_category(body.title, body.description or "")


@router.get("/categories")
async def categories():
    return [{"key": k, "label": v} for k, v in ml.CATEGORIES.items()]


@router.get("/locations")
async def locations():
    return await db.locations.find({}, {"_id": 0}).sort("name", 1).to_list(500)


@router.post("/items/check-duplicates")
async def check_duplicates(body: DuplicateIn, user: dict = Depends(get_current_user)):
    probe = body.model_dump()
    probe["category"] = probe["category"] or ml.predict_category(body.title, body.description or "")["category"]
    z = await zones()
    out = []
    candidates = await db.items.find({"type": body.type, "is_deleted": False, "status": {"$nin": INACTIVE}}, {"_id": 0}).to_list(1000)
    await attach_images([probe, *candidates])
    for c in candidates:
        res = ml.score_pair(probe, c, z, mode="duplicate")
        if res["score"] >= ml.DUPLICATE_THRESHOLD:
            out.append({**summary(c), "similarity": res["score"], "reasons": res["reasons"]})
    return sorted(out, key=lambda x: -x["similarity"])[:3]


@router.post("/items")
async def create_item(body: ItemIn, user: dict = Depends(require_active)):
    if not user.get("report_policy_ack"):
        raise HTTPException(403, "Please review and acknowledge the Responsible Use Policy before your first report")
    if body.category not in ml.CATEGORIES:
        raise HTTPException(422, "Invalid category")
    item = await create_item_internal(body, user["id"])
    return public_item(item, user)


async def create_item_internal(body: ItemIn, owner_id: str) -> dict:
    data = body.model_dump()
    clues = data.pop("private_clues") or ""
    if data["predicted_category"] is None:
        pred = ml.predict_category(body.title, body.description)
        data["predicted_category"], data["prediction_confidence"] = pred["category"], pred["confidence"]
    status = BASE_STATUS[body.type]
    item = {**data, "id": new_id(), "owner_id": owner_id, "status": status, "is_deleted": False,
            "has_private_clues": bool(clues.strip()), "created_at": iso(), "updated_at": iso(),
            "status_history": [{"status": status, "at": iso(), "by": owner_id, "note": "Report created"}]}
    await db.items.insert_one(dict(item))
    if clues.strip():
        await db.item_private_clues.insert_one({"item_id": item["id"], "clues": clues.strip(), "updated_at": iso()})
    await audit(owner_id, "item.create", "item", item["id"], {"type": body.type, "category": body.category})
    await recompute_matches(item)
    await run_watchlists(item)
    item.pop("_id", None)
    return await db.items.find_one({"id": item["id"]}, {"_id": 0})


@router.get("/items")
async def list_items(type: Optional[str] = None, category: Optional[str] = None, location: Optional[str] = None,
                     status: Optional[str] = None, q: Optional[str] = None, sort: str = "newest", limit: int = 24, skip: int = 0):
    query = {"is_deleted": False}
    if type in ("lost", "found"):
        query["type"] = type
    if category:
        query["category"] = category
    if location:
        query["location"] = location
    if status:
        query["status"] = status
    if q:
        rx = {"$regex": re.escape(q.strip()), "$options": "i"}
        cats = [k for k, v in ml.CATEGORIES.items() if q.lower() in v.lower()]
        query["$or"] = [{"title": rx}, {"description": rx}, {"location": rx}, {"color": rx}, {"category": {"$in": cats}}]
    direction = 1 if sort == "oldest" else -1
    total = await db.items.count_documents(query)
    rows = await db.items.find(query, {"_id": 0}).sort("created_at", direction).skip(max(skip, 0)).limit(min(limit, 100)).to_list(100)
    return {"total": total, "items": [public_item(r) for r in rows]}


@router.get("/items/mine")
async def my_items(user: dict = Depends(get_current_user)):
    rows = await db.items.find({"owner_id": user["id"], "is_deleted": False}, {"_id": 0}).sort("created_at", -1).to_list(500)
    out = []
    for r in rows:
        field = "lost_id" if r["type"] == "lost" else "found_id"
        r = public_item(r, user)
        r["match_count"] = await db.item_matches.count_documents({field: r["id"], "feedback_irrelevant": {"$ne": True}})
        r["open_claims"] = await db.claims.count_documents({"item_id": r["id"], "status": {"$in": ["pending", "verifying"]}})
        out.append(r)
    return out


async def get_item_or_404(item_id):
    item = await db.items.find_one({"id": item_id, "is_deleted": False}, {"_id": 0})
    if not item:
        raise HTTPException(404, "Item not found")
    return item


@router.get("/items/{item_id}")
async def get_item(item_id: str, viewer=Depends(get_optional_user)):
    item = await get_item_or_404(item_id)
    out = public_item(item, viewer)
    is_admin = bool(viewer and viewer.get("role") == "admin")
    if out["is_owner"] or is_admin:
        clues = await db.item_private_clues.find_one({"item_id": item_id}, {"_id": 0})
        out["private_clues"] = clues["clues"] if clues else ""
        out["secure_collection_location"] = item.get("secure_collection_location")
    elif viewer:
        approved = await db.claims.find_one({"item_id": item_id, "claimant_id": viewer["id"], "status": {"$in": ["approved", "completed"]}})
        if approved:
            out["secure_collection_location"] = item.get("secure_collection_location")
        mine = await db.claims.find_one({"item_id": item_id, "claimant_id": viewer["id"]}, {"_id": 0, "id": 1, "status": 1}, sort=[("created_at", -1)])
        out["my_claim"] = mine
    if not out["is_owner"]:
        out["status_history"] = [{"status": h["status"], "at": h["at"]} for h in item.get("status_history", [])]
    return out


@router.patch("/items/{item_id}")
async def update_item(item_id: str, body: ItemUpdate, user: dict = Depends(require_active)):
    item = await get_item_or_404(item_id)
    if item["owner_id"] != user["id"]:
        raise HTTPException(403, "Only the report owner can edit this report")
    if item["status"] in INACTIVE:
        raise HTTPException(409, "Closed or returned reports cannot be edited")
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if "category" in data and data["category"] not in ml.CATEGORIES:
        raise HTTPException(422, "Invalid category")
    clues = data.pop("private_clues", None)
    if clues is not None:
        await db.item_private_clues.update_one({"item_id": item_id}, {"$set": {"clues": clues.strip(), "updated_at": iso()}}, upsert=True)
        data["has_private_clues"] = bool(clues.strip())
    data["updated_at"] = iso()
    await db.items.update_one({"id": item_id}, {"$set": data})
    await audit(user["id"], "item.update", "item", item_id, {"fields": list(data.keys())})
    updated = await get_item_or_404(item_id)
    await recompute_matches(updated)
    return public_item(await get_item_or_404(item_id), user)


@router.post("/items/{item_id}/close")
async def close_item(item_id: str, user: dict = Depends(require_active)):
    item = await get_item_or_404(item_id)
    if item["owner_id"] != user["id"]:
        raise HTTPException(403, "Only the report owner can close this report")
    if item["status"] in INACTIVE:
        raise HTTPException(409, "Report already closed")
    if item["status"] == "READY FOR HANDOVER":
        raise HTTPException(409, "Cancel the pending handover before closing")
    await set_status(item_id, "CLOSED", user["id"], "Closed by owner")
    await audit(user["id"], "item.close", "item", item_id)
    return {"ok": True}


@router.get("/items/{item_id}/matches")
async def item_matches(item_id: str, user: dict = Depends(get_current_user)):
    item = await get_item_or_404(item_id)
    if item["owner_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(403, "Only the report owner can view its matches")
    mine, other = ("lost_id", "found_id") if item["type"] == "lost" else ("found_id", "lost_id")
    rows = await db.item_matches.find({mine: item_id}, {"_id": 0}).sort("score", -1).to_list(50)
    out = []
    for m in rows:
        o = await db.items.find_one({"id": m[other], "is_deleted": False}, {"_id": 0})
        if o:
            out.append({"id": m["id"], "score": m["score"], "breakdown": m["breakdown"], "reasons": m["reasons"], "weights": m.get("weights") or ml.MATCH_WEIGHTS,
                        "feedback": (m.get("feedback") or {}).get(user["id"]), "item": summary(o)})
    return {"weights": ml.MATCH_WEIGHTS, "image_weight": ml.IMAGE_WEIGHT, "matches": out}


@router.get("/matches/mine")
async def my_matches(user: dict = Depends(get_current_user)):
    my_ids = [i["id"] async for i in db.items.find({"owner_id": user["id"], "is_deleted": False, "status": {"$nin": INACTIVE}}, {"id": 1})]
    rows = await db.item_matches.find({"$or": [{"lost_id": {"$in": my_ids}}, {"found_id": {"$in": my_ids}}], "feedback_irrelevant": {"$ne": True}}, {"_id": 0}).sort("score", -1).to_list(12)
    out = []
    for m in rows:
        mine_id, other_id = (m["lost_id"], m["found_id"]) if m["lost_id"] in my_ids else (m["found_id"], m["lost_id"])
        a = await db.items.find_one({"id": mine_id}, {"_id": 0})
        b = await db.items.find_one({"id": other_id, "is_deleted": False}, {"_id": 0})
        if a and b:
            out.append({"id": m["id"], "score": m["score"], "reasons": m["reasons"], "mine": summary(a), "other": summary(b)})
    return out


@router.post("/matches/{match_id}/feedback")
async def match_feedback(match_id: str, body: FeedbackIn, user: dict = Depends(require_active)):
    m = await db.item_matches.find_one({"id": match_id}, {"_id": 0})
    if not m:
        raise HTTPException(404, "Match not found")
    owners = [i["owner_id"] async for i in db.items.find({"id": {"$in": [m["lost_id"], m["found_id"]]}}, {"owner_id": 1})]
    if user["id"] not in owners:
        raise HTTPException(403, "Not your match")
    fb = {**(m.get("feedback") or {}), user["id"]: "relevant" if body.relevant else "irrelevant"}
    await db.item_matches.update_one({"id": match_id}, {"$set": {"feedback": fb, "feedback_irrelevant": "irrelevant" in fb.values()}})
    for iid in (m["lost_id"], m["found_id"]):
        await reset_status(iid, user["id"], "Match feedback")
    return {"ok": True}


ALLOWED_IMAGE = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
PHOTO_SEARCH_MIN = 0.30


@router.post("/items/photo-search")
async def photo_search(file: UploadFile = File(...), type: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Compare an uploaded photo (not stored) with photos of active reports. Visual similarity is never proof of ownership."""
    if file.content_type not in ALLOWED_IMAGE:
        raise HTTPException(415, "Only JPEG, PNG or WEBP images are allowed")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "Image must be 5 MB or smaller")
    try:
        probe = await asyncio.get_running_loop().run_in_executor(None, embed_image, data)
    except Exception:
        raise HTTPException(422, "Could not read this image file")
    query = {"is_deleted": False, "status": {"$nin": INACTIVE}, "image_paths.0": {"$exists": True}}
    if type in ("lost", "found"):
        query["type"] = type
    items = await attach_images(await db.items.find(query, {"_id": 0}).to_list(2000))
    out = []
    for it in items:
        sims = [s for e in it.get("_img", []) if (s := image_similarity(probe, e)) is not None]
        if sims and max(sims) >= PHOTO_SEARCH_MIN:
            out.append({**summary(it), "photo_similarity": round(max(sims) * 100)})
    out.sort(key=lambda x: -x["photo_similarity"])
    return {"results": out[:12], "searched": len(items)}


@router.post("/uploads")
async def upload(file: UploadFile = File(...), user: dict = Depends(require_active)):
    if file.content_type not in ALLOWED_IMAGE:
        raise HTTPException(415, "Only JPEG, PNG or WEBP images are allowed")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "Image must be 5 MB or smaller")
    path = f"{APP_NAME}/uploads/{user['id']}/{uuid.uuid4()}.{ALLOWED_IMAGE[file.content_type]}"
    try:
        features = await asyncio.get_running_loop().run_in_executor(None, embed_image, data)
    except Exception:
        raise HTTPException(422, "Could not read this image file")
    result = put_object(path, data, file.content_type)
    await db.files.insert_one({"id": new_id(), "storage_path": result["path"], "owner_id": user["id"], "content_type": file.content_type,
                               "size": result.get("size", len(data)), "is_deleted": False, "created_at": iso(), **features})
    return {"path": result["path"]}


async def backfill_image_embeddings():
    """Compute embeddings for photos uploaded before photo matching existed, then refresh matches."""
    loop = asyncio.get_running_loop()
    changed = 0
    async for f in db.files.find({"embedding": {"$exists": False}, "is_deleted": False}, {"_id": 0}):
        try:
            data, _ = await loop.run_in_executor(None, get_object, f["storage_path"])
            features = await loop.run_in_executor(None, embed_image, data)
            await db.files.update_one({"storage_path": f["storage_path"]}, {"$set": features})
            changed += 1
        except Exception as e:
            logging.getLogger("back2u").warning(f"Embedding backfill failed for {f['storage_path']}: {e}")
    if changed:
        async for it in db.items.find({"is_deleted": False, "status": {"$nin": INACTIVE}, "type": "lost"}, {"_id": 0}):
            await recompute_matches(it)
    return changed


@router.get("/files/{path:path}")
async def download(path: str):
    record = await db.files.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
    if not record:
        raise HTTPException(404, "File not found")
    data, ctype = get_object(path)
    return Response(content=data, media_type=record.get("content_type", ctype), headers={"Cache-Control": "public, max-age=86400"})
