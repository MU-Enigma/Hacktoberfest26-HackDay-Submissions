import nextcord
from nextcord.ext import commands
from sorts.database.connection import get_db
from sorts.services.club_service import ClubService
from sorts.database import models as db_models
from sorts.bot.views.club_list import ClubPagingView
from sorts.bot.utils import BRAND_COLOR, get_guild_university, create_sortling_embed, clean_text


class ClubsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.club_service = ClubService()

    @nextcord.slash_command(name="clubs", description="Browse the full club directory.")
    async def clubs(self, interaction: nextcord.Interaction):
        """Presents a paginated list of all active clubs."""
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

                clubs, total_count = self.club_service.get_clubs_paginated(db, univ.id, page=1, per_page=3)

                if total_count == 0:
                    embed, file = create_sortling_embed(
                        title="No Clubs Published",
                        description="The club directory is empty. Ask an administrator to run `/admin sync`.",
                        is_error=False,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                view = ClubPagingView(univ.id, 1, 3, total_count, None)
                await interaction.send(embed=view.make_embed(clubs), view=view)

        except Exception as e:
            embed, file = create_sortling_embed(
                title="Something went wrong",
                description="Could not load the club directory. Please try again.",
                is_error=True,
            )
            await interaction.send(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="club", description="Look up a specific club by name.")
    async def club(
        self,
        interaction: nextcord.Interaction,
        name: str = nextcord.SlashOption(description="Club name or keyword to search for"),
    ):
        """Displays the full profile card for a specific club."""
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

                matches = self.club_service.search_clubs(db, univ.id, name)

                if not matches:
                    embed, file = create_sortling_embed(
                        title="No Results",
                        description=f"No club found matching **{name}**. Browse the full list with `/clubs`.",
                        is_error=True,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                if len(matches) > 1:
                    names_list = "\n".join(f"• {c.name}" for c in matches[:6])
                    embed, file = create_sortling_embed(
                        title="Multiple Results",
                        description=f"Several clubs match **{name}**. Try a more specific name:\n\n{names_list}",
                        is_error=False,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                club = matches[0]

                summary = clean_text(club.summary)
                full_desc = clean_text(club.description or "")

                cat_text = clean_text(club.category or "General")
                type_text = "Official Club" if club.official else "Verified Community Club"
                ver = club.get_verification()
                conf = ver.get("confidence", 100 if club.official else 75)
                is_ver = "Verified" if ver.get("verified", True) else "Unverified"

                desc_parts = [
                    f"> **{summary}**",
                ]
                if full_desc:
                    desc_parts.extend([
                        "",
                        "## About",
                        full_desc,
                    ])

                desc_parts.extend([
                    "",
                    "━━━━━━━━━━━━━━━━━━━━━━━",
                    "",
                    "## Club Overview",
                    f"• **Category**: {cat_text}",
                    f"• **Club Type**: {type_text}",
                    "",
                    "━━━━━━━━━━━━━━━━━━━━━━━",
                    "",
                    "## Details & Schedule",
                    f"• **Meeting Schedule**: {clean_text(club.meeting_frequency or 'Bi-weekly sessions')}",
                    f"• **Commitment Level**: {clean_text(club.commitment or 'Medium commitment')}",
                    f"• **Verification Status**: {conf}% Confidence ({is_ver})"
                ])

                soc_dict = club.get_socials()
                social_labels = {
                    "website": "Website",
                    "instagram": "Instagram",
                    "linkedin": "LinkedIn",
                    "github": "GitHub",
                    "youtube": "YouTube",
                    "discord": "Discord",
                    "linktree": "Linktree",
                    "beacons": "Beacons",
                    "email": "Email"
                }

                social_links = []
                for key, label in social_labels.items():
                    val = soc_dict.get(key)
                    if val and val not in ["-", "Unknown", "N/A", "none", "null"]:
                        if key == "email" and not val.startswith("mailto:"):
                            social_links.append(f"[{label}](mailto:{val})")
                        else:
                            social_links.append(f"[{label}]({val})")

                if social_links:
                    desc_parts.extend([
                        "",
                        "━━━━━━━━━━━━━━━━━━━━━━━",
                        "",
                        "## Official Links",
                        "  ·  ".join(social_links)
                    ])

                embed = nextcord.Embed(
                    title=clean_text(club.name),
                    description="\n".join(desc_parts),
                    color=BRAND_COLOR,
                )
                if club.image:
                    embed.set_thumbnail(url=club.image)

                embed.set_footer(text="Sortling • Campus Clubs")
                await interaction.send(embed=embed)

        except Exception as e:
            embed, file = create_sortling_embed(
                title="Something went wrong",
                description="Could not load club details. Please try again.",
                is_error=True,
            )
            await interaction.send(embed=embed, ephemeral=True)

    @club.on_autocomplete("name")
    async def club_autocomplete(self, interaction: nextcord.Interaction, name: str):
        try:
            with get_db() as db:
                univ = get_guild_university(db, interaction.guild_id)
                if not univ:
                    await interaction.response.send_autocomplete([])
                    return
                matches = self.club_service.search_clubs(db, univ.id, name)
                choices = [c.name for c in matches[:25]]
                await interaction.response.send_autocomplete(choices)
        except Exception:
            await interaction.response.send_autocomplete([])


def setup(bot):
    bot.add_cog(ClubsCog(bot))
