"""The SRP Energy (hourly statistics) integration.

Unlike the built-in ``srp_energy`` integration, this component consumes SRP's
*hourly* usage data and imports it into Home Assistant's long-term statistics so
it can be used as a source in the Energy Dashboard, with both kWh consumption and
cost. A small set of informational sensors is also exposed for regular dashboard
cards and automations.
"""

from __future__ import annotations

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from srpenergy.client import SrpEnergyClient

from .const import CONF_ID, CONF_IS_TOU
from .coordinator import SrpEnergyConfigEntry, SrpEnergyStatisticsCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SrpEnergyConfigEntry) -> bool:
    """Set up SRP Energy from a config entry."""
    client = SrpEnergyClient(
        entry.data[CONF_ID],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    coordinator = SrpEnergyStatisticsCoordinator(
        hass,
        entry,
        client,
        account_id=entry.data[CONF_ID],
        is_tou=entry.data.get(CONF_IS_TOU, False),
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SrpEnergyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
