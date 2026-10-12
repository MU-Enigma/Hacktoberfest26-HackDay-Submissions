import nextcord
from sorts.database.connection import get_db
from sorts.services.import_service import ImportService
from sorts.bot.utils import BRAND_COLOR

class AdminPreviewView(nextcord.ui.View):
    def __init__(self, job_id: int):
        super().__init__(timeout=300.0)  # 5 minutes timeout for admin action
        self.job_id = job_id
        self.import_service = ImportService()

    @nextcord.ui.button(label="Publish Changes", style=nextcord.ButtonStyle.success)
    async def publish_btn(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Disable buttons to avoid double clicks
        button.disabled = True
        self.clear_items()
        
        try:
            with get_db() as db:
                job = self.import_service.get_job(db, self.job_id)
                if job and job.status == "approved":
                    embed = nextcord.Embed(
                        title="Already Published",
                        description="These changes are already live. Run `/admin sync` to fetch fresh data.",
                        color=BRAND_COLOR,
                    )
                    await interaction.response.edit_message(embed=embed, view=None)
                    return

                self.import_service.publish_job(db, self.job_id)

            embed = nextcord.Embed(
                title="Published",
                description="The club directory has been updated. Students will see the latest data immediately.",
                color=BRAND_COLOR,
            )
            await interaction.response.edit_message(embed=embed, view=None)
        except Exception as e:
            embed = nextcord.Embed(
                title="Publish Failed",
                description=f"Could not publish changes.\n`{str(e)}`",
                color=BRAND_COLOR,
            )
            await interaction.response.edit_message(embed=embed, view=None)
