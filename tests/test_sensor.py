"""Test the SRP Energy informational sensors."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.sensor import ATTR_STATE_CLASS, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.srp_energy.const import DOMAIN

from .const import (
    EXPECTED_LATEST_DAY_COST,
    EXPECTED_LATEST_DAY_USAGE,
    EXPECTED_LATEST_HOUR_COST,
    EXPECTED_LATEST_HOUR_USAGE,
)


async def _setup(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.srp_energy.coordinator.async_add_external_statistics"
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()


def _state(
    hass: HomeAssistant, entry: MockConfigEntry, key: str
):
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_{key}"
    )
    assert entity_id is not None
    return hass.states.get(entity_id)


async def test_sensor_values(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_srp_client: MagicMock,
) -> None:
    """Sensors report the latest hour/day usage and cost."""
    await _setup(hass, mock_config_entry)

    assert float(_state(hass, mock_config_entry, "latest_hour_usage").state) == (
        pytest.approx(EXPECTED_LATEST_HOUR_USAGE)
    )
    assert float(_state(hass, mock_config_entry, "latest_hour_cost").state) == (
        pytest.approx(EXPECTED_LATEST_HOUR_COST)
    )
    assert float(_state(hass, mock_config_entry, "latest_day_usage").state) == (
        pytest.approx(EXPECTED_LATEST_DAY_USAGE)
    )
    assert float(_state(hass, mock_config_entry, "latest_day_cost").state) == (
        pytest.approx(EXPECTED_LATEST_DAY_COST)
    )


async def test_sensors_not_total_increasing(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_srp_client: MagicMock,
) -> None:
    """Live sensors must not be total_increasing (avoids energy double counting)."""
    await _setup(hass, mock_config_entry)

    for key in ("latest_hour_usage", "latest_day_usage"):
        state = _state(hass, mock_config_entry, key)
        assert (
            state.attributes.get(ATTR_STATE_CLASS)
            != SensorStateClass.TOTAL_INCREASING
        )
