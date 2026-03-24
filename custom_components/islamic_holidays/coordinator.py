"""Data coordinator for Islamic Holidays."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
import logging
import re
from typing import Any

from homeassistant.components.calendar import CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import IslamicHolidaysApiClient, IslamicHolidaysApiError
from .const import (
    CONF_HIJRI_ADJUSTMENT,
    CONF_HOLIDAY_FILTER,
    DEFAULT_HIJRI_ADJUSTMENT,
    DEFAULT_HOLIDAY_FILTER,
    DOMAIN,
    EID_AL_ADHA_DAY_SPAN,
    EID_AL_FITR_DAY_SPAN,
    EID_UL_ADHA_SUMMARY,
    EID_UL_FITR_SUMMARY,
    HOLIDAY_FILTER_ALL,
    HOLIDAY_FILTER_MAJOR,
    MAJOR_HOLIDAY_NAMES,
    MONTHS_LOOKBACK_FROM_TODAY_MONTH,
    MONTHS_TO_FETCH,
    REQUEST_DELAY_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


def _parse_gregorian_date(value: str) -> date | None:
    """Parse DD-MM-YYYY from AlAdhan."""
    try:
        day_s, month_s, year_s = value.split("-", 2)
        return date(int(year_s), int(month_s), int(day_s))
    except (ValueError, TypeError):
        return None


def _previous_month(y: int, m: int) -> tuple[int, int]:
    if m == 1:
        return y - 1, 12
    return y, m - 1


def _subtract_months(y: int, m: int, n: int) -> tuple[int, int]:
    """Return (year, month) for the month ``n`` months before (y, m)."""
    cy, cm = y, m
    for _ in range(n):
        cy, cm = _previous_month(cy, cm)
    return cy, cm


def _iter_months(start_y: int, start_m: int, count: int) -> list[tuple[int, int]]:
    """Return consecutive Gregorian months as (year, month)."""
    out: list[tuple[int, int]] = []
    y, m = start_y, start_m
    for _ in range(count):
        out.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _slug_fragment(text: str, max_len: int = 64) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip()).strip("-").lower()
    return (slug or "event")[:max_len]


def _exclusive_end_date_for_summary(start: date, summary: str) -> date:
    """Return CalendarEvent ``end`` date (exclusive) for an all-day span."""
    if summary == EID_UL_FITR_SUMMARY:
        return start + timedelta(days=EID_AL_FITR_DAY_SPAN)
    if summary == EID_UL_ADHA_SUMMARY:
        return start + timedelta(days=EID_AL_ADHA_DAY_SPAN)
    return start


class IslamicHolidaysCoordinator(DataUpdateCoordinator[list[CalendarEvent]]):
    """Coordinator fetching AlAdhan months and building calendar events."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: IslamicHolidaysApiClient,
        entry: ConfigEntry,
        *,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client
        self.entry = entry
        self.config_entry = entry
        self._unknown_skipped: set[str] = set()

    def _filter_mode(self) -> str:
        return self.entry.options.get(CONF_HOLIDAY_FILTER, DEFAULT_HOLIDAY_FILTER)

    def _hijri_adjustment(self) -> int:
        return int(
            self.entry.options.get(CONF_HIJRI_ADJUSTMENT, DEFAULT_HIJRI_ADJUSTMENT)
        )

    def _include_holiday_name(self, name: str) -> bool:
        mode = self._filter_mode()
        normalized = name.strip()
        if mode == HOLIDAY_FILTER_ALL:
            return True
        if mode == HOLIDAY_FILTER_MAJOR:
            if normalized in MAJOR_HOLIDAY_NAMES:
                return True
            if normalized not in self._unknown_skipped:
                self._unknown_skipped.add(normalized)
                _LOGGER.debug(
                    "Skipping non-major holiday label (major filter): %s", name
                )
            return False
        return True

    def _build_events_from_days(
        self, days: list[dict[str, Any]]
    ) -> list[CalendarEvent]:
        """Turn AlAdhan day records into CalendarEvent instances."""
        events: list[CalendarEvent] = []
        seen: set[tuple[str, str]] = set()

        for day in days:
            greg = day.get("gregorian") or {}
            date_str = greg.get("date")
            if not date_str:
                continue
            g_date = _parse_gregorian_date(date_str)
            if g_date is None:
                continue

            hijri = day.get("hijri") or {}
            method = hijri.get("method") or ""
            h_date = hijri.get("date") or ""

            names: list[str] = []
            for key in ("holidays", "adjustedHolidays"):
                for item in hijri.get(key) or []:
                    if isinstance(item, str) and item:
                        names.append(item)

            deduped: list[str] = []
            seen_names: set[str] = set()
            for n in names:
                if n not in seen_names:
                    seen_names.add(n)
                    deduped.append(n)

            for summary in deduped:
                summary_clean = summary.strip()
                if not self._include_holiday_name(summary_clean):
                    continue
                key = (g_date.isoformat(), summary_clean)
                if key in seen:
                    continue
                seen.add(key)

                desc_parts: list[str] = []
                if h_date:
                    desc_parts.append(f"Hijri date: {h_date}")
                if method:
                    desc_parts.append(f"Calendar method: {method}")
                description = " · ".join(desc_parts) if desc_parts else None

                end_date = _exclusive_end_date_for_summary(g_date, summary_clean)
                uid = f"{DOMAIN}_{g_date.isoformat()}_{_slug_fragment(summary_clean)}"
                events.append(
                    CalendarEvent(
                        summary=summary_clean,
                        start=g_date,
                        end=end_date,
                        description=description,
                        uid=uid,
                    )
                )

        events.sort(key=lambda e: (e.start, e.summary))
        return events

    async def _async_update_data(self) -> list[CalendarEvent]:
        """Fetch rolling window of Gregorian months and merge events."""
        today = dt_util.now().date()
        start_y, start_m = _subtract_months(
            today.year, today.month, MONTHS_LOOKBACK_FROM_TODAY_MONTH
        )
        months = _iter_months(start_y, start_m, MONTHS_TO_FETCH)
        _LOGGER.debug(
            "Fetching %d Gregorian months starting %04d-%02d",
            len(months),
            start_y,
            start_m,
        )
        adjustment = self._hijri_adjustment()

        results: list[list[dict[str, Any]]] = []
        try:
            for idx, (year, month) in enumerate(months):
                chunk = await self.client.fetch_gregorian_month(
                    month, year, hijri_adjustment=adjustment
                )
                results.append(chunk)
                if idx < len(months) - 1:
                    await asyncio.sleep(REQUEST_DELAY_SECONDS)
        except IslamicHolidaysApiError as err:
            raise UpdateFailed(f"AlAdhan API error: {err}") from err

        merged: list[dict[str, Any]] = []
        for chunk in results:
            merged.extend(chunk)

        events = self._build_events_from_days(merged)

        # Final dedupe if the same day appears in overlapping requests (should not)
        final: dict[str, CalendarEvent] = {}
        for ev in events:
            assert ev.uid is not None
            final[ev.uid] = ev

        return sorted(final.values(), key=lambda e: (e.start, e.summary))
