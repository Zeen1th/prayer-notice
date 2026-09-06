"""
Database management for Prayer Discord Bot using aiosqlite.
Manages persistent guild settings for prayer times and notifications.
"""

from dataclasses import dataclass
from typing import Optional, List
import aiosqlite
import os

@dataclass
class GuildSettings:
    guild_id: int
    channel_id: Optional[int]
    role_id: Optional[int]
    city_name: str
    latitude: float
    longitude: float
    timezone: str
    calculation_method: str = "EGYPT"
    madhab: str = "SHAFI"
    notifications_enabled: bool = True
    last_notified_prayer: Optional[str] = None
    last_notified_date: Optional[str] = None

class Database:
    def __init__(self, db_path: str = "data/prayerbot.db"):
        self.db_path = db_path
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

    async def init(self):
        """Initialize database schema and tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER,
                    role_id INTEGER,
                    city_name TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    timezone TEXT NOT NULL,
                    calculation_method TEXT NOT NULL DEFAULT 'EGYPT',
                    madhab TEXT NOT NULL DEFAULT 'SHAFI',
                    notifications_enabled INTEGER NOT NULL DEFAULT 1,
                    last_notified_prayer TEXT,
                    last_notified_date TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()

    async def get_guild(self, guild_id: int) -> Optional[GuildSettings]:
        """Fetch settings for a single guild."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM guild_settings WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            return GuildSettings(
                guild_id=row["guild_id"],
                channel_id=row["channel_id"],
                role_id=row["role_id"],
                city_name=row["city_name"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                timezone=row["timezone"],
                calculation_method=row["calculation_method"],
                madhab=row["madhab"],
                notifications_enabled=bool(row["notifications_enabled"]),
                last_notified_prayer=row["last_notified_prayer"],
                last_notified_date=row["last_notified_date"],
            )

    async def get_all_active_guilds(self) -> List[GuildSettings]:
        """Fetch all guilds configured for notifications."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM guild_settings WHERE notifications_enabled = 1 AND channel_id IS NOT NULL"
            )
            rows = await cursor.fetchall()
            return [
                GuildSettings(
                    guild_id=row["guild_id"],
                    channel_id=row["channel_id"],
                    role_id=row["role_id"],
                    city_name=row["city_name"],
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    timezone=row["timezone"],
                    calculation_method=row["calculation_method"],
                    madhab=row["madhab"],
                    notifications_enabled=bool(row["notifications_enabled"]),
                    last_notified_prayer=row["last_notified_prayer"],
                    last_notified_date=row["last_notified_date"],
                )
                for row in rows
            ]

    async def upsert_location(
        self,
        guild_id: int,
        city_name: str,
        latitude: float,
        longitude: float,
        timezone: str,
        method: Optional[str] = None
    ):
        """Set or update location for a guild."""
        method_clause = method or "EGYPT"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, city_name, latitude, longitude, timezone, calculation_method)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    city_name = excluded.city_name,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    timezone = excluded.timezone,
                    calculation_method = COALESCE(?, guild_settings.calculation_method),
                    updated_at = CURRENT_TIMESTAMP
            """, (guild_id, city_name, latitude, longitude, timezone, method_clause, method))
            await db.commit()

    async def update_channel(self, guild_id: int, channel_id: int):
        """Update notification channel for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE guild_settings
                SET channel_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = ?
            """, (channel_id, guild_id))
            await db.commit()

    async def update_role(self, guild_id: int, role_id: Optional[int]):
        """Update prayer notification mention role (or None to disable role pings)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE guild_settings
                SET role_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = ?
            """, (role_id, guild_id))
            await db.commit()

    async def update_method(self, guild_id: int, method: str):
        """Update calculation method (e.g. UMM_AL_QURA, EGYPT, MWL, ISNA, KARACHI)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE guild_settings
                SET calculation_method = ?, updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = ?
            """, (method, guild_id))
            await db.commit()

    async def update_madhab(self, guild_id: int, madhab: str):
        """Update Asr juristic method (SHAFI or HANAFI)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE guild_settings
                SET madhab = ?, updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = ?
            """, (madhab, guild_id))
            await db.commit()

    async def toggle_notifications(self, guild_id: int, enabled: bool):
        """Enable or disable notifications for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE guild_settings
                SET notifications_enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = ?
            """, (1 if enabled else 0, guild_id))
            await db.commit()

    async def record_notification_sent(self, guild_id: int, prayer_name: str, date_str: str):
        """Record the last prayer notification sent to avoid double pings."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE guild_settings
                SET last_notified_prayer = ?, last_notified_date = ?, updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = ?
            """, (prayer_name, date_str, guild_id))
            await db.commit()
