"""The SRP Energy (Hourly) integration."""

from __future__ import annotations

from srpenergy.client import SrpEnergyClient

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_ACCOUNT_ID
from .coordinator import SrpEnergyHourlyConfigEntry, SrpEnergyHourlyCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: SrpEnergyHourlyConfigEntry
) -> bool:
    """Set up SRP Energy (Hourly) from a config entry."""
    client = SrpEnergyClient(
        entry.data[CONF_ACCOUNT_ID],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    coordinator = SrpEnergyHourlyCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SrpEnergyHourlyConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
