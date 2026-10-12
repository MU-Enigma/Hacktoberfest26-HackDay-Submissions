"""
selector_detector.py
--------------------
Heuristic auto-detection of CSS selectors for club pages.

When an ImportSource has no parser_config, the pipeline calls
`detect_parser_config(html)` here.  We try a ranked list of common
university-site patterns, score each by how many elements yield a
non-empty name, and return the best-scoring config.

If nothing scores >= 2, we fall back to a broad "any heading in a
block" strategy that at least names clubs even if descriptions are thin.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Ranked candidate configs ────────────────────────────────────────────────
# Each entry is (club_selector, name_selectors_to_try, description_selector, extra_fields)
# name_selectors_to_try is a list; we pick the first that gives results.

CANDIDATE_PROFILES: List[Dict[str, Any]] = [
    # 1 ── ElementsKit team widget (WordPress + ElementsKit plugin)
    {
        "label": "ElementsKit-team",
        "club_selector": "div.ekit-wid-con",
        "name_selector": "h2.profile-title",
        "description_selector": ".ekit-team-modal-content",
        "image_selector": "div.profile-header img",
        "website_selector": ".ekit-team-modal-content a",
    },
    # 2 ── Bootstrap / generic card grids
    {
        "label": "bootstrap-card",
        "club_selector": ".card",
        "name_selector": ".card-title",
        "description_selector": ".card-body p, .card-text",
    },
    # 3 ── WordPress posts (standard archive)
    {
        "label": "wp-article",
        "club_selector": "article",
        "name_selector": "h2.entry-title, h1.entry-title, .entry-title",
        "description_selector": ".entry-content p, .entry-summary p",
    },
    # 4 ── Jet Engine / Jet Listing Grid (WordPress)
    {
        "label": "jet-listing",
        "club_selector": ".jet-listing-grid__item",
        "name_selector": "h2,h3,h4",
        "description_selector": "p",
    },
    # 5 ── Elementor loop items
    {
        "label": "elementor-loop",
        "club_selector": ".elementor-loop-item",
        "name_selector": "h2,h3,h4",
        "description_selector": "p",
    },
    # 6 ── Generic elements with "club" or "society" in the class
    {
        "label": "class-club",
        "club_selector": "[class*='club'],[class*='society'],[class*='org-card']",
        "name_selector": "h2,h3,h4,.title,.name",
        "description_selector": "p,.description,.desc",
    },
    # 7 ── Table rows with club data
    {
        "label": "table-row",
        "club_selector": "table tbody tr",
        "name_selector": "td:first-child",
        "description_selector": "td:nth-child(2)",
    },
    # 8 ── Definition lists
    {
        "label": "dl-item",
        "club_selector": "dl",
        "name_selector": "dt",
        "description_selector": "dd",
    },
    # 9 ── Unordered-list items that contain a heading
    {
        "label": "li-heading",
        "club_selector": "ul > li",
        "name_selector": "h2,h3,h4,strong,b",
        "description_selector": "p,span",
    },
    # 10 ── Broad fallback: any block-level element with a heading inside
    {
        "label": "generic-div-heading",
        "club_selector": "div",
        "name_selector": "h3,h4",
        "description_selector": "p",
    },
]

# ── Minimum results to trust a config ──────────────────────────────────────
MIN_RESULTS = 2


def _score_config(soup: BeautifulSoup, cfg: Dict[str, Any]) -> int:
    """Return the number of elements that produce a non-empty name."""
    elements = soup.select(cfg["club_selector"])
    if not elements:
        return 0
    count = 0
    name_sel = cfg.get("name_selector", "")
    for el in elements:
        if name_sel:
            found = el.select_one(name_sel)
            if found and found.get_text(strip=True):
                count += 1
        else:
            # No name selector — count presence of element itself
            count += 1
    return count


def detect_parser_config(html_content: str) -> Dict[str, Any]:
    """
    Analyse *html_content* and return the best-matching parser_config dict.

    The returned dict has at minimum ``club_selector`` and ``name_selector``
    keys and is ready for use by BS4Extractor.

    Falls back to a permissive config if nothing good is found.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    best_cfg: Optional[Dict[str, Any]] = None
    best_score = 0

    for profile in CANDIDATE_PROFILES:
        score = _score_config(soup, profile)
        label = profile.get("label", "?")
        logger.debug(f"SelectorDetector: '{label}' -> {score} results")

        if score > best_score:
            best_score = score
            best_cfg = profile

        # If the top two candidates are the same profile, stop early to avoid
        # over-fitting on a noisy selector like "div".
        if score >= 10 and label != "generic-div-heading":
            break

    if best_cfg and best_score >= MIN_RESULTS:
        # Strip internal 'label' key before returning
        result = {k: v for k, v in best_cfg.items() if k != "label"}
        logger.info(
            f"SelectorDetector: selected profile '{best_cfg['label']}' "
            f"({best_score} matching elements). club_selector={result['club_selector']!r}"
        )
        return result

    # Nothing worked well — return a very broad fallback
    logger.warning(
        "SelectorDetector: no profile matched >= 2 results. "
        "Falling back to broad heading scan."
    )
    return {
        "club_selector": "section,div",
        "name_selector": "h2,h3,h4",
        "description_selector": "p",
    }
