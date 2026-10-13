import os
import secrets
from datetime import timedelta
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import ml
from core import db, iso, now, parse_dt, new_id, sha256, audit, notify, require_active, require_admin, get_current_user
from routes_items import get_item_or_404, set_status, reset_status, summary, INACTIVE

router = APIRouter(prefix="/api")

MAX_ATTEMPTS = int(os.environ.get("MAX_CLAIM_ATTEMPTS_PER_DAY", "3"))
TOKEN_MINUTES = int(os.environ.get("HANDOVER_TOKEN_MINUTES", "30"))
OPEN_CLAIM = ["pending", "verifying", "approved"]


class ClaimIn(BaseModel):
    marks: str = Field(min_length=3, max_length=1000)
    contents: Optional[str] = Field(default="", max_length=1000)
    circumstances: str = Field(min_length=3, max_length=1000)
    lost_item_id: Optional[str] = None


class ReviewIn(BaseModel):
    action: Literal["start_verification", "approve", "reject"]
    note: Optional[str] = Field(default="", max_length=500)


class ScanIn(BaseModel):
    token: Optional[str] = None
    handover_id: Optional[str] = None
    code: Optional[str] = None


class AdminCompleteIn(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class StoryIn(BaseModel):
    opt_out: bool


def score_label(score):
    if score is None:
        return "No private clues stored - verify manually"
    return "Strong" if score >= 60 else ("Partial" if score >= 30 else "Weak")


async def claim_history(claim_id, status, actor, note=""):
    await db.claims.update_one({"id": claim_id}, {"$set": {"status": status, "updated_at": iso()},
                                                  "$push": {"history": {"status": status, "at": iso(), "by": actor, "note": note}}})


@router.post("/items/{item_id}/claims")
async def submit_claim(item_id: str, body: ClaimIn, user: dict = Depends(require_active)):
    item = await get_item_or_404(item_id)
    if item["type"] != "found":
        raise HTTPException(400, "Claims can only be made on found items")
    if item["owner_id"] == user["id"]:
        raise HTTPException(400, "You cannot claim an item you reported")
    if item["status"] in INACTIVE or item["status"] == "READY FOR HANDOVER":
        raise HTTPException(409, "This item is not available for claims")
    since = (now() - timedelta(hours=24)).isoformat()
    attempts = await db.claim_verification_attempts.count_documents({"user_id": user["id"], "item_id": item_id, "created_at": {"$gte": since}})
    if attempts >= MAX_ATTEMPTS:
        raise HTTPException(429, f"Too many ownership claim attempts for this item. Please try again after 24 hours or contact a campus office.")
    if await db.claims.find_one({"item_id": item_id, "claimant_id": user["id"], "status": {"$in": OPEN_CLAIM}}):
        raise HTTPException(409, "You already have an open claim on this item")
    if body.lost_item_id:
        lost = await db.items.find_one({"id": body.lost_item_id, "owner_id": user["id"], "type": "lost", "is_deleted": False})
        if not lost:
            raise HTTPException(400, "Linked lost report not found")
    clues = await db.item_private_clues.find_one({"item_id": item_id})
    text = f"{body.marks} {body.contents or ''}"
    score = ml.verify_claim(text, clues["clues"]) if clues and clues.get("clues") else None
    claim = {"id": new_id(), "item_id": item_id, "lost_item_id": body.lost_item_id, "claimant_id": user["id"], "finder_id": item["owner_id"],
             "marks": body.marks, "contents": body.contents, "circumstances": body.circumstances, "verification_score": score,
             "status": "pending", "created_at": iso(), "updated_at": iso(),
             "history": [{"status": "pending", "at": iso(), "by": user["id"], "note": "Claim submitted"}]}
    await db.claims.insert_one(dict(claim))
    await db.claim_verification_attempts.insert_one({"id": new_id(), "claim_id": claim["id"], "user_id": user["id"], "item_id": item_id,
                                                      "score": score, "created_at": iso()})
    if score is not None and score < 20 and attempts + 1 >= 2:
        await db.moderation_reports.insert_one({"id": new_id(), "source": "automated", "reporter_id": None, "target_type": "claim",
                                                "target_id": claim["id"], "target_user_id": user["id"],
                                                "reason": "Repeated low-confidence ownership claims on the same item (automated flag for human review)",
                                                "details": f"{attempts + 1} attempts in 24h", "status": "open", "created_at": iso()})
    if item["status"] in ("FOUND", "MATCH FOUND"):
        await set_status(item_id, "CLAIM PENDING", user["id"], "Ownership claim submitted")
    if body.lost_item_id:
        await set_status(body.lost_item_id, "CLAIM PENDING", user["id"], "Claim submitted on a found item")
    await notify(item["owner_id"], "claim", "New ownership claim", f"Someone has claimed '{item['title']}'. Review their details.", f"/items/{item_id}", pref="claims")
    await audit(user["id"], "claim.submit", "claim", claim["id"], {"item_id": item_id, "attempt": attempts + 1})
    return {"id": claim["id"], "status": "pending", "attempts_remaining": MAX_ATTEMPTS - attempts - 1,
            "message": "Claim submitted. The finder will review your details. Correct answers are never revealed."}


@router.get("/claims/mine")
async def my_claims(user: dict = Depends(get_current_user)):
    rows = await db.claims.find({"claimant_id": user["id"]}, {"_id": 0, "verification_score": 0}).sort("created_at", -1).to_list(200)
    for r in rows:
        it = await db.items.find_one({"id": r["item_id"]}, {"_id": 0})
        r["item"] = summary(it) if it else None
        hs = await db.handover_sessions.find_one({"claim_id": r["id"]}, {"_id": 0, "id": 1, "status": 1})
        r["handover"] = hs
    return rows


@router.get("/items/{item_id}/claims")
async def item_claims(item_id: str, user: dict = Depends(get_current_user)):
    item = await get_item_or_404(item_id)
    if item["owner_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(403, "Only the finder or an administrator can review claims")
    rows = await db.claims.find({"item_id": item_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for r in rows:
        c = await db.users.find_one({"id": r["claimant_id"]}, {"_id": 0, "name": 1})
        r["claimant_name"] = c["name"] if c else "Unknown"
        r["score_label"] = score_label(r.get("verification_score"))
        r["attempts"] = await db.claim_verification_attempts.count_documents({"item_id": item_id, "user_id": r["claimant_id"]})
        hs = await db.handover_sessions.find_one({"claim_id": r["id"]}, {"_id": 0, "id": 1, "status": 1})
        r["handover"] = hs
    return rows


async def _reset_after_claim(claim, actor, note):
    open_left = await db.claims.count_documents({"item_id": claim["item_id"], "status": {"$in": ["pending", "verifying"]}})
    item = await db.items.find_one({"id": claim["item_id"]}, {"_id": 0})
    if open_left and item and item["status"] not in INACTIVE:
        await set_status(claim["item_id"], "CLAIM PENDING", actor, note)
    else:
        await db.items.update_one({"id": claim["item_id"], "status": {"$nin": INACTIVE}}, {"$set": {"status": "FOUND"}})
        await reset_status(claim["item_id"], actor, note)
    if claim.get("lost_item_id"):
        await db.items.update_one({"id": claim["lost_item_id"], "status": {"$nin": INACTIVE}}, {"$set": {"status": "LOST"}})
        await reset_status(claim["lost_item_id"], actor, note)


@router.post("/claims/{claim_id}/review")
async def review_claim(claim_id: str, body: ReviewIn, user: dict = Depends(require_active)):
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(404, "Claim not found")
    is_admin = user.get("role") == "admin"
    if claim["finder_id"] != user["id"] and not is_admin:
        raise HTTPException(403, "Only the finder or an administrator can review this claim")
    if claim["status"] not in ("pending", "verifying"):
        raise HTTPException(409, f"Claim is already {claim['status']}")
    item = await get_item_or_404(claim["item_id"])
    if body.action == "start_verification":
        await claim_history(claim_id, "verifying", user["id"], body.note)
        await set_status(item["id"], "VERIFICATION IN PROGRESS", user["id"], "Finder is verifying ownership")
        if claim.get("lost_item_id"):
            await set_status(claim["lost_item_id"], "VERIFICATION IN PROGRESS", user["id"], "Ownership verification in progress")
        await notify(claim["claimant_id"], "claim", "Verification in progress", f"The finder is verifying your claim on '{item['title']}'.", f"/items/{item['id']}", pref="claims")
    elif body.action == "approve":
        if await db.claims.find_one({"item_id": item["id"], "status": {"$in": ["approved", "completed"]}}):
            raise HTTPException(409, "Another claim on this item has already been approved")
        await claim_history(claim_id, "approved", user["id"], body.note)
        session = {"id": new_id(), "claim_id": claim_id, "item_id": item["id"], "lost_item_id": claim.get("lost_item_id"),
                   "finder_id": claim["finder_id"], "claimant_id": claim["claimant_id"], "status": "active",
                   "token_hash": None, "code_hash": None, "token_expires_at": None, "token_used": False,
                   "finder_confirmed_at": None, "claimant_confirmed_at": None, "created_at": iso(),
                   "events": [{"event": "session.created", "at": iso(), "by": user["id"]}]}
        await db.handover_sessions.insert_one(dict(session))
        await set_status(item["id"], "READY FOR HANDOVER", user["id"], "Claim approved - awaiting handover")
        if claim.get("lost_item_id"):
            await set_status(claim["lost_item_id"], "READY FOR HANDOVER", user["id"], "Claim approved - awaiting handover")
        async for other in db.claims.find({"item_id": item["id"], "status": {"$in": ["pending", "verifying"]}, "id": {"$ne": claim_id}}, {"_id": 0}):
            await claim_history(other["id"], "rejected", user["id"], "Another claim was approved")
            await notify(other["claimant_id"], "claim", "Claim not approved", f"Your claim on '{item['title']}' was not approved.", f"/items/{item['id']}", pref="claims")
        await notify(claim["claimant_id"], "claim", "Claim approved", f"Your claim on '{item['title']}' was approved. Arrange a safe handover.", f"/handover/{session['id']}", pref="claims")
        await audit(user["id"], "handover.session_created", "handover", session["id"], {"claim_id": claim_id})
    else:
        await claim_history(claim_id, "rejected", user["id"], body.note)
        await _reset_after_claim(claim, user["id"], "Claim rejected")
        await notify(claim["claimant_id"], "claim", "Claim not approved", f"Your claim on '{item['title']}' was not approved.", f"/items/{item['id']}", pref="claims")
    await audit(user["id"], f"claim.{body.action}", "claim", claim_id, {"by_admin": is_admin, "note": body.note})
    return {"ok": True}


async def _cancel_sessions(claim_id, actor):
    async for s in db.handover_sessions.find({"claim_id": claim_id, "status": "active"}, {"_id": 0}):
        await db.handover_sessions.update_one({"id": s["id"]}, {"$set": {"status": "cancelled", "token_hash": None, "code_hash": None},
                                                                 "$push": {"events": {"event": "session.cancelled", "at": iso(), "by": actor}}})
        await audit(actor, "handover.cancel", "handover", s["id"])


@router.post("/claims/{claim_id}/cancel")
async def cancel_claim(claim_id: str, user: dict = Depends(get_current_user)):
    claim = await db.claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(404, "Claim not found")
    if claim["claimant_id"] != user["id"]:
        raise HTTPException(403, "Only the claimant can cancel this claim")
    if claim["status"] not in OPEN_CLAIM:
        raise HTTPException(409, f"Claim is already {claim['status']}")
    await claim_history(claim_id, "cancelled", user["id"], "Cancelled by claimant")
    await _cancel_sessions(claim_id, user["id"])
    await _reset_after_claim(claim, user["id"], "Claim cancelled")
    await notify(claim["finder_id"], "claim", "Claim cancelled", "A claimant cancelled their claim on your found item.", f"/items/{claim['item_id']}", pref="claims")
    await audit(user["id"], "claim.cancel", "claim", claim_id)
    return {"ok": True}


# ---------------- Handover ----------------
def handover_view(s: dict, user: dict) -> dict:
    out = {k: v for k, v in s.items() if k not in ("token_hash", "code_hash", "_id")}
    out["role"] = "finder" if user["id"] == s["finder_id"] else ("claimant" if user["id"] == s["claimant_id"] else "admin")
    out["token_active"] = bool(s.get("token_hash")) and not s.get("token_used") and (parse_dt(s.get("token_expires_at")) or now()) > now()
    return out


async def _session_for(handover_id, user):
    s = await db.handover_sessions.find_one({"id": handover_id}, {"_id": 0})
    if not s:
        raise HTTPException(404, "Handover not found")
    if user["id"] not in (s["finder_id"], s["claimant_id"]) and user.get("role") != "admin":
        raise HTTPException(403, "You are not a participant in this handover")
    return s


@router.get("/handovers/mine")
async def my_handovers(user: dict = Depends(get_current_user)):
    rows = await db.handover_sessions.find({"$or": [{"finder_id": user["id"]}, {"claimant_id": user["id"]}]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    out = []
    for s in rows:
        v = handover_view(s, user)
        it = await db.items.find_one({"id": s["item_id"]}, {"_id": 0})
        v["item"] = summary(it) if it else None
        out.append(v)
    return out


@router.get("/handovers/{handover_id}")
async def get_handover(handover_id: str, user: dict = Depends(get_current_user)):
    s = await _session_for(handover_id, user)
    v = handover_view(s, user)
    it = await db.items.find_one({"id": s["item_id"]}, {"_id": 0})
    v["item"] = summary(it)
    v["secure_collection_location"] = it.get("secure_collection_location")
    v["collection_window"] = it.get("collection_window")
    v["holder"] = it.get("holder")
    names = {u["id"]: u["name"] async for u in db.users.find({"id": {"$in": [s["finder_id"], s["claimant_id"]]}}, {"_id": 0, "id": 1, "name": 1})}
    v["finder_name"], v["claimant_name"] = names.get(s["finder_id"]), names.get(s["claimant_id"])
    rc = await db.handover_receipts.find_one({"handover_id": handover_id}, {"_id": 0, "id": 1, "receipt_no": 1})
    v["receipt"] = rc
    return v


@router.post("/handovers/{handover_id}/token")
async def issue_token(handover_id: str, user: dict = Depends(require_active)):
    s = await _session_for(handover_id, user)
    if user["id"] != s["finder_id"]:
        raise HTTPException(403, "Only the finder can generate the handover QR code")
    if s["status"] != "active":
        raise HTTPException(409, f"Handover is {s['status']}")
    if s.get("claimant_confirmed_at"):
        raise HTTPException(409, "The owner has already confirmed receipt")
    token = secrets.token_urlsafe(32)
    code = f"{secrets.randbelow(10**6):06d}"
    expires = (now() + timedelta(minutes=TOKEN_MINUTES)).isoformat()
    await db.handover_sessions.update_one({"id": handover_id}, {
        "$set": {"token_hash": sha256(token), "code_hash": sha256(f"{handover_id}:{code}"), "token_expires_at": expires, "token_used": False},
        "$push": {"events": {"event": "token.issued", "at": iso(), "by": user["id"]}}})
    await audit(user["id"], "handover.token_issued", "handover", handover_id, {"expires_at": expires})
    return {"token": token, "code": code, "expires_at": expires, "handover_id": handover_id}


async def _complete(s: dict, actor: str, method: str, reason: str = ""):
    res = await db.handover_sessions.update_one({"id": s["id"], "status": "active"}, {
        "$set": {"status": "completed", "completed_at": iso(), "token_hash": None, "code_hash": None, "token_used": True, "method": method},
        "$push": {"events": {"event": "handover.completed", "at": iso(), "by": actor, "method": method}}})
    if res.modified_count == 0:
        raise HTTPException(409, "Handover has already been completed or is no longer active")
    item = await db.items.find_one({"id": s["item_id"]}, {"_id": 0})
    receipt = {"id": new_id(), "receipt_no": f"B2U-{secrets.token_hex(4).upper()}", "handover_id": s["id"], "claim_id": s["claim_id"],
               "item_id": s["item_id"], "lost_item_id": s.get("lost_item_id"), "item_title": item["title"], "item_category": item["category"],
               "item_location": item["location"], "finder_id": s["finder_id"], "claimant_id": s["claimant_id"], "method": method,
               "admin_reason": reason or None, "transaction_status": "COMPLETED", "story_opt_out": [],
               "found_reported_at": item["created_at"], "completed_at": iso()}
    await db.handover_receipts.insert_one(dict(receipt))
    await set_status(s["item_id"], "RETURNED", actor, f"Handover completed ({method}). Receipt {receipt['receipt_no']}")
    if s.get("lost_item_id"):
        await set_status(s["lost_item_id"], "RETURNED", actor, f"Recovered. Receipt {receipt['receipt_no']}")
    await claim_history(s["claim_id"], "completed", actor, "Handover completed")
    for uid in (s["finder_id"], s["claimant_id"]):
        await notify(uid, "handover", "Item returned", f"'{item['title']}' has been returned. Receipt {receipt['receipt_no']}.", f"/receipts/{receipt['id']}")
    await audit(actor, "handover.completed", "handover", s["id"], {"method": method, "receipt": receipt["receipt_no"], "reason": reason})
    return receipt


@router.post("/handovers/scan")
async def scan(body: ScanIn, user: dict = Depends(require_active)):
    if body.token:
        s = await db.handover_sessions.find_one({"token_hash": sha256(body.token)}, {"_id": 0})
        method = "qr"
    elif body.handover_id and body.code:
        s = await db.handover_sessions.find_one({"id": body.handover_id, "code_hash": sha256(f"{body.handover_id}:{body.code.strip()}")}, {"_id": 0})
        method = "code"
    else:
        raise HTTPException(400, "Provide a QR token or a handover ID with confirmation code")
    if not s:
        await audit(user["id"], "handover.scan_invalid", "handover", body.handover_id, {"method": "qr" if body.token else "code"})
        raise HTTPException(400, "Invalid, expired or already-used handover code")
    if user["id"] != s["claimant_id"]:
        await audit(user["id"], "handover.scan_unauthorized", "handover", s["id"])
        raise HTTPException(403, "Only the approved claimant can confirm receipt with this code")
    if s["status"] != "active" or s.get("token_used"):
        raise HTTPException(409, "This handover code has already been used")
    if (parse_dt(s.get("token_expires_at")) or now()) <= now():
        raise HTTPException(410, "This handover code has expired. Ask the finder to generate a new one.")
    res = await db.handover_sessions.update_one({"id": s["id"], "token_used": False, "status": "active"}, {
        "$set": {"token_used": True, "claimant_confirmed_at": iso(), "token_hash": None, "code_hash": None},
        "$push": {"events": {"event": "claimant.confirmed", "at": iso(), "by": user["id"], "method": method}}})
    if res.modified_count == 0:
        raise HTTPException(409, "This handover code has already been used")
    await audit(user["id"], "handover.claimant_confirmed", "handover", s["id"], {"method": method})
    s = await db.handover_sessions.find_one({"id": s["id"]}, {"_id": 0})
    if s.get("finder_confirmed_at"):
        receipt = await _complete(s, user["id"], method)
        return {"status": "completed", "handover_id": s["id"], "receipt_id": receipt["id"]}
    await notify(s["finder_id"], "handover", "Owner confirmed receipt", "The owner scanned your code. Confirm the handover to finish.", f"/handover/{s['id']}")
    return {"status": "awaiting_finder", "handover_id": s["id"]}


@router.post("/handovers/{handover_id}/finder-confirm")
async def finder_confirm(handover_id: str, user: dict = Depends(require_active)):
    s = await _session_for(handover_id, user)
    if user["id"] != s["finder_id"]:
        raise HTTPException(403, "Only the finder can confirm handing over the item")
    if s["status"] != "active":
        raise HTTPException(409, f"Handover is {s['status']}")
    if s.get("finder_confirmed_at"):
        raise HTTPException(409, "You have already confirmed")
    await db.handover_sessions.update_one({"id": handover_id}, {"$set": {"finder_confirmed_at": iso()},
                                                                 "$push": {"events": {"event": "finder.confirmed", "at": iso(), "by": user["id"]}}})
    await audit(user["id"], "handover.finder_confirmed", "handover", handover_id)
    s = await db.handover_sessions.find_one({"id": handover_id}, {"_id": 0})
    if s.get("claimant_confirmed_at"):
        receipt = await _complete(s, user["id"], s["events"][-2].get("method", "qr") if len(s["events"]) > 1 else "qr")
        return {"status": "completed", "receipt_id": receipt["id"]}
    return {"status": "awaiting_claimant"}


@router.post("/handovers/{handover_id}/cancel")
async def cancel_handover(handover_id: str, user: dict = Depends(get_current_user)):
    s = await _session_for(handover_id, user)
    if s["status"] != "active":
        raise HTTPException(409, f"Handover is {s['status']}")
    claim = await db.claims.find_one({"id": s["claim_id"]}, {"_id": 0})
    await _cancel_sessions(s["claim_id"], user["id"])
    await claim_history(s["claim_id"], "cancelled", user["id"], "Handover cancelled")
    await _reset_after_claim(claim, user["id"], "Handover cancelled")
    other = s["claimant_id"] if user["id"] == s["finder_id"] else s["finder_id"]
    await notify(other, "handover", "Handover cancelled", "A pending handover was cancelled.", f"/handover/{handover_id}")
    return {"ok": True}


@router.post("/admin/handovers/{handover_id}/complete")
async def admin_complete(handover_id: str, body: AdminCompleteIn, admin: dict = Depends(require_admin)):
    s = await db.handover_sessions.find_one({"id": handover_id}, {"_id": 0})
    if not s:
        raise HTTPException(404, "Handover not found")
    receipt = await _complete(s, admin["id"], "admin_assisted", body.reason)
    return {"status": "completed", "receipt_id": receipt["id"]}


@router.get("/receipts/mine")
async def my_receipts(user: dict = Depends(get_current_user)):
    return await db.handover_receipts.find({"$or": [{"finder_id": user["id"]}, {"claimant_id": user["id"]}]}, {"_id": 0}).sort("completed_at", -1).to_list(200)


@router.get("/receipts/{receipt_id}")
async def get_receipt(receipt_id: str, user: dict = Depends(get_current_user)):
    r = await db.handover_receipts.find_one({"id": receipt_id}, {"_id": 0})
    if not r:
        raise HTTPException(404, "Receipt not found")
    if user["id"] not in (r["finder_id"], r["claimant_id"]) and user.get("role") != "admin":
        raise HTTPException(403, "Not your receipt")
    names = {u["id"]: u["name"] async for u in db.users.find({"id": {"$in": [r["finder_id"], r["claimant_id"]]}}, {"_id": 0, "id": 1, "name": 1})}
    return {**r, "finder_name": names.get(r["finder_id"]), "claimant_name": names.get(r["claimant_id"]), "my_story_opt_out": user["id"] in r.get("story_opt_out", [])}


@router.post("/receipts/{receipt_id}/story")
async def story_pref(receipt_id: str, body: StoryIn, user: dict = Depends(get_current_user)):
    r = await db.handover_receipts.find_one({"id": receipt_id}, {"_id": 0})
    if not r or user["id"] not in (r["finder_id"], r["claimant_id"]):
        raise HTTPException(404, "Receipt not found")
    op = {"$addToSet": {"story_opt_out": user["id"]}} if body.opt_out else {"$pull": {"story_opt_out": user["id"]}}
    await db.handover_receipts.update_one({"id": receipt_id}, op)
    return {"ok": True}
