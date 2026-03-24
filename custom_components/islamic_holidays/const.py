"""Constants for Islamic Holidays integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "islamic_holidays"

API_BASE_URL: Final = "https://api.aladhan.com"
API_G_TO_H_CALENDAR: Final = "/v1/gToHCalendar/{month}/{year}"

CONF_CALENDAR_NAME: Final = "calendar_name"
CONF_UPDATE_INTERVAL_HOURS: Final = "update_interval_hours"
CONF_HOLIDAY_FILTER: Final = "holiday_filter"
CONF_HIJRI_ADJUSTMENT: Final = "hijri_adjustment"

DEFAULT_CALENDAR_NAME: Final = "Islamic holidays"
DEFAULT_UPDATE_INTERVAL_HOURS: Final = 24
DEFAULT_HOLIDAY_FILTER: Final = "major"
DEFAULT_HIJRI_ADJUSTMENT: Final = 0

HOLIDAY_FILTER_MAJOR: Final = "major"
HOLIDAY_FILTER_ALL: Final = "all"

# AlAdhan usually tags the first day only; extend to multi-day all-day events (exclusive end date).
EID_UL_FITR_SUMMARY: Final = "Eid-ul-Fitr"
EID_UL_ADHA_SUMMARY: Final = "Eid-ul-Adha"
EID_AL_FITR_DAY_SPAN: Final = 3
EID_AL_ADHA_DAY_SPAN: Final = 4

# First month to fetch = current calendar month minus this many months, then fetch
# MONTHS_TO_FETCH consecutive Gregorian months. This keeps ~1y past + ~1y ahead so
# events like Eid in May remain visible when "today" has moved to mid-year or later.
MONTHS_LOOKBACK_FROM_TODAY_MONTH: Final = 12
MONTHS_TO_FETCH: Final = 24

# Throttle consecutive AlAdhan calls (coordinator fetches many months in a row).
REQUEST_DELAY_SECONDS: Final = 0.35

# HTTP 429: total attempts per logical request (first try + retries).
API_429_MAX_ATTEMPTS: Final = 4
API_429_BACKOFF_INITIAL_SECONDS: Final = 1.0
API_429_BACKOFF_MAX_SECONDS: Final = 60.0

# Labels returned by AlAdhan for widely observed Islamic days (excludes Urs, tariqa-specific, etc.)
MAJOR_HOLIDAY_NAMES: Final[frozenset[str]] = frozenset(
    {
        "1st Day of Ramadan",
        "Arafa",
        "Ashura",
        "Beginning of the holy months",
        "End of the holy months",
        "Eid-ul-Adha",
        "Eid-ul-Fitr",
        "First time Adhan was called in 622 AD",
        "Hajj",
        "Lailat-ul-Bara'at",
        "Lailat-ul-Miraj",
        "Lailat-ul-Qadr",
        "Lailat-ul-Ragha'ib",
        "Mawlid (Birth) al-Nabi ﷺ",
        "Veiling of the Prophet Muhammad ﷺ",
    }
)
