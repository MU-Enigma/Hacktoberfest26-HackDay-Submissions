import logging
from datetime import datetime
import nextcord
from nextcord.ext import commands

from sorts.database.connection import get_db
from sorts.database import models as db_models
from sorts.bot.utils import get_guild_university, create_sortling_embed, BRAND_COLOR

logger = logging.getLogger(__name__)


class FeedbackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(name="feedback", description="Rate your club recommendations.")
    async def feedback(
        self,
        interaction: nextcord.Interaction,
        rating: int = nextcord.SlashOption(
            description="How well did the matches fit? (1 = poor, 5 = excellent)",
            choices=[1, 2, 3, 4, 5],
        ),
        comments: str = nextcord.SlashOption(
            description="Anything you'd like to share about your matches?",
            required=False,
        ),
    ):
        """Records feedback tied to the user's most recent session or general feedback."""
        user_id = str(interaction.user.id)
        user_name = str(interaction.user)

        logger.info(f"[FEEDBACK_SUBMITTED] User='{user_name}' ({user_id}) Rating={rating}/5 Comments='{comments or 'None'}'")
        print(f"[FEEDBACK_LOG] User='{user_name}' ({user_id}) Rating={rating}/5 Comments='{comments or 'None'}'", flush=True)

        try:
            with get_db() as db:
                univ = get_guild_university(db, interaction.guild_id)
                if not univ:
                    embed, file = create_sortling_embed(
                        title="Not Configured",
                        description="This server hasn't been linked to a university yet. Ask an administrator to run `/setup`.",
                        is_error=True,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                latest_session = (
                    db.query(db_models.RecommendationSession)
                    .filter_by(user_identifier=user_id, university_id=univ.id)
                    .order_by(db_models.RecommendationSession.created_at.desc())
                    .first()
                )

                rec_id = None
                if latest_session and latest_session.recommendations:
                    rec_id = latest_session.recommendations[0].id

                if rec_id:
                    existing = db.query(db_models.Feedback).filter_by(recommendation_id=rec_id).first()
                    if existing:
                        existing.rating = rating
                        existing.comments = comments or existing.comments
                        existing.created_at = datetime.utcnow()
                        db.commit()
                        msg = "Your feedback has been updated. Thank you!"
                    else:
                        db.add(db_models.Feedback(
                            recommendation_id=rec_id,
                            rating=rating,
                            comments=comments,
                            created_at=datetime.utcnow(),
                        ))
                        db.commit()
                        msg = "Feedback received! It helps improve future matches."
                else:
                    # Record feedback even if no session recommendation exists
                    dummy_rec = db_models.Recommendation(
                        session_id=latest_session.id if latest_session else None,
                        club_id=1,
                        rank=1,
                        score=1.0,
                        explanation="General Feedback"
                    )
                    db.add(dummy_rec)
                    db.commit()
                    db.refresh(dummy_rec)

                    db.add(db_models.Feedback(
                        recommendation_id=dummy_rec.id,
                        rating=rating,
                        comments=comments or "General Student Feedback",
                        created_at=datetime.utcnow(),
                    ))
                    db.commit()
                    msg = "Feedback received! Thank you for helping us improve."

                embed, file = create_sortling_embed(title="Feedback Saved", description=msg, is_error=False)
                await interaction.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error saving feedback: {e}", exc_info=True)
            embed, file = create_sortling_embed(
                title="Something went wrong",
                description="Could not save feedback. Please try again.",
                is_error=True,
            )
            await interaction.send(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(FeedbackCog(bot))
