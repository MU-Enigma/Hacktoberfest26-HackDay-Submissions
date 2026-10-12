from typing import List, Dict, Any
import logging
from bs4 import BeautifulSoup
from sorts.core.interfaces import IExtractor

logger = logging.getLogger(__name__)

class BS4Extractor(IExtractor):
    def extract(self, html_content: str, parser_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts club information from HTML using BeautifulSoup and dynamic CSS selectors."""
        soup = BeautifulSoup(html_content, "html.parser")
        
        club_selector = parser_config.get("club_selector", "article")
        club_elements = soup.select(club_selector)
        logger.info(f"BS4Extractor: Found {len(club_elements)} elements matching selector '{club_selector}'")

        clubs = []
        for index, elem in enumerate(club_elements):
            try:
                # Extract text helper
                def get_text(sel_key: str, default: str = "") -> str:
                    sel = parser_config.get(sel_key)
                    if not sel:
                        return default
                    found = elem.select_one(sel)
                    return found.get_text(strip=True) if found else default

                # Extract attribute helper
                def get_attr(sel_key: str, attr_name: str, default: str = None) -> Any:
                    sel = parser_config.get(sel_key)
                    if not sel:
                        return default
                    found = elem.select_one(sel)
                    return found.get(attr_name) if (found and found.has_attr(attr_name)) else default

                name = get_text("name_selector")
                if not name:
                    logger.warning(f"BS4Extractor: Element {index} missing name. Skipping.")
                    continue

                summary = get_text("summary_selector")
                description = get_text("description_selector")
                
                # If description is empty, use summary as description
                if not description:
                    description = summary

                meeting_frequency = get_text("meeting_frequency_selector")
                commitment = get_text("commitment_selector")
                # Try src first; fall back to data-src for lazy-loaded images
                image = get_attr("image_selector", "src") or get_attr("image_selector", "data-src")

                # Extract links intelligently
                website = get_attr("website_selector", "href")
                discord = get_attr("discord_selector", "href")
                instagram = get_attr("instagram_selector", "href")
                email = get_attr("email_selector", "href")

                # Fallback link scanning: if links were not found by explicit selectors, scan all anchor tags inside the card
                anchors = elem.find_all("a")
                for a in anchors:
                    href = a.get("href", "")
                    if not href:
                        continue
                    
                    if "discord.gg" in href or "discord.com/invite" in href:
                        if not discord:
                            discord = href
                    elif "instagram.com" in href:
                        if not instagram:
                            instagram = href
                    elif href.startswith("mailto:"):
                        if not email:
                            email = href
                    elif not website and href.startswith("http") and not any(x in href for x in ["discord", "instagram"]):
                        website = href

                # Clean up email mailto: prefix
                if email and email.startswith("mailto:"):
                    email = email[7:]

                clubs.append({
                    "name": name,
                    "summary": summary,
                    "description": description,
                    "website": website,
                    "discord": discord,
                    "instagram": instagram,
                    "email": email,
                    "image": image,
                    "meeting_frequency": meeting_frequency,
                    "commitment": commitment,
                })
                logger.debug(f"BS4Extractor: Successfully extracted club: {name}")

            except Exception as e:
                logger.error(f"BS4Extractor: Error parsing element {index}: {str(e)}")
                continue

        return clubs
