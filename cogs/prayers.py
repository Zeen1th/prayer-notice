"""
Prayer timetable and test slash commands.
Provides /today, /next, and /testnotification commands.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import discord
from discord import app_commands
from discord.ext import commands

from core.database import Database
from core.prayer_engine import (
    PrayerEngine,
    PRAYER_NAMES_AR,
    PRAYER_NAMES_EN,
)
from core.scheduler import build_prayer_embed

class PrayersCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database):
        self.bot = bot
        self.db = db

    @app_commands.command(
        name="today",
        description="Display today's complete prayer times timetable for this server",
    )
    async def today(self, interaction: discord.Interaction):
        guild = await self.db.get_guild(interaction.guild_id)
        if not guild:
            await interaction.response.send_message(
                "⚠️ This server hasn't set a location yet! Run `/setlocation <city>` first.",
                ephemeral=True,
            )
            return

        try:
            tz = ZoneInfo(guild.timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        now = datetime.now(tz)
        today_date = now.date()

        prayers = PrayerEngine.calculate_prayers(
            latitude=guild.latitude,
            longitude=guild.longitude,
            target_date=today_date,
            timezone_str=guild.timezone,
            method_str=guild.calculation_method,
            madhab_str=guild.madhab,
        )

        next_prayer_name, next_prayer_time, remaining = PrayerEngine.get_next_prayer(
            latitude=guild.latitude,
            longitude=guild.longitude,
            timezone_str=guild.timezone,
            method_str=guild.calculation_method,
            madhab_str=guild.madhab,
            reference_time=now,
        )

        embed = discord.Embed(
            title=f"🕌 مواقيت الصلاة اليوم | Prayer Times Today",
            description=f"📍 **{guild.city_name}**\n📅 {now.strftime('%A, %d %B %Y')} | {now.strftime('%I:%M %p %Z')}",
            color=discord.Color.gold(),
        )

        timetable = [
            ("fajr", "الفجر / Fajr", prayers.fajr),
            ("sunrise", "الشروق / Sunrise", prayers.sunrise),
            ("dhuhr", "الظهر / Dhuhr", prayers.dhuhr),
            ("asr", "العصر / Asr", prayers.asr),
            ("maghrib", "المغرب / Maghrib", prayers.maghrib),
            ("isha", "العشاء / Isha", prayers.isha),
        ]

        lines = []
        for key, label, p_time in timetable:
            time_str = p_time.strftime("%I:%M %p")
            is_next = (key == next_prayer_name)
            if is_next:
                lines.append(f"🟢 **`{time_str}` — {label}** 👈 *(القادمة / Next)*")
            else:
                lines.append(f"▫️ `{time_str}` — {label}")

        embed.add_field(name="📋 الجدول / Schedule", value="\n".join(lines), inline=False)

        # Remaining time string
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        next_ar = PRAYER_NAMES_AR.get(next_prayer_name, next_prayer_name.title())
        embed.add_field(
            name="⏳ الصلاة القادمة / Next Prayer",
            value=f"**{next_ar}** in **{hours}h {minutes}m** (at {next_prayer_time.strftime('%I:%M %p')})",
            inline=False,
        )

        embed.set_footer(text=f"Method: {guild.calculation_method} | Madhab: {guild.madhab}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="next",
        description="Show how much time is left until the next prayer",
    )
    async def next_prayer(self, interaction: discord.Interaction):
        guild = await self.db.get_guild(interaction.guild_id)
        if not guild:
            await interaction.response.send_message(
                "⚠️ This server hasn't set a location yet! Run `/setlocation <city>` first.",
                ephemeral=True,
            )
            return

        try:
            tz = ZoneInfo(guild.timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        now = datetime.now(tz)

        next_prayer_name, next_prayer_time, remaining = PrayerEngine.get_next_prayer(
            latitude=guild.latitude,
            longitude=guild.longitude,
            timezone_str=guild.timezone,
            method_str=guild.calculation_method,
            madhab_str=guild.madhab,
            reference_time=now,
        )

        ar_name = PRAYER_NAMES_AR.get(next_prayer_name, next_prayer_name.title())
        en_name = PRAYER_NAMES_EN.get(next_prayer_name, next_prayer_name.title())

        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)

        embed = discord.Embed(
            title=f"⏳ الصلاة القادمة: {ar_name} ({en_name})",
            description=(
                f"الوقت المتبقي: **{hours} ساعة و {minutes} دقيقة**\n"
                f"موعد الأذان: **{next_prayer_time.strftime('%I:%M %p')}**\n"
                f"📍 المدينة: {guild.city_name}"
            ),
            color=discord.Color.teal(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="testnotification",
        description="Send a sample prayer notification now to verify channel and permissions",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def test_notification(self, interaction: discord.Interaction):
        guild = await self.db.get_guild(interaction.guild_id)
        if not guild:
            await interaction.response.send_message(
                "⚠️ Please set your location first using `/setlocation <city>`.",
                ephemeral=True,
            )
            return

        target_channel_id = guild.channel_id or interaction.channel_id
        channel = self.bot.get_channel(target_channel_id) or interaction.channel

        try:
            tz = ZoneInfo(guild.timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        now = datetime.now(tz)
        embed = build_prayer_embed(
            prayer_key="asr",
            prayer_time=now,
            city_name=guild.city_name,
            next_prayer_name="maghrib",
            next_prayer_time=now + timedelta(hours=2, minutes=45),
        )

        if guild.role_id:
            mention = "@everyone" if guild.role_id == guild.guild_id else f"<@&{guild.role_id}>"
        else:
            mention = None

        content_str = f"🧪 **[Test Notification / إشعار تجريبي]**\n{mention}" if mention else "🧪 **[Test Notification / إشعار تجريبي]**"

        await channel.send(
            content=content_str,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
        )

        if channel.id != interaction.channel_id:
            await interaction.response.send_message(
                f"✅ Sample notification sent to {channel.mention}!", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "✅ Sample notification sent!", ephemeral=True
            )

async def setup(bot: commands.Bot):
    db: Database = bot.db
    await bot.add_cog(PrayersCog(bot, db))
