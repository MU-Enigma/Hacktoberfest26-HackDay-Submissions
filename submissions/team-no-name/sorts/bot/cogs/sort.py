import os
import nextcord
from nextcord.ext import commands
from sorts.database.connection import get_db
from sorts.database import models as db_models
from sorts.services.session_service import SessionService
from sorts.bot.views.questionnaire import QuestionnaireView
from sorts.bot.utils import BRAND_COLOR, create_sortling_embed, get_guild_university


class SortCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session_service = SessionService()

    @nextcord.slash_command(name="sort", description="Find the clubs that match who you are.")
    async def sort(self, interaction: nextcord.Interaction):
        """Starts an adaptive recommendation session for the user."""
        user_id = str(interaction.user.id)

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

                # Count total questions so the view can display progress
                total_questions = db.query(db_models.Question).filter_by(university_id=univ.id).count()
                if total_questions == 0:
                    embed, file = create_sortling_embed(
                        title="No Questions Available",
                        description="The questionnaire hasn't been set up for this university. Contact a Sortling administrator.",
                        is_error=True,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                session = self.session_service.create_session(db, univ.id, user_identifier=user_id)
                first_q = self.session_service.get_next_question(db, session.id)

                if not first_q:
                    embed, file = create_sortling_embed(
                        title="No Questions Available",
                        description="The questionnaire hasn't been set up for this university. Contact a Sortling administrator.",
                        is_error=True,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                view = QuestionnaireView(session.id, first_q, total_questions)

                embed = nextcord.Embed(
                    title=first_q.text,
                    description="> **Interactive Club Recommendation Quiz**\n\nSelect the option that fits you best below:",
                    color=BRAND_COLOR,
                )
                embed.set_footer(text="Sortling • Question 1")

                thinking_path = os.path.join("Sortling Mascot", "thinking.gif")
                file = None
                if os.path.exists(thinking_path):
                    file = nextcord.File(thinking_path, filename="thinking.gif")
                    embed.set_thumbnail(url="attachment://thinking.gif")

                if file:
                    await interaction.send(embed=embed, view=view, file=file, ephemeral=True)
                else:
                    await interaction.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            embed, file = create_sortling_embed(
                title="Something went wrong",
                description="Could not start the session. Please try again in a moment.",
                is_error=True,
            )
            await interaction.send(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(SortCog(bot))
