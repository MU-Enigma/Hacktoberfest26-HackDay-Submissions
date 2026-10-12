import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sorts.core.extractor.bs4_extractor import BS4Extractor
from sorts.core.extractor.selector_detector import detect_parser_config
from sorts.core.traits.rule_trait_inferencer import RuleTraitInferencer
from sorts.database.models import (
    University, ImportSource, ImportJob, Club, Trait, ClubTrait, DraftClub, DraftClubTrait
)
import requests

logger = logging.getLogger(__name__)

class ImporterPipeline:
    def __init__(self):
        self.extractor = BS4Extractor()
        self.trait_inferencer = RuleTraitInferencer()

    def run_import(self, db: Session, source_id: int) -> int:
        """Runs the crawler and trait inference pipeline for a given ImportSource.
        
        Saves results as DraftClub and DraftClubTrait records.
        """
        source = db.query(ImportSource).filter_by(id=source_id).first()
        if not source:
            raise ValueError(f"Import source {source_id} not found.")

        # Create a new ImportJob
        job = ImportJob(
            university_id=source.university_id,
            source_id=source.id,
            status="running",
            created_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        try:
            # 1. Fetch HTML Content
            html_content = ""
            if source.source_type == "file":
                filepath = source.url
                if not os.path.exists(filepath):
                    logger.warning(f"Seed file '{filepath}' not found for source {source.id}. Returning empty seed container.")
                    html_content = "<div></div>"
                else:
                    with open(filepath, "r", encoding="utf-8") as f:
                        html_content = f.read()
            else:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                response = requests.get(source.url, headers=headers, timeout=15)
                response.raise_for_status()
                html_content = response.text

            # 2. Resolve parser config — auto-detect if none stored yet
            parser_config = source.get_parser_config()
            if not parser_config.get("club_selector"):
                logger.info(f"ImporterPipeline: no parser_config for source {source.id}; auto-detecting selectors.")
                parser_config = detect_parser_config(html_content)
                # Persist so future syncs skip detection
                source.set_parser_config(parser_config)
                db.commit()
                logger.info(f"ImporterPipeline: detected config saved for source {source.id}: {parser_config}")

            raw_clubs = self.extractor.extract(html_content, parser_config)
            
            # Fetch all traits in the DB for keyword matching
            all_traits = db.query(Trait).all()
            
            # Retrieve currently active clubs for comparison
            active_clubs = db.query(Club).filter_by(university_id=source.university_id).all()
            active_clubs_by_slug = {c.slug: c for c in active_clubs}

            draft_slugs = set()

            # 3. Process and write Drafts
            for rc in raw_clubs:
                name = rc["name"]
                slug = self._slugify(name)
                draft_slugs.add(slug)

                # Infer traits
                inferred_traits = self.trait_inferencer.infer_traits(name, rc["description"], all_traits)

                # Determine draft status (new, updated, unchanged)
                status = "new"
                if slug in active_clubs_by_slug:
                    active_c = active_clubs_by_slug[slug]
                    # Check if anything changed
                    changed = (
                        active_c.name != name or
                        active_c.summary != rc["summary"] or
                        active_c.description != rc["description"] or
                        active_c.website != rc["website"] or
                        active_c.discord != rc["discord"] or
                        active_c.instagram != rc["instagram"] or
                        active_c.email != rc["email"] or
                        active_c.image != rc["image"] or
                        active_c.meeting_frequency != rc["meeting_frequency"] or
                        active_c.commitment != rc["commitment"]
                    )
                    
                    # Also check if trait weights changed
                    if not changed:
                        active_traits_map = {t.trait.slug: t.weight for t in active_c.traits}
                        inferred_traits_map = {t.trait_slug: t.weight for t in inferred_traits}
                        if active_traits_map != inferred_traits_map:
                            changed = True
                    
                    status = "updated" if changed else "unchanged"

                # Create DraftClub
                draft_c = DraftClub(
                    import_job_id=job.id,
                    name=name,
                    summary=rc["summary"],
                    description=rc["description"],
                    website=rc["website"],
                    discord=rc["discord"],
                    instagram=rc["instagram"],
                    email=rc["email"],
                    image=rc["image"],
                    meeting_frequency=rc["meeting_frequency"],
                    commitment=rc["commitment"],
                    status=status
                )
                db.add(draft_c)
                db.commit()
                db.refresh(draft_c)

                # Save DraftClubTraits
                for it in inferred_traits:
                    trait_obj = db.query(Trait).filter_by(slug=it.trait_slug).first()
                    if trait_obj:
                        dct = DraftClubTrait(
                            draft_club_id=draft_c.id,
                            trait_id=trait_obj.id,
                            weight=it.weight
                        )
                        db.add(dct)
            
            # Detect removed clubs: active clubs that were NOT found in the crawl
            for slug, active_c in active_clubs_by_slug.items():
                if slug not in draft_slugs:
                    draft_c = DraftClub(
                        import_job_id=job.id,
                        name=active_c.name,
                        summary=active_c.summary,
                        description=active_c.description,
                        website=active_c.website,
                        discord=active_c.discord,
                        instagram=active_c.instagram,
                        email=active_c.email,
                        image=active_c.image,
                        meeting_frequency=active_c.meeting_frequency,
                        commitment=active_c.commitment,
                        status="removed"
                    )
                    db.add(draft_c)
                    db.commit()
                    db.refresh(draft_c)
                    
                    # Copy old traits to the removed draft club for preview
                    for ct in active_c.traits:
                        dct = DraftClubTrait(
                            draft_club_id=draft_c.id,
                            trait_id=ct.trait_id,
                            weight=ct.weight
                        )
                        db.add(dct)

            # Complete the Job successfully
            job.status = "completed"
            job.finished_at = datetime.utcnow()
            db.commit()
            logger.info(f"ImportJob {job.id} completed successfully.")
            return job.id

        except Exception as e:
            logger.exception("Import pipeline encountered an error.")
            job.status = "failed"
            job.finished_at = datetime.utcnow()
            job.error_message = str(e)
            db.commit()
            raise e

    def get_import_diff(self, db: Session, job_id: int) -> Dict[str, List[DraftClub]]:
        """Retrieves categorized draft clubs for admin review."""
        drafts = db.query(DraftClub).filter_by(import_job_id=job_id).all()
        diff = {"new": [], "updated": [], "removed": [], "unchanged": []}
        for d in drafts:
            if d.status in diff:
                diff[d.status].append(d)
        return diff

    def publish_import(self, db: Session, job_id: int) -> None:
        """Applies draft changes to the active tables (Clubs, ClubTraits) transactionally."""
        job = db.query(ImportJob).filter_by(id=job_id).first()
        if not job:
            raise ValueError(f"Import job {job_id} not found.")
        if job.status != "completed":
            raise ValueError(f"Cannot publish job {job_id} in state: {job.status}")

        draft_clubs = db.query(DraftClub).filter_by(import_job_id=job_id).all()
        for dc in draft_clubs:
            slug = self._slugify(dc.name)
            
            if dc.status == "new":
                # Create new Club
                c = Club(
                    university_id=job.university_id,
                    name=dc.name,
                    slug=slug,
                    summary=dc.summary,
                    description=dc.description,
                    website=dc.website,
                    discord=dc.discord,
                    instagram=dc.instagram,
                    email=dc.email,
                    image=dc.image,
                    meeting_frequency=dc.meeting_frequency,
                    commitment=dc.commitment,
                )
                db.add(c)
                db.commit()
                db.refresh(c)
                
                # Copy traits
                for dct in dc.traits:
                    ct = ClubTrait(
                        club_id=c.id,
                        trait_id=dct.trait_id,
                        weight=dct.weight
                    )
                    db.add(ct)

            elif dc.status == "updated":
                # Update existing Club
                c = db.query(Club).filter_by(university_id=job.university_id, slug=slug).first()
                if c:
                    c.name = dc.name
                    c.summary = dc.summary
                    c.description = dc.description
                    c.website = dc.website
                    c.discord = dc.discord
                    c.instagram = dc.instagram
                    c.email = dc.email
                    c.image = dc.image
                    c.meeting_frequency = dc.meeting_frequency
                    c.commitment = dc.commitment
                    
                    # Delete old traits, insert new traits
                    db.query(ClubTrait).filter_by(club_id=c.id).delete()
                    db.commit()
                    
                    for dct in dc.traits:
                        ct = ClubTrait(
                            club_id=c.id,
                            trait_id=dct.trait_id,
                            weight=dct.weight
                        )
                        db.add(ct)

            elif dc.status == "removed":
                # Delete existing Club
                c = db.query(Club).filter_by(university_id=job.university_id, slug=slug).first()
                if c:
                    db.delete(c)  # Cascades to ClubTraits

        # Mark job as approved
        job.status = "approved"
        db.commit()
        logger.info(f"ImportJob {job_id} changes published.")

    def _slugify(self, text: str) -> str:
        """Converts string into web-friendly lowercase slug."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        return re.sub(r"[-\s]+", "-", text)
