from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sorts.core.importer.pipeline import ImporterPipeline
from sorts.database import models as db_models

class ImportService:
    def __init__(self):
        self.pipeline = ImporterPipeline()

    def trigger_import(self, db: Session, source_id: int) -> int:
        """Launches the crawler pipeline for the given source and stores draft items."""
        return self.pipeline.run_import(db, source_id)

    def get_job(self, db: Session, job_id: int) -> Optional[db_models.ImportJob]:
        """Retrieves import job state."""
        return db.query(db_models.ImportJob).filter_by(id=job_id).first()

    def get_draft_diff(self, db: Session, job_id: int) -> Dict[str, List[db_models.DraftClub]]:
        """Calculates differences between imported drafts and existing live clubs."""
        return self.pipeline.get_import_diff(db, job_id)

    def publish_job(self, db: Session, job_id: int) -> None:
        """Promotes draft changes to active university clubs."""
        self.pipeline.publish_import(db, job_id)

    def get_university_sources(self, db: Session, university_id: int) -> List[db_models.ImportSource]:
        """Lists available crawler source URLs/files for a university."""
        return db.query(db_models.ImportSource).filter_by(university_id=university_id, is_active=True).all()

    def get_latest_job(self, db: Session, university_id: int) -> Optional[db_models.ImportJob]:
        """Gets the most recent import job for a university."""
        return db.query(db_models.ImportJob)\
            .filter_by(university_id=university_id)\
            .order_by(db_models.ImportJob.created_at.desc())\
            .first()
