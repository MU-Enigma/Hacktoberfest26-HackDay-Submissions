import pytest
from sorts.database.connection import get_db, init_db
from sorts.database import models as db_models
from sorts.services.seed_service import seed_database, sync_verified_clubs
from sorts.services.club_service import ClubService

@pytest.fixture
def test_db():
    init_db()
    with get_db() as db:
        seed_database(db, "sorts/assets/data/mahindra_seed.json")
        sync_verified_clubs(db)
        yield db

def test_verified_registry_total_count(test_db):
    univ = test_db.query(db_models.University).filter_by(slug="mahindra").first()
    assert univ is not None

    clubs = test_db.query(db_models.Club).filter_by(university_id=univ.id).all()
    assert len(clubs) == 50

def test_duplicate_merges_and_alias_searches(test_db):
    univ = test_db.query(db_models.University).filter_by(slug="mahindra").first()
    service = ClubService()

    # 1. Erudite / Literary search
    res_erudite = service.search_clubs(test_db, univ.id, "erudite")
    assert len(res_erudite) >= 1
    assert "Erudite" in res_erudite[0].name

    res_literary = service.search_clubs(test_db, univ.id, "literary")
    assert len(res_literary) >= 1
    assert "Literary" in res_literary[0].name or "Erudite" in res_literary[0].name

    # 2. Outreach / Community service search
    res_outreach = service.search_clubs(test_db, univ.id, "outreach")
    assert len(res_outreach) >= 1
    assert "Outreach" in res_outreach[0].name

    # 3. BAJA search
    res_baja = service.search_clubs(test_db, univ.id, "baja")
    assert len(res_baja) >= 1
    assert "BAJA" in res_baja[0].name

def test_newly_verified_clubs(test_db):
    univ = test_db.query(db_models.University).filter_by(slug="mahindra").first()
    service = ClubService()

    # AI Club
    res_ai = service.search_clubs(test_db, univ.id, "ai club")
    assert len(res_ai) >= 1
    assert res_ai[0].name == "AI Club"
    assert res_ai[0].official is False
    assert res_ai[0].get_verification()["confidence"] == 75

    # Econova
    res_eco = service.search_clubs(test_db, univ.id, "econova")
    assert len(res_eco) >= 1
    assert res_eco[0].name == "Econova"

    # MasterShot
    res_master = service.search_clubs(test_db, univ.id, "mastershot")
    assert len(res_master) >= 1
    assert "MasterShot" in res_master[0].name

    # C-Cube-E
    res_ccube = service.search_clubs(test_db, univ.id, "ccube")
    assert len(res_ccube) >= 1
    assert "C-Cube-E" in res_ccube[0].name
