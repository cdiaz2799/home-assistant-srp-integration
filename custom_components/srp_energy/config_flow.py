"""Config flow for the SRP Energy (hourly statistics) integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from srpenergy.client import SrpEnergyClient

from .const import CONF_ID, CONF_IS_TOU, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SrpEnergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SRP Energy."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            account_id = user_input[CONF_ID]
            await self.async_set_unique_id(account_id)
            self._abort_if_unique_id_configured()

            try:
                is_valid = await self._async_validate(user_input)
            except ValueError:
                errors["base"] = "invalid_account"
            except Exception:  # noqa: BLE001 - srpenergy raises bare exceptions
                _LOGGER.exception("Unexpected error validating SRP credentials")
                errors["base"] = "unknown"
            else:
                if is_valid:
                    return self.async_create_entry(
                        title=user_input[CONF_NAME], data=user_input
                    )
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ID): str,
                    vol.Required(
                        CONF_NAME,
                        default=self.hass.config.location_name or DEFAULT_NAME,
                    ): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_IS_TOU, default=False): bool,
                }
            ),
            errors=errors,
        )

    async def _async_validate(self, user_input: dict[str, Any]) -> bool:
        """Validate the account id and credentials against SRP."""
        client = SrpEnergyClient(
            user_input[CONF_ID],
            user_input[CONF_USERNAME],
            user_input[CONF_PASSWORD],
        )
        return await self.hass.async_add_executor_job(client.validate)
