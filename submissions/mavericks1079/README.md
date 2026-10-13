# Back2U — Intelligent Campus Lost & Found

## Team

**Team name:** MAVERICKS 1079

### Members

- Shantanu Srivastava — [@shantanusrivastava18](https://github.com/shantanusrivastava18)
- [@TRGsci](https://github.com/TRGsci)
- [@tanmaychakradhari](https://github.com/tanmaychakradhari)

## Problem

Every semester, students at Mahindra University lose everyday belongings such as ID cards, keys, earphones, water bottles, wallets, calculators and bags. The campus is large, with academic blocks, many hostels, dining halls, sports grounds and parking areas spread across it. A lost item can be in any of dozens of places.

Today there is no trustworthy, central way to get these items back. Students post on notice boards and WhatsApp groups, where messages get buried and the same item is reported many times. Anyone who finds something has no clear person to hand it to or way to reach the owner. These channels are also unsafe, because there is no way to check who really owns an item. A person can claim something that isn't theirs, and valuable things like phones, wallets and ID cards can end up with the wrong person. Nothing records who handed what to whom, so disputes are hard to settle.

The result is that:

- Owners lose items they could have recovered.
- Finders don't know what to do with what they find.
- Campus staff waste time answering the same questions.

## Solution

**Back2U** is a web app where students report items they lost or found, using the actual campus locations from the Mahindra University map (Library, Hostel 4A, Dining-1, Soccer Field and so on). It gives the campus one trusted place to report, match and return belongings.

How it works:

1. **Report.** A student chooses "I Lost It" or "I Found It" and fills in the title, description, colour, date and photos. The location is picked from the real campus locations. The app suggests a category from the text and can autofill details from a photo.
2. **Duplicate check.** Before a report is submitted, the app warns if a very similar report already exists.
3. **Smart matching.** Each lost report is compared with found reports and given a score from 0 to 100 with the reasons behind it. The score combines description similarity (35%), category (20%), colour and attributes (15%), location (15%) and date (15%). When both reports have photos, a photo comparison is included.
4. **Watchlists and notifications.** Students can save keywords, a category or locations and get an in-app notification when a matching report appears.
5. **Secure ownership claim.** A finder can add hidden details (for example a sticker or an engraving) that are never shown publicly. Someone claiming the item must answer questions about them, and claim attempts per day are limited.
6. **Safe handover.** After a claim is approved, a single-use QR code that expires in 30 minutes is created. Both people confirm the handover and the app produces a receipt. Items move through clear statuses: Lost, Found, Match Found, Claim Pending, Verification in Progress, Ready for Handover, Returned and Closed.
7. **Safety and administration.** Every user accepts a Responsible Use Policy and can report misuse. Admins can moderate reports, suspend or ban users, handle appeals, manage locations and review an audit log.

**Impact:** faster recoveries, fewer duplicate reports, verified ownership, a receipt and audit trail for every handover, and less repeated work for campus staff.

## Technologies used

- **Frontend:** React, Tailwind CSS, shadcn/ui, React Router
- **Backend:** Python, FastAPI, Uvicorn
- **Database:** MongoDB (Motor async driver)
- **Machine learning:** TF-IDF text similarity (matching, category prediction), MobileNetV2 via ONNX Runtime (photo similarity and photo autofill)
- **Security:** JWT authentication, bcrypt password hashing, hidden private clues, rate-limited claims, hashed single-use handover tokens, audit logging
- **Testing:** Pytest
- **AI / LLM tools:** Emergent, ChatGPT

## How to run

**Requirements:** Python 3.11, Node.js with Yarn, and a running MongoDB instance.

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd <repo-folder>

# 2. Backend (runs on port 8001)
cd backend
pip install -r requirements.txt
cp .env.example .env
#   Open .env and fill in:
#   MONGO_URL, DB_NAME, JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD,
#   DEMO_PASSWORD, EMERGENT_LLM_KEY (needed for photo uploads)
uvicorn server:app --host 0.0.0.0 --port 8001

# 3. Optional: add sample items (run after the backend has started once)
python seed.py

# 4. Frontend (runs on port 3000) - open a second terminal
cd frontend
yarn install
#   Create frontend/.env with:
#   REACT_APP_BACKEND_URL=http://localhost:8001
yarn start

# 5. Run the tests (backend must be running)
cd backend
python -m pytest tests -q
```

Then open http://localhost:3000.

On startup the backend creates the admin account from `ADMIN_EMAIL` / `ADMIN_PASSWORD`, three demo students (`alice@campus.edu`, `bob@campus.edu`, `carol@campus.edu`, password from `DEMO_PASSWORD`) and the campus map locations. The login page has a demo-login button for the student accounts.

## Demo

- **Demo link:** Will add soon
- **Screenshots / video:** Will add soon

## Notes

- **Photo uploads** use Emergent's object storage, so they need a valid `EMERGENT_LLM_KEY`. Without it, the rest of the app still works but photo uploads fail.
- **Locations** come from the Mahindra University campus map. They are listed in `DEFAULT_LOCATIONS` in `backend/server.py` and synced to the database on startup. Admins can add more from the admin dashboard.
- **Photo similarity** is only a hint and is never treated as proof of ownership. Private clues are never used in matching.
- **Never commit `.env` files.** Use `backend/.env.example` as the template.
- **Future ideas:** email or SMS notifications, a mobile app, an interactive campus map for picking locations, integration with university ID login, and a better image model for detecting items like keys and ID cards.
