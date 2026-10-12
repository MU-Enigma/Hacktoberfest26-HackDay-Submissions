import json
import logging
from typing import Dict, Any, Tuple

from sorts.database.connection import get_db
from sorts.database import models as db_models
from sorts.services.club_service import ClubService
from sorts.services.session_service import SessionService

logger = logging.getLogger("sortling.api")


def handle_api_request(path: str, method: str, params: Dict[str, Any], body_data: Dict[str, Any]) -> Tuple[int, dict]:
    """Handles REST API requests from Devvit webroot app or external clients."""
    with get_db() as db:
        # 1. GET /api/university
        if path == "/api/university" and method == "GET":
            sub = params.get("subreddit", [None])[0]
            slug = params.get("slug", [None])[0]

            univ = None
            if sub:
                clean_sub = sub.strip().lstrip("r/").lower()
                all_univs = db.query(db_models.University).all()
                univ = next(
                    (u for u in all_univs if getattr(u, "reddit_subreddit", None) and getattr(u, "reddit_subreddit", "").strip().lstrip("r/").lower() == clean_sub),
                    None,
                )
            if not univ and slug:
                univ = db.query(db_models.University).filter_by(slug=slug).first()

            if not univ:
                from sorts.config.settings import DEFAULT_UNIVERSITY_SLUG
                univ = db.query(db_models.University).filter_by(slug=DEFAULT_UNIVERSITY_SLUG).first()

            if not univ:
                univ = db.query(db_models.University).first()

            if not univ:
                return 404, {"error": "University not found"}

            return 200, {
                "id": univ.id,
                "slug": univ.slug,
                "name": univ.name,
                "website": univ.website,
                "description": univ.description,
                "reddit_subreddit": getattr(univ, "reddit_subreddit", None),
            }

        # 2. GET /api/clubs
        if path == "/api/clubs" and method == "GET":
            univ_id_param = params.get("university_id", [1])[0]
            try:
                univ_id = int(univ_id_param)
            except ValueError:
                univ_id = 1

            query = params.get("query", [""])[0]

            service = ClubService()
            if query:
                clubs = service.search_clubs(db, univ_id, query)
            else:
                clubs, _ = service.get_clubs_paginated(db, univ_id, page=1, per_page=50)

            return 200, {
                "count": len(clubs),
                "clubs": [c.to_schema_dict() for c in clubs],
            }

        # 3. GET /api/events
        if path == "/api/events" and method == "GET":
            univ_id_param = params.get("university_id", [1])[0]
            try:
                univ_id = int(univ_id_param)
            except ValueError:
                univ_id = 1

            events = (
                db.query(db_models.Event)
                .filter_by(university_id=univ_id)
                .order_by(db_models.Event.id.desc())
                .all()
            )
            return 200, {
                "count": len(events),
                "events": [
                    {
                        "id": e.id,
                        "name": e.name,
                        "slug": e.slug,
                        "organizer": e.organizer,
                        "category": e.category,
                        "summary": e.summary,
                        "description": e.description,
                        "prizes": e.prizes,
                        "registration_deadline": e.registration_deadline,
                        "event_date": e.event_date,
                        "team_rules": e.team_rules,
                        "registration_link": e.registration_link,
                        "email_required": e.email_required,
                    }
                    for e in events
                ],
            }

        # 4. POST /api/sort/session OR /api/sessions/start (Start quiz session)
        if path in ("/api/sort/session", "/api/sessions/start") and method == "POST":
            univ_id = int(body_data.get("university_id", 1))
            user_id = body_data.get("user_id", "reddit_user")

            session_svc = SessionService()
            session = session_svc.create_session(db, univ_id, user_identifier=user_id)
            first_q = session_svc.get_next_question(db, session.id)

            if not first_q:
                return 400, {"error": "No questions available"}

            return 200, {
                "session_id": session.id,
                "question": {
                    "id": first_q.id,
                    "code": first_q.code,
                    "text": first_q.text,
                    "options": [{"id": o.id, "text": o.text} for o in first_q.options],
                },
            }

        # 5. POST /api/sort/answer OR /api/sessions/answer (Submit answer)
        if path in ("/api/sort/answer", "/api/sessions/answer") and method == "POST":
            session_id = body_data.get("session_id")
            question_id_raw = body_data.get("question_id")
            option_id_raw = body_data.get("option_id")
            selected_option_idx = body_data.get("selected_option_index")

            if not session_id or question_id_raw is None:
                return 400, {"error": "Missing session_id or question_id"}

            session_svc = SessionService()
            question_id = int(question_id_raw)

            # Resolve option_id if passed as selected_option_index
            option_id = None
            if option_id_raw is not None:
                option_id = int(option_id_raw)
            elif selected_option_idx is not None:
                curr_q = db.query(db_models.Question).filter_by(id=question_id).first()
                if curr_q and 0 <= int(selected_option_idx) < len(curr_q.options):
                    option_id = curr_q.options[int(selected_option_idx)].id

            if option_id is None:
                return 400, {"error": "Invalid option selection"}

            session_svc.submit_answer(db, session_id, question_id, option_id)

            next_q = session_svc.get_next_question(db, session_id)
            if next_q:
                q_dict = {
                    "id": next_q.id,
                    "code": next_q.code,
                    "text": next_q.text,
                    "options": [{"id": o.id, "text": o.text} for o in next_q.options],
                }
                return 200, {
                    "completed": False,
                    "is_complete": False,
                    "session_id": session_id,
                    "question": q_dict,
                    "next_question": q_dict,
                }

            # Convergence reached - generate top 3 recommendations
            recs = session_svc.generate_recommendations(db, session_id, limit=3)
            rec_list = [
                {
                    "rank": r.rank,
                    "score": round(r.score, 2),
                    "explanation": r.explanation,
                    "club_name": r.club.name if r.club else "Campus Club",
                    "club": r.club.to_schema_dict() if r.club else None,
                }
                for r in recs
            ]
            return 200, {
                "completed": True,
                "is_complete": True,
                "recommendations": rec_list,
            }

        return 404, {"error": "Endpoint not found"}
