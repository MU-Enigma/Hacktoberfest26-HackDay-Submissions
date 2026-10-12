import os
import nextcord
from nextcord.ext import commands
from sorts.database.connection import get_db
from sorts.database import models as db_models
from sorts.services.import_service import ImportService
from sorts.bot.views.admin_preview import AdminPreviewView
from sorts.bot.utils import BRAND_COLOR, create_sortling_embed, get_guild_university, clean_text


def _clean_url(url: str) -> str:
    """
    Strips Google (and other) tracking parameters that get appended when
    copying links from search results, e.g. &ved=...&usg=...
    These turn a valid URL into a 404 because they are concatenated directly
    onto the path instead of after a proper '?'.
    """
    import re
    # Remove &ved=... &usg=... &sa=... that Google injects after the real URL
    url = re.sub(r'&(ved|usg|sa|ei|sqi|source|rlz|oq|gs_lcp|sclient)=[^\s&]*', '', url)
    # If the URL now ends with a dangling '?' or '&', clean that up too
    url = url.rstrip('?&')
    return url.strip()


def _is_admin(interaction: nextcord.Interaction) -> bool:
    if not interaction.user:
        return False
    if interaction.guild and interaction.guild.owner_id == interaction.user.id:
        return True
    if hasattr(interaction.user, "guild_permissions"):
        perms = interaction.user.guild_permissions
        return bool(perms.administrator or perms.manage_guild)
    return False


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.import_service = ImportService()

    # ─── /setup ───────────────────────────────────────────────────────────────

    @nextcord.slash_command(name="setup", description="Link this server to a university profile.")
    async def setup_university(
        self,
        interaction: nextcord.Interaction,
        name: str = nextcord.SlashOption(description="Full name of the university"),
        website: str = nextcord.SlashOption(description="Official website URL"),
        logo_url: str = nextcord.SlashOption(description="URL to the university logo", required=False),
        description: str = nextcord.SlashOption(description="Short one-line description", required=False),
    ):
        """Registers or updates this server's university profile."""
        if not _is_admin(interaction):
            embed, file = create_sortling_embed(
                title="Access Denied",
                description="Only server administrators can run setup.",
                is_error=True,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild_id = interaction.guild_id
        if not guild_id:
            embed, file = create_sortling_embed(
                title="Server Only",
                description="This command can only be used inside a Discord server.",
                is_error=True,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        from sorts.config.settings import EXEMPTED_GUILDS
        if guild_id in EXEMPTED_GUILDS:
            embed, file = create_sortling_embed(
                title="Already Configured",
                description="This server is pre-configured and does not need setup.",
                is_error=False,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        _DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━"
        _thinking_path = os.path.join("Sortling Mascot", "thinking.gif")

        # Send step 1 embed immediately so admins can see progress (like /sort)
        _step1_embed = nextcord.Embed(
            title="Connecting to Sortling",
            description="Linking this server to Sortling...",
            color=BRAND_COLOR,
        )
        _step1_embed.set_footer(text="Sortling • Step 1 of 2")
        if os.path.exists(_thinking_path):
            _gif = nextcord.File(_thinking_path, filename="thinking.gif")
            _step1_embed.set_thumbnail(url="attachment://thinking.gif")
            await interaction.response.send_message(embed=_step1_embed, file=_gif, ephemeral=True)
        else:
            await interaction.response.send_message(embed=_step1_embed, ephemeral=True)

        try:
            with get_db() as db:
                univ = db.query(db_models.University).filter_by(guild_id=str(guild_id)).first()
                slug = f"guild_{guild_id}"

                cleaned_website = _clean_url(website) if (website and website.startswith("http")) else website
                src_url = cleaned_website if (cleaned_website and cleaned_website.startswith("http")) else f"sorts/assets/data/{slug}_clubs.html"
                src_type = "url" if (cleaned_website and cleaned_website.startswith("http")) else "file"

                if not univ:
                    # ── Create university ────────────────────────────────────
                    univ = db_models.University(
                        slug=slug,
                        name=name,
                        website=cleaned_website or website,
                        logo=logo_url,
                        description=description or f"Campus guide for {name}.",
                        guild_id=str(guild_id),
                    )
                    db.add(univ)
                    db.commit()
                    db.refresh(univ)

                    import_src = db_models.ImportSource(
                        university_id=univ.id,
                        name="Official Source",
                        source_type=src_type,
                        url=src_url,
                    )
                    db.add(import_src)
                    db.commit()

                    # Seed the universal question bank so /sort works immediately
                    from sorts.services.seed_service import seed_default_questions
                    q_count = seed_default_questions(db, univ.id)

                    # ── Step 2: scanning clubs ────────────────────────────
                    _step2_embed = nextcord.Embed(
                        title="Scanning Club Directory",
                        description="Crawling your website for clubs...",
                        color=BRAND_COLOR,
                    )
                    _step2_embed.set_footer(text="Sortling • Step 2 of 2")
                    _step2_embed.set_thumbnail(url="attachment://thinking.gif")
                    await interaction.edit_original_message(embed=_step2_embed)

                    # ── Auto-sync: crawl website and stage clubs ──────────────
                    job_id = None
                    diff = {"new": [], "updated": [], "removed": []}
                    sync_error = None
                    try:
                        sources = self.import_service.get_university_sources(db, univ.id)
                        if sources:
                            job_id = self.import_service.trigger_import(db, sources[0].id)
                            diff = self.import_service.get_draft_diff(db, job_id)
                    except Exception as sync_err:
                        sync_error = str(sync_err)

                    new_clubs = diff.get("new", [])
                    new_count = len(new_clubs)

                    if job_id and new_count > 0:
                        # ── Onboarding review embed ──────────────────────────
                        club_lines = [f"• {dc.name}" for dc in new_clubs[:12]]
                        if new_count > 12:
                            club_lines.append(f"• ... and {new_count - 12} more.")

                        desc_parts = [
                            f"> **{new_count} clubs found. Review before publishing to students.**",
                            "",
                            _DIVIDER,
                            "",
                            "## Questions Ready",
                            f"• {q_count} questions loaded - `/sort` is active.",
                            "",
                            _DIVIDER,
                            "",
                            f"## Clubs Found  ({new_count})",
                            *club_lines,
                            "",
                            _DIVIDER,
                            "",
                            "Click **Publish Directory** to make clubs visible to students.",
                            "Click **Skip for Now** to publish later using `/admin review`.",
                        ]
                        embed = nextcord.Embed(
                            title="Club Directory Preview",
                            description="\n".join(desc_parts),
                            color=BRAND_COLOR,
                        )
                        from sorts.bot.views.setup_onboarding import SetupOnboardingView
                        view = SetupOnboardingView(job_id, q_count, new_count, name)
                        await interaction.edit_original_message(embed=embed, view=view, attachments=[])

                    else:
                        # ── No clubs found or sync failed ────────────────────
                        lines = [
                            f"> **{name} is now registered on Sortling.**",
                            "",
                            _DIVIDER,
                            "",
                            "## Summary",
                            f"• {q_count} questions loaded - `/sort` is active.",
                        ]
                        if sync_error:
                            lines += [
                                "• Unable to reach your website. The club directory could not be loaded.",
                                f"• Reason: `{sync_error}`",
                                "• Check the URL is correct, then run `/admin sync` to retry.",
                            ]
                        else:
                            lines += [
                                "• No clubs were found on your website.",
                                "• The page may require a login, use JavaScript, or list clubs differently.",
                                "• Use `/admin add_club` to add clubs manually, or `/admin sync` to retry with a different URL.",
                            ]
                        lines += ["", _DIVIDER]
                        embed = nextcord.Embed(
                            title="Setup Complete",
                            description="\n".join(lines),
                            color=BRAND_COLOR,
                        )
                        await interaction.edit_original_message(embed=embed, view=None, attachments=[])

                else:
                    # ── Update existing university profile ───────────────────
                    univ.name = name
                    if website:
                        univ.website = cleaned_website or website
                    if logo_url:
                        univ.logo = logo_url
                    if description:
                        univ.description = description

                    existing_src = db.query(db_models.ImportSource).filter_by(university_id=univ.id).first()
                    url_changed = False
                    if existing_src and cleaned_website and cleaned_website.startswith("http"):
                        if existing_src.url != cleaned_website:
                            url_changed = True
                        existing_src.url = cleaned_website
                        existing_src.source_type = "url"
                        # Reset stored selectors so detector runs fresh on the new URL
                        if url_changed:
                            existing_src.set_parser_config({})
                    elif not existing_src:
                        existing_src = db_models.ImportSource(
                            university_id=univ.id,
                            name="Official Source",
                            source_type=src_type,
                            url=src_url,
                        )
                        db.add(existing_src)

                    db.commit()

                    # Ensure question bank exists (idempotent)
                    from sorts.services.seed_service import seed_default_questions
                    q_count = seed_default_questions(db, univ.id)

                    # ── Step 2: scanning for club changes ─────────────────
                    _step2u_embed = nextcord.Embed(
                        title="Checking for Club Changes",
                        description="Crawling your website for updates...",
                        color=BRAND_COLOR,
                    )
                    _step2u_embed.set_footer(text="Sortling • Step 2 of 2")
                    _step2u_embed.set_thumbnail(url="attachment://thinking.gif")
                    await interaction.edit_original_message(embed=_step2u_embed)

                    # ── Auto-sync: crawl and stage clubs ─────────────────────
                    job_id = None
                    diff = {"new": [], "updated": [], "removed": []}
                    sync_error = None
                    try:
                        sources = self.import_service.get_university_sources(db, univ.id)
                        if sources:
                            job_id = self.import_service.trigger_import(db, sources[0].id)
                            diff = self.import_service.get_draft_diff(db, job_id)
                    except Exception as sync_err:
                        sync_error = str(sync_err)

                    new_clubs = diff.get("new", [])
                    updated_clubs = diff.get("updated", [])
                    new_count = len(new_clubs)
                    updated_count = len(updated_clubs)
                    actionable_count = new_count + updated_count

                    if job_id and actionable_count > 0:
                        # ── Review embed (same as onboarding) ────────────────
                        preview_clubs = (new_clubs + updated_clubs)[:12]
                        club_lines = [f"• {dc.name}" for dc in preview_clubs]
                        if actionable_count > 12:
                            club_lines.append(f"• ... and {actionable_count - 12} more.")

                        desc_parts = [
                            f"> **Profile updated. {actionable_count} club change(s) ready for review.**",
                            "",
                            _DIVIDER,
                            "",
                            "## Questions Ready",
                            f"• {q_count} questions loaded - `/sort` is active.",
                            "",
                            _DIVIDER,
                            "",
                            f"## Pending Changes  ({actionable_count})",
                            *club_lines,
                            "",
                            _DIVIDER,
                            "",
                            "Click **Publish Directory** to make clubs visible to students.",
                            "Click **Skip for Now** to publish later using `/admin review`.",
                        ]
                        embed = nextcord.Embed(
                            title="Club Directory Preview",
                            description="\n".join(desc_parts),
                            color=BRAND_COLOR,
                        )
                        from sorts.bot.views.setup_onboarding import SetupOnboardingView
                        view = SetupOnboardingView(job_id, q_count, actionable_count, name)
                        await interaction.edit_original_message(embed=embed, view=view, attachments=[])

                    else:
                        # ── No actionable changes ─────────────────────────────
                        lines = [
                            f"> **Profile updated for {name}.**",
                            "",
                            _DIVIDER,
                            "",
                            "## Summary",
                            f"• {q_count} questions loaded - `/sort` is active.",
                        ]
                        if sync_error:
                            lines += [
                                "• Unable to reach your website. The club directory could not be loaded.",
                                f"• Reason: `{sync_error}`",
                                "• Check the URL is correct, then run `/admin sync` to retry.",
                            ]
                        else:
                            removed_count = len(diff.get("removed", []))
                            if removed_count:
                                lines += [
                                    f"• {removed_count} club(s) marked for removal. Run `/admin review` to publish.",
                                ]
                            else:
                                lines += [
                                    "• No new club changes detected.",
                                    "• Use `/admin add_club` to add clubs manually.",
                                ]
                        lines += ["", _DIVIDER]
                        embed = nextcord.Embed(
                            title="Setup Complete",
                            description="\n".join(lines),
                            color=BRAND_COLOR,
                        )
                        await interaction.edit_original_message(embed=embed, view=None, attachments=[])

        except Exception as e:
            embed, file = create_sortling_embed(
                title="Setup Failed",
                description=f"Something went wrong. Please try again or contact support.\n`{e}`",
                is_error=True,
            )
            await interaction.edit_original_message(embed=embed, view=None, attachments=[])

    # ─── /admin ───────────────────────────────────────────────────────────────

    @nextcord.slash_command(name="admin", description="Manage the club directory for this server.")
    async def admin(self, interaction: nextcord.Interaction):
        pass

    # ─── /admin sync ──────────────────────────────────────────────────────────

    @admin.subcommand(name="sync", description="Fetch the latest club data from the university website.")
    async def sync(self, interaction: nextcord.Interaction):
        """Crawls the configured source and stages changes for review."""
        if not _is_admin(interaction):
            embed, file = create_sortling_embed(
                title="Access Denied",
                description="Only server administrators can sync the club directory.",
                is_error=True,
            )
            await interaction.send(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            with get_db() as db:
                univ = get_guild_university(db, interaction.guild_id)
                if not univ:
                    embed, file = create_sortling_embed(
                        title="Not Configured",
                        description="Run `/setup` first to link this server to a university.",
                        is_error=True,
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

                sources = self.import_service.get_university_sources(db, univ.id)
                if not sources:
                    embed, file = create_sortling_embed(
                        title="No Source Configured",
                        description="No club data source has been set up for this university. Contact a Sortling administrator.",
                        is_error=True,
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

                # Use the first active source
                source = sources[0]
                job_id = self.import_service.trigger_import(db, source.id)

                desc_parts = [
                    "> **Club data sync processed.**",
                    "",
                    "## Sync Status",
                    "• **Status**: Source processed successfully.",
                    "• **Next Step**: Run `/admin review` to preview changes before publishing.",
                    "• **Manual Entry**: Administrators can also add clubs anytime using `/admin add_club`."
                ]

                embed, file = create_sortling_embed(
                    title="Sync Complete",
                    description="\n".join(desc_parts),
                    is_error=False,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed, file = create_sortling_embed(
                title="Sync Failed",
                description=f"The sync could not complete. Please try again.\n`{e}`",
                is_error=True,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ─── /admin review ────────────────────────────────────────────────────────

    @admin.subcommand(name="review", description="Preview pending club changes before they go live.")
    async def review(self, interaction: nextcord.Interaction):
        """Shows staged changes from the latest sync and lets admins approve them."""
        if not _is_admin(interaction):
            embed, file = create_sortling_embed(
                title="Access Denied",
                description="Only server administrators can review pending changes.",
                is_error=True,
            )
            await interaction.send(embed=embed, ephemeral=True)
            return

        try:
            with get_db() as db:
                univ = get_guild_university(db, interaction.guild_id)
                if not univ:
                    embed, file = create_sortling_embed(
                        title="Not Configured",
                        description="Run `/setup` first to link this server to a university.",
                        is_error=True,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                job = self.import_service.get_latest_job(db, univ.id)
                if not job:
                    embed, file = create_sortling_embed(
                        title="Nothing to Review",
                        description="No sync has been run yet. Use `/admin sync` to fetch the latest club data.",
                        is_error=False,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                if job.status == "approved":
                    embed, file = create_sortling_embed(
                        title="Already Published",
                        description="The most recent sync has already been published. Run `/admin sync` to fetch fresh data.",
                        is_error=False,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                diff = self.import_service.get_draft_diff(db, job.id)
                new_names = [f"+ {dc.name}" for dc in diff["new"]]
                up_names  = [f"~ {dc.name}" for dc in diff["updated"]]
                rem_names = [f"- {dc.name}" for dc in diff["removed"]]

                embed = nextcord.Embed(
                    title="Pending Club Changes",
                    description="Review the changes below, then click **Publish** to make them live.",
                    color=BRAND_COLOR,
                )
                embed.add_field(
                    name=f"New  ({len(new_names)})",
                    value=clean_text("\n".join(new_names) or "None"),
                    inline=True,
                )
                embed.add_field(
                    name=f"Updated  ({len(up_names)})",
                    value=clean_text("\n".join(up_names) or "None"),
                    inline=True,
                )
                embed.add_field(
                    name=f"Removed  ({len(rem_names)})",
                    value=clean_text("\n".join(rem_names) or "None"),
                    inline=True,
                )
                embed.set_footer(text="Publishing will immediately update the club directory for all students.")

                view = AdminPreviewView(job.id)
                await interaction.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            embed, file = create_sortling_embed(
                title="Review Failed",
                description=f"Could not load pending changes.\n`{e}`",
                is_error=True,
            )
            await interaction.send(embed=embed, ephemeral=True)

    # ─── /admin publish ───────────────────────────────────────────────────────

    @admin.subcommand(name="publish", description="Immediately publish the latest synced club data.")
    async def publish(self, interaction: nextcord.Interaction):
        """Skips review and publishes the most recent sync directly."""
        if not _is_admin(interaction):
            embed, file = create_sortling_embed(
                title="Access Denied",
                description="Only server administrators can publish changes.",
                is_error=True,
            )
            await interaction.send(embed=embed, ephemeral=True)
            return

        try:
            with get_db() as db:
                univ = get_guild_university(db, interaction.guild_id)
                if not univ:
                    embed, file = create_sortling_embed(
                        title="Not Configured",
                        description="Run `/setup` first to link this server to a university.",
                        is_error=True,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                job = self.import_service.get_latest_job(db, univ.id)
                if not job:
                    embed, file = create_sortling_embed(
                        title="Nothing to Publish",
                        description="Run `/admin sync` to fetch the latest club data first.",
                        is_error=False,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                if job.status == "approved":
                    embed, file = create_sortling_embed(
                        title="Already Published",
                        description="The latest sync is already live. Run `/admin sync` to check for new changes.",
                        is_error=False,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                self.import_service.publish_job(db, job.id)
                embed, file = create_sortling_embed(
                    title="Published",
                    description="The club directory has been updated. Students will see the latest data immediately.",
                    is_error=False,
                )
                await interaction.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed, file = create_sortling_embed(
                title="Publish Failed",
                description=f"Could not publish changes.\n`{e}`",
                is_error=True,
            )
            await interaction.send(embed=embed, ephemeral=True)

    # ─── /admin add_club ──────────────────────────────────────────────────────

    @admin.subcommand(name="add_club", description="Manually add a new student club to this server's university directory.")
    async def add_club(
        self,
        interaction: nextcord.Interaction,
        name: str = nextcord.SlashOption(description="Full name of the club"),
        summary: str = nextcord.SlashOption(description="Short one-line summary of what the club does"),
        description: str = nextcord.SlashOption(description="Detailed description of activities and goals"),
        category: str = nextcord.SlashOption(description="Category (e.g. Technology, Cultural, Sports)", required=False),
        commitment: str = nextcord.SlashOption(description="Commitment level (e.g. Low, Medium, High)", required=False),
        meeting_frequency: str = nextcord.SlashOption(description="Meeting schedule (e.g. Weekly, Bi-weekly)", required=False),
        website: str = nextcord.SlashOption(description="Official website or linktree URL", required=False),
        instagram: str = nextcord.SlashOption(description="Instagram profile URL", required=False),
        discord: str = nextcord.SlashOption(description="Discord invite URL", required=False),
    ):
        """Allows server administrators to manually register a new club into the database."""
        if not _is_admin(interaction):
            embed, file = create_sortling_embed(
                title="Access Denied",
                description="Only server owners and administrators can add new clubs.",
                is_error=True,
            )
            await interaction.send(embed=embed, ephemeral=True)
            return

        try:
            with get_db() as db:
                univ = get_guild_university(db, interaction.guild_id)
                if not univ:
                    embed, file = create_sortling_embed(
                        title="Not Configured",
                        description="Run `/setup` first to link this server to a university.",
                        is_error=True,
                    )
                    await interaction.send(embed=embed, ephemeral=True)
                    return

                import re
                base_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
                slug = base_slug
                counter = 1
                while db.query(db_models.Club).filter_by(university_id=univ.id, slug=slug).first():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                club = db_models.Club(
                    university_id=univ.id,
                    name=name,
                    slug=slug,
                    summary=summary,
                    description=description,
                    category=category or "General",
                    commitment=commitment or "Medium commitment",
                    meeting_frequency=meeting_frequency or "Bi-weekly sessions",
                    website=website,
                    instagram=instagram,
                    discord=discord,
                    official=True
                )
                club.set_verification(confidence=100, verified=True, source=["Admin Added"], last_verified="2026-07-21")
                db.add(club)
                db.commit()
                db.refresh(club)

                from sorts.core.traits.rule_trait_inferencer import RuleTraitInferencer
                inferencer = RuleTraitInferencer()
                trait_weights = inferencer.infer_traits(name=name, summary=summary, description=description, category=category or "General")

                for trait_slug, weight in trait_weights.items():
                    t_obj = db.query(db_models.Trait).filter_by(slug=trait_slug).first()
                    if t_obj:
                        ct = db_models.ClubTrait(club_id=club.id, trait_id=t_obj.id, weight=weight)
                        db.add(ct)
                db.commit()

                desc_parts = [
                    f"> **{name} has been added to the {univ.name} club directory.**",
                    "",
                    "## Club Details",
                    f"• **Category**: {category or 'General'}",
                    f"• **Summary**: {summary}",
                    f"• **Status**: Verified & active for `/sort` recommendations.",
                ]

                embed, file = create_sortling_embed(
                    title="Club Added Successfully",
                    description="\n".join(desc_parts),
                    is_error=False,
                )
                await interaction.send(embed=embed)
        except Exception as e:
            embed, file = create_sortling_embed(
                title="Failed to Add Club",
                description=f"Could not save the club entry.\n`{e}`",
                is_error=True,
            )
            await interaction.send(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(AdminCog(bot))
