import pytest
from sorts.database.connection import get_db, init_db
from sorts.database import models as db_models
from sorts.services.seed_service import seed_database, ensure_qubit_club_seeded
from sorts.services.club_service import ClubService

@pytest.fixture
def test_db():
    init_db()
    with get_db() as db:
        seed_database(db, "sorts/assets/data/mahindra_seed.json")
        ensure_qubit_club_seeded(db)
        yield db

def test_qubit_club_seeded_and_searchable(test_db):
    univ = test_db.query(db_models.University).filter_by(slug="mahindra").first()
    assert univ is not None

    qubit = test_db.query(db_models.Club).filter_by(university_id=univ.id, slug="qubit-club").first()
    assert qubit is not None
    assert qubit.name == "Qubit Club"
    assert qubit.commitment == "Medium commitment"
    assert "quantum computing" in qubit.summary.lower()

    # Verify search via aliases
    service = ClubService()
    
    matches_qubit = service.search_clubs(test_db, univ.id, "qubit")
    assert len(matches_qubit) >= 1
    assert any(c.name == "Qubit Club" for c in matches_qubit)

    matches_quantum = service.search_clubs(test_db, univ.id, "quantum")
    assert len(matches_quantum) >= 1
    assert any(c.name == "Qubit Club" for c in matches_quantum)

    matches_qiskit = service.search_clubs(test_db, univ.id, "qiskit")
    assert len(matches_qiskit) >= 1
    assert any(c.name == "Qubit Club" for c in matches_qiskit)

    matches_qc = service.search_clubs(test_db, univ.id, "quantum computing")
    assert len(matches_qc) >= 1
    assert any(c.name == "Qubit Club" for c in matches_qc)
