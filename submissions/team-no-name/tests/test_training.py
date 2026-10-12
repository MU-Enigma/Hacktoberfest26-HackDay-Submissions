import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sorts.database.connection import Base
from sorts.database import models as db_models
from sorts.services.training_service import TrainingService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed basic university, trait, club, session, recommendation
    univ = db_models.University(name="Test University", slug="test_univ", website="https://test.edu")
    session.add(univ)
    session.commit()

    t_software = db_models.Trait(slug="software", name="Software", description="Coding", category="Domain")
    session.add(t_software)
    session.commit()

    club = db_models.Club(university_id=univ.id, name="Coding Club", slug="coding_club", summary="Coding club", description="Coding club desc")
    session.add(club)
    session.commit()

    rec_session = db_models.RecommendationSession(id=str(uuid.uuid4()), university_id=univ.id, user_identifier="user_123")
    session.add(rec_session)
    session.commit()

    rec = db_models.Recommendation(session_id=rec_session.id, club_id=club.id, rank=1, score=0.8, explanation="Test")
    session.add(rec)
    session.commit()

    yield session
    session.close()


def test_self_training_reinforcement(db_session):
    training_svc = TrainingService()
    session_obj = db_session.query(db_models.RecommendationSession).first()

    # Apply positive gradient reinforcement for 'software' trait
    training_svc.process_feedback_deltas(
        db=db_session,
        session_id=session_obj.id,
        added_interests=["software"],
        removed_interests=[]
    )

    club_trait = db_session.query(db_models.ClubTrait).first()
    assert club_trait is not None
    assert club_trait.weight == 0.05
