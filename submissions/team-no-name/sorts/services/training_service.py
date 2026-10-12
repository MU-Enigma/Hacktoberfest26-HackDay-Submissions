import logging
from typing import List
from sqlalchemy.orm import Session
from sorts.database import models as db_models

logger = logging.getLogger(__name__)


class TrainingService:
    """Automated Self-Training Engine.
    
    Ingests student feedback deltas from 'Am I wrong?' interest reconfigurations
    and updates club trait weights via online gradient adjustment.
    """

    LEARNING_RATE = 0.05

    def _calculate_decayed_lr(self, db: Session, club_id: int) -> float:
        """Calculates a decayed learning rate based on historical feedback count to stabilize established weights."""
        feedback_count = (
            db.query(db_models.Feedback)
            .join(db_models.Recommendation)
            .filter(db_models.Recommendation.club_id == club_id)
            .count()
        )
        return round(self.LEARNING_RATE / (1.0 + 0.1 * feedback_count), 4)

    def process_feedback_deltas(
        self,
        db: Session,
        session_id: str,
        added_interests: List[str],
        removed_interests: List[str]
    ) -> None:
        """Applies online self-training adjustments to club trait matrices based on user feedback."""
        if not added_interests and not removed_interests:
            return

        session = db.query(db_models.RecommendationSession).filter_by(id=session_id).first()
        if not session or not session.recommendations:
            return

        # Get top recommended clubs for this session
        top_club_ids = [r.club_id for r in session.recommendations[:3]]
        clubs = db.query(db_models.Club).filter(db_models.Club.id.in_(top_club_ids)).all()

        all_traits = db.query(db_models.Trait).all()
        trait_map = {t.slug: t for t in all_traits}

        adjusted_count = 0

        for club in clubs:
            lr = self._calculate_decayed_lr(db, club.id)

            # 1. Reinforce added interests with decayed learning rate
            for slug in added_interests:
                if slug in trait_map:
                    t_obj = trait_map[slug]
                    ct = db.query(db_models.ClubTrait).filter_by(club_id=club.id, trait_id=t_obj.id).first()
                    if not ct:
                        ct = db_models.ClubTrait(club_id=club.id, trait_id=t_obj.id, weight=0.0)
                        db.add(ct)
                    
                    old_w = ct.weight
                    ct.weight = min(1.0, round(ct.weight + lr, 3))
                    logger.info(f"[SELF_TRAINING] Reinforced club '{club.name}' trait '{slug}' (lr={lr:.4f}): {old_w:.2f} -> {ct.weight:.2f}")
                    adjusted_count += 1

            # 2. Decay removed interests with decayed learning rate
            for slug in removed_interests:
                if slug in trait_map:
                    t_obj = trait_map[slug]
                    ct = db.query(db_models.ClubTrait).filter_by(club_id=club.id, trait_id=t_obj.id).first()
                    if ct:
                        old_w = ct.weight
                        ct.weight = max(0.0, round(ct.weight - lr, 3))
                        logger.info(f"[SELF_TRAINING] Decayed club '{club.name}' trait '{slug}' (lr={lr:.4f}): {old_w:.2f} -> {ct.weight:.2f}")
                        adjusted_count += 1

        db.commit()
        logger.info(f"[SELF_TRAINING_ENGINE] Session {session_id}: Processed {adjusted_count} weight adjustments for {len(clubs)} clubs.")
