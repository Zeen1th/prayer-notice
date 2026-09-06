"""
Settings slash commands for Prayer Discord Bot.
Allows server administrators to configure location, channel, role ping, and calculation methods.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from core.database import Database
from core.geocoder import Geocoder
from core.prayer_engine import METHOD_LABELS, METHOD_MAP

class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database, geocoder: Geocoder):
        self.bot = bot
        self.db = db
        self.geocoder = geocoder

    settings_group = app_commands.Group(
        name="prayer-settings",
        description="Configure prayer notification settings for this server",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @app_commands.command(
        name="setlocation",
        description="Set your city/location for accurate prayer times (e.g., Cairo, Riyadh, London)",
    )
    @app_commands.describe(city="Name of the city or region (e.g., Cairo, Egypt or Riyadh)")
    @app_commands.default_permissions(manage_guild=True)
    async def set_location(self, interaction: discord.Interaction, city: str):
        await interaction.response.defer(ephemeral=False)

        result = await self.geocoder.search_city(city)
        if not result:
            await interaction.followup.send(
                f"❌ Could not find location for **'{city}'**. Please try a more specific search (e.g., *'Alexandria, Egypt'*).",
                ephemeral=True,
            )
            return

        address, lat, lon, timezone, recommended_method = result

        # Check existing method if already configured
        existing = await self.db.get_guild(interaction.guild_id)
        method_to_use = existing.calculation_method if existing else recommended_method

        await self.db.upsert_location(
            guild_id=interaction.guild_id,
            city_name=address,
            latitude=lat,
            longitude=lon,
            timezone=timezone,
            method=method_to_use,
        )

        embed = discord.Embed(
            title="✅ تم تحديث الموقع | Location Updated",
            description=f"**{address}**",
            color=discord.Color.green(),
        )
        embed.add_field(name="🌐 الإحداثيات / Coordinates", value=f"`{lat:.4f}, {lon:.4f}`", inline=True)
        embed.add_field(name="🕒 المنطقة الزمنية / Timezone", value=f"`{timezone}`", inline=True)
        embed.add_field(
            name="📐 طريقة الحساب / Method",
            value=f"`{method_to_use}`\n{METHOD_LABELS.get(method_to_use, '')}",
            inline=False,
        )
        embed.set_footer(text="Use /today to see the calculated prayer timetable.")

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="setchannel",
        description="Set the channel where prayer notices will be posted",
    )
    @app_commands.describe(channel="Channel to receive prayer announcements (defaults to current channel)")
    @app_commands.default_permissions(manage_guild=True)
    async def set_channel(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ):
        target_channel = channel or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Please specify a valid text channel.", ephemeral=True
            )
            return

        # Check permissions
        permissions = target_channel.permissions_for(interaction.guild.me)
        if not permissions.send_messages or not permissions.embed_links:
            await interaction.response.send_message(
                f"⚠️ The bot lacks **Send Messages** or **Embed Links** permission in {target_channel.mention}. Please grant these permissions.",
                ephemeral=True,
            )
            return

        guild = await self.db.get_guild(interaction.guild_id)
        if not guild:
            await interaction.response.send_message(
                "⚠️ Please set your server location first using `/setlocation <city>`.",
                ephemeral=True,
            )
            return

        await self.db.update_channel(interaction.guild_id, target_channel.id)

        embed = discord.Embed(
            title="📢 تم تعيين القناة | Channel Configured",
            description=f"Prayer notifications will now be posted to {target_channel.mention}.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="setrole",
        description="Set a role or @everyone to mention when prayer time arrives",
    )
    @app_commands.describe(
        role="Specific role to ping (leave empty if using @everyone or disabling)",
        mention_everyone="Set to True to ping @everyone on prayer alerts",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def set_role(
        self,
        interaction: discord.Interaction,
        role: Optional[discord.Role] = None,
        mention_everyone: bool = False,
    ):
        guild = await self.db.get_guild(interaction.guild_id)
        if not guild:
            await interaction.response.send_message(
                "⚠️ Please set your server location first using `/setlocation <city>`.",
                ephemeral=True,
            )
            return

        if mention_everyone or (role and role.id == interaction.guild_id):
            role_id = interaction.guild_id
            msg = "✅ Prayer notifications will now ping **@everyone**."
        elif role:
            role_id = role.id
            msg = f"✅ Prayer notifications will now ping {role.mention}."
        else:
            role_id = None
            msg = "✅ Role mentions have been disabled. Prayer notifications will be sent without pings."

        await self.db.update_role(interaction.guild_id, role_id)
        await interaction.response.send_message(msg)

    @app_commands.command(
        name="setmethod",
        description="Set calculation convention (e.g., Umm Al-Qura, Egyptian Authority, MWL, ISNA)",
    )
    @app_commands.describe(method="Calculation standard used by your local mosque authority")
    @app_commands.choices(
        method=[
            app_commands.Choice(name="Egyptian General Authority (Egypt, Levant)", value="EGYPT"),
            app_commands.Choice(name="Umm Al-Qura University (Saudi Arabia, Gulf)", value="UMM_AL_QURA"),
            app_commands.Choice(name="Muslim World League (Europe, Global)", value="MWL"),
            app_commands.Choice(name="Univ. of Islamic Sciences Karachi (Pakistan, India)", value="KARACHI"),
            app_commands.Choice(name="ISNA - Islamic Society of North America (US, Canada)", value="NORTH_AMERICA"),
            app_commands.Choice(name="Dubai / UAE Awqaf", value="DUBAI"),
            app_commands.Choice(name="Qatar Awqaf", value="QATAR"),
            app_commands.Choice(name="Kuwait Awqaf", value="KUWAIT"),
            app_commands.Choice(name="Singapore (MUIS)", value="SINGAPORE"),
        ]
    )
    @app_commands.default_permissions(manage_guild=True)
    async def set_method(self, interaction: discord.Interaction, method: app_commands.Choice[str]):
        guild = await self.db.get_guild(interaction.guild_id)
        if not guild:
            await interaction.response.send_message(
                "⚠️ Please set your server location first using `/setlocation <city>`.",
                ephemeral=True,
            )
            return

        await self.db.update_method(interaction.guild_id, method.value)
        await interaction.response.send_message(
            f"✅ Calculation method updated to **{method.name}**."
        )

    @app_commands.command(
        name="setmadhab",
        description="Set Asr juristic calculation method (Shafi/Standard or Hanafi)",
    )
    @app_commands.describe(madhab="Shafi/Hanbali/Maliki (Standard) or Hanafi")
    @app_commands.choices(
        madhab=[
            app_commands.Choice(name="Shafi / Hanbali / Maliki (Standard shadow ratio 1:1)", value="SHAFI"),
            app_commands.Choice(name="Hanafi (Later Asr shadow ratio 2:1)", value="HANAFI"),
        ]
    )
    @app_commands.default_permissions(manage_guild=True)
    async def set_madhab(self, interaction: discord.Interaction, madhab: app_commands.Choice[str]):
        guild = await self.db.get_guild(interaction.guild_id)
        if not guild:
            await interaction.response.send_message(
                "⚠️ Please set your server location first using `/setlocation <city>`.",
                ephemeral=True,
            )
            return

        await self.db.update_madhab(interaction.guild_id, madhab.value)
        await interaction.response.send_message(
            f"✅ Asr juristic method set to **{madhab.name}**."
        )

    @app_commands.command(
        name="togglenotifications",
        description="Enable or pause automated prayer notifications",
    )
    @app_commands.describe(enabled="True to enable notifications, False to pause them")
    @app_commands.default_permissions(manage_guild=True)
    async def toggle_notifications(self, interaction: discord.Interaction, enabled: bool):
        guild = await self.db.get_guild(interaction.guild_id)
        if not guild:
            await interaction.response.send_message(
                "⚠️ Please set your server location first using `/setlocation <city>`.",
                ephemeral=True,
            )
            return

        await self.db.toggle_notifications(interaction.guild_id, enabled)
        status_text = "enabled 🔔" if enabled else "paused 🔕"
        await interaction.response.send_message(
            f"✅ Prayer notifications have been **{status_text}**."
        )

    @app_commands.command(
        name="settings",
        description="Display the current prayer configuration for this server",
    )
    async def show_settings(self, interaction: discord.Interaction):
        guild = await self.db.get_guild(interaction.guild_id)
        if not guild:
            await interaction.response.send_message(
                "ℹ️ This server has not been configured yet. Use `/setlocation <city>` to get started!",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"⚙️ إعدادات الصلاة | Prayer Settings for {interaction.guild.name}",
            color=discord.Color.blue(),
        )

        channel_display = f"<#{guild.channel_id}>" if guild.channel_id else "*(Not set)*"
        if guild.role_id:
            role_display = "@everyone" if guild.role_id == guild.guild_id else f"<@&{guild.role_id}>"
        else:
            role_display = "*(None)*"
        status_display = "🔔 Enabled" if guild.notifications_enabled else "🔕 Paused"

        embed.add_field(name="📍 Location", value=guild.city_name, inline=False)
        embed.add_field(name="🕒 Timezone", value=f"`{guild.timezone}`", inline=True)
        embed.add_field(name="📢 Channel", value=channel_display, inline=True)
        embed.add_field(name="🔔 Status", value=status_display, inline=True)
        embed.add_field(name="👥 Ping Role", value=role_display, inline=True)
        embed.add_field(
            name="📐 Calculation Method",
            value=f"`{guild.calculation_method}`\n{METHOD_LABELS.get(guild.calculation_method, '')}",
            inline=False,
        )
        embed.add_field(name="⚖️ Madhab (Asr)", value=f"`{guild.madhab}`", inline=True)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    db: Database = bot.db
    geocoder = Geocoder()
    await bot.add_cog(SettingsCog(bot, db, geocoder))
