import math
from typing import List, Dict, Optional
from sorts.core.interfaces import IQuestionSelector
from sorts.core.domain.entities import Question, Club

class VarianceQuestionSelector(IQuestionSelector):
    def __init__(self, top_k_cutoff: int = 10, temperature: float = 5.0):
        """
        Args:
            top_k_cutoff: Number of top clubs to consider.
            temperature: Softmax temperature parameter to adjust distribution sharpness.
        """
        self.top_k_cutoff = top_k_cutoff
        self.temperature = temperature

    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Calculates cosine similarity between two vectors."""
        v1_sum_sq = sum(val ** 2 for val in vec1.values())
        v1_norm = math.sqrt(v1_sum_sq)
        v2_sum_sq = sum(val ** 2 for val in vec2.values())
        v2_norm = math.sqrt(v2_sum_sq)
        if v1_norm <= 0.001 or v2_norm <= 0.001:
            return 0.0
        dot_product = sum(vec1.get(k, 0.0) * vec2.get(k, 0.0) for k in vec1.keys())
        return dot_product / (v1_norm * v2_norm + 1e-9)

    def _calculate_scores(self, traits: Dict[str, float], clubs: List[Club]) -> List[float]:
        """Calculates match scores dynamically using adaptive stage weights and deal-breaker vetoes."""
        interest_slugs = {slug for slug in traits.keys() if "commitment" not in slug}
        commitment_slugs = {slug for slug in traits.keys() if "commitment" in slug}

        s_pos_interests = {slug: val for slug, val in traits.items() if slug in interest_slugs and val > 0.001}
        s_neg_interests = {slug: abs(val) for slug, val in traits.items() if slug in interest_slugs and val < -0.001}
        s_commitments = {slug: val for slug, val in traits.items() if slug in commitment_slugs and abs(val) > 0.001}

        num_answered = len(traits)
        if num_answered < 3:
            w_dot, w_interest, w_overlap, w_commit = 0.40, 0.25, 0.25, 0.10
        else:
            w_dot, w_interest, w_overlap, w_commit = 0.30, 0.40, 0.15, 0.15

        scores = []
        for club in clubs:
            c_interests = {}
            c_commitments = {}
            for ct in club.traits:
                if ct.trait_slug in interest_slugs:
                    c_interests[ct.trait_slug] = ct.weight
                elif ct.trait_slug in commitment_slugs:
                    c_commitments[ct.trait_slug] = ct.weight

            is_vetoed = False
            if s_neg_interests and c_interests:
                for slug, neg_val in s_neg_interests.items():
                    if neg_val >= 0.8 and c_interests.get(slug, 0.0) >= 0.7:
                        is_vetoed = True
                        break

            if is_vetoed:
                overall_score = 0.0
            else:
                max_dot = sum(s_pos_interests.values()) if s_pos_interests else 1.0
                dot = sum(s_pos_interests[k] * c_interests.get(k, 0.0) for k in s_pos_interests) if s_pos_interests else 0.0
                dot_score = dot / (max_dot + 1e-9)

                interest_score = self._cosine_similarity(s_pos_interests, c_interests)

                matched_count = sum(1 for k in s_pos_interests if k in c_interests) if s_pos_interests else 0
                overlap_score = matched_count / len(s_pos_interests) if s_pos_interests else 0.0

                if c_commitments and s_commitments:
                    commitment_score = self._cosine_similarity(s_commitments, c_commitments)
                else:
                    commitment_score = 0.7

                disinterest_penalty = 0.0
                if s_neg_interests and c_interests:
                    disinterest_sq_sum = sum(((s_neg_interests[slug] * c_interests.get(slug, 0.0)) ** 2) for slug in s_neg_interests)
                    c_norm = math.sqrt(sum(v**2 for v in c_interests.values())) + 1e-9
                    disinterest_penalty = disinterest_sq_sum / c_norm

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

                ver_conf = 1.0
                if hasattr(club, "verification") and isinstance(club.verification, dict):
                    ver_conf = club.verification.get("confidence", 100) / 100.0
                official_bonus = 0.015 if getattr(club, "official", False) else 0.005
                tie_breaker = ((getattr(club, "id", 0) or 0) % 97) * 0.0001
                overall_score += (official_bonus * ver_conf) + tie_breaker

            scores.append(max(0.0, min(1.0, overall_score)))
        return scores

    def _calculate_entropy(self, scores: List[float], dynamic_temp: Optional[float] = None) -> float:
        """Applies softmax to scores and calculates Shannon Entropy using dynamic temperature scaling."""
        if not scores:
            return 0.0
            
        temp = dynamic_temp if dynamic_temp is not None else self.temperature
        max_score = max(scores)
        exp_scores = [math.exp(temp * (s - max_score)) for s in scores]
        sum_exp = sum(exp_scores)
        
        probabilities = [e / (sum_exp + 1e-9) for e in exp_scores]
        
        entropy = 0.0
        for p in probabilities:
            if p > 1e-6:
                entropy -= p * math.log2(p)
        return entropy

    def select_next_question(
        self, unasked_questions: List[Question], current_session_traits: Dict[str, float], candidate_clubs: List[Club]
    ) -> Optional[Question]:
        """Selects the next question utilizing Information Gain Ratio (IGR).
        
        Information Gain Ratio normalizes Shannon Entropy reduction by split entropy
        (intrinsic question entropy) to eliminate bias towards multi-option questions.
        """
        if not unasked_questions:
            return None
        if not candidate_clubs:
            return unasked_questions[0]

        num_answered = len(current_session_traits)
        dynamic_temp = self.temperature + (1.5 * num_answered)

        # Baseline entropy of current candidate scores
        current_scores = self._calculate_scores(current_session_traits, candidate_clubs)
        current_scores.sort(reverse=True)
        top_current_scores = current_scores[:self.top_k_cutoff]
        current_entropy = self._calculate_entropy(top_current_scores, dynamic_temp=dynamic_temp)

        best_question = None
        best_gain_ratio = -1e9

        for q in unasked_questions:
            if not q.options:
                continue

            expected_entropy = 0.0
            split_entropy = 0.0
            num_opts = len(q.options)
            opt_p = 1.0 / num_opts

            for opt in q.options:
                sim_traits = current_session_traits.copy()
                for mod in opt.trait_modifiers:
                    sim_traits[mod.trait_slug] = max(-1.0, min(1.0, sim_traits.get(mod.trait_slug, 0.0) + mod.weight))
                
                sim_scores = self._calculate_scores(sim_traits, candidate_clubs)
                sim_scores.sort(reverse=True)
                top_sim_scores = sim_scores[:self.top_k_cutoff]
                
                expected_entropy += opt_p * self._calculate_entropy(top_sim_scores, dynamic_temp=dynamic_temp)
                split_entropy -= opt_p * math.log2(opt_p + 1e-9)

            info_gain = max(0.0, current_entropy - expected_entropy)
            gain_ratio = info_gain / (split_entropy + 1e-9)

            if gain_ratio > best_gain_ratio:
                best_gain_ratio = gain_ratio
                best_question = q

        return best_question if best_question else unasked_questions[0]
