# Back2U — PRD

## Original problem statement
"MASTER PROMPT: Build Back2U — An Intelligent Campus Lost & Found Web Platform" (full brief from the customer): a responsive web app only (no native app) where students report lost items (I LOST IT) and found items (I FOUND IT). It needs ML categorization, an intelligent matching engine (0-100 score with explanation and configurable weights), duplicate detection, hidden ownership clues with secure claim verification and rate limits, watchlists with in-app notifications, secure single-use QR handovers that need two-party confirmation and produce receipts, a status lifecycle (LOST → … → RETURNED/CLOSED), a community feed with real stats, an admin dashboard (moderation, suspend/ban, appeals, audit, locations), a mandatory Responsible Use Policy, info pages, README, .env.example, tests. Section 20 asked for a professional footer based on reference images, plus a Contact Us form.

## User choices
- JWT email/password auth, with admin and demo accounts
- Local ML: TF-IDF character/word n-grams plus logistic regression, no external API
- Email domain restriction set through ALLOWED_EMAIL_DOMAINS (empty means any domain)
- Emergent object storage for photos
- Reference-image footer feature (section 20, including Contact Us): "dont add this feature". The footer is kept simple, with the section 5 links.

## Architecture
React (CRA + shadcn + Tailwind) → FastAPI (/api; core.py, ml.py, routes_items/claims/misc/admin.py) → MongoDB. Object storage is reached through the Emergent proxy. Seed script: backend/seed.py.

## Personas
Student who lost an item; student who found one; campus administrator/moderator.

## Implemented (2026-10-12)
- Auth: register (policy checkbox, version and timestamp recorded), login with brute-force lockout, demo-login for demo students only, protected routes, role guards, suspension/ban enforced on the backend.
- Lost/found forms with ML category prediction (shows confidence, user can override), photo upload, preview step and duplicate dialog. Policy acknowledgement is required before the first report.
- Matching engine with reasons and breakdown, relevant/irrelevant feedback, notifications. Matches are recalculated when a report is edited.
- Private clues and claim verification scoring. Limit of 3 attempts per item per day. Automated flag goes to human review.
- Claim review (start verification / approve / reject / cancel). QR and 6-digit code handover: hashed, single-use, 30-minute expiry. Both parties must confirm. Admin-assisted fallback. Receipts with an option to opt out of success stories.
- Watchlists (CRUD, threshold, notifications without duplicates), notifications page, notification preference controls.
- Community feed, home page sections, stats from the database, anonymized recoveries.
- Admin dashboard: stats, misuse reports, users (warn/suspend/ban/reinstate), claims, handovers, appeals, items, locations, audit log.
- Info pages (about, how-it-works, safety, policy, privacy, terms, help), report-misuse page, simple footer.
- README, .env.example, unit tests (backend/tests).

## Implemented (2026-10-12) — Photo matching
- A pretrained MobileNetV2 image model (run locally) plus colour histograms turn each photo into features once, when it is uploaded. Older photos were backfilled on startup.
- When both reports have photos, photo similarity counts for 20% of the match score and the other factors are scaled down. It is also used in duplicate warnings and in watchlists that have a reference photo. The matches panel shows a "Photo similarity" bar. Photo similarity is never treated as proof of ownership.
- Photo storage now retries once when the storage service has a temporary error.

## Implemented (2026-10-12) — Photo search
- Browse page has a "Search by photo" button (students must be logged in). The photo is not saved. It is compared against the photo features of active reports, takes about 0.3 seconds, respects the lost/found filter, and shows a "% alike" badge with a note that looking alike is not proof of ownership.

## Implemented (2026-10-12) — Snap to Report
- Photo search results now always offer "I lost this" / "I found this" ("No visually similar items found" when empty, "Not what you're looking for?" otherwise). The photo is saved only when the student picks one, and it is then attached to the new lost or found report form.

## Implemented (2026-10-12) — Photo autofill
- When a report starts from a snapped photo, the image model suggests a category (only above 30% confidence) and colours. The "Suggested from your photo" card shows what the model saw. The student can override everything, and the text model refines the category once a title is typed.

## Backlog
- P1: email verification and email notifications
- P2: admin-managed categories (needs classifier retraining); FastAPI lifespan migration; explicit CORS origins

## Next tasks
Act on the user's feedback after they review the MVP.
