import nextcord
from sorts.database.connection import get_db
from sorts.services.import_service import ImportService
from sorts.bot.utils import BRAND_COLOR

_DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━"


class SetupOnboardingView(nextcord.ui.View):
    """
    Shown at the end of /setup for new universities.
    Lets the admin publish the crawled club directory in one click,
    or defer to /admin review later.
    """

    def __init__(self, job_id: int, q_count: int, club_count: int, univ_name: str):
        super().__init__(timeout=300.0)
        self.job_id = job_id
        self.q_count = q_count
        self.club_count = club_count
        self.univ_name = univ_name
        self.import_service = ImportService()

    # ── Publish Directory ────────────────────────────────────────────────────

    @nextcord.ui.button(label="Publish Directory", style=nextcord.ButtonStyle.success)
    async def publish_btn(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        button.disabled = True
        self.clear_items()

        try:
            with get_db() as db:
                job = self.import_service.get_job(db, self.job_id)
                if job and job.status == "approved":
                    desc = "\n".join([
                        f"> **{self.univ_name} is already live on Sortling.**",
                        "",
                        _DIVIDER,
                        "",
                        "## Summary",
                        f"• **Questions**: {self.q_count} loaded - `/sort` is ready for students.",
                        f"• **Clubs**: {self.club_count} already published.",
                        "",
                        _DIVIDER,
                        "",
                        "Run `/admin sync` to check for new changes.",
                    ])
                    embed = nextcord.Embed(title="Already Published", description=desc, color=BRAND_COLOR)
                    await interaction.response.edit_message(embed=embed, view=None, attachments=[])
                    return

                self.import_service.publish_job(db, self.job_id)

            desc = "\n".join([
                f"> **{self.univ_name} is now live on Sortling.**",
                "",
                _DIVIDER,
                "",
                "## Summary",
                f"• **Questions**: {self.q_count} loaded - `/sort` is ready for students.",
                f"• **Clubs**: {self.club_count} published to the directory.",
                "",
                _DIVIDER,
                "",
                "Students can run `/sort` to find their best-fit clubs.",
                "Use `/admin sync` anytime to pull fresh data from your website.",
            ])
            embed = nextcord.Embed(title="Setup Complete", description=desc, color=BRAND_COLOR)
            await interaction.response.edit_message(embed=embed, view=None, attachments=[])

        except Exception as e:
            desc = "\n".join([
                "The club directory could not be published.",
                "",
                _DIVIDER,
                "",
                "## What to do",
                "• Run `/admin review` to retry publishing.",
                f"• Error: `{e}`",
            ])
            embed = nextcord.Embed(title="Publish Failed", description=desc, color=BRAND_COLOR)
            await interaction.response.edit_message(embed=embed, view=None, attachments=[])

    # ── Skip for Now ─────────────────────────────────────────────────────────

    @nextcord.ui.button(label="Skip for Now", style=nextcord.ButtonStyle.secondary)
    async def skip_btn(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.clear_items()

        desc = "\n".join([
            f"> **{self.univ_name} is registered. Club directory is not yet published.**",
            "",
            _DIVIDER,
            "",
            "## Summary",
            f"• **Questions**: {self.q_count} loaded - `/sort` is active.",
            f"• **Clubs**: {self.club_count} clubs staged, pending review.",
            "",
            _DIVIDER,
            "",
            "Run `/admin review` when you are ready to publish the club directory.",
        ])
        embed = nextcord.Embed(title="Setup Saved", description=desc, color=BRAND_COLOR)
        await interaction.response.edit_message(embed=embed, view=None, attachments=[])
