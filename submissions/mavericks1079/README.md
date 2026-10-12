# Back2U — Intelligent Campus Lost & Found (web app)

Responsive website (React + FastAPI + MongoDB) that helps students report lost/found items, get ML-ranked matches, verify ownership with private clues, and complete secure two-party QR handovers with receipts.

## Run
```
# backend (port 8001)
cd backend && pip install -r requirements.txt
cp .env.example .env   # fill values
uvicorn server:app --host 0.0.0.0 --port 8001
python seed.py          # optional sample items (needs object storage key)
# frontend (port 3000)
cd frontend && yarn install && yarn start   # set REACT_APP_BACKEND_URL in frontend/.env
# tests
cd backend && python -m pytest tests -q
```
Admin + demo users are seeded on startup from env (`ADMIN_EMAIL/ADMIN_PASSWORD`, demo students `alice|bob|carol@campus.edu` with `DEMO_PASSWORD`; the login page has a demo-login button for students only).

## Architecture
- `backend/core.py` – Mongo client, JWT auth (bcrypt, 8h bearer/httpOnly cookie), role & suspension guards (`require_active`, `require_admin`), audit log, notifications, object storage.
- `backend/ml.py` – categorizer + matching + claim verification + watchlist scoring.
- `backend/routes_items.py` – items, uploads, duplicate check, matches. `routes_claims.py` – claims, handovers, receipts. `routes_misc.py` – auth, profile, watchlists, notifications, feed/stats, abuse reports, appeals. `routes_admin.py` – moderation dashboard APIs.
- `frontend/src/pages/*` – React pages; shadcn/ui components; Tailwind.

## Data model (MongoDB collections)
users, policy_acceptances, items (with status_history), item_private_clues (never returned publicly), item_matches, claims, claim_verification_attempts, watchlists, notifications (unique dedupe_key), handover_sessions (hashed token/code), handover_receipts, audit_logs, moderation_reports, moderation_actions, appeals, locations, files, login_attempts. Indexes are created in `server.py` startup.

## ML
- **Categorizer**: TF-IDF char (2-5) + word (1-2) n-grams → multinomial logistic regression trained on ~140 labelled campus item phrases at startup. Returns top-3 probabilities; if confidence < 0.30 the suggestion falls back to "Other" and the user is asked to choose. Users can always override; final and predicted categories are both stored.
- **Matching** (`score_pair`, weights in `MATCH_WEIGHTS`): description/title cosine similarity on char n-gram TF-IDF (35%), category compatibility incl. related categories (20%), colour/attribute overlap (15%), location (same=1, same zone=0.6) (15%), date compatibility (found must not precede lost; decays over 14 days) (15%). Score 0-100 with reasons. Threshold 45 for matches, 70 for duplicate warnings. Self-matches and RETURNED/CLOSED items are excluded; private clues are never used.
- **Photo matching** (`image_ml.py`): pretrained MobileNetV2 (ONNX, ImageNet, `backend/models/mobilenetv2.onnx`, run with onnxruntime on CPU) → sqrt-softmax embedding (cosine, 75%) + HSV colour-histogram intersection (25%). Features are computed once at upload and stored on the `files` record, so matching is a fast vector comparison (older photos are backfilled on startup). When both reports have photos, image similarity gets `IMAGE_WEIGHT` = 20% and the other weights scale to 80%; otherwise the text-only weights apply. Used in matches, duplicate warnings and watchlists with a reference photo. Visual similarity is never proof of ownership.
- **Photo search** (`POST /api/items/photo-search`, logged-in users): an uploaded photo (not stored) is embedded the same way and compared with stored photo features of active reports; results with ≥30% similarity are ranked on the Browse page.
- **Photo autofill** (`photo_autofill.py`, `POST /api/ml/photo-suggest {path}`, own uploads only): when a report starts from a snapped photo, MobileNetV2 ImageNet labels are mapped to Back2U categories (suggested only if mapped probability ≥ 30%; ImageNet has no "keys"/"ID card" classes so those are never photo-suggested), and the dominant object colour is found by mapping centre pixels to a named palette minus the background (border) distribution. Text prediction refines the category once a title is typed unless it is uncertain.
- **Claim verification**: claimant details vs finder's private clues (char cosine + clue-token recall) → score shown only to the finder/admin. 3 attempts/item/24h. Repeated low scores create an automated moderation flag for human review (no auto-ban).

## Handover security
Approval creates a session. The finder generates a `secrets.token_urlsafe(32)` token (QR holds only `/handover/scan?t=<token>`) and a 6-digit code; only SHA-256 hashes are stored, expiry 30 min, regenerating invalidates the old one. Only the approved claimant can redeem it, once (atomic update). The item becomes RETURNED only when both the claimant redemption and the finder confirmation exist; completion is atomic and idempotent. Admin-assisted completion requires a reason and is audited.

## Known limitations
- Email verification is not implemented (accounts show "not verified"). No email notifications.
- Image similarity uses ImageNet MobileNetV2 features (not fine-tuned on campus items). ML categories are fixed (admin view is read-only).
- Policy, privacy and terms text require university/legal review before production use.
- Demo-login endpoint must be removed or disabled for production.
