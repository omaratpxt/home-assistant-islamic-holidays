"""AlAdhan API client for Gregorian → Hijri calendar with holidays."""

from __future__ import annotations

import asyncio
import email.utils
import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp
from homeassistant.util import dt as dt_util

from .const import (
    API_429_BACKOFF_INITIAL_SECONDS,
    API_429_BACKOFF_MAX_SECONDS,
    API_429_MAX_ATTEMPTS,
    API_BASE_URL,
    API_G_TO_H_CALENDAR,
)

_LOGGER = logging.getLogger(__name__)


class IslamicHolidaysApiError(Exception):
    """Base exception for AlAdhan API errors."""


class IslamicHolidaysConnectionError(IslamicHolidaysApiError):
    """Connection error."""


def _retry_after_seconds(value: str | None) -> float | None:
    """Parse Retry-After header (seconds or HTTP-date)."""
    if not value:
        return None
    raw = value.strip()
    if raw.isdigit():
        return float(raw)
    try:
        when = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    delta = (when - datetime.now(timezone.utc)).total_seconds()
    return max(0.0, delta)


class IslamicHolidaysApiClient:
    """Async client for AlAdhan gToHCalendar endpoint."""

    def __init__(
        self,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._own_session = False

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        return self._session

    async def close(self) -> None:
        """Close the session if we own it."""
        if self._own_session and self._session:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a request to the AlAdhan API (retries on 429)."""
        session = await self._get_session()
        url = f"{API_BASE_URL}{path}"

        backoff = API_429_BACKOFF_INITIAL_SECONDS

        for attempt in range(1, API_429_MAX_ATTEMPTS + 1):
            try:
                async with session.request(method, url, params=params) as response:
                    if response.status == 429:
                        if attempt >= API_429_MAX_ATTEMPTS:
                            raise IslamicHolidaysApiError("Rate limit exceeded")

                        header = response.headers.get("Retry-After")
                        wait = _retry_after_seconds(header)
                        if wait is None:
                            wait = min(backoff, API_429_BACKOFF_MAX_SECONDS)
                            backoff = min(
                                backoff * 2.0, API_429_BACKOFF_MAX_SECONDS
                            )

                        wait = min(wait, API_429_BACKOFF_MAX_SECONDS)
                        _LOGGER.warning(
                            "AlAdhan rate limited; waiting %.1fs then retry "
                            "(%d/%d)",
                            wait,
                            attempt,
                            API_429_MAX_ATTEMPTS,
                        )
                        await asyncio.sleep(wait)
                        continue

                    if response.status >= 400:
                        text = await response.text()
                        raise IslamicHolidaysApiError(
                            f"API error {response.status}: {text}"
                        )

                    payload = await response.json()

            except aiohttp.ClientError as err:
                raise IslamicHolidaysConnectionError(
                    f"Connection error: {err}"
                ) from err

            if not isinstance(payload, dict):
                raise IslamicHolidaysApiError("Invalid response shape")

            if payload.get("code") != 200:
                raise IslamicHolidaysApiError(
                    payload.get("status") or "Unexpected response code"
                )

            return payload.get("data")

    async def fetch_gregorian_month(
        self,
        month: int,
        year: int,
        *,
        hijri_adjustment: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch Hijri + holiday annotations for each day in a Gregorian month.

        Returns the ``data`` array from AlAdhan (list of day objects).
        """
        path = API_G_TO_H_CALENDAR.format(month=month, year=year)
        params: dict[str, str] = {}
        if hijri_adjustment:
            params["adjustment"] = str(hijri_adjustment)

        _LOGGER.debug("Fetching AlAdhan calendar %d/%d params=%s", month, year, params)
        data = await self._request("GET", path, params=params or None)

        if not isinstance(data, list):
            _LOGGER.warning("Unexpected calendar payload type: %s", type(data))
            return []

        return data

    async def validate_connection(
        self,
        *,
        hijri_adjustment: int = 0,
    ) -> bool:
        """Validate API reachability with a single month request."""
        today = dt_util.now().date()
        await self.fetch_gregorian_month(
            today.month, today.year, hijri_adjustment=hijri_adjustment
        )
        return True
