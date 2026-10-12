import os
import logging
from typing import Optional, List, Dict
import nextcord
from sqlalchemy.orm import Session

from sorts.database.connection import get_db
from sorts.database import models as db_models
from sorts.services.session_service import SessionService
from sorts.services.training_service import TrainingService
from sorts.bot.utils import BRAND_COLOR, clean_text, create_sortling_embed

logger = logging.getLogger(__name__)

RANK_MEDALS = {
    1: "`1`",
    2: "`2`",
    3: "`3`",
}

INTEREST_NODES = [
    ("software", "Software & Coding"),
    ("web_dev", "Web & App Development"),
    ("ai_data", "AI & Machine Learning"),
    ("competitive_coding", "Competitive Programming"),
    ("hardware", "Hardware & Electronics"),
    ("robotics_automotive", "Robotics & BAJA Racing"),
    ("aerospace", "Aerospace & Drones"),
    ("public_speaking", "Public Speaking & Debates"),
    ("mun_journalism", "Model UN & Journalism"),
    ("entrepreneurship", "Entrepreneurship & Startups"),
    ("music", "Music & Jamming"),
    ("performing_arts", "Dance & Theatre"),
    ("design_media", "Design & Photography"),
    ("gaming_esports", "Gaming & Esports"),
    ("social", "Social & Community Events"),
]


class OptionButton(nextcord.ui.Button):
    def __init__(self, option_id: int, question_id: int, label: str, style: nextcord.ButtonStyle):
        super().__init__(label=label, style=style)
        self.option_id = option_id
        self.question_id = question_id

    async def callback(self, interaction: nextcord.Interaction):
        view: "QuestionnaireView" = self.view

        try:
            with get_db() as db:
                view.session_service.submit_answer(db, view.session_id, self.question_id, self.option_id)
                next_q = view.session_service.get_next_question(db, view.session_id)

                if next_q:
                    view.advance(next_q)
                    embed = nextcord.Embed(
                        title=clean_text(next_q.text),
                        description="Select the option that fits you best.",
                        color=BRAND_COLOR,
                    )
                    embed.set_footer(
                        text=f"Sortling • Question {view.question_number}"
                    )
                    embed.set_thumbnail(url="attachment://thinking.gif")
                    await interaction.response.edit_message(embed=embed, view=view)

                else:
                    loading_embed = nextcord.Embed(
                        title="Analyzing Your Profile...",
                        description="Finding your best-fit club matches...",
                        color=BRAND_COLOR,
                    )
                    thinking_path = os.path.join("Sortling Mascot", "thinking.gif")
                    file = None
                    if os.path.exists(thinking_path):
                        file = nextcord.File(thinking_path, filename="thinking.gif")
                        loading_embed.set_thumbnail(url="attachment://thinking.gif")
                        await interaction.response.edit_message(embed=loading_embed, file=file, view=None)
                    else:
                        await interaction.response.edit_message(embed=loading_embed, view=None)

                    recs = view.session_service.generate_recommendations(db, view.session_id)

                    if not recs:
                        embed, file = create_sortling_embed(
                            title="No Matches Found",
                            description="We couldn't find matches for your profile. Try /clubs to browse all clubs.",
                            is_error=False,
                        )
                        if file:
                            await interaction.followup.send(embed=embed, file=file)
                        else:
                            await interaction.followup.send(embed=embed)
                        return

                    univ = db.query(db_models.University).filter_by(
                        id=recs[0].session.university_id
                    ).first()
                    univ_name = univ.name if univ else "your campus"

                    embed = nextcord.Embed(
                        title="Your Club Matches",
                        description=(
                            f"> **Top recommendation matches based on your answers.**\n\n"
                            f"Here are the best-fit clubs for you at **{univ_name}**:\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=BRAND_COLOR,
                    )

                    for r in recs[:3]:
                        club = r.club
                        medal = RANK_MEDALS.get(r.rank, f"#{r.rank}")
                        embed.add_field(
                            name=f"{medal}  {clean_text(club.name)}",
                            value=(
                                f"> **{clean_text(club.summary)}**\n\n"
                                f"• **Why you fit**: {clean_text(r.explanation)}"
                            ),
                            inline=False,
                        )

                    embed.set_footer(text="Sortling • Rate your matches anytime with /feedback")

                    icon_path = os.path.join("Sortling Mascot", "Icon_Neutral.png")
                    file = None
                    if os.path.exists(icon_path):
                        file = nextcord.File(icon_path, filename="Icon_Neutral.png")
                        embed.set_thumbnail(url="attachment://Icon_Neutral.png")

                    result_view = RecommendationResultsView(view.session_id)

                    if file:
                        await interaction.followup.send(embed=embed, file=file, view=result_view)
                    else:
                        await interaction.followup.send(embed=embed, view=result_view)

        except Exception as e:
            logger.error(f"Questionnaire error: {e}", exc_info=True)
            embed, file = create_sortling_embed(
                title="Something went wrong",
                description="An error occurred. Please try running `/sort` again.",
                is_error=True,
            )
            try:
                if file:
                    await interaction.followup.send(embed=embed, file=file, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception:
                pass


class QuestionnaireView(nextcord.ui.View):
    def __init__(self, session_id: str, initial_q: db_models.Question, total_questions: int = 16):
        super().__init__(timeout=300.0)
        self.session_id = session_id
        self.session_service = SessionService()
        self.total_questions = total_questions
        self.question_number = 1
        self._populate_buttons(initial_q)

    def advance(self, question: db_models.Question):
        """Move to the next question, updating buttons and counter."""
        self.question_number += 1
        self._populate_buttons(question)

    def _populate_buttons(self, question: db_models.Question):
        """Rebuild buttons for the current question using uniform neutral styling."""
        self.clear_items()
        for idx, opt in enumerate(question.options):
            btn = OptionButton(
                option_id=opt.id,
                question_id=question.id,
                label=opt.text,
                style=nextcord.ButtonStyle.secondary,
            )
            self.add_item(btn)


class RefineInterestsView(nextcord.ui.View):
    def __init__(self, session_id: str, active_trait_slugs: List[str]):
        super().__init__(timeout=180.0)
        self.session_id = session_id
        self.session_service = SessionService()

        options = []
        for slug, label in INTEREST_NODES:
            is_checked = slug in active_trait_slugs
            options.append(
                nextcord.SelectOption(
                    label=label,
                    value=slug,
                    default=is_checked,
                    description="Matched from quiz" if is_checked else "Tap to add"
                )
            )

        self.select = nextcord.ui.Select(
            custom_id=f"refine_select_{session_id[:8]}",
            placeholder="Check or uncheck your interest areas...",
            min_values=0,
            max_values=len(options),
            options=options,
        )
        self.select.callback = self._on_select_submit
        self.add_item(self.select)

    async def _on_select_submit(self, interaction: nextcord.Interaction):
        selected_slugs = set(self.select.values)

        try:
            with get_db() as db:
                session = self.session_service.get_session(db, self.session_id)
                if not session:
                    await interaction.response.send_message("Session expired.", ephemeral=True)
                    return

                # Calculate positive traits safely inside DB session
                session_traits_db = db.query(db_models.SessionTrait).filter(
                    db_models.SessionTrait.session_id == self.session_id
                ).all()

                old_positive = set()
                for st in session_traits_db:
                    if st.value > 0.0:
                        t_obj = db.query(db_models.Trait).filter_by(id=st.trait_id).first()
                        if t_obj:
                            old_positive.add(t_obj.slug)

                added_interests = list(selected_slugs - old_positive)
                removed_interests = list(old_positive - selected_slugs)

                logger.info(
                    f"[TRAINING_LOG] Missed Interest Feedback for session {self.session_id}: "
                    f"Added={added_interests}, Removed={removed_interests}"
                )

                if session.recommendations:
                    rec_id = session.recommendations[0].id
                    comment_str = f"[MISSED_INTEREST_FEEDBACK] Added: {added_interests}, Removed: {removed_interests}"
                    fb = db_models.Feedback(
                        recommendation_id=rec_id,
                        rating=4,
                        comments=comment_str
                    )
                    db.add(fb)

                # Trigger Automated Self-Training Engine
                try:
                    training_svc = TrainingService()
                    training_svc.process_feedback_deltas(db, self.session_id, added_interests, removed_interests)
                except Exception as te:
                    logger.error(f"Self-training execution error: {te}", exc_info=True)

                all_traits = db.query(db_models.Trait).all()
                trait_map = {t.slug: t for t in all_traits}

                for slug, label in INTEREST_NODES:
                    if slug in trait_map:
                        t_obj = trait_map[slug]
                        st = db.query(db_models.SessionTrait).filter_by(
                            session_id=self.session_id, trait_id=t_obj.id
                        ).first()
                        if not st:
                            st = db_models.SessionTrait(
                                session_id=self.session_id, trait_id=t_obj.id, value=0.0
                            )
                            db.add(st)

                        if slug in selected_slugs:
                            st.value = 1.0
                        else:
                            st.value = -0.5

                session.status = "active"
                db.commit()

                next_q = self.session_service.get_next_question(db, self.session_id)

                if next_q and added_interests:
                    view = QuestionnaireView(self.session_id, next_q)
                    embed = nextcord.Embed(
                        title=f"Follow-up: {clean_text(next_q.text)}",
                        description=(
                            f"**Interest Profile Updated!**\n"
                            f"Added: {', '.join(added_interests)}.\n\n"
                            f"Select the option that fits you best below:"
                        ),
                        color=BRAND_COLOR,
                    )
                    embed.set_footer(text="Sortling • Quick follow-up")

                    thinking_path = os.path.join("Sortling Mascot", "thinking.gif")
                    file = None
                    if os.path.exists(thinking_path):
                        file = nextcord.File(thinking_path, filename="thinking.gif")
                        embed.set_thumbnail(url="attachment://thinking.gif")

                    if file:
                        await interaction.response.send_message(
                            embed=embed,
                            view=view,
                            file=file,
                            ephemeral=True
                        )
                    else:
                        await interaction.response.send_message(
                            embed=embed,
                            view=view,
                            ephemeral=True
                        )
                else:
                    new_recs = self.session_service.generate_recommendations(db, self.session_id)

                    univ = db.query(db_models.University).filter_by(id=session.university_id).first()
                    univ_name = univ.name if univ else "your campus"

                    embed = nextcord.Embed(
                        title="Your Refined Club Matches",
                        description=(
                            f"> **Updated recommendation matches based on your refined interests.**\n\n"
                            f"Re-ranked clubs for you at **{univ_name}**:\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=BRAND_COLOR,
                    )

                    for r in new_recs[:3]:
                        club = r.club
                        medal = RANK_MEDALS.get(r.rank, f"#{r.rank}")
                        embed.add_field(
                            name=f"{medal}  {clean_text(club.name)}",
                            value=(
                                f"> **{clean_text(club.summary)}**\n\n"
                                f"• **Why you fit**: {clean_text(r.explanation)}"
                            ),
                            inline=False,
                        )

                    embed.set_footer(text="Sortling • Tailored for you")

                    icon_path = os.path.join("Sortling Mascot", "Icon_Neutral.png")
                    file = None
                    if os.path.exists(icon_path):
                        file = nextcord.File(icon_path, filename="Icon_Neutral.png")
                        embed.set_thumbnail(url="attachment://Icon_Neutral.png")

                    result_view = RecommendationResultsView(self.session_id)
                    if file:
                        await interaction.response.send_message(embed=embed, view=result_view, file=file, ephemeral=True)
                    else:
                        await interaction.response.send_message(embed=embed, view=result_view, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in _on_select_submit: {e}", exc_info=True)
            try:
                await interaction.response.send_message("An error occurred while saving your refined interests.", ephemeral=True)
            except Exception:
                pass


class RecommendationResultsView(nextcord.ui.View):
    def __init__(self, session_id: str):
        super().__init__(timeout=600.0)
        self.session_id = session_id
        self.session_service = SessionService()

    @nextcord.ui.button(label="Am I wrong?", style=nextcord.ButtonStyle.secondary)
    async def refine_interests_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        try:
            with get_db() as db:
                session = self.session_service.get_session(db, self.session_id)
                if not session:
                    await interaction.response.send_message("Session expired.", ephemeral=True)
                    return

                session_traits = db.query(db_models.SessionTrait).filter(
                    db_models.SessionTrait.session_id == self.session_id,
                    db_models.SessionTrait.value > 0.0
                ).all()

                active_trait_slugs = []
                for st in session_traits:
                    t_obj = db.query(db_models.Trait).filter_by(id=st.trait_id).first()
                    if t_obj:
                        active_trait_slugs.append(t_obj.slug)

                view = RefineInterestsView(self.session_id, active_trait_slugs)
                await interaction.response.send_message(
                    "**Refine Your Interests**\nCheck any missing interests or uncheck incorrect ones to re-rank your recommendations:",
                    view=view,
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error in refine_interests_button: {e}", exc_info=True)
            try:
                await interaction.response.send_message("An error occurred while opening interest refinement.", ephemeral=True)
            except Exception:
                pass

    @nextcord.ui.button(label="I want more!", style=nextcord.ButtonStyle.secondary)
    async def more_clubs_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        try:
            with get_db() as db:
                session = self.session_service.get_session(db, self.session_id)
                if not session:
                    await interaction.response.send_message("Session expired.", ephemeral=True)
                    return

                contenders = (
                    db.query(db_models.Recommendation)
                    .filter(
                        db_models.Recommendation.session_id == self.session_id,
                        db_models.Recommendation.rank > 3,
                        db_models.Recommendation.score > 0.05
                    )
                    .order_by(db_models.Recommendation.rank.asc())
                    .limit(3)
                    .all()
                )

                if not contenders:
                    embed, file = create_sortling_embed(
                        title="No Additional Matches",
                        description="There are no other close contenders matching your quiz profile. Try `/clubs` to browse the full directory!",
                        is_error=False,
                    )
                    if file:
                        await interaction.response.send_message(embed=embed, file=file, ephemeral=True)
                    else:
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                univ = db.query(db_models.University).filter_by(id=session.university_id).first()
                univ_name = univ.name if univ else "your campus"

                embed = nextcord.Embed(
                    title="Other Clubs You Might Enjoy",
                    description=(
                        f"> **Additional close contenders matching your profile.**\n\n"
                        f"More recommended clubs at **{univ_name}**:\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    color=BRAND_COLOR,
                )

                rank_badges = {4: "`4`", 5: "`5`", 6: "`6`"}
                for r in contenders:
                    club = r.club
                    badge = rank_badges.get(r.rank, f"#{r.rank}")
                    embed.add_field(
                        name=f"{badge}  {clean_text(club.name)}",
                        value=(
                            f"> **{clean_text(club.summary)}**\n\n"
                            f"• **Why you fit**: {clean_text(r.explanation)}"
                        ),
                        inline=False,
                    )

                embed.set_footer(text="Sortling • Close Contenders")

                icon_path = os.path.join("Sortling Mascot", "Icon_Neutral.png")
                file = None
                if os.path.exists(icon_path):
                    file = nextcord.File(icon_path, filename="Icon_Neutral.png")
                    embed.set_thumbnail(url="attachment://Icon_Neutral.png")

                if file:
                    await interaction.response.send_message(embed=embed, file=file, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in more_clubs_button: {e}", exc_info=True)
            try:
                await interaction.response.send_message("An error occurred while loading additional clubs.", ephemeral=True)
            except Exception:
                pass
