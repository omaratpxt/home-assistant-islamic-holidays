"""Config flow for Islamic Holidays integration."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IslamicHolidaysApiClient, IslamicHolidaysApiError, IslamicHolidaysConnectionError
from .const import (
    CONF_CALENDAR_NAME,
    CONF_HIJRI_ADJUSTMENT,
    CONF_HOLIDAY_FILTER,
    CONF_UPDATE_INTERVAL_HOURS,
    DEFAULT_CALENDAR_NAME,
    DEFAULT_HIJRI_ADJUSTMENT,
    DEFAULT_HOLIDAY_FILTER,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
    HOLIDAY_FILTER_ALL,
    HOLIDAY_FILTER_MAJOR,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CALENDAR_NAME, default=DEFAULT_CALENDAR_NAME): str,
        vol.Optional(CONF_HOLIDAY_FILTER, default=DEFAULT_HOLIDAY_FILTER): vol.In(
            [HOLIDAY_FILTER_MAJOR, HOLIDAY_FILTER_ALL]
        ),
        vol.Optional(
            CONF_HIJRI_ADJUSTMENT, default=DEFAULT_HIJRI_ADJUSTMENT
        ): vol.All(vol.Coerce(int), vol.Range(min=-3, max=3)),
    }
)


class IslamicHolidaysConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Islamic Holidays."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_key = str(uuid.uuid4())
            await self.async_set_unique_id(unique_key)
            session = async_get_clientsession(self.hass)
            client = IslamicHolidaysApiClient(session=session)

            adj = int(user_input.get(CONF_HIJRI_ADJUSTMENT, DEFAULT_HIJRI_ADJUSTMENT))

            try:
                await client.validate_connection(hijri_adjustment=adj)
            except IslamicHolidaysConnectionError:
                errors["base"] = "cannot_connect"
            except IslamicHolidaysApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config validation")
                errors["base"] = "unknown"
            else:
                cal_name = user_input.get(CONF_CALENDAR_NAME, DEFAULT_CALENDAR_NAME)
                title = f"Islamic Holidays ({cal_name})"

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_CALENDAR_NAME: cal_name,
                    },
                    options={
                        CONF_UPDATE_INTERVAL_HOURS: DEFAULT_UPDATE_INTERVAL_HOURS,
                        CONF_HOLIDAY_FILTER: user_input.get(
                            CONF_HOLIDAY_FILTER, DEFAULT_HOLIDAY_FILTER
                        ),
                        CONF_HIJRI_ADJUSTMENT: adj,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        """Return the options flow."""
        return IslamicHolidaysOptionsFlow()


class IslamicHolidaysOptionsFlow(OptionsFlow):
    """Options for Islamic Holidays."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL_HOURS,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL_HOURS,
                            DEFAULT_UPDATE_INTERVAL_HOURS,
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=6, max=168)),
                    vol.Optional(
                        CONF_HOLIDAY_FILTER,
                        default=self.config_entry.options.get(
                            CONF_HOLIDAY_FILTER, DEFAULT_HOLIDAY_FILTER
                        ),
                    ): vol.In([HOLIDAY_FILTER_MAJOR, HOLIDAY_FILTER_ALL]),
                    vol.Optional(
                        CONF_HIJRI_ADJUSTMENT,
                        default=self.config_entry.options.get(
                            CONF_HIJRI_ADJUSTMENT, DEFAULT_HIJRI_ADJUSTMENT
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=-3, max=3)),
                }
            ),
        )
