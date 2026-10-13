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

# Locations taken from the Mahindra University campus map: (name, zone, is_safe_point)
DEFAULT_LOCATIONS = [
    # Vineet Nayyar Academic Block
    ("Library", "Vineet Nayyar Academic Block", True),
    ("Centre for Sustainability", "Vineet Nayyar Academic Block", False),
    ("School of Design Innovation", "Vineet Nayyar Academic Block", False),
    ("School of Hospitality Management", "Vineet Nayyar Academic Block", False),
    ("Culinary", "Vineet Nayyar Academic Block", False),
    ("Aero Space", "Vineet Nayyar Academic Block", False),
    # Academic Blocks
    ("Classrooms", "Academic Blocks", False),
    ("Centre for Executive Education", "Academic Blocks", False),
    ("Centre for Life Sciences", "Academic Blocks", False),
    ("AIC Mahindra", "Academic Blocks", False),
    ("Little Scholars Academy", "Academic Blocks", False),
    ("Indra Mahindra School of Education", "Academic Blocks", False),
    ("School of Management", "Academic Blocks", False),
    ("School of Media & Digital Communication", "Academic Blocks", False),
    # Engineering
    ("Ecole Centrale School of Engineering", "Engineering", False),
    ("CAIR Labs", "Engineering", False),
    ("Fluid Mechanics Robotics", "Engineering", False),
    ("Workshops", "Engineering", False),
    # Hostels
    ("Hostel 1", "Hostels", False), ("Hostel 2", "Hostels", False), ("Hostel 3", "Hostels", False),
    ("Hostel 4A", "Hostels", False), ("Hostel 4B", "Hostels", False),
    ("Studio Apartment", "Hostels", False), ("Evolve Center", "Hostels", False),
    ("Shivalik Hostel", "Hostels-5", False), ("Ajantha Hostel", "Hostels-5", False), ("Vindhya Hostel", "Hostels-5", False),
    ("Himalaya Hostel", "Hostels-5", False), ("Aravali Hostel", "Hostels-5", False), ("Satpura Hostel", "Hostels-5", False),
    ("Nilgiri Hostel", "Hostels-5", False), ("Kailash Hostel", "Hostels-5", False),
    # Residential
    ("Guest House", "Residential", False), ("Residential Bungalows", "Residential", False),
    # Dining & amenities
    ("Dining-1", "Dining & Amenities", False), ("Dining-2", "Dining & Amenities", False), ("Dining-3", "Dining & Amenities", False),
    ("Cafe", "Dining & Amenities", False), ("Shopping Complex", "Dining & Amenities", False),
    ("Health Care Centre", "Dining & Amenities", True),
    # Sports
    ("Soccer Field", "Sports", False), ("Shuttle Court", "Sports", False), ("Swimming Pool", "Sports", False),
    # Convention & NCC
    ("Convention Centre", "Convention & NCC", False), ("NCC Office", "Convention & NCC", False),
    # Parking & utilities
    ("MLCP", "Parking & Utilities", False),
    ("Parking (Academic Blocks)", "Parking & Utilities", False), ("Parking (Soccer Field)", "Parking & Utilities", False),
    ("Parking (Convention Centre)", "Parking & Utilities", False),
    ("Infra Office", "Parking & Utilities", True), ("Power House-1", "Parking & Utilities", False),
]
# Old placeholder locations that get removed on startup
LEGACY_LOCATIONS = [
    "Central Library", "Library Reading Room", "Lecture Hall Complex", "Computer Science Block", "Main Cafeteria",
    "Student Activity Centre", "Sports Complex", "Gymnasium", "Boys Hostel A", "Girls Hostel B", "Main Gate",
    "Parking Lot", "Campus Security Office", "Admin Building",
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
    # Keep the locations list in sync with the campus map (removes legacy placeholders, adds/updates map locations;
    # locations added manually by an admin are left untouched).
    await db.locations.delete_many({"name": {"$in": LEGACY_LOCATIONS}})
    for n, z, s in DEFAULT_LOCATIONS:
        await db.locations.update_one({"name": n}, {"$set": {"zone": z, "is_safe_point": s},
                                      "$setOnInsert": {"id": new_id(), "created_at": iso()}}, upsert=True)
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

