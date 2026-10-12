from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from sorts.core.domain.entities import (
    Trait, Club, ClubTraitValue, Question, RecommendationEvidence
)

class IExtractor(ABC):
    @abstractmethod
    def extract(self, html_content: str, parser_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parses HTML content and extracts raw club information.
        
        Returns:
            List of dictionaries containing extracted club attributes.
        """
        pass

class ITraitInferencer(ABC):
    @abstractmethod
    def infer_traits(self, club_name: str, club_description: str, all_traits: List[Trait]) -> List[ClubTraitValue]:
        """Analyzes club details and infers the relevance weights of various traits.
        
        Returns:
            List of ClubTraitValue objects.
        """
        pass

class IRecommendationEngine(ABC):
    @abstractmethod
    def calculate_recommendations(
        self, session_traits: Dict[str, float], clubs: List[Club]
    ) -> List[RecommendationEvidence]:
        """Calculates similarity scores and matches student session traits against candidate clubs.
        
        Returns:
            List of RecommendationEvidence objects containing overall match scores and per-trait evidence.
        """
        pass

class IQuestionSelector(ABC):
    @abstractmethod
    def select_next_question(
        self, unasked_questions: List[Question], current_session_traits: Dict[str, float], candidate_clubs: List[Club]
    ) -> Optional[Question]:
        """Determines the next best question to ask the user, based on the current session profile
        and the remaining candidate clubs.
        
        Returns:
            The selected Question entity, or None if no further questions should be asked.
        """
        pass

class IExplanationGenerator(ABC):
    @abstractmethod
    def generate_explanation(self, evidence: RecommendationEvidence) -> str:
        """Converts structured matching evidence details into a natural language description.
        
        Returns:
            A human-readable explanation string.
        """
        pass
