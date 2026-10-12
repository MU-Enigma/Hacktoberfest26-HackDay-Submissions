from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

import os  # noqa: E402
import asyncio  # noqa: E402
import logging  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from core import db, client, init_storage, hash_password, verify_password, iso, new_id, POLICY_VERSION  # noqa: E402
import routes_items  # noqa: E402
import routes_claims  # noqa: E402
import routes_misc  # noqa: E402
import routes_admin  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("back2u")

app = FastAPI(title="Back2U API")
for r in (routes_items.router, routes_claims.router, routes_misc.router, routes_admin.router):
    app.include_router(r)


@app.get("/api/")
async def root():
    return {"message": "Back2U API", "policy_version": POLICY_VERSION}


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_LOCATIONS = [
    ("Central Library", "Academic Core", True), ("Library Reading Room", "Academic Core", False), ("Lecture Hall Complex", "Academic Core", False),
    ("Computer Science Block", "Academic Core", False), ("Main Cafeteria", "Student Life", False), ("Student Activity Centre", "Student Life", False),
    ("Sports Complex", "Sports", False), ("Gymnasium", "Sports", False), ("Boys Hostel A", "Residential", False), ("Girls Hostel B", "Residential", False),
    ("Main Gate", "Perimeter", False), ("Parking Lot", "Perimeter", False), ("Campus Security Office", "Admin", True), ("Admin Building", "Admin", True),
]


async def ensure_user(email, password, name, role, is_demo=False):
    existing = await db.users.find_one({"email": email})
    if existing is None:
        await db.users.insert_one({"id": new_id(), "email": email, "password_hash": hash_password(password), "name": name, "role": role,
                                   "status": "active", "email_verified": False, "policy_version": POLICY_VERSION, "policy_accepted_at": iso(),
                                   "report_policy_ack": True, "is_demo": is_demo,
                                   "notification_prefs": {"matches": True, "claims": True, "watchlist": True}, "created_at": iso()})
    elif not verify_password(password, existing["password_hash"]):
        await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(password)}})


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.items.create_index("id", unique=True)
    await db.items.create_index([("type", 1), ("status", 1), ("created_at", -1)])
    await db.items.create_index("owner_id")
    await db.item_private_clues.create_index("item_id", unique=True)
    await db.item_matches.create_index([("lost_id", 1), ("found_id", 1)], unique=True)
    await db.claims.create_index([("item_id", 1), ("claimant_id", 1)])
    await db.claim_verification_attempts.create_index([("user_id", 1), ("item_id", 1), ("created_at", -1)])
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.notifications.create_index("dedupe_key", unique=True, partialFilterExpression={"dedupe_key": {"$type": "string"}})
    await db.handover_sessions.create_index("token_hash")
    await db.handover_receipts.create_index("handover_id", unique=True)
    await db.audit_logs.create_index("created_at")
    await db.login_attempts.create_index("identifier")
    await db.locations.create_index("name", unique=True)
    if await db.locations.count_documents({}) == 0:
        await db.locations.insert_many([{"id": new_id(), "name": n, "zone": z, "is_safe_point": s, "created_at": iso()} for n, z, s in DEFAULT_LOCATIONS])
    await ensure_user(os.environ["ADMIN_EMAIL"].lower(), os.environ["ADMIN_PASSWORD"], "Back2U Admin", "admin")
    demo_pw = os.environ["DEMO_PASSWORD"]
    for email, name in (("alice@campus.edu", "Alice Sharma"), ("bob@campus.edu", "Bob Mathew"), ("carol@campus.edu", "Carol Dsouza")):
        await ensure_user(email, demo_pw, name, "student", is_demo=True)
    try:
        init_storage()
        logger.info("Storage initialized")
        asyncio.create_task(routes_items.backfill_image_embeddings())
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
