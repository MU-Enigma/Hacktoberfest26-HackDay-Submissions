import pytest
from bs4 import BeautifulSoup
from sorts.core.extractor.bs4_extractor import BS4Extractor
from sorts.core.traits.rule_trait_inferencer import RuleTraitInferencer
from sorts.core.domain.entities import Trait, ClubTraitValue

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <article class="club-card">
        <h2 class="club-name">Dev Club</h2>
        <p class="club-summary">A student coding club.</p>
        <div class="club-description">
            Dev Club is dedicated to writing code, programming web applications, and participating in programming hackathons.
            We hold weekly sessions for beginners and experts alike.
        </div>
        <img class="club-logo" src="https://example.com/logo.png">
        <a class="link-discord" href="https://discord.gg/devclub">Discord</a>
        <a class="link-email" href="mailto:devclub@univ.edu">Email</a>
    </article>
</body>
</html>
"""

def test_bs4_extractor():
    extractor = BS4Extractor()
    config = {
        "club_selector": "article.club-card",
        "name_selector": ".club-name",
        "summary_selector": ".club-summary",
        "description_selector": ".club-description",
        "image_selector": "img.club-logo",
        "discord_selector": "a.link-discord",
        "email_selector": "a.link-email",
    }
    
    clubs = extractor.extract(SAMPLE_HTML, config)
    assert len(clubs) == 1
    club = clubs[0]
    assert club["name"] == "Dev Club"
    assert club["summary"] == "A student coding club."
    assert "writing code" in club["description"]
    assert club["discord"] == "https://discord.gg/devclub"
    assert club["email"] == "devclub@univ.edu"
    assert club["image"] == "https://example.com/logo.png"


def test_rule_trait_inferencer():
    inferencer = RuleTraitInferencer()
    
    # Define dummy traits
    traits = [
        Trait(slug="software", name="Software & Coding", description="Coding...", category="Technical"),
        Trait(slug="hardware", name="Robotics", description="Robots...", category="Technical"),
        Trait(slug="public_speaking", name="Speaking", description="Speak...", category="Literary"),
    ]
    
    # 1. Software-focused description
    desc_software = "We build web systems, write Python code, and practice programming algorithms."
    inferred = inferencer.infer_traits("Dev Club", desc_software, traits)
    
    inferred_map = {t.trait_slug: t.weight for t in inferred}
    assert "software" in inferred_map
    assert inferred_map["software"] > 0.5  # Boosted weight
    assert "hardware" not in inferred_map
    assert inferred_map["commitment_medium"] == 1.0  # Default to medium commitment

    # 2. Hardware-focused description with high commitment keyword
    desc_hardware = "We build robots with Arduino boards, circuits, and sensors. Highly intensive daily projects."
    inferred_hw = inferencer.infer_traits("RoboTech", desc_hardware, traits)
    inferred_hw_map = {t.trait_slug: t.weight for t in inferred_hw}
    
    assert "hardware" in inferred_hw_map
    assert inferred_hw_map["hardware"] > 0.5
    assert inferred_hw_map["commitment_high"] == 1.0
