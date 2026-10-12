import nextcord
from sorts.database.connection import get_db
from sorts.services.club_service import ClubService
from sorts.database import models as db_models
from sorts.bot.utils import BRAND_COLOR, clean_text

class ClubPagingView(nextcord.ui.View):
    def __init__(self, university_id: int, current_page: int, per_page: int, total_count: int, primary_color_hex: str):
        super().__init__(timeout=120.0)
        self.university_id = university_id
        self.page = current_page
        self.per_page = per_page
        self.total_count = total_count
        self.club_service = ClubService()
        self.color = BRAND_COLOR
        self.update_buttons()

    def update_buttons(self):
        """Disables or enables pagination buttons based on current page index."""
        self.prev_page_btn.disabled = self.page <= 1
        self.next_page_btn.disabled = self.page * self.per_page >= self.total_count

    def make_embed(self, clubs: list[db_models.Club]) -> nextcord.Embed:
        embed = nextcord.Embed(
            title=clean_text(f"Club Directory - Page {self.page}"),
            description=(
                f"> **Explore verified campus clubs and student organizations.**\n\n"
                f"Showing clubs **{((self.page - 1) * self.per_page) + 1}** to **{min(self.page * self.per_page, self.total_count)}** of **{self.total_count}**:\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=self.color
        )
        for club in clubs:
            lines = [f"> **{clean_text(club.summary)}**"]
            if club.commitment:
                lines.append(f"• **Commitment**: {clean_text(club.commitment)}")
            embed.add_field(
                name=clean_text(club.name),
                value="\n".join(lines),
                inline=False
            )
        embed.set_footer(text="Sortling • Type /club <name> to view full profile")
        return embed

    @nextcord.ui.button(label="< Previous", style=nextcord.ButtonStyle.secondary)
    async def prev_page_btn(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if self.page > 1:
            self.page -= 1
            with get_db() as db:
                clubs, _ = self.club_service.get_clubs_paginated(db, self.university_id, self.page, self.per_page)
                self.update_buttons()
                await interaction.response.edit_message(embed=self.make_embed(clubs), view=self)

    @nextcord.ui.button(label="Next >", style=nextcord.ButtonStyle.secondary)
    async def next_page_btn(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if self.page * self.per_page < self.total_count:
            self.page += 1
            with get_db() as db:
                clubs, _ = self.club_service.get_clubs_paginated(db, self.university_id, self.page, self.per_page)
                self.update_buttons()
                await interaction.response.edit_message(embed=self.make_embed(clubs), view=self)
