"""Seed demo items: python seed.py (run once after the backend has started so users/locations exist)."""
import asyncio
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import requests  # noqa: E402
from core import db, now, iso, new_id, put_object, APP_NAME  # noqa: E402
from routes_items import ItemIn, create_item_internal  # noqa: E402

IMG = {
    "wallet": "https://images.unsplash.com/photo-1627123424574-724758594e93?w=800&q=80",
    "earbuds": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=800&q=80",
    "keys": "https://images.unsplash.com/photo-1575908539614-ff89490f4a78?w=800&q=80",
    "bottle": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=800&q=80",
    "calculator": "https://images.unsplash.com/photo-1648201637025-1c77b9be3013?w=800&q=80",
    "backpack": "https://images.unsplash.com/photo-1622560481979-f5b0174242a0?w=800&q=80",
}


async def store_image(key, owner_id):
    data = requests.get(IMG[key], timeout=60).content
    res = put_object(f"{APP_NAME}/seed/{key}.jpg", data, "image/jpeg")
    await db.files.update_one({"storage_path": res["path"]}, {"$setOnInsert": {"id": new_id(), "storage_path": res["path"], "owner_id": owner_id,
                              "content_type": "image/jpeg", "size": len(data), "is_deleted": False, "created_at": iso()}}, upsert=True)
    return res["path"]


def ago(days, hours=0):
    return (now() - timedelta(days=days, hours=hours)).isoformat()


async def main():
    if await db.items.count_documents({"seed": True}):
        print("Seed items already present")
        return
    users = {u["email"]: u["id"] async for u in db.users.find({}, {"email": 1, "id": 1})}
    alice, bob, carol = users["alice@campus.edu"], users["bob@campus.edu"], users["carol@campus.edu"]
    specs = [
        (alice, "earbuds", dict(type="lost", title="White wireless earbuds case", description="Lost my white earbuds in a charging case, probably left on a desk.",
              category="electronics", color="white", attributes="charging case, small scratch on lid", location="Library", occurred_at=ago(2),
              private_clues="sticker of a blue star inside the lid; left earbud has a tiny chip", contact_pref="in_app", collection_pref="Infra Office")),
        (bob, "earbuds", dict(type="found", title="Earbuds in white charging case", description="Found a white wireless earbuds charging case on a reading table.",
              category="electronics", color="white", attributes="charging case", location="Centre for Sustainability", occurred_at=ago(1, 20),
              private_clues="blue star sticker inside lid, chip on left earbud", secure_collection_location="Infra Office, counter 2",
              collection_window="Weekdays 10:00-17:00", holder="office", notes_for_owner="Handed to campus security.")),
        (carol, "wallet", dict(type="found", title="Brown leather wallet", description="Brown leather bifold wallet found near the cafeteria billing counter.",
              category="wallets", color="brown", attributes="bifold, worn edges", location="Dining-1", occurred_at=ago(1),
              private_clues="contains a metro card and a photo of a dog", secure_collection_location="Infra Office, Room 104",
              collection_window="Mon-Fri 9:00-16:00", holder="office")),
        (bob, "keys", dict(type="lost", title="Bunch of keys with red tag", description="Three silver keys on a ring with a red plastic tag, lost after gym.",
              category="keys", color="silver red", attributes="three keys, red tag", location="Soccer Field", occurred_at=ago(3),
              private_clues="tag has room number 214 written", contact_pref="in_app")),
        (alice, "bottle", dict(type="found", title="Green steel water bottle", description="Matte green insulated steel water bottle left in lecture hall row 5.",
              category="bottles", color="green", attributes="insulated, matte finish", location="Classrooms", occurred_at=ago(0, 6),
              private_clues="dent at the bottom, initials R.K. scratched near base", secure_collection_location="With finder - meet at Library entrance",
              collection_window="Evenings after 17:00", holder="finder")),
        (carol, "calculator", dict(type="lost", title="Casio scientific calculator", description="Lost my Casio fx-991 scientific calculator during the maths exam.",
              category="electronics", color="black", attributes="fx-991, cover missing", location="Centre for Life Sciences", occurred_at=ago(4),
              private_clues="name engraved on back", contact_pref="in_app")),
        (alice, "backpack", dict(type="lost", title="Black backpack", description="Black backpack with laptop compartment and a water bottle pocket.",
              category="bags", color="black", attributes="laptop compartment", location="Convention Centre", occurred_at=ago(5),
              private_clues="keychain of a small panda on zipper", contact_pref="in_app")),
    ]
    for owner, img, spec in specs:
        path = await store_image(img, owner)
        item = await create_item_internal(ItemIn(**spec, image_paths=[path]), owner)
        await db.items.update_one({"id": item["id"]}, {"$set": {"seed": True}})
        print("Seeded", spec["title"])


if __name__ == "__main__":
    asyncio.run(main())
