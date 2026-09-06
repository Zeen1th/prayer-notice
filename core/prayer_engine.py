"""
Astronomical prayer time calculation engine using adhanpy.
Calculates exact solar prayer times for any location, date, method, and madhab.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Optional, Tuple
from zoneinfo import ZoneInfo

from adhanpy.PrayerTimes import PrayerTimes
from adhanpy.calculation.CalculationMethod import CalculationMethod
from adhanpy.calculation.CalculationParameters import CalculationParameters
from adhanpy.calculation.Madhab import Madhab


# Method mapping string -> CalculationMethod
METHOD_MAP: Dict[str, CalculationMethod] = {
    "EGYPT": CalculationMethod.EGYPTIAN,
    "EGYPTIAN": CalculationMethod.EGYPTIAN,
    "UMM_AL_QURA": CalculationMethod.UMM_AL_QURA,
    "MWL": CalculationMethod.MUSLIM_WORLD_LEAGUE,
    "MUSLIM_WORLD_LEAGUE": CalculationMethod.MUSLIM_WORLD_LEAGUE,
    "KARACHI": CalculationMethod.KARACHI,
    "NORTH_AMERICA": CalculationMethod.NORTH_AMERICA,
    "ISNA": CalculationMethod.NORTH_AMERICA,
    "DUBAI": CalculationMethod.DUBAI,
    "QATAR": CalculationMethod.QATAR,
    "KUWAIT": CalculationMethod.KUWAIT,
    "SINGAPORE": CalculationMethod.SINGAPORE,
    "MOON_SIGHTING_COMMITTEE": CalculationMethod.MOON_SIGHTING_COMMITTEE,
}

METHOD_LABELS: Dict[str, str] = {
    "EGYPT": "Egyptian General Authority of Survey (الهيئة العامة للمساحة المصرية)",
    "UMM_AL_QURA": "Umm Al-Qura University, Makkah (جامعة أم القرى - مكة المكرمة)",
    "MWL": "Muslim World League (رابطة العالم الإسلامي)",
    "KARACHI": "University of Islamic Sciences, Karachi (جامعة العلوم الإسلامية بكراتشي)",
    "NORTH_AMERICA": "ISNA - Islamic Society of North America",
    "DUBAI": "Dubai / UAE (دائرة الشؤون الإسلامية بدبي)",
    "QATAR": "Ministry of Awqaf, Qatar (وزارة الأوقاف والشؤون الإسلامية بقطر)",
    "KUWAIT": "Ministry of Awqaf, Kuwait (وزارة الأوقاف والشؤون الإسلامية بالكويت)",
    "SINGAPORE": "MUIS, Singapore",
}

MADHAB_MAP: Dict[str, Madhab] = {
    "SHAFI": Madhab.SHAFI,
    "HANAFI": Madhab.HANAFI,
}

PRAYER_NAMES_AR = {
    "fajr": "الفجر",
    "sunrise": "الشروق",
    "dhuhr": "الظهر",
    "asr": "العصر",
    "maghrib": "المغرب",
    "isha": "العشاء",
}

PRAYER_NAMES_EN = {
    "fajr": "Fajr",
    "sunrise": "Sunrise",
    "dhuhr": "Dhuhr",
    "asr": "Asr",
    "maghrib": "Maghrib",
    "isha": "Isha",
}

@dataclass
class DailyPrayers:
    calc_date: date
    fajr: datetime
    sunrise: datetime
    dhuhr: datetime
    asr: datetime
    maghrib: datetime
    isha: datetime
    timezone: ZoneInfo

    def to_dict(self) -> Dict[str, datetime]:
        return {
            "fajr": self.fajr,
            "sunrise": self.sunrise,
            "dhuhr": self.dhuhr,
            "asr": self.asr,
            "maghrib": self.maghrib,
            "isha": self.isha,
        }


class PrayerEngine:
    @staticmethod
    def calculate_prayers(
        latitude: float,
        longitude: float,
        target_date: date,
        timezone_str: str,
        method_str: str = "EGYPT",
        madhab_str: str = "SHAFI",
    ) -> DailyPrayers:
        """
        Calculate prayer times for a specific coordinates, date, and timezone.
        """
        tz = ZoneInfo(timezone_str)
        method = METHOD_MAP.get(method_str.upper(), CalculationMethod.EGYPTIAN)
        madhab = MADHAB_MAP.get(madhab_str.upper(), Madhab.SHAFI)

        params = CalculationParameters(method=method)
        params.madhab = madhab

        pt = PrayerTimes(
            coordinates=(latitude, longitude),
            date=target_date,
            calculation_parameters=params,
            time_zone=tz,
        )

        return DailyPrayers(
            calc_date=target_date,
            fajr=pt.fajr,
            sunrise=pt.sunrise,
            dhuhr=pt.dhuhr,
            asr=pt.asr,
            maghrib=pt.maghrib,
            isha=pt.isha,
            timezone=tz,
        )

    @classmethod
    def get_next_prayer(
        cls,
        latitude: float,
        longitude: float,
        timezone_str: str,
        method_str: str = "EGYPT",
        madhab_str: str = "SHAFI",
        reference_time: Optional[datetime] = None,
    ) -> Tuple[str, datetime, timedelta]:
        """
        Determine the next upcoming prayer relative to current or reference time.
        Returns: (prayer_key, prayer_datetime, time_remaining)
        """
        tz = ZoneInfo(timezone_str)
        now = reference_time or datetime.now(tz)
        today = now.date()

        today_prayers = cls.calculate_prayers(
            latitude, longitude, today, timezone_str, method_str, madhab_str
        )

        # Standard 5 prayers (excluding sunrise from mandatory prayer notifications,
        # but included if before sunrise)
        ordered_prayers = [
            ("fajr", today_prayers.fajr),
            ("dhuhr", today_prayers.dhuhr),
            ("asr", today_prayers.asr),
            ("maghrib", today_prayers.maghrib),
            ("isha", today_prayers.isha),
        ]

        for name, prayer_time in ordered_prayers:
            if now < prayer_time:
                return name, prayer_time, (prayer_time - now)

        # If current time is past Isha, next prayer is Fajr tomorrow
        tomorrow = today + timedelta(days=1)
        tomorrow_prayers = cls.calculate_prayers(
            latitude, longitude, tomorrow, timezone_str, method_str, madhab_str
        )
        return "fajr", tomorrow_prayers.fajr, (tomorrow_prayers.fajr - now)
