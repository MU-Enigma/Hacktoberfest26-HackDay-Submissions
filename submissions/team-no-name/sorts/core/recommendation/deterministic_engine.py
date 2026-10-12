from typing import List, Dict
import math
from sorts.core.interfaces import IRecommendationEngine
from sorts.core.domain.entities import Club, RecommendationEvidence, TraitMatchEvidence

class DeterministicRecommendationEngine(IRecommendationEngine):
    def __init__(self, trait_names: Dict[str, str] = None):
        """
        Args:
            trait_names: Optional dictionary mapping trait slugs to human-readable names.
        """
        self.trait_names = trait_names or {}

    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Calculates cosine similarity between two vectors."""
        epsilon = 1e-9
        
        v1_sum_sq = sum(val ** 2 for val in vec1.values())
        v1_norm = math.sqrt(v1_sum_sq)
        
        v2_sum_sq = sum(val ** 2 for val in vec2.values())
        v2_norm = math.sqrt(v2_sum_sq)
        
        if v1_norm <= 0.001 or v2_norm <= 0.001:
            return 0.0
            
        dot_product = sum(vec1.get(k, 0.0) * vec2.get(k, 0.0) for k in vec1.keys())
        return dot_product / (v1_norm * v2_norm + epsilon)

    def calculate_recommendations(
        self, session_traits: Dict[str, float], clubs: List[Club]
    ) -> List[RecommendationEvidence]:
        """Calculates match scores dynamically by separating interests, commitment, and disinterest penalties.
        
        - Positive interest alignment uses non-negative student vector matching.
        - Disinterest (negative student trait values) applies a targeted linear penalty.
        - Official status & verification confidence act as bounded tie-breakers.
        """
        # Classify traits dynamically
        interest_slugs = {slug for slug in session_traits.keys() if "commitment" not in slug}
        commitment_slugs = {slug for slug in session_traits.keys() if "commitment" in slug}

        # Extract student positive & negative vectors
        s_pos_interests = {slug: val for slug, val in session_traits.items() if slug in interest_slugs and val > 0.001}
        s_neg_interests = {slug: abs(val) for slug, val in session_traits.items() if slug in interest_slugs and val < -0.001}
        s_commitments = {slug: val for slug, val in session_traits.items() if slug in commitment_slugs and abs(val) > 0.001}

        # Adaptive Stage-Based Weighting based on session density
        num_answered = len(session_traits)
        if num_answered < 3:
            w_dot, w_interest, w_overlap, w_commit = 0.40, 0.25, 0.25, 0.10
        else:
            w_dot, w_interest, w_overlap, w_commit = 0.30, 0.40, 0.15, 0.15

        results = []

        for club in clubs:
            # Extract club vectors
            c_interests = {}
            c_commitments = {}
            matches = []

            for ct in club.traits:
                if ct.trait_slug in interest_slugs:
                    c_interests[ct.trait_slug] = ct.weight
                elif ct.trait_slug in commitment_slugs:
                    c_commitments[ct.trait_slug] = ct.weight

                s_val = session_traits.get(ct.trait_slug, 0.0)
                contribution = s_val * ct.weight
                if abs(contribution) > 0.001:
                    trait_name = self.trait_names.get(ct.trait_slug, ct.trait_slug.replace("_", " ").title())
                    matches.append(
                        TraitMatchEvidence(
                            trait_slug=ct.trait_slug,
                            trait_name=trait_name,
                            student_weight=s_val,
                            club_weight=ct.weight,
                            contribution=contribution,
                        )
                    )

            # Deal-Breaker Hard Veto Check (Strong negative preference vs High club specialization)
            is_vetoed = False
            if s_neg_interests and c_interests:
                for slug, neg_val in s_neg_interests.items():
                    if neg_val >= 0.8 and c_interests.get(slug, 0.0) >= 0.7:
                        is_vetoed = True
                        break

            if is_vetoed:
                overall_score = 0.0
            else:
                # 1. Weighted Dot Product
                max_dot = sum(s_pos_interests.values()) if s_pos_interests else 1.0
                dot = sum(s_pos_interests[k] * c_interests.get(k, 0.0) for k in s_pos_interests) if s_pos_interests else 0.0
                dot_score = dot / (max_dot + 1e-9)

                # 2. Cosine Similarity
                norm_s = math.sqrt(sum(v**2 for v in s_pos_interests.values())) if s_pos_interests else 0.0
                norm_c = math.sqrt(sum(v**2 for v in c_interests.values())) if c_interests else 0.0
                interest_score = (dot / (norm_s * norm_c + 1e-9)) if norm_s > 0 and norm_c > 0 else 0.0

                # 3. Multi-Trait Overlap Ratio
                matched_count = sum(1 for k in s_pos_interests if k in c_interests) if s_pos_interests else 0
                overlap_score = (matched_count / len(s_pos_interests)) if s_pos_interests else 0.0

                # 4. Commitment Alignment
                if c_commitments and s_commitments:
                    norm_cs = math.sqrt(sum(v**2 for v in s_commitments.values()))
                    norm_cc = math.sqrt(sum(v**2 for v in c_commitments.values()))
                    c_dot = sum(s_commitments[k] * c_commitments.get(k, 0.0) for k in s_commitments)
                    commitment_score = c_dot / (norm_cs * norm_cc + 1e-9)
                else:
                    commitment_score = 0.7  # Neutral default for unstated commitment

                # 5. Quadratic Disinterest Penalty
                disinterest_penalty = 0.0
                if s_neg_interests and c_interests:
                    disinterest_sq_sum = sum(((s_neg_interests[slug] * c_interests.get(slug, 0.0)) ** 2) for slug in s_neg_interests)
                    c_norm = math.sqrt(sum(v**2 for v in c_interests.values())) + 1e-9
                    disinterest_penalty = disinterest_sq_sum / c_norm

                # Adaptive Composite Scoring
                if c_interests and dot <= 0.0 and interest_score <= 0.0:
                    overall_score = 0.0
                else:
                    overall_score = (
                        (w_dot * dot_score)
                        + (w_interest * interest_score)
                        + (w_overlap * overlap_score)
                        + (w_commit * commitment_score)
                        - (0.15 * disinterest_penalty)
                    )

                # Micro tie-breaker based on club ID & verification
                ver_conf = 1.0
                if hasattr(club, "verification") and isinstance(club.verification, dict):
                    ver_conf = club.verification.get("confidence", 100) / 100.0
                official_bonus = 0.015 if getattr(club, "official", False) else 0.005
                tie_breaker = ((getattr(club, "id", 0) or 0) % 97) * 0.0001
                overall_score += (official_bonus * ver_conf) + tie_breaker

            overall_score = max(0.0, min(1.0, overall_score))
            matches.sort(key=lambda m: m.contribution, reverse=True)

            results.append(
                RecommendationEvidence(
                    club_id=club.id if club.id else 0,
                    club_name=club.name,
                    overall_score=overall_score,
                    matches=matches,
                )
            )

        results.sort(key=lambda r: r.overall_score, reverse=True)
        return self._apply_mmr_diversity(results, clubs)

    def _apply_mmr_diversity(
        self, results: List[RecommendationEvidence], clubs: List[Club], top_k: int = 10, lambda_param: float = 0.75
    ) -> List[RecommendationEvidence]:
        """Applies Maximal Marginal Relevance (MMR) to balance match relevance with category diversity."""
        if not results or len(results) <= 1:
            return results

        club_vectors = {}
        for club in clubs:
            vec = {ct.trait_slug: ct.weight for ct in club.traits if "commitment" not in ct.trait_slug}
            club_vectors[club.id] = vec

        selected = []
        candidates = list(results)

        # First pick is the highest overall score match
        selected.append(candidates.pop(0))

        while candidates and len(selected) < top_k:
            best_mmr = -1e9
            best_cand_idx = 0

            for i, cand in enumerate(candidates):
                relevance = cand.overall_score
                cand_vec = club_vectors.get(cand.club_id, {})

                max_sim = 0.0
                for sel in selected:
                    sel_vec = club_vectors.get(sel.club_id, {})
                    sim = self._cosine_similarity(cand_vec, sel_vec)
                    if sim > max_sim:
                        max_sim = sim

                mmr_score = (lambda_param * relevance) - ((1.0 - lambda_param) * max_sim)
                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_cand_idx = i

            selected.append(candidates.pop(best_cand_idx))

        return selected + candidates
