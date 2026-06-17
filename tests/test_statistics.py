"""Test statistics import for the SRP Energy (Hourly) integration."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from homeassistant.components.recorder.statistics import (
    get_last_statistics,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.srp_energy_hourly.const import DOMAIN, PHOENIX_ZONE_INFO

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

CONSUMPTION_ID = f"{DOMAIN}:123456789_energy_consumption"
COST_ID = f"{DOMAIN}:123456789_energy_cost"


def _build_rows(hours: int) -> list[tuple]:
    """Build `hours` of SRP-style usage rows ending before now (Phoenix time)."""
    rows: list[tuple] = []
    base = (dt_util.now(PHOENIX_ZONE_INFO) - timedelta(hours=hours)).replace(
        minute=0, second=0, microsecond=0
    )
    for i in range(hours):
        local: datetime = base + timedelta(hours=i)
        rows.append(
            (
                local.strftime("%m/%d/%Y"),
                local.strftime("%I:%M %p"),
                local.isoformat(),
                f"{1.0 + i * 0.1:.1f}",
                f"{0.10 + i * 0.01:.2f}",
            )
        )
    return rows


async def _setup(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)


async def test_statistics_imported(
    recorder_mock,
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_srp_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Both consumption and cost statistics are imported with cumulative sums."""
    rows = _build_rows(24)
    mock_srp_client.usage.return_value = rows

    await _setup(hass, mock_config_entry)

    expected_kwh = sum(float(r[3]) for r in rows)
    expected_cost = sum(float(r[4]) for r in rows)

    last = await hass.async_add_executor_job(
        get_last_statistics, hass, 1, CONSUMPTION_ID, True, {"sum"}
    )
    assert CONSUMPTION_ID in last
    assert last[CONSUMPTION_ID][0]["sum"] == pytest.approx(expected_kwh)

    last_cost = await hass.async_add_executor_job(
        get_last_statistics, hass, 1, COST_ID, True, {"sum"}
    )
    assert COST_ID in last_cost
    assert last_cost[COST_ID][0]["sum"] == pytest.approx(expected_cost)


async def test_statistics_resume_no_double_count(
    recorder_mock,
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_srp_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A refresh that overlaps prior data must not double-count the sum."""
    rows = _build_rows(24)
    mock_srp_client.usage.return_value = rows
    await _setup(hass, mock_config_entry)

    expected_kwh = sum(float(r[3]) for r in rows)

    # Re-run the coordinator with the same overlapping data.
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)

    last = await hass.async_add_executor_job(
        get_last_statistics, hass, 1, CONSUMPTION_ID, True, {"sum"}
    )
    assert last[CONSUMPTION_ID][0]["sum"] == pytest.approx(expected_kwh)


async def test_hourly_buckets_present(
    recorder_mock,
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_srp_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Each hour becomes its own statistic bucket."""
    rows = _build_rows(24)
    mock_srp_client.usage.return_value = rows
    await _setup(hass, mock_config_entry)

    stats = await hass.async_add_executor_job(
        statistics_during_period,
        hass,
        dt_util.utcnow() - timedelta(days=2),
        None,
        {CONSUMPTION_ID},
        "hour",
        None,
        {"sum", "state"},
    )
    assert len(stats[CONSUMPTION_ID]) == 24
