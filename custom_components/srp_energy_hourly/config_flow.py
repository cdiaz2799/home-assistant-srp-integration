"""Config flow for the SRP Energy (Hourly) integration."""

from __future__ import annotations

import logging
from typing import Any

from srpenergy.client import SrpEnergyClient
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import CONF_ACCOUNT_ID, CONF_IS_TOU, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCOUNT_ID): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_IS_TOU, default=False): bool,
    }
)


class SrpEnergyHourlyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SRP Energy (Hourly)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_ACCOUNT_ID])
            self._abort_if_unique_id_configured()

            client = SrpEnergyClient(
                user_input[CONF_ACCOUNT_ID],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                is_valid = await self.hass.async_add_executor_job(client.validate)
            except Exception:  # noqa: BLE001 - client raises bare exceptions
                _LOGGER.exception("Unexpected error validating SRP credentials")
                errors["base"] = "unknown"
            else:
                if is_valid:
                    return self.async_create_entry(
                        title=f"SRP {user_input[CONF_ACCOUNT_ID]}",
                        data=user_input,
                    )
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
