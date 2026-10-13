"""Back2U ML: TF-IDF (char + word n-grams) + logistic regression categorizer, and weighted matching."""
import re
from datetime import datetime, timezone

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.metrics.pairwise import cosine_similarity

from image_ml import best_similarity

CATEGORIES = {
    "electronics": "Electronics",
    "id_cards": "ID cards & access cards",
    "wallets": "Wallets & purses",
    "keys": "Keys",
    "bags": "Bags & backpacks",
    "books": "Books & stationery",
    "clothing": "Clothing & accessories",
    "bottles": "Bottles & containers",
    "jewelry": "Jewelry",
    "other": "Other",
}

TRAINING = {
    "electronics": [
        "wireless earbuds in white charging case", "airpods pro case lost", "iphone with cracked screen",
        "samsung galaxy phone blue cover", "laptop charger usb-c power adapter", "macbook air silver laptop",
        "bluetooth headphones over ear sony", "power bank 10000mah", "smart watch black strap", "ipad tablet with pencil",
        "phone charger cable white", "calculator casio scientific fx-991", "usb flash drive pendrive 32gb",
        "mouse wireless logitech", "earphones wired black", "kindle e-reader", "noise cancelling headset",
        "graphing calculator texas instruments", "android phone in pink case", "laptop dell inspiron grey",
    ],
    "id_cards": [
        "student id card with photo", "university identity card", "library card", "access card for hostel",
        "college id badge with lanyard", "rfid access card dorm", "driving licence card", "aadhaar card",
        "staff id card blue lanyard", "metro card travel pass", "bus pass student", "lab access swipe card",
        "id card holder with name", "identity badge clip", "exam hall ticket admit card",
    ],
    "wallets": [
        "brown leather wallet with cards", "black wallet bifold", "purse with zip coins", "pink clutch purse",
        "card holder wallet slim", "wallet containing cash and debit card", "small coin pouch", "ladies handbag purse red",
        "money clip wallet", "velcro wallet blue", "trifold wallet canvas", "wallet with bank cards inside",
    ],
    "keys": [
        "bunch of keys with keychain", "room key with red tag", "car key toyota remote", "bike lock key",
        "house keys on ring", "locker key number tag", "keychain with three keys", "scooter key honda",
        "hostel room keys", "key fob with carabiner", "single silver key", "padlock key small",
    ],
    "bags": [
        "black backpack with laptop compartment", "blue school bag", "tote bag canvas", "gym duffel bag",
        "sling bag grey", "laptop bag messenger", "drawstring bag sports", "rucksack wildcraft red",
        "jansport backpack navy", "handbag leather brown", "travel bag trolley", "lunch bag insulated",
    ],
    "books": [
        "physics textbook hc verma", "notebook with lecture notes", "spiral notebook blue cover", "novel paperback",
        "pencil box with pens", "geometry box compass", "engineering drawing sheets", "lab record file",
        "diary journal leather", "calculus textbook", "highlighters and sticky notes", "register notebook ruled",
        "library book returned late", "fountain pen parker", "folder with assignment papers",
    ],
    "clothing": [
        "black hoodie jacket", "denim jacket blue", "umbrella black foldable", "sunglasses rayban",
        "cap baseball hat", "scarf woolen red", "sweater grey", "spectacles glasses frame", "gloves winter",
        "sports shoes nike", "raincoat yellow", "watch analog leather strap", "belt brown leather", "lab coat white",
    ],
    "bottles": [
        "steel water bottle", "milton flask blue", "plastic water bottle", "thermos coffee flask", "lunch box tiffin",
        "hydro flask green bottle", "tupperware container", "sipper bottle with straw", "glass bottle", "coffee mug travel",
        "insulated tumbler", "shaker bottle gym protein",
    ],
    "jewelry": [
        "gold ring", "silver necklace chain", "earrings pearl", "bracelet beaded", "engagement ring diamond",
        "pendant locket", "anklet silver", "nose pin gold", "bangle", "chain with pendant", "stud earrings", "charm bracelet",
    ],
    "other": [
        "badminton racket", "cricket bat", "guitar pick", "toy", "medicine box", "umbrella stand", "plant pot",
        "basketball", "yoga mat", "skateboard", "frisbee", "musical instrument case", "football",
    ],
}

RELATED = {frozenset(p) for p in [("wallets", "id_cards"), ("bags", "clothing"), ("jewelry", "clothing"), ("electronics", "bags"), ("books", "bags")]}

COLORS = ["black", "white", "red", "blue", "navy", "green", "yellow", "orange", "purple", "pink", "brown", "grey", "gray",
          "silver", "gold", "beige", "maroon", "teal", "transparent"]

# Configurable matching weights (sum = 1.0).
MATCH_WEIGHTS = {"description": 0.35, "category": 0.20, "attributes": 0.15, "location": 0.15, "date": 0.15}
# When both reports have photos, image similarity takes this share and the others are scaled down proportionally.
IMAGE_WEIGHT = 0.20
UNCERTAIN_THRESHOLD = 0.30
MATCH_THRESHOLD = 45
DUPLICATE_THRESHOLD = 70

_texts, _labels = [], []
for cat, examples in TRAINING.items():
    for ex in examples:
        _texts.append(ex)
        _labels.append(cat)

_char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)
_word = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)
classifier = Pipeline([
    ("features", FeatureUnion([("char", _char), ("word", _word)])),
    ("clf", LogisticRegression(C=10, max_iter=3000)),
])
classifier.fit(_texts, _labels)
_sim_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True).fit(_texts)


def predict_category(title: str, description: str = "") -> dict:
    text = f"{title} {title} {description}".lower().strip()
    probs = classifier.predict_proba([text])[0]
    classes = classifier.classes_
    order = np.argsort(probs)[::-1]
    top = [{"category": classes[i], "label": CATEGORIES[classes[i]], "probability": round(float(probs[i]), 3)} for i in order[:3]]
    best = top[0]
    uncertain = best["probability"] < UNCERTAIN_THRESHOLD
    return {
        "category": "other" if uncertain else best["category"],
        "model_top": best["category"],
        "confidence": best["probability"],
        "uncertain": uncertain,
        "top": top,
        "model": "TF-IDF char(2-5)+word(1-2) n-grams -> multinomial logistic regression",
    }


def text_sim(a: str, b: str) -> float:
    a, b = (a or "").lower().strip(), (b or "").lower().strip()
    if not a or not b:
        return 0.0
    m = _sim_vec.transform([a, b])
    return float(cosine_similarity(m[0], m[1])[0][0])


def tokens(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2}


def extract_colors(text: str) -> set:
    found = tokens(text) & set(COLORS)
    return {"grey" if c == "gray" else c for c in found}


def _public_text(item: dict) -> str:
    return " ".join(str(item.get(k) or "") for k in ("title", "description", "color", "attributes"))


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a and b) else 0.0


def location_sim(a: str, b: str, zones: dict) -> float:
    if not a or not b:
        return 0.3
    if a.strip().lower() == b.strip().lower():
        return 1.0
    za, zb = zones.get(a), zones.get(b)
    if za and zb and za == zb:
        return 0.6
    return min(0.4, text_sim(a, b))


def _days(a, b):
    def p(v):
        if not v:
            return None
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    da, db_ = p(a), p(b)
    if not da or not db_:
        return None
    return (db_ - da).total_seconds() / 86400


def date_sim(lost_at, found_at, mode="match") -> float:
    d = _days(lost_at, found_at)
    if d is None:
        return 0.4
    if mode == "duplicate":
        return max(0.0, 1 - abs(d) / 3)
    if d < -1:
        return 0.0
    return max(0.0, 1 - max(d, 0) / 14)


def score_pair(a: dict, b: dict, zones: dict, mode: str = "match") -> dict:
    """a, b are item dicts (public fields only). mode=match compares lost (a) vs found (b)."""
    desc = 0.6 * text_sim(_public_text(a), _public_text(b)) + 0.4 * text_sim(a.get("title"), b.get("title"))
    desc = min(1.0, desc * 1.4)
    ca, cb = a.get("category"), b.get("category")
    cat = 1.0 if ca == cb else (0.5 if frozenset((ca, cb)) in RELATED else 0.0)
    cola, colb = extract_colors(_public_text(a)), extract_colors(_public_text(b))
    if cola and colb:
        attr = 0.7 * _jaccard(cola, colb) + 0.3 * _jaccard(tokens(a.get("attributes")), tokens(b.get("attributes")))
    else:
        attr = 0.4
    loc = location_sim(a.get("location"), b.get("location"), zones)
    dt = date_sim(a.get("occurred_at"), b.get("occurred_at"), mode)
    parts = {"description": desc, "category": cat, "attributes": attr, "location": loc, "date": dt}
    weights = dict(MATCH_WEIGHTS)
    img = best_similarity(a.get("_img") or [], b.get("_img") or [])
    if img is not None:
        weights = {k: v * (1 - IMAGE_WEIGHT) for k, v in weights.items()}
        weights["image"] = IMAGE_WEIGHT
        parts["image"] = img
    score = round(100 * sum(weights[k] * v for k, v in parts.items()))
    reasons = []
    if img is not None and img >= 0.6:
        reasons.append("Photos look visually similar (not proof of ownership)")
    elif img is not None and img < 0.3:
        reasons.append("Photos look visually different")
    if desc >= 0.5:
        reasons.append("Descriptions and titles are semantically similar")
    if cat == 1.0:
        reasons.append(f"Same category ({CATEGORIES.get(ca, ca)})")
    elif cat == 0.5:
        reasons.append("Related categories")
    shared = cola & colb
    if shared:
        reasons.append(f"Shared colour: {', '.join(sorted(shared))}")
    if loc >= 1.0:
        reasons.append(f"Same location ({a.get('location')})")
    elif loc >= 0.6:
        reasons.append("Locations are in the same campus zone")
    if dt >= 0.7:
        reasons.append("Dates are close together")
    elif dt == 0.0 and mode == "match":
        reasons.append("Found before it was reported lost (unlikely)")
    return {"score": max(0, min(100, score)), "breakdown": {k: round(v, 3) for k, v in parts.items()}, "reasons": reasons,
            "weights": {k: round(v, 3) for k, v in weights.items()}}


def verify_claim(answer: str, clues: str) -> int:
    """Score 0-100 of how well a claimant's independent details match the finder's private clues."""
    if not answer or not clues:
        return 0
    clue_tokens = tokens(clues)
    recall = len(clue_tokens & tokens(answer)) / len(clue_tokens) if clue_tokens else 0
    return round(100 * min(1.0, 0.5 * text_sim(answer, clues) * 1.3 + 0.5 * recall))


def watchlist_score(wl: dict, item: dict, zones: dict) -> int:
    text = _public_text(item)
    parts, weights = [], []
    if wl.get("keywords"):
        kw = tokens(wl["keywords"])
        overlap = len(kw & tokens(text)) / len(kw) if kw else 0
        parts.append(max(overlap, min(1.0, text_sim(wl["keywords"], text) * 1.6)))
        weights.append(0.45)
    if wl.get("category"):
        parts.append(1.0 if wl["category"] == item.get("category") else 0.0)
        weights.append(0.25)
    if wl.get("color"):
        parts.append(1.0 if extract_colors(wl["color"]) & extract_colors(text) else 0.0)
        weights.append(0.15)
    if wl.get("locations"):
        parts.append(max(location_sim(l, item.get("location"), zones) for l in wl["locations"]))
        weights.append(0.15)
    img = best_similarity(wl.get("_img") or [], item.get("_img") or [])
    if img is not None:
        parts.append(img)
        weights.append(0.20)
    if not weights:
        return 0
    return round(100 * sum(p * w for p, w in zip(parts, weights)) / sum(weights))
