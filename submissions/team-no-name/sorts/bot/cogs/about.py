import nextcord
from nextcord.ext import commands
from sorts.database.connection import get_db
from sorts.bot.utils import create_sortling_embed, BRAND_COLOR, get_guild_university, clean_text


class AboutCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(name="about", description="Learn about Sortling and how it works.")
    async def about(self, interaction: nextcord.Interaction):
        """Displays the university profile and a short explanation of Sortling."""
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

                desc_parts = [
                    "> **Your campus, sorted.**",
                    "",
                    "## About",
                    "Sortling connects students with clubs, hackathons, and opportunities at their campus. Answer a few questions and get matched with communities that fit your skills, interests, and schedule.",
                    "",
                    "━━━━━━━━━━━━━━━━━━━━━━━",
                    "",
                    "## How it Works",
                    "• **Club Matching**: Type `/sort` to answer a few questions and get personalized club recommendations.",
                    "• **Campus Clubs Directory**: Type `/clubs` or `/club <name>` to explore verified student organizations.",
                    "• **Hackathons & Opportunities**: Type `/events` or `/event <name>` to discover upcoming competitions, prizes, and registration details.",
                    "",
                    "━━━━━━━━━━━━━━━━━━━━━━━",
                    "",
                    "## Legal & Privacy",
                    "[Terms of Service](https://sortling-bot.onrender.com/terms)  ·  [Privacy Policy](https://sortling-bot.onrender.com/privacy)"
                ]

                embed, file = create_sortling_embed(
                    title="Sortling",
                    description="\n".join(desc_parts),
                    is_error=False,
                )
                embed.set_footer(text="Sortling • Club Matching for Students")

                if file:
                    await interaction.send(embed=embed)
                else:
                    await interaction.send(embed=embed)

        except Exception as e:
            embed, file = create_sortling_embed(
                title="Something went wrong",
                description="Could not load the about page. Please try again.",
                is_error=True,
            )
            await interaction.send(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(AboutCog(bot))
