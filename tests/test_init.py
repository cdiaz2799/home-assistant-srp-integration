"""Test setup and unload of the SRP Energy integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_setup_and_unload(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_srp_client: MagicMock,
) -> None:
    """The entry loads, imports statistics, and unloads cleanly."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.srp_energy.coordinator.async_add_external_statistics"
    ) as mock_add_stats:
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    # Consumption and cost statistics were imported.
    assert mock_add_stats.call_count == 2

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
