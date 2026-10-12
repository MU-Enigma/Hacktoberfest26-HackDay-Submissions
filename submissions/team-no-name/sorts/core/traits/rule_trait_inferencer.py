from typing import List
import re
from sorts.core.interfaces import ITraitInferencer
from sorts.core.domain.entities import Trait, ClubTraitValue

class RuleTraitInferencer(ITraitInferencer):
    def __init__(self):
        # Define keyword groups for interest-based traits
        self.keywords = {
            "software": [
                r"\bcod(e|ing|er|ers)\b", r"\bprogramm(ing|er|ers)\b", r"\bsoftware\b", 
                r"\bsoftware develop(ment|er|ers)?\b", r"\bweb develop(ment|er|ers)?\b", 
                r"\bapp develop(ment|er|ers)?\b", r"\bhackathon(s)?\b", r"\bpython\b", 
                r"\bjava\b", r"\bweb dev\b", r"\bapp dev\b", r"\balgorithm(s)?\b", 
                r"\bgit\b", r"\bgithub\b", r"\bcomputer science\b", r"\bopen-source\b",
                r"\bqiskit\b", r"\bquantum\b"
            ],
            "hardware": [
                r"\brobotic(s)?\b", r"\bhardware\b", r"\barduino\b", r"\braspberry pi\b", 
                r"\belectronic(s)?\b", r"\bcircuit(s)?\b", r"\bsensor(s)?\b", 
                r"\bmicrocontroller(s)?\b", r"\bembedded system(s)?\b", r"\biot\b", 
                r"\binternet of things\b", r"\blab\b", r"\bengineering\b", r"\bmechanic(s|al)?\b", 
                r"\bfabricat(e|ion|ed)\b", r"\bmanufactur(ing|ed)\b", r"\bvehicle(s)?\b", 
                r"\bautomotive\b", r"\bmachinery\b"
            ],
            "public_speaking": [
                r"\bpublic speaking\b", r"\bdebate(s|d|r|rs)?\b", r"\borator(y|s)?\b", 
                r"\btoastmaster(s)?\b", r"\bspeech(es)?\b", r"\bspeaking\b", 
                r"\bmun\b", r"\bmodel united nations\b", r"\bpersuasion\b", r"\belocution\b"
            ],
            "entrepreneurship": [
                r"\bbusiness\b", r"\bfinance\b", r"\bentrepreneur(ship|s)?\b", 
                r"\bstartup(s)?\b", r"\bpitch(es)?\b", r"\bstock market\b", 
                r"\bcase study\b", r"\bfounder(s)?\b", r"\bmarketing\b", 
                r"\bconsulting\b", r"\bacumen\b"
            ],
            "aerospace": [
                r"\baerospace\b", r"\baviation\b", r"\bdrone(s)?\b", 
                r"\baerodynamic(s)?\b", r"\bplane(s)?\b", r"\bflight\b", 
                r"\buav(s)?\b", r"\baircraft\b"
            ],
            "music": [
                r"\bmusic\b", r"\bsing(ing|er|ers)?\b", r"\binstrument(s|al)?\b", 
                r"\bband(s)?\b", r"\bjam(ming)?\b", r"\bguitar(s)?\b", 
                r"\bsongwriter(s)?\b", r"\bvocals\b"
            ],
            "social": [
                r"\bsocial(izing)?\b", r"\bcommunity\b", r"\bnetwork(ing)?\b", 
                r"\bfestival(s)?\b", r"\bcollaborat(e|ion|ive)\b", r"\bteamwork\b", 
                r"\binteraction(s)?\b", r"\bpeer(s)?\b", r"\bgathering(s)?\b", 
                r"\bmeetup(s)?\b"
            ],
            "creative": [
                r"\bcreative\b", r"\bcreativity\b", r"\bart(s|istry|istic)?\b", 
                r"\bpoetry\b", r"\bdance(r|rs|ing)?\b", r"\btheatre\b", 
                r"\bperform(ance|ing)\b", r"\bphotograph(y|er|s)?\b", 
                r"\bpaint(ing)?\b", r"\bwriting\b", r"\bexpression\b"
            ]
        }

    def infer_traits(self, club_name: str, club_description: str, all_traits: List[Trait]) -> List[ClubTraitValue]:
        """Infers traits and scores based on keywords in name and description."""
        inferred = []
        name_lower = club_name.lower()
        desc_lower = club_description.lower()
        full_text = f"{name_lower} {desc_lower}"

        # 1. Process interest-based traits
        for trait in all_traits:
            slug = trait.slug
            if slug in self.keywords:
                patterns = self.keywords[slug]
                matches = 0
                for pattern in patterns:
                    matches += len(re.findall(pattern, full_text))

                if matches > 0:
                    # Base weight of 0.5 for first match, plus 0.15 for every subsequent keyword hit
                    weight = min(0.5 + (matches - 1) * 0.15, 1.0)
                    
                    # Boost weight to 1.0 if name contains explicit indicator (e.g. "Coding" -> software)
                    # Let's check name matches specifically
                    for pattern in patterns:
                        if re.search(pattern, name_lower):
                            weight = 1.0
                            break
                    
                    inferred.append(ClubTraitValue(trait_slug=slug, weight=weight))

        # 2. Process commitment-based traits
        # Check text signals for workload
        commitment_high_patterns = [r"\bhigh commitment\b", r"\bintensive\b", r"\bcompetition(s)?\b", r"\bnational\b", r"\bdaily\b"]
        commitment_medium_patterns = [r"\bmedium commitment\b", r"\bweekly\b", r"\bbi-weekly\b", r"\bbalanced\b"]
        commitment_low_patterns = [r"\blow commitment\b", r"\bmonthly\b", r"\bcasual\b", r"\boccasional\b", r"\bsocial jam\b"]

        high_hits = sum(len(re.findall(p, desc_lower)) for p in commitment_high_patterns)
        medium_hits = sum(len(re.findall(p, desc_lower)) for p in commitment_medium_patterns)
        low_hits = sum(len(re.findall(p, desc_lower)) for p in commitment_low_patterns)

        # Default to medium commitment if there are no hits, or determine based on highest hits
        if high_hits > medium_hits and high_hits > low_hits:
            inferred.append(ClubTraitValue(trait_slug="commitment_high", weight=1.0))
        elif low_hits > medium_hits and low_hits > high_hits:
            inferred.append(ClubTraitValue(trait_slug="commitment_low", weight=1.0))
        else:
            # Fallback default
            inferred.append(ClubTraitValue(trait_slug="commitment_medium", weight=1.0))

        return inferred
