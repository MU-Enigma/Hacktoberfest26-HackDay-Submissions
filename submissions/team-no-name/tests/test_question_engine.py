import pytest
from sorts.core.questions.variance_selector import VarianceQuestionSelector
from sorts.core.domain.entities import (
    Question, QuestionOption, OptionTraitModifier, Club, ClubTraitValue
)

def test_variance_question_selector():
    selector = VarianceQuestionSelector()

    # Create dummy traits and questions
    # Question 1: about software
    q1 = Question(
        university_id=1,
        text="Do you like coding?",
        code="likes_coding",
        options=[
            QuestionOption(
                text="Yes",
                trait_modifiers=[OptionTraitModifier(trait_slug="software", weight=1.0)]
            ),
            QuestionOption(
                text="No",
                trait_modifiers=[OptionTraitModifier(trait_slug="software", weight=-1.0)]
            )
        ],
        id=1
    )

    # Question 2: about music
    q2 = Question(
        university_id=1,
        text="Do you like music?",
        code="likes_music",
        options=[
            QuestionOption(
                text="Yes",
                trait_modifiers=[OptionTraitModifier(trait_slug="music", weight=1.0)]
            ),
            QuestionOption(
                text="No",
                trait_modifiers=[OptionTraitModifier(trait_slug="music", weight=-1.0)]
            )
        ],
        id=2
    )

    # Setup candidate clubs
    # Club A is software focused
    club_a = Club(
        university_id=1,
        name="Software Club",
        slug="software-club",
        summary="Coding",
        description="Coding",
        traits=[ClubTraitValue(trait_slug="software", weight=1.0)],
        id=101
    )
    
    # Club B is music focused
    club_b = Club(
        university_id=1,
        name="Band",
        slug="band",
        summary="Jamming",
        description="Jamming",
        traits=[ClubTraitValue(trait_slug="music", weight=1.0)],
        id=102
    )

    unasked = [q1, q2]
    
    # 1. At start, student traits are all 0.0
    current_traits = {}
    
    # The selector should pick a question that overlaps with the clubs. Both q1 and q2 do.
    next_q = selector.select_next_question(unasked, current_traits, [club_a, club_b])
    assert next_q is not None
    assert next_q.id in (1, 2)

    # 2. Suppose student profile already has software = +0.8 (meaning we answered yes to coding)
    # The top club is now club_a. We want to resolve ambiguity, or look at what differentiates them.
    # If we ask likes_music (q2), it modifies 'music', which differentiates club_a and club_b.
    # Let's test if the engine can run without failing and return a valid question.
    next_q_refined = selector.select_next_question([q2], {"software": 0.8}, [club_a, club_b])
    assert next_q_refined.id == 2
