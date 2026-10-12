import pytest
from sorts.core.recommendation.deterministic_engine import DeterministicRecommendationEngine
from sorts.core.recommendation.explanation_generator import ExplanationGenerator
from sorts.core.domain.entities import Club, ClubTraitValue, RecommendationEvidence

def test_deterministic_recommendation_engine():
    trait_names = {
        "software": "Software Development",
        "social": "Social Collaborations",
        "commitment_medium": "Medium commitment",
    }
    
    engine = DeterministicRecommendationEngine(trait_names=trait_names)
    
    # Setup candidate clubs
    club_a = Club(
        university_id=1,
        name="Coding Guild",
        slug="coding-guild",
        summary="Code group",
        description="Coding is fun",
        traits=[
            ClubTraitValue(trait_slug="software", weight=1.0),
            ClubTraitValue(trait_slug="social", weight=0.5),
        ],
        id=101
    )
    
    club_b = Club(
        university_id=1,
        name="Board Games",
        slug="board-games",
        summary="Play games",
        description="Social board games",
        traits=[
            ClubTraitValue(trait_slug="social", weight=1.0),
        ],
        id=102
    )

    # 1. Student who likes software (+0.8) and is slightly social (+0.2)
    session_traits_1 = {"software": 0.8, "social": 0.2}
    
    recs = engine.calculate_recommendations(session_traits_1, [club_a, club_b])
    
    assert len(recs) == 2
    # club_a should score higher due to software match
    assert recs[0].club_id == 101
    assert recs[0].overall_score > recs[1].overall_score
    
    # Check evidence details
    coding_guild_ev = recs[0]
    assert len(coding_guild_ev.matches) == 2
    
    software_match = [m for m in coding_guild_ev.matches if m.trait_slug == "software"][0]
    assert software_match.trait_name == "Software Development"
    assert software_match.student_weight == 0.8
    assert software_match.club_weight == 1.0
    assert software_match.contribution == pytest.approx(0.8)

    # 2. Student who is extremely social (+1.0) but doesn't care about software (0.0)
    session_traits_2 = {"social": 1.0}
    recs_2 = engine.calculate_recommendations(session_traits_2, [club_a, club_b])
    
    # club_b should score higher because it has higher density/focus on social (score 1.0 vs 0.5/(1.5) = 0.33)
    assert recs_2[0].club_id == 102


def test_explanation_generator():
    generator = ExplanationGenerator()
    
    from sorts.core.domain.entities import TraitMatchEvidence
    
    # 1. Setup sample positive matches
    evidence = RecommendationEvidence(
        club_id=101,
        club_name="Coding Guild",
        overall_score=0.8,
        matches=[
            TraitMatchEvidence(
                trait_slug="software",
                trait_name="Software Development",
                student_weight=0.8,
                club_weight=1.0,
                contribution=0.8
            ),
            TraitMatchEvidence(
                trait_slug="commitment_medium",
                trait_name="Medium Commitment",
                student_weight=1.0,
                club_weight=1.0,
                contribution=1.0
            )
        ]
    )
    
    explanation = generator.generate_explanation(evidence)
    assert "software development" in explanation.lower()
    assert "balanced weekly pace" in explanation.lower()
