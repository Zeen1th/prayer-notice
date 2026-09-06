"""
Comprehensive test suite verifying database operations, geocoding,
prayer calculations, and seasonal shifts.
"""

import asyncio
import os
import shutil
import tempfile
from datetime import date, datetime
from zoneinfo import ZoneInfo

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import Database
from core.geocoder import Geocoder
from core.prayer_engine import PrayerEngine
from core.scheduler import build_prayer_embed

async def test_database():
    print("--- 1. Testing Database Operations ---")
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")

    db = Database(db_path)
    await db.init()

    # 1. Upsert Location
    await db.upsert_location(
        guild_id=123456789,
        city_name="Cairo, Egypt",
        latitude=30.0444,
        longitude=31.2357,
        timezone="Africa/Cairo",
        method="EGYPT",
    )

    guild = await db.get_guild(123456789)
    assert guild is not None, "Guild should exist"
    assert guild.city_name == "Cairo, Egypt"
    assert guild.latitude == 30.0444
    assert guild.calculation_method == "EGYPT"
    print("  ✓ Upsert location passed")

    # 2. Update Channel
    await db.update_channel(123456789, 987654321)
    guild = await db.get_guild(123456789)
    assert guild.channel_id == 987654321
    print("  ✓ Update channel passed")

    # 3. Active guilds list
    active = await db.get_all_active_guilds()
    assert len(active) == 1
    assert active[0].guild_id == 123456789
    print("  ✓ Active guilds list passed")

    # 4. Method & Madhab update
    await db.update_method(123456789, "UMM_AL_QURA")
    await db.update_madhab(123456789, "HANAFI")
    guild = await db.get_guild(123456789)
    assert guild.calculation_method == "UMM_AL_QURA"
    assert guild.madhab == "HANAFI"
    print("  ✓ Update method & madhab passed")

    # 5. Deduplication record
    await db.record_notification_sent(123456789, "fajr", "2026-09-05")
    guild = await db.get_guild(123456789)
    assert guild.last_notified_prayer == "fajr"
    assert guild.last_notified_date == "2026-09-05"
    print("  ✓ Deduplication record passed")

    shutil.rmtree(temp_dir)
    print("  All database tests passed!\n")

async def test_geocoder():
    print("--- 2. Testing Geocoder & Timezone Resolver ---")
    geocoder = Geocoder()

    # Search for Cairo
    res = await geocoder.search_city("Cairo, Egypt")
    assert res is not None, "Cairo should be found"
    address, lat, lon, tz, method = res
    print(f"  Result: {address} ({lat:.2f}, {lon:.2f}) - TZ: {tz} - Method: {method}")
    assert "Africa/Cairo" in tz
    assert method == "EGYPT"
    print("  ✓ Geocoding Cairo passed")

    # Search for Riyadh
    res2 = await geocoder.search_city("Riyadh, Saudi Arabia")
    assert res2 is not None, "Riyadh should be found"
    address2, lat2, lon2, tz2, method2 = res2
    print(f"  Result: {address2} ({lat2:.2f}, {lon2:.2f}) - TZ: {tz2} - Method: {method2}")
    assert "Asia/Riyadh" in tz2
    assert method2 == "UMM_AL_QURA"
    print("  ✓ Geocoding Riyadh passed!\n")

def test_prayer_engine():
    print("--- 3. Testing Prayer Calculations & Dynamic Shifts ---")
    # Date 1: September 5, 2026
    p_sep = PrayerEngine.calculate_prayers(
        latitude=30.0444,
        longitude=31.2357,
        target_date=date(2026, 9, 5),
        timezone_str="Africa/Cairo",
        method_str="EGYPT",
        madhab_str="SHAFI",
    )
    print(f"  Sep 5 Cairo: Fajr={p_sep.fajr.strftime('%H:%M')} Maghrib={p_sep.maghrib.strftime('%H:%M')}")

    # Date 2: November 5, 2026 (2 months later)
    p_nov = PrayerEngine.calculate_prayers(
        latitude=30.0444,
        longitude=31.2357,
        target_date=date(2026, 11, 5),
        timezone_str="Africa/Cairo",
        method_str="EGYPT",
        madhab_str="SHAFI",
    )
    print(f"  Nov 5 Cairo: Fajr={p_nov.fajr.strftime('%H:%M')} Maghrib={p_nov.maghrib.strftime('%H:%M')}")

    # Confirm astronomical shifts occur
    assert p_sep.fajr != p_nov.fajr, "Fajr should shift across seasons"
    assert p_sep.maghrib != p_nov.maghrib, "Maghrib should shift across seasons"
    print("  ✓ Dynamic seasonal alignment confirmed!")

    # Test Madhab difference
    p_hanafi = PrayerEngine.calculate_prayers(
        latitude=30.0444,
        longitude=31.2357,
        target_date=date(2026, 9, 5),
        timezone_str="Africa/Cairo",
        method_str="EGYPT",
        madhab_str="HANAFI",
    )
    assert p_hanafi.asr > p_sep.asr, "Hanafi Asr must be later than Shafi Asr"
    print(f"  ✓ Madhab Asr test passed (Shafi {p_sep.asr.strftime('%H:%M')} vs Hanafi {p_hanafi.asr.strftime('%H:%M')})")

    # Test Next Prayer
    ref_time = datetime(2026, 9, 5, 10, 0, 0, tzinfo=ZoneInfo("Africa/Cairo"))
    next_name, next_time, rem = PrayerEngine.get_next_prayer(
        latitude=30.0444,
        longitude=31.2357,
        timezone_str="Africa/Cairo",
        method_str="EGYPT",
        reference_time=ref_time,
    )
    assert next_name == "dhuhr", f"Expected Dhuhr at 10:00 AM, got {next_name}"
    print(f"  ✓ Next prayer helper passed (At 10:00 AM, next is {next_name} at {next_time.strftime('%H:%M')})")

    # Test Embed generation
    embed = build_prayer_embed(
        prayer_key="dhuhr",
        prayer_time=next_time,
        city_name="Cairo, Egypt",
        next_prayer_name="asr",
        next_prayer_time=p_sep.asr,
    )
    assert embed.title is not None
    assert "الظهر" in embed.title
    print("  ✓ Embed builder passed!\n")

async def main():
    await test_database()
    await test_geocoder()
    test_prayer_engine()
    print("==========================================")
    print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
    print("==========================================")

if __name__ == "__main__":
    asyncio.run(main())
