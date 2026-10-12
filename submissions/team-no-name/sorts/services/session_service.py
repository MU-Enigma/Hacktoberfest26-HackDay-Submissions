import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
import logging

from sorts.core.domain.exceptions import SessionNotFoundException, QuestionNotFoundException
from sorts.core.domain import entities as domain_ent
from sorts.core.recommendation.deterministic_engine import DeterministicRecommendationEngine
from sorts.core.recommendation.explanation_generator import ExplanationGenerator
from sorts.core.questions.variance_selector import VarianceQuestionSelector
from sorts.database import models as db_models

logger = logging.getLogger(__name__)

class SessionService:
    def __init__(self):
        self.question_selector = VarianceQuestionSelector()
        self.explanation_generator = ExplanationGenerator()

    def create_session(self, db: Session, university_id: int, user_identifier: Optional[str] = None) -> db_models.RecommendationSession:
        """Creates a new recommendation session for a student."""
        session_id = str(uuid.uuid4())
        session = db_models.RecommendationSession(
            id=session_id,
            university_id=university_id,
            user_identifier=user_identifier,
            status="active",
            created_at=datetime.utcnow()
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"Created session {session_id} for university {university_id}")
        return session

    def get_session(self, db: Session, session_id: str) -> Optional[db_models.RecommendationSession]:
        return db.query(db_models.RecommendationSession).filter_by(id=session_id).first()

    def get_next_question(self, db: Session, session_id: str) -> Optional[db_models.Question]:
        """Returns the next question dynamically chosen to bisect the remaining candidate pool.
        The tree traversal length depends entirely on user responses and confidence convergence.
        """
        session = self.get_session(db, session_id)
        if not session:
            raise SessionNotFoundException(session_id)

        # 1. Fetch answered question IDs
        answered_q_ids = [ans.question_id for ans in session.answers]

        # 2. Get unasked questions
        unasked_db_questions = db.query(db_models.Question)\
            .filter(db_models.Question.university_id == session.university_id)\
            .filter(~db_models.Question.id.in_(answered_q_ids) if answered_q_ids else True)\
            .all()

        if not unasked_db_questions:
            return None

        # 3. Get all clubs for candidate comparison
        db_clubs = db.query(db_models.Club).filter_by(university_id=session.university_id).all()
        if not db_clubs:
            return unasked_db_questions[0]

        domain_clubs = [self._map_club(c) for c in db_clubs]
        session_traits = {st.trait.slug: st.value for st in session.traits}

        # 4. Calculate current scores for all candidate clubs
        scores = self.question_selector._calculate_scores(session_traits, domain_clubs)
        club_scores = list(zip(domain_clubs, scores))
        club_scores.sort(key=lambda cs: cs[1], reverse=True)

        num_answered = len(answered_q_ids)

        # 1. Soft cap at 8 questions maximum
        if num_answered >= 8:
            logger.info(f"Session {session_id}: Reached soft 8 questions cap. Finishing tree.")
            return None

        # 2. Dynamic Convergence Check (3 to 8 questions)
        if num_answered >= 3:
            top_score = club_scores[0][1] if club_scores else 0.0
            second_score = club_scores[1][1] if len(club_scores) > 1 else 0.0
            margin = top_score - second_score

            # Stop if user denied all traits (all scores 0.0)
            if top_score <= 0.0:
                logger.info(f"Session {session_id}: User denied all traits after {num_answered} questions. Finishing tree.")
                return None

            # Fast exit (3-5 questions): top match is clear (top_score >= 0.45 AND margin >= 0.15)
            if top_score >= 0.45 and margin >= 0.15:
                logger.info(f"Session {session_id}: Adaptive decision tree convergence reached after {num_answered} questions (Top: {top_score:.2f}, Margin: {margin:.2f}). Finishing tree.")
                return None

            # Exit at 6+ questions if any positive match exists
            if num_answered >= 6 and top_score > 0.10:
                logger.info(f"Session {session_id}: Exit at {num_answered} questions with top score {top_score:.2f}.")
                return None

        # 6. Filter candidate pool for next question selection to current viable clubs (score > 0.0)
        viable_candidates = [c for c, s in club_scores if s > 0.0]
        if not viable_candidates:
            viable_candidates = domain_clubs

        # 7. Map DB models to Domain models
        domain_questions = [self._map_question(q) for q in unasked_db_questions]

        # 8. Select next question that maximizes information gain specifically over viable candidates
        selected_domain_q = self.question_selector.select_next_question(
            domain_questions, session_traits, viable_candidates
        )

        if not selected_domain_q:
            return None

        return db.query(db_models.Question).filter_by(id=selected_domain_q.id).first()

    def submit_answer(self, db: Session, session_id: str, question_id: int, option_id: int) -> None:
        """Saves a student's answer and adjusts session traits based on option modifiers."""
        session = self.get_session(db, session_id)
        if not session:
            raise SessionNotFoundException(session_id)

        db_option = db.query(db_models.QuestionOption).filter_by(id=option_id, question_id=question_id).first()
        if not db_option:
            raise ValueError(f"Option {option_id} does not belong to question {question_id}.")

        # Log answer
        ans = db_models.SessionAnswer(
            session_id=session_id,
            question_id=question_id,
            option_id=option_id,
            answered_at=datetime.utcnow()
        )
        db.add(ans)

        # Apply trait modifiers
        for mod in db_option.trait_modifiers:
            st = db.query(db_models.SessionTrait).filter_by(session_id=session_id, trait_id=mod.trait_id).first()
            if not st:
                st = db_models.SessionTrait(
                    session_id=session_id,
                    trait_id=mod.trait_id,
                    value=0.0
                )
                db.add(st)
            # Add modifier weight to session trait value, clamped to [-1.0, 1.0]
            st.value = max(-1.0, min(1.0, st.value + mod.weight))
        
        db.commit()
        logger.debug(f"Submitted answer for session {session_id}, question {question_id}, option {option_id}")

    def generate_recommendations(self, db: Session, session_id: str, limit: int = 6) -> List[db_models.Recommendation]:
        """Calculates final recommendations, generates explanations, saves top limit (default 6), and closes the session."""
        session = self.get_session(db, session_id)
        if not session:
            raise SessionNotFoundException(session_id)

        # Fetch traits and clubs
        db_clubs = db.query(db_models.Club).filter_by(university_id=session.university_id).all()
        db_traits = db.query(db_models.Trait).all()
        
        trait_names = {t.slug: t.name for t in db_traits}
        recommender = DeterministicRecommendationEngine(trait_names=trait_names)

        # Map to domain
        session_traits = {st.trait.slug: st.value for st in session.traits}
        domain_clubs = [self._map_club(c) for c in db_clubs]

        # Calculate recommendations
        evidence_list = recommender.calculate_recommendations(session_traits, domain_clubs)

        # Exclude existing recommendations for this session (clear previous runs)
        db.query(db_models.Recommendation).filter_by(session_id=session_id).delete()

        # Create final recommendations
        db_recs = []
        for index, ev in enumerate(evidence_list[:limit]):
            explanation = self.explanation_generator.generate_explanation(ev)
            rec = db_models.Recommendation(
                session_id=session_id,
                club_id=ev.club_id,
                rank=index + 1,
                score=ev.overall_score,
                explanation=explanation
            )
            db.add(rec)
            db_recs.append(rec)

        session.status = "completed"
        session.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Generated {len(db_recs)} recommendations for session {session_id}")
        return db_recs

    def _map_question(self, q: db_models.Question) -> domain_ent.Question:
        options = []
    def _map_question(self, q: db_models.Question) -> domain_ent.Question:
        options = []
        for opt in q.options:
            modifiers = [
                domain_ent.OptionTraitModifier(
                    trait_slug=mod.trait.slug,
                    weight=mod.weight
                ) for mod in opt.trait_modifiers
            ]
            options.append(domain_ent.QuestionOption(
                id=opt.id,
                text=opt.text,
                trait_modifiers=modifiers
            ))
        return domain_ent.Question(
            id=q.id,
            text=q.text,
            code=q.code if hasattr(q, 'code') else f"q_{q.id}",
            university_id=q.university_id,
            options=options
        )

    def _map_club(self, c: db_models.Club) -> domain_ent.Club:
        traits = [
            domain_ent.ClubTraitValue(
                trait_slug=ct.trait.slug,
                weight=ct.weight
            ) for ct in c.traits
        ]
        return domain_ent.Club(
            id=c.id,
            university_id=c.university_id,
            name=c.name,
            slug=c.slug,
            summary=c.summary,
            description=c.description,
            traits=traits
        )
