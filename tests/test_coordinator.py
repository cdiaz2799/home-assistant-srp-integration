"""Test the SRP Energy statistics coordinator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.srp_energy.coordinator import SrpEnergyStatisticsCoordinator

from .const import (
    EXPECTED_LATEST_DAY_USAGE,
    EXPECTED_LATEST_HOUR_USAGE,
    MOCK_CONFIG,
    SAMPLE_HOURS,
    SAMPLE_START,
    usage_side_effect,
)

PHOENIX = ZoneInfo("America/Phoenix")


def _build_coordinator(
    hass: HomeAssistant, entry: MockConfigEntry
) -> SrpEnergyStatisticsCoordinator:
    client = MagicMock()
    client.usage.side_effect = usage_side_effect
    return SrpEnergyStatisticsCoordinator(
        hass,
        entry,
        client,
        account_id=MOCK_CONFIG["id"],
        is_tou=False,
    )


async def test_first_run_imports_all_hours(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """On the first run every fetched hour is imported with monotonic sums."""
    mock_config_entry.add_to_hass(hass)
    coordinator = _build_coordinator(hass, mock_config_entry)

    with (
        patch.object(
            coordinator, "_async_last_stat", AsyncMock(return_value=(None, 0.0))
        ),
        patch(
            "custom_components.srp_energy.coordinator.async_add_external_statistics"
        ) as mock_add,
    ):
        snapshot = await coordinator._async_update_data()

    assert mock_add.call_count == 2

    cons_meta = mock_add.call_args_list[0].args[1]
    cons_stats = mock_add.call_args_list[0].args[2]
    cost_meta = mock_add.call_args_list[1].args[1]
    cost_stats = mock_add.call_args_list[1].args[2]

    assert cons_meta["statistic_id"] == "srp_energy:1234567890_energy_consumption"
    assert cons_meta["source"] == "srp_energy"
    assert cons_meta["has_sum"] is True
    assert cost_meta["statistic_id"] == "srp_energy:1234567890_energy_cost"

    assert len(cons_stats) == SAMPLE_HOURS
    assert len(cost_stats) == SAMPLE_HOURS

    # Timestamps are tz-aware and aligned to the top of the hour.
    for stat in cons_stats:
        assert stat["start"].tzinfo is not None
        assert stat["start"].minute == 0
        assert stat["start"].second == 0

    # Sums are monotonically increasing.
    sums = [stat["sum"] for stat in cons_stats]
    assert sums == sorted(sums)
    assert cons_stats[0]["sum"] == cons_stats[0]["state"]

    assert snapshot.latest_hour_usage == EXPECTED_LATEST_HOUR_USAGE
    assert snapshot.latest_day_usage == EXPECTED_LATEST_DAY_USAGE


async def test_resume_skips_recorded_hours(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Resuming imports only hours after the last recorded statistic."""
    mock_config_entry.add_to_hass(hass)
    coordinator = _build_coordinator(hass, mock_config_entry)

    # Pretend hour index 23 (the first day's 23:00 Phoenix) was the last import.
    last_start = (
        (SAMPLE_START + timedelta(hours=23)).replace(tzinfo=PHOENIX).astimezone(UTC)
    )
    base_sum = 100.0

    with (
        patch.object(
            coordinator,
            "_async_last_stat",
            AsyncMock(return_value=(last_start, base_sum)),
        ),
        patch(
            "custom_components.srp_energy.coordinator.async_add_external_statistics"
        ) as mock_add,
    ):
        await coordinator._async_update_data()

    cons_stats = mock_add.call_args_list[0].args[2]

    # Hours 24..47 remain (24 records).
    assert len(cons_stats) == SAMPLE_HOURS - 24
    # First imported hour is strictly after the last recorded one.
    assert cons_stats[0]["start"] > last_start
    # The running sum continues from the recovered base sum.
    assert cons_stats[0]["sum"] == base_sum + cons_stats[0]["state"]


async def test_fetch_usage_chunks_large_ranges(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A multi-month range is fetched in multiple chunked requests."""
    mock_config_entry.add_to_hass(hass)
    coordinator = _build_coordinator(hass, mock_config_entry)
    coordinator._client.usage.side_effect = None
    coordinator._client.usage.return_value = []

    start = datetime(2022, 1, 1)
    end = datetime(2022, 12, 31)
    coordinator._fetch_usage(start, end)

    # 365 days in 90-day chunks -> at least four requests.
    assert coordinator._client.usage.call_count >= 4
