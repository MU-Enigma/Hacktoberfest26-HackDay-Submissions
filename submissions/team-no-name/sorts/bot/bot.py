import os
import logging
import nextcord
from nextcord.ext import commands

from sorts.config import settings
from sorts.bot.utils import create_sortling_embed

logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_CHANNELS = {1475575132108882133, 1475575133979803653, 1475575132108882132}


class SortlingBot(commands.Bot):
    def __init__(self):
        intents = nextcord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def on_ready(self):
        logger.info(f"Bot connected as: {self.user.name} (ID: {self.user.id})")
        logger.info("Syncing slash commands globally...")
        activity = nextcord.Activity(type=nextcord.ActivityType.listening, name="/sort")
        await self.change_presence(activity=activity)
        logger.info("Ready to guide students!")

    async def check_application_command(self, interaction: nextcord.Interaction) -> bool:
        cmd_name = interaction.application_command.name if interaction.application_command else ""

        # Restrict administrative commands (/admin, /setup) to Server Owners and Administrators/Managers
        if cmd_name in ("admin", "setup"):
            is_owner = interaction.guild and interaction.user and (interaction.guild.owner_id == interaction.user.id)
            is_admin = interaction.user_permissions and (
                interaction.user_permissions.administrator or interaction.user_permissions.manage_guild
            )
            if not is_owner and not is_admin:
                embed, file = create_sortling_embed(
                    title="Access Denied",
                    description="Only server owners and administrators can run administrative commands.",
                    is_error=True,
                )
                try:
                    if file:
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                    else:
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                except Exception:
                    pass
                return False
            return True

        # Allow Admins and Mods (users with Administrator, Manage Guild, or Manage Messages permissions) anywhere
        if interaction.user_permissions:
            perms = interaction.user_permissions
            if perms.administrator or perms.manage_guild or perms.manage_messages:
                return True

        env_channels = os.getenv("SORTLING_ALLOWED_CHANNELS", "")
        if env_channels:
            allowed_channels = {int(c.strip()) for c in env_channels.split(",") if c.strip().isdigit()}
        else:
            allowed_channels = DEFAULT_ALLOWED_CHANNELS

        # Enforce dedicated channel restriction if triggered by a student in an unapproved channel
        if interaction.channel_id and interaction.channel_id not in allowed_channels:
            channel_mentions = " or ".join([f"<#{cid}>" for cid in sorted(allowed_channels)])
            embed, file = create_sortling_embed(
                title="Wrong Channel 📍",
                description=f"Please use {channel_mentions} to run Sortling commands!",
                is_error=False,
            )
            try:
                if file:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception:
                pass
            return False

        return True


def run_bot():
    """Bootstraps and executes the Nextcord Bot client with automatic reconnection resiliency."""
    if not settings.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN is missing! Please configure it in your environment/.env file.")
        print("Error: DISCORD_TOKEN is missing. Please set it in your .env file.")
        return

    import time
    import asyncio

    while True:
        try:
            # Explicitly create and set a fresh event loop for each connection attempt
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            bot = SortlingBot()

            # Load all Cogs
            extensions = [
                "sorts.bot.cogs.about",
                "sorts.bot.cogs.clubs",
                "sorts.bot.cogs.feedback",
                "sorts.bot.cogs.sort",
                "sorts.bot.cogs.admin",
                "sorts.bot.cogs.events"
            ]

            for ext in extensions:
                try:
                    bot.load_extension(ext)
                    logger.info(f"Loaded extension: {ext}")
                except Exception as e:
                    logger.exception(f"Failed to load extension {ext}: {str(e)}")

            logger.info("Connecting Sortling to Discord Gateway...")
            bot.run(settings.DISCORD_TOKEN)
            logger.warning("Bot event loop exited normally. Reconnecting in 10 seconds...")
            time.sleep(10)
        except nextcord.errors.HTTPException as http_err:
            if getattr(http_err, "status", None) == 429:
                logger.warning("Discord API Cloudflare ban (429) active. Backing off for 10 minutes (600s) to allow complete rate-limit cooldown...")
                time.sleep(600)
            else:
                logger.error(f"Bot HTTP exception: {http_err}. Reconnecting in 30 seconds...")
                time.sleep(30)
        except Exception as e:
            logger.error(f"Bot execution exception: {e}. Reconnecting in 30 seconds...", exc_info=True)
            time.sleep(30)
