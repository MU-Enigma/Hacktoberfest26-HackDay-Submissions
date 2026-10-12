import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sorts.database.connection import Base
from sorts.database import models as db_models
from sorts.services.seed_service import seed_database
from sorts.services.session_service import SessionService
from sorts.services.import_service import ImportService
from sorts.services.club_service import ClubService

# Setup an in-memory SQLite database for testing services
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_database_seeding_and_session_flow(db_session):
    seed_file = "sorts/assets/data/mahindra_seed.json"
    assert os.path.exists(seed_file), "Seed file is required for verification."
    
    # 1. Run Seeder
    seed_database(db_session, seed_file)
    
    # Verify university seeded
    univ = db_session.query(db_models.University).filter_by(slug="mahindra").first()
    assert univ is not None
    assert univ.name == "Mahindra University"
    
    # Verify traits and questions seeded
    traits_count = db_session.query(db_models.Trait).count()
    assert traits_count > 0
    questions_count = db_session.query(db_models.Question).count()
    assert questions_count > 0

    # 1.5 Run import & publish to populate clubs in DB
    import_svc = ImportService()
    source = db_session.query(db_models.ImportSource).first()
    job_id = import_svc.trigger_import(db_session, source.id)
    import_svc.publish_job(db_session, job_id)

    # 2. Run Recommendation Session Flow via SessionService
    session_svc = SessionService()
    session = session_svc.create_session(db_session, univ.id, user_identifier="test_user_123")
    assert session.id is not None
    assert session.status == "active"

    # Answer all questions in sequence
    loop_limit = 20
    answered_count = 0
    while answered_count < loop_limit:
        next_q = session_svc.get_next_question(db_session, session.id)
        if not next_q:
            break
            
        # Select first option
        option = next_q.options[0]
        session_svc.submit_answer(db_session, session.id, next_q.id, option.id)
        answered_count += 1
        
    assert answered_count > 0
    
    # Generate recommendations
    recs = session_svc.generate_recommendations(db_session, session.id, limit=3)
    assert len(recs) > 0
    assert recs[0].rank == 1
    assert recs[0].score >= 0.0
    assert len(recs[0].explanation) > 0

    # Verify session marked completed
    db_session.refresh(session)
    assert session.status == "completed"
    assert session.completed_at is not None


def test_crawler_import_and_publish_flow(db_session):
    # Seed university metadata first
    seed_file = "sorts/assets/data/mahindra_seed.json"
    seed_database(db_session, seed_file)

    import_svc = ImportService()
    
    # Fetch import source
    source = db_session.query(db_models.ImportSource).first()
    assert source is not None
    
    # 1. Run Import (crawls the local HTML file)
    job_id = import_svc.trigger_import(db_session, source.id)
    assert job_id > 0
    
    job = import_svc.get_job(db_session, job_id)
    assert job.status == "completed"

    # Verify draft clubs were created
    drafts = db_session.query(db_models.DraftClub).filter_by(import_job_id=job_id).all()
    assert len(drafts) > 0
    
    # Check that Enigma or Electrowizards exists in drafts
    draft_names = {d.name for d in drafts}
    assert "Enigma" in draft_names or "Electrowizards" in draft_names

    # Check traits are mapped in drafts
    draft_c = drafts[0]
    assert len(draft_c.traits) > 0

    # 2. Publish drafts
    import_svc.publish_job(db_session, job_id)
    
    # Verify job marked approved
    db_session.refresh(job)
    assert job.status == "approved"
    
    # Verify clubs are active in the university directory
    clubs = db_session.query(db_models.Club).filter_by(university_id=source.university_id).all()
    assert len(clubs) > 0
    
    active_club_names = {c.name for c in clubs}
    assert "Enigma" in active_club_names
    
    # Check that traits exist on the published clubs
    active_c = db_session.query(db_models.Club).filter_by(name="Enigma").first()
    assert len(active_c.traits) > 0
    assert active_c.traits[0].weight > 0.0
