"""Calendar platform for Islamic Holidays."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEntityDescription, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_CALENDAR_NAME, DEFAULT_CALENDAR_NAME, DOMAIN
from .coordinator import IslamicHolidaysCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up calendar from config entry."""
    coordinator: IslamicHolidaysCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    name = entry.data.get(CONF_CALENDAR_NAME, DEFAULT_CALENDAR_NAME)
    async_add_entities([IslamicHolidaysCalendarEntity(coordinator, entry, name)])


class IslamicHolidaysCalendarEntity(
    CoordinatorEntity[IslamicHolidaysCoordinator], CalendarEntity
):
    """Read-only calendar of Islamic holidays from AlAdhan."""

    def __init__(
        self,
        coordinator: IslamicHolidaysCoordinator,
        entry: ConfigEntry,
        calendar_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = CalendarEntityDescription(
            key="islamic_holidays",
            name=calendar_name,
        )
        self._attr_unique_id = f"{entry.unique_id}_calendar"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        now = dt_util.now()
        for ev in self.coordinator.data or []:
            if ev.end_datetime_local > now:
                return ev
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events in the requested window."""
        result: list[CalendarEvent] = []
        for ev in self.coordinator.data or []:
            if ev.end_datetime_local > start_date and ev.start_datetime_local < end_date:
                result.append(ev)
        return result
