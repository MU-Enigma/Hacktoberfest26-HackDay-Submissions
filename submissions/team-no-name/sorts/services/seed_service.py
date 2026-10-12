import os
import json
import logging
from sqlalchemy.orm import Session
from sorts.database.models import (
    University, ImportSource, Trait, Question, QuestionOption, OptionTraitModifier
)

logger = logging.getLogger(__name__)

_GLOBAL_DEFAULTS_PATH = "sorts/assets/data/global_defaults.json"


def seed_global_traits(db: Session) -> None:
    """Seeds the universal trait vocabulary into the database.

    Traits are shared across all universities — they define the vector space
    used by the recommendation engine.  Safe to call on every boot; skips
    any trait that already exists.
    """
    if not os.path.exists(_GLOBAL_DEFAULTS_PATH):
        logger.warning(f"global_defaults.json not found at {_GLOBAL_DEFAULTS_PATH}. Skipping trait seed.")
        return

    with open(_GLOBAL_DEFAULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    seeded = 0
    for trait_data in data.get("traits", []):
        existing = db.query(Trait).filter_by(slug=trait_data["slug"]).first()
        if not existing:
            db.add(Trait(
                slug=trait_data["slug"],
                name=trait_data["name"],
                description=trait_data["description"],
                category=trait_data["category"],
            ))
            seeded += 1
    db.commit()
    if seeded:
        logger.info(f"Seeded {seeded} global traits.")
    else:
        logger.debug("Global traits already present. Skipping.")


def seed_default_questions(db: Session, university_id: int) -> int:
    """Seeds the universal question bank for a university that has just been set up.

    Loads questions from global_defaults.json and clones them (with their
    options and trait modifiers) into the given university.  Idempotent —
    skips questions whose code already exists for that university.

    Returns the number of questions actually created.
    """
    if not os.path.exists(_GLOBAL_DEFAULTS_PATH):
        logger.warning(f"global_defaults.json not found at {_GLOBAL_DEFAULTS_PATH}. Skipping question seed.")
        return 0

    with open(_GLOBAL_DEFAULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build slug → Trait.id map for modifier FK lookups
    slug_to_trait_id = {
        t.slug: t.id
        for t in db.query(Trait).all()
    }

    created = 0
    for q_data in data.get("questions", []):
        existing = db.query(Question).filter_by(
            university_id=university_id, code=q_data["code"]
        ).first()
        if existing:
            continue

        question = Question(
            university_id=university_id,
            text=q_data["text"],
            code=q_data["code"],
        )
        db.add(question)
        db.commit()
        db.refresh(question)

        for opt_data in q_data.get("options", []):
            option = QuestionOption(question_id=question.id, text=opt_data["text"])
            db.add(option)
            db.commit()
            db.refresh(option)

            for trait_slug, weight in opt_data.get("trait_modifiers", {}).items():
                trait_id = slug_to_trait_id.get(trait_slug)
                if trait_id:
                    db.add(OptionTraitModifier(
                        option_id=option.id,
                        trait_id=trait_id,
                        weight=weight,
                    ))
        db.commit()
        created += 1

    logger.info(f"Seeded {created} default questions for university_id={university_id}.")
    return created


def seed_database(db: Session, seed_filepath: str) -> None:
    """Seeds the database with university, traits, questions, and import sources from a JSON file."""
    if not os.path.exists(seed_filepath):
        logger.error(f"Seed file not found: {seed_filepath}")
        return

    logger.info(f"Seeding database from: {seed_filepath}")
    with open(seed_filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Seed University
    univ_data = data["university"]
    db_univ = db.query(University).filter_by(slug=univ_data["slug"]).first()
    if not db_univ:
        db_univ = University(
            slug=univ_data["slug"],
            name=univ_data["name"],
            website=univ_data["website"],
            logo=univ_data.get("logo"),
            primary_color=univ_data.get("primary_color"),
            secondary_color=univ_data.get("secondary_color"),
            description=univ_data.get("description"),
        )
        db_univ.set_metadata(univ_data.get("metadata", {}))
        db.add(db_univ)
        db.commit()
        db.refresh(db_univ)
        logger.info(f"Seeded university: {db_univ.name} (ID: {db_univ.id})")
    else:
        logger.info(f"University '{univ_data['name']}' already exists. Skipping.")

    # 2. Seed Import Sources
    for src in data.get("import_sources", []):
        db_src = db.query(ImportSource).filter_by(university_id=db_univ.id, url=src["url"]).first()
        if not db_src:
            db_src = ImportSource(
                university_id=db_univ.id,
                name=src["name"],
                source_type=src["source_type"],
                url=src["url"],
            )
            db_src.set_parser_config(src.get("parser_config", {}))
            db.add(db_src)
            logger.info(f"Seeded import source: {db_src.name}")
    db.commit()

    # 3. Seed Traits
    slug_to_trait_id = {}
    for trait_data in data.get("traits", []):
        db_trait = db.query(Trait).filter_by(slug=trait_data["slug"]).first()
        if not db_trait:
            db_trait = Trait(
                slug=trait_data["slug"],
                name=trait_data["name"],
                description=trait_data["description"],
                category=trait_data["category"],
            )
            db.add(db_trait)
            db.commit()
            db.refresh(db_trait)
            logger.info(f"Seeded trait: {db_trait.slug}")
        else:
            logger.debug(f"Trait '{trait_data['slug']}' already exists. Skipping.")
        slug_to_trait_id[db_trait.slug] = db_trait.id

    # 4. Seed Questions & Options
    for q_data in data.get("questions", []):
        db_q = db.query(Question).filter_by(university_id=db_univ.id, code=q_data["code"]).first()
        if not db_q:
            db_q = Question(
                university_id=db_univ.id,
                text=q_data["text"],
                code=q_data["code"],
            )
            db.add(db_q)
            db.commit()
            db.refresh(db_q)
            logger.info(f"Seeded question: {db_q.code}")

            for opt_data in q_data.get("options", []):
                db_opt = QuestionOption(
                    question_id=db_q.id,
                    text=opt_data["text"],
                )
                db.add(db_opt)
                db.commit()
                db.refresh(db_opt)

                for trait_slug, weight in opt_data.get("trait_modifiers", {}).items():
                    trait_id = slug_to_trait_id.get(trait_slug)
                    if trait_id:
                        db_mod = OptionTraitModifier(
                            option_id=db_opt.id,
                            trait_id=trait_id,
                            weight=weight,
                        )
                        db.add(db_mod)
            db.commit()
            logger.info(f"Seeded options and modifiers for question: {db_q.code}")
        else:
            logger.debug(f"Question '{q_data['code']}' already exists. Skipping.")

    logger.info("Database seeding finished.")

def ensure_qubit_club_seeded(db: Session) -> None:
    """Ensures Qubit Club exists in the database with appropriate trait mappings."""
    from sorts.database import models as db_models

    univ = db.query(db_models.University).filter_by(slug="mahindra").first()
    if not univ:
        return

    qubit = db.query(db_models.Club).filter_by(university_id=univ.id, slug="qubit-club").first()
    if not qubit:
        qubit = db.query(db_models.Club).filter(
            db_models.Club.university_id == univ.id,
            db_models.Club.name.ilike("%Qubit Club%")
        ).first()

    summary_text = (
        "We introduce students to quantum computing through hands-on workshops, technical sessions, "
        "hackathons, and collaborative projects. Members explore quantum algorithms, Qiskit, cloud "
        "quantum platforms, and emerging research while building a strong foundation in quantum technologies."
    )

    desc_text = (
        "Qubit Club is dedicated to introducing students to quantum computing, quantum algorithms, Qiskit, "
        "and cloud quantum platforms. Members participate in technical workshops, R&D projects, hackathons, "
        "and research in mathematics, physics, computer science, artificial intelligence, and emerging technologies. "
        "Best suited for students interested in CS, AI, Math, Physics, and Research."
    )

    if not qubit:
        qubit = db_models.Club(
            university_id=univ.id,
            slug="qubit-club",
            name="Qubit Club",
            summary=summary_text,
            description=desc_text,
            website="https://qubit-mu.github.io",
            discord="https://discord.gg/qubit-mu",
            instagram="https://instagram.com/qubit_mu",
            email="qubit@mahindrauniversity.edu.in",
            meeting_frequency="Weekly sessions",
            commitment="Medium commitment"
        )
        db.add(qubit)
        db.commit()
        db.refresh(qubit)
        logger.info(f"Seeded Qubit Club into database (ID: {qubit.id}).")
    else:
        qubit.summary = summary_text
        qubit.description = desc_text
        qubit.commitment = "Medium commitment"
        db.commit()

    # Map traits for Qubit Club so /sort can naturally recommend it
    trait_weights = {
        "software": 0.9,            # Programming & CS
        "ai_data": 1.0,             # AI, Data Science & Quantum Computing
        "competitive_coding": 0.8, # Algorithms, Qiskit & Hackathons
        "creative": 0.6,            # Emerging Tech & R&D Research
        "commitment_medium": 1.0,  # Medium Commitment
        "social": 0.5               # Workshops & collaborative projects
    }

    for slug, weight in trait_weights.items():
        t_obj = db.query(db_models.Trait).filter_by(slug=slug).first()
        if t_obj:
            ct = db.query(db_models.ClubTrait).filter_by(club_id=qubit.id, trait_id=t_obj.id).first()
            if not ct:
                ct = db_models.ClubTrait(club_id=qubit.id, trait_id=t_obj.id, weight=weight)
                db.add(ct)
            else:
                ct.weight = weight
    db.commit()
    logger.info("Qubit Club trait mappings synchronized.")

def sync_verified_clubs(db: Session) -> None:
    """Synchronizes the database with the verified club registry and merges duplicates."""
    from sorts.database import models as db_models

    univ = db.query(db_models.University).filter_by(slug="mahindra").first()
    if not univ:
        logger.warning("Mahindra University record not found during club sync.")
        return

    # 1. Merge duplicates by deleting redundant duplicate rows
    duplicate_slugs_to_remove = [
        "debate-literary-club-erudite",
        "debate-literary-club",
        "community-service-club-outreach",
        "community-service-club",
        "baja-sae-team"
    ]
    for dup_slug in duplicate_slugs_to_remove:
        dup_club = db.query(db_models.Club).filter_by(university_id=univ.id, slug=dup_slug).first()
        if dup_club:
            logger.info(f"Merging duplicate club '{dup_club.name}' into main registry...")
            db.delete(dup_club)
    db.commit()

    # 2. Load verified dataset
    json_path = "sorts/assets/data/verified_clubs.json"
    if not os.path.exists(json_path):
        logger.error(f"Verified clubs file missing: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        clubs_data = json.load(f)

    logger.info(f"Synchronizing {len(clubs_data)} verified clubs into database...")

    for club_info in clubs_data:
        slug = club_info["slug"]
        db_club = db.query(db_models.Club).filter_by(university_id=univ.id, slug=slug).first()
        if not db_club:
            db_club = db_models.Club(
                university_id=univ.id,
                slug=slug,
                name=club_info["name"],
                summary=club_info["summary"],
                description=club_info["description"],
                category=club_info.get("category", "General"),
                official=club_info.get("official", True),
                meeting_frequency=club_info.get("meeting_frequency", "Bi-weekly sessions"),
                commitment=club_info.get("commitment", "Medium commitment")
            )
            db.add(db_club)
            db.commit()
            db.refresh(db_club)

        # Update attributes
        db_club.name = club_info["name"]
        db_club.summary = club_info["summary"]
        db_club.description = club_info["description"]
        db_club.category = club_info.get("category", "General")
        db_club.official = club_info.get("official", True)
        db_club.meeting_frequency = club_info.get("meeting_frequency", "Bi-weekly sessions")
        db_club.commitment = club_info.get("commitment", "Medium commitment")

        db_club.set_aliases(club_info.get("aliases", []))
        
        ver = club_info.get("verification", {})
        db_club.set_verification(
            confidence=ver.get("confidence", 95 if db_club.official else 75),
            verified=ver.get("verified", True),
            source=ver.get("source", []),
            last_verified=ver.get("lastVerified", "2026-07-19")
        )

        soc = club_info.get("socials", {})
        db_club.set_socials(soc)

        meta = club_info.get("metadata", {})
        db_club.set_club_metadata(
            status=meta.get("status", "active"),
            tags=meta.get("tags", [])
        )
        db.commit()

        # Synchronize trait weights (clear stale traits first)
        db.query(db_models.ClubTrait).filter_by(club_id=db_club.id).delete()
        traits_dict = club_info.get("traits", {})
        for trait_slug, weight in traits_dict.items():
            t_obj = db.query(db_models.Trait).filter_by(slug=trait_slug).first()
            if t_obj:
                ct = db_models.ClubTrait(club_id=db_club.id, trait_id=t_obj.id, weight=weight)
                db.add(ct)
        db.commit()

    total_count = db.query(db_models.Club).filter_by(university_id=univ.id).count()
    logger.info(f"Registry sync complete. Total active clubs: {total_count}")


def sync_verified_events(db: Session) -> None:
    """Synchronizes upcoming campus hackathons, workshops, and opportunities into the database."""
    from sorts.database import models as db_models

    univ = db.query(db_models.University).filter_by(slug="mahindra").first()
    if not univ:
        return

    sih_event = db.query(db_models.Event).filter_by(university_id=univ.id, slug="smart-india-hackathon-2026").first()
    if not sih_event:
        sih_event = db_models.Event(
            university_id=univ.id,
            slug="smart-india-hackathon-2026",
            name="Smart India Hackathon 2026 (Internal Hackathon)",
            organizer="Mahindra University & SIH 2026",
            category="Hackathon",
            summary="BUILD. INNOVATE. REPRESENT MAHINDRA UNIVERSITY.",
            description=(
                "Smart India Hackathon 2026 Internal Hackathon is India's biggest innovation challenge! "
                "Solve real-world problems proposed by Government Ministries, Departments & Industry (around 250 problem statements). "
                "Work with a multidisciplinary team across AI & ML, Cybersecurity, Healthcare, Robotics, Sustainability, and Smart Technologies "
                "to build impactful solutions and earn the opportunity to represent Mahindra University on a national stage."
            ),
            prizes=(
                "**Cash Prizes Worth ₹60,000!**\n"
                "• **1st Prize**: ₹10,000 x 3 teams\n"
                "• **2nd Prize**: ₹6,000 x 3 teams\n"
                "• **3rd Prize**: ₹4,000 x 3 teams\n\n"
                "• **National Stage**: Winner of each Problem Statement receives 1st Prize of ₹1,00,000 (₹1 Lakh) at SIH 2026!"
            ),
            registration_deadline="10 August 2026",
            event_date="19 August 2026",
            team_rules=(
                "• **Team Size**: 6 Members per Team\n"
                "• **Diversity Requirement**: At least 1 Female Team Member is MANDATORY\n"
                "• **Eligibility**: Students from Any Year & Discipline can team up together\n"
                "• **Experience**: No prior hackathon experience required"
            ),
            email_required=True,
            registration_link="https://qrco.de/bgvXHe",
            official=True
        )
        db.add(sih_event)
        db.commit()
        logger.info("Seeded Smart India Hackathon 2026 into Mahindra University events registry.")
    else:
        sih_event.name = "Smart India Hackathon 2026 (Internal Hackathon)"
        sih_event.organizer = "Mahindra University & SIH 2026"
        sih_event.category = "Hackathon"
        sih_event.summary = "BUILD. INNOVATE. REPRESENT MAHINDRA UNIVERSITY."
        sih_event.description = (
            "Smart India Hackathon 2026 Internal Hackathon is India's biggest innovation challenge! "
            "Solve real-world problems proposed by Government Ministries, Departments & Industry (around 250 problem statements). "
            "Work with a multidisciplinary team across AI & ML, Cybersecurity, Healthcare, Robotics, Sustainability, and Smart Technologies "
            "to build impactful solutions and earn the opportunity to represent Mahindra University on a national stage."
        )
        sih_event.prizes = (
            "**Cash Prizes Worth ₹60,000!**\n"
            "• **1st Prize**: ₹10,000 x 3 teams\n"
            "• **2nd Prize**: ₹6,000 x 3 teams\n"
            "• **3rd Prize**: ₹4,000 x 3 teams\n\n"
            "• **National Stage**: Winner of each Problem Statement receives 1st Prize of ₹1,00,000 (₹1 Lakh) at SIH 2026!"
        )
        sih_event.registration_deadline = "10 August 2026"
        sih_event.event_date = "19 August 2026"
        sih_event.team_rules = (
            "• **Team Size**: 6 Members per Team\n"
            "• **Diversity Requirement**: At least 1 Female Team Member is MANDATORY\n"
            "• **Eligibility**: Students from Any Year & Discipline can team up together\n"
            "• **Experience**: No prior hackathon experience required"
        )
        sih_event.email_required = True
        sih_event.registration_link = "https://qrco.de/bgvXHe"
        db.commit()
