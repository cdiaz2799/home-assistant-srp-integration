"""Diagnostics support for SRP Energy (Hourly)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_ACCOUNT_ID
from .coordinator import SrpEnergyHourlyConfigEntry

TO_REDACT = {CONF_ACCOUNT_ID, CONF_USERNAME, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SrpEnergyHourlyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry_data": async_redact_data(entry.data, TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "live_data": {
            "yesterday_kwh": data.yesterday_kwh if data else None,
            "yesterday_cost": data.yesterday_cost if data else None,
            "latest_hour_kwh": data.latest_hour_kwh if data else None,
            "latest_hour_cost": data.latest_hour_cost if data else None,
            "latest_hour_start": (
                data.latest_hour_start.isoformat()
                if data and data.latest_hour_start
                else None
            ),
        },
    }
