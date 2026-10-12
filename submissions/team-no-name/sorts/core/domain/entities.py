from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class Trait:
    slug: str
    name: str
    description: str
    category: str
    id: Optional[int] = None

@dataclass
class ClubTraitValue:
    trait_slug: str
    weight: float

@dataclass
class OptionTraitModifier:
    trait_slug: str
    weight: float

@dataclass
class QuestionOption:
    text: str
    trait_modifiers: List[OptionTraitModifier] = field(default_factory=list)
    id: Optional[int] = None
    question_id: Optional[int] = None

@dataclass
class Question:
    university_id: int
    text: str
    code: str
    options: List[QuestionOption] = field(default_factory=list)
    id: Optional[int] = None

@dataclass
class University:
    slug: str
    name: str
    website: str
    logo: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    id: Optional[int] = None

@dataclass
class ImportSource:
    university_id: int
    name: str
    source_type: str  # "website", "file"
    url: str
    parser_config: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    id: Optional[int] = None

@dataclass
class ImportJob:
    university_id: int
    source_id: int
    status: str  # "pending", "running", "completed", "failed", "approved"
    created_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    id: Optional[int] = None

@dataclass
class Club:
    university_id: int
    name: str
    slug: str
    summary: str
    description: str
    category: Optional[str] = "General"
    official: bool = True
    aliases: List[str] = field(default_factory=list)
    website: Optional[str] = None
    discord: Optional[str] = None
    instagram: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    youtube: Optional[str] = None
    linktree: Optional[str] = None
    beacons: Optional[str] = None
    email: Optional[str] = None
    image: Optional[str] = None
    meeting_frequency: Optional[str] = None
    commitment: Optional[str] = None
    verification: Optional[Dict[str, Any]] = field(default_factory=dict)
    socials: Optional[Dict[str, str]] = field(default_factory=dict)
    traits: List[ClubTraitValue] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    id: Optional[int] = None

@dataclass
class DraftClub:
    import_job_id: int
    name: str
    summary: str
    description: str
    website: Optional[str] = None
    discord: Optional[str] = None
    instagram: Optional[str] = None
    email: Optional[str] = None
    image: Optional[str] = None
    meeting_frequency: Optional[str] = None
    commitment: Optional[str] = None
    traits: List[ClubTraitValue] = field(default_factory=list)
    status: str = "new"  # "new", "updated", "removed", "unchanged"
    id: Optional[int] = None

@dataclass
class SessionAnswer:
    session_id: str
    question_id: int
    option_id: int
    answered_at: datetime

@dataclass
class RecommendationSession:
    id: str  # UUID
    university_id: int
    user_identifier: Optional[str] = None  # Discord ID or other key
    status: str = "active"  # "active", "completed"
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    traits: Dict[str, float] = field(default_factory=dict)  # trait_slug -> weight value
    answers: List[SessionAnswer] = field(default_factory=list)

@dataclass
class Recommendation:
    session_id: str
    club_id: int
    score: float
    rank: int
    explanation: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[int] = None

@dataclass
class Feedback:
    recommendation_id: int
    rating: int  # 1 to 5
    comments: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[int] = None

@dataclass
class TraitMatchEvidence:
    trait_slug: str
    trait_name: str
    student_weight: float
    club_weight: float
    contribution: float

@dataclass
class RecommendationEvidence:
    club_id: int
    club_name: str
    overall_score: float
    matches: List[TraitMatchEvidence] = field(default_factory=list)
