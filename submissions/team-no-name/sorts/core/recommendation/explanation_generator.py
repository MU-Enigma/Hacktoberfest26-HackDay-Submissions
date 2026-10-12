from sorts.core.interfaces import IExplanationGenerator
from sorts.core.domain.entities import RecommendationEvidence


class ExplanationGenerator(IExplanationGenerator):
    def generate_explanation(self, evidence: RecommendationEvidence) -> str:
        """Generates a varied, natural explanation based on interest and commitment matches."""
        # Separate interest matches from commitment matches
        # Separate interest matches from commitment matches (require student_weight >= 0.3 for active interest phrases)
        interest_matches = [
            m for m in evidence.matches
            if m.contribution > 0.001 and m.student_weight >= 0.3 and "commitment" not in m.trait_slug
        ]
        commitment_matches = [
            m for m in evidence.matches
            if m.contribution > 0.001 and m.student_weight > 0 and "commitment" in m.trait_slug
        ]

        interest_matches.sort(key=lambda m: m.contribution, reverse=True)
        commitment_matches.sort(key=lambda m: m.contribution, reverse=True)

        acronyms = {"AI", "UN", "BAJA", "DSA", "IOT", "MUN", "SAE", "EIC", "TEDX"}

        def format_name(name: str) -> str:
            words = name.split()
            return " ".join(w if w.upper() in acronyms else w.lower() for w in words)

        interest_phrases = []
        for m in interest_matches[:2]:
            interest_phrases.append(format_name(m.trait_name))

        commitment_phrase = ""
        if commitment_matches:
            c_slug = commitment_matches[0].trait_slug
            if c_slug == "commitment_high":
                commitment_phrase = "an intensive schedule"
            elif c_slug == "commitment_medium":
                commitment_phrase = "a balanced weekly pace"
            elif c_slug == "commitment_low":
                commitment_phrase = "a flexible commitment"

        # Deterministic variation based on club name to avoid repetitive phrasing across recommendations
        seed = sum(ord(c) for c in (evidence.club_name or ""))

        if interest_phrases and commitment_phrase:
            topic = " & ".join(interest_phrases)
            templates = [
                f"Directly matches your focus in {topic} with {commitment_phrase}.",
                f"Fits your interest in {topic} while aligning with {commitment_phrase}.",
                f"Strong overlap with your passion for {topic} and {commitment_phrase}."
            ]
            return templates[seed % len(templates)]
        elif interest_phrases:
            topic = " & ".join(interest_phrases)
            templates = [
                f"Aligns directly with your interest in {topic}.",
                f"Strong match for your focus on {topic}.",
                f"Fits your passion for {topic} and active campus engagement."
            ]
            return templates[seed % len(templates)]
        elif commitment_phrase:
            return f"Fits your availability with {commitment_phrase}."

        if evidence.overall_score <= 0.001:
            return "A great starting point to explore campus life."
        return "Fits your general profile across campus activities."
