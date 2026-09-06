"""
Background scheduler for Prayer Discord Bot.
Continuously monitors prayer times across all configured servers
and posts reminder embeds when prayer time arrives.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

import discord
from discord.ext import tasks

from core.database import Database, GuildSettings
from core.prayer_engine import PrayerEngine, PRAYER_NAMES_AR, PRAYER_NAMES_EN

logger = logging.getLogger("prayerbot.scheduler")

ATHKAR = {
    "adhan_dua": (
        "**دعاء بعد الأذان:**\n"
        "«اللَّهُمَّ رَبَّ هَذِهِ الدَّعْوَةِ التَّامَّةِ، وَالصَّلَاةِ القَائِمَةِ، "
        "آتِ مُحَمَّدًا الوَسِيلَةَ وَالفَضِيلَةَ، وَابْعَثْهُ مَقَامًا مَحْمُودًا الَّذِي وَعَدْتَهُ»"
    ),
    "fajr_reminder": "«الصَّلَاةُ خَيْرٌ مِنَ النَّوْمِ» — صلاة الفجر تفتح أبواب البركة والسكينة.",
    "general_reminder": "«حَافِظُوا عَلَى الصَّلَوَاتِ وَالصَّلَاةِ الْوُسْطَىٰ وَقُومُوا لِلَّهِ قَانِتِينَ»",
}


def build_prayer_embed(
    prayer_key: str,
    prayer_time: datetime,
    city_name: str,
    next_prayer_name: Optional[str] = None,
    next_prayer_time: Optional[datetime] = None,
) -> discord.Embed:
    """Construct a beautiful, informative Discord embed for the prayer alert."""
    ar_name = PRAYER_NAMES_AR.get(prayer_key, prayer_key.title())
    en_name = PRAYER_NAMES_EN.get(prayer_key, prayer_key.title())

    # Colors: Emerald for general prayers, Deep Blue for Isha/Fajr, Sunset Orange for Maghrib
    colors = {
        "fajr": discord.Color.from_rgb(44, 62, 80),      # Midnight blue
        "dhuhr": discord.Color.from_rgb(243, 156, 18),   # Golden Sun
        "asr": discord.Color.from_rgb(39, 174, 96),      # Emerald green
        "maghrib": discord.Color.from_rgb(230, 126, 34), # Sunset Orange
        "isha": discord.Color.from_rgb(26, 36, 56),      # Deep night
    }
    color = colors.get(prayer_key, discord.Color.dark_green())

    embed = discord.Embed(
        title=f"🕌 حان الآن موعد أذان {ar_name} | {en_name} Prayer",
        color=color,
        timestamp=prayer_time,
    )

    embed.add_field(
        name="📍 المدينة / Location",
        value=city_name,
        inline=True,
    )
    embed.add_field(
        name="⏰ الوقت / Time",
        value=f"**{prayer_time.strftime('%I:%M %p')}**",
        inline=True,
    )

    if next_prayer_name and next_prayer_time:
        next_ar = PRAYER_NAMES_AR.get(next_prayer_name, next_prayer_name.title())
        embed.add_field(
            name="⏳ الصلاة القادمة / Next Prayer",
            value=f"{next_ar} at {next_prayer_time.strftime('%I:%M %p')}",
            inline=False,
        )

    # Specific reminder for Fajr, general for others
    if prayer_key == "fajr":
        embed.description = f"{ATHKAR['fajr_reminder']}\n\n{ATHKAR['adhan_dua']}"
    else:
        embed.description = f"{ATHKAR['general_reminder']}\n\n{ATHKAR['adhan_dua']}"

    embed.set_footer(text="تقبل الله منا ومنكم صالح الأعمال")
    return embed


class PrayerScheduler:
    def __init__(self, bot: discord.Client, db: Database):
        self.bot = bot
        self.db = db

    def start(self):
        """Start the background check loop."""
        if not self.check_prayer_times.is_running():
            self.check_prayer_times.start()
            logger.info("Prayer scheduler started (interval: 30s).")

    def stop(self):
        """Stop the background check loop."""
        if self.check_prayer_times.is_running():
            self.check_prayer_times.cancel()
            logger.info("Prayer scheduler stopped.")

    @tasks.loop(seconds=30)
    async def check_prayer_times(self):
        """Main loop executed every 30 seconds to check against current prayer times."""
        try:
            guilds = await self.db.get_all_active_guilds()
            for guild in guilds:
                await self._process_guild(guild)
        except Exception as e:
            logger.error(f"Error in scheduler tick: {e}", exc_info=True)

    @check_prayer_times.before_loop
    async def before_check(self):
        """Wait until Discord client is fully ready before starting the loop."""
        await self.bot.wait_until_ready()

    async def _process_guild(self, guild: GuildSettings):
        """Evaluate prayer times for a single server and dispatch notice if due."""
        if not guild.channel_id:
            return

        try:
            tz = ZoneInfo(guild.timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        now = datetime.now(tz)
        today_date = now.date()
        date_str = today_date.isoformat()

        prayers = PrayerEngine.calculate_prayers(
            latitude=guild.latitude,
            longitude=guild.longitude,
            target_date=today_date,
            timezone_str=guild.timezone,
            method_str=guild.calculation_method,
            madhab_str=guild.madhab,
        )

        schedule = [
            ("fajr", prayers.fajr),
            ("dhuhr", prayers.dhuhr),
            ("asr", prayers.asr),
            ("maghrib", prayers.maghrib),
            ("isha", prayers.isha),
        ]

        for prayer_name, prayer_time in schedule:
            # Check if this minute matches the prayer minute
            if now.hour == prayer_time.hour and now.minute == prayer_time.minute:
                # Check deduplication
                if (
                    guild.last_notified_prayer == prayer_name
                    and guild.last_notified_date == date_str
                ):
                    continue

                # Prayer is due! Send notification
                await self._send_notification(guild, prayer_name, prayer_time, date_str)
                break

    async def _send_notification(
        self,
        guild: GuildSettings,
        prayer_name: str,
        prayer_time: datetime,
        date_str: str,
    ):
        """Post the prayer alert to the server's designated channel."""
        try:
            channel = self.bot.get_channel(guild.channel_id)
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(guild.channel_id)
                except discord.NotFound:
                    logger.warning(f"Channel {guild.channel_id} not found in guild {guild.guild_id}.")
                    return
                except discord.Forbidden:
                    logger.warning(f"No permissions to access channel {guild.channel_id} in guild {guild.guild_id}.")
                    return

            # Next prayer calculation
            next_name, next_time, _ = PrayerEngine.get_next_prayer(
                guild.latitude,
                guild.longitude,
                guild.timezone,
                guild.calculation_method,
                guild.madhab,
                reference_time=prayer_time + discord.utils.utcnow().resolution,
            )

            embed = build_prayer_embed(
                prayer_key=prayer_name,
                prayer_time=prayer_time,
                city_name=guild.city_name,
                next_prayer_name=next_name,
                next_prayer_time=next_time,
            )

            if guild.role_id:
                if guild.role_id == guild.guild_id:
                    mention_text = "@everyone"
                else:
                    mention_text = f"<@&{guild.role_id}>"
            else:
                mention_text = None

            await channel.send(
                content=mention_text,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(everyone=True, roles=True)
            )
            logger.info(
                f"Dispatched {prayer_name} prayer alert to guild {guild.guild_id} (Channel: {guild.channel_id})"
            )

            # Record in database to prevent double dispatch
            await self.db.record_notification_sent(guild.guild_id, prayer_name, date_str)

        except Exception as e:
            logger.error(
                f"Failed to send prayer notification to guild {guild.guild_id}: {e}",
                exc_info=True,
            )
