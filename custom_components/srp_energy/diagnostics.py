"""Diagnostics support for the SRP Energy integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_ID
from .coordinator import SrpEnergyConfigEntry

TO_REDACT = {CONF_ID, CONF_USERNAME, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SrpEnergyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    snapshot = coordinator.data
    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "consumption_statistic_id": coordinator.consumption_statistic_id,
        "cost_statistic_id": coordinator.cost_statistic_id,
        "snapshot": asdict(snapshot) if snapshot else None,
    }
