from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sorts.database import models as db_models

class ClubService:
    def get_club_by_slug(self, db: Session, university_id: int, slug: str) -> Optional[db_models.Club]:
        """Retrieves a single club by its slug name."""
        return db.query(db_models.Club).filter_by(university_id=university_id, slug=slug.lower().strip()).first()

    def get_club_by_id(self, db: Session, club_id: int) -> Optional[db_models.Club]:
        """Retrieves a single club by its unique ID."""
        return db.query(db_models.Club).filter_by(id=club_id).first()

    def get_clubs_paginated(
        self, db: Session, university_id: int, page: int = 1, per_page: int = 5
    ) -> Tuple[List[db_models.Club], int]:
        """Retrieves a paginated list of clubs for a university, alongside total count."""
        query = db.query(db_models.Club).filter_by(university_id=university_id)
        total_count = query.count()

        offset = (page - 1) * per_page
        clubs = query.order_by(db_models.Club.name).offset(offset).limit(per_page).all()
        
        return clubs, total_count

    def search_clubs(self, db: Session, university_id: int, search_query: str) -> List[db_models.Club]:
        """Searches clubs based on name, aliases, tags, category, summary, or description."""
        query_str = search_query.lower().strip()
        if not query_str:
            return []

        all_clubs = db.query(db_models.Club).filter_by(university_id=university_id).order_by(db_models.Club.name).all()

        # 1. Exact name match
        exact_matches = [c for c in all_clubs if query_str == c.name.lower()]
        if exact_matches:
            return exact_matches

        # 2. Alias match (exact or phrase boundary)
        alias_matches = []
        for c in all_clubs:
            aliases = [a.lower() for a in c.get_aliases()]
            if any(query_str == a or query_str in a or a in query_str for a in aliases):
                if c not in alias_matches:
                    alias_matches.append(c)

        if len(alias_matches) == 1:
            return alias_matches

        # 3. Direct substring name match
        name_matches = [c for c in all_clubs if query_str in c.name.lower()]
        if len(name_matches) == 1:
            return name_matches

        # Combine name and alias matches
        combined = []
        for c in name_matches + alias_matches:
            if c not in combined:
                combined.append(c)

        if combined:
            return combined

        # 4. Search within summary, description, category, and metadata tags
        content_matches = []
        for c in all_clubs:
            summary_lower = (c.summary or "").lower()
            desc_lower = (c.description or "").lower()
            cat_lower = (c.category or "").lower()
            tags = [t.lower() for t in c.get_club_metadata().get("tags", [])]

            if (query_str in summary_lower or 
                query_str in desc_lower or 
                query_str in cat_lower or 
                any(query_str in t for t in tags)):
                content_matches.append(c)

        return content_matches
