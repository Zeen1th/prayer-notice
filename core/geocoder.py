"""
Geocoding and Timezone resolution for Prayer Discord Bot.
Converts city names to latitude, longitude, formatted address, and IANA timezone.
"""

from typing import Optional, Tuple
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import asyncio

class Geocoder:
    def __init__(self, user_agent: str = "PrayerNoticeDiscordBot/1.0"):
        self.geolocator = Nominatim(user_agent=user_agent, timeout=10)
        self.tz_finder = TimezoneFinder()

    async def search_city(self, query: str) -> Optional[Tuple[str, float, float, str, str]]:
        """
        Search for a city by query string.
        Returns tuple of:
            (display_name, latitude, longitude, timezone_str, recommended_method)
        or None if not found.
        """
        # Run blocking geopy call in executor
        loop = asyncio.get_running_loop()
        location = await loop.run_in_executor(
            None,
            lambda: self.geolocator.geocode(query, language="en")
        )

        if not location:
            return None

        lat = location.latitude
        lon = location.longitude
        display_name = location.address

        # Find timezone from coordinates
        tz_name = await loop.run_in_executor(
            None,
            lambda: self.tz_finder.timezone_at(lat=lat, lng=lon)
        )

        if not tz_name:
            tz_name = "UTC"

        recommended_method = self._recommend_method(display_name, lat, lon)

        return display_name, lat, lon, tz_name, recommended_method

    def _recommend_method(self, address: str, lat: float, lon: float) -> str:
        """Infer best calculation method based on country or coordinates."""
        addr_lower = address.lower()
        if any(country in addr_lower for country in ["saudi arabia", "riyadh", "makkah", "medina", "jeddah"]):
            return "UMM_AL_QURA"
        if any(country in addr_lower for country in ["egypt", "cairo", "alexandria", "giza"]):
            return "EGYPT"
        if any(country in addr_lower for country in ["united arab emirates", "dubai", "abu dhabi", "sharjah"]):
            return "DUBAI"
        if "qatar" in addr_lower:
            return "QATAR"
        if "kuwait" in addr_lower:
            return "KUWAIT"
        if any(country in addr_lower for country in ["pakistan", "india", "bangladesh", "afghanistan"]):
            return "KARACHI"
        if any(country in addr_lower for country in ["united states", "usa", "canada"]):
            return "NORTH_AMERICA"
        if "turkey" in addr_lower:
            return "TURKEY"
        if any(country in addr_lower for country in ["singapore", "malaysia", "indonesia"]):
            return "SINGAPORE"
        return "MUSLIM_WORLD_LEAGUE"
