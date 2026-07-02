"""Shared constants and helpers for the SRP Energy tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME

from custom_components.srp_energy.const import CONF_ID, CONF_IS_TOU

MOCK_CONFIG: dict[str, Any] = {
    CONF_ID: "1234567890",
    CONF_NAME: "SRP",
    CONF_USERNAME: "test-user",
    CONF_PASSWORD: "test-pass",
    CONF_IS_TOU: False,
}

# 48 hours of sample hourly usage. Anchored a few days in the past (Phoenix is
# DST-free) so it falls inside the coordinator's "now - lookback" fetch window.
_PHOENIX = ZoneInfo("America/Phoenix")
SAMPLE_START = (
    datetime.now(_PHOENIX).replace(hour=0, minute=0, second=0, microsecond=0)
    - timedelta(days=4)
).replace(tzinfo=None)
SAMPLE_HOURS = 48


def _usage_kwh(index: int) -> float:
    return round(1.0 + index * 0.1, 4)


def _usage_cost(index: int) -> float:
    return round(0.15 + index * 0.01, 4)


def generate_usage(
    start: datetime = SAMPLE_START, hours: int = SAMPLE_HOURS
) -> list[tuple[str, str, str, str, str]]:
    """Build a list of SRP-style hourly records (all values as strings)."""
    records: list[tuple[str, str, str, str, str]] = []
    for i in range(hours):
        moment = start + timedelta(hours=i)
        records.append(
            (
                moment.strftime("%m/%d/%Y"),
                moment.strftime("%I:00 %p"),
                moment.isoformat(),  # naive local (Phoenix) ISO string
                f"{_usage_kwh(i):.4f}",
                f"{_usage_cost(i):.4f}",
            )
        )
    return records


SAMPLE_USAGE = generate_usage()


def usage_side_effect(
    start: datetime, end: datetime, is_tou: bool
) -> list[tuple[str, str, str, str, str]]:
    """Return only the sample records whose date falls in the request window.

    Mirrors the real client, which returns each hour once, so the coordinator's
    chunked backfill doesn't produce duplicates in tests.
    """
    return [
        record
        for record in SAMPLE_USAGE
        if start.date() <= datetime.fromisoformat(record[2]).date() <= end.date()
    ]


# Expected snapshot values derived from the sample data.
EXPECTED_LATEST_HOUR_USAGE = _usage_kwh(SAMPLE_HOURS - 1)
EXPECTED_LATEST_HOUR_COST = _usage_cost(SAMPLE_HOURS - 1)
# The latest day is the second calendar day (hours 24..47).
EXPECTED_LATEST_DAY_USAGE = round(sum(_usage_kwh(i) for i in range(24, 48)), 4)
EXPECTED_LATEST_DAY_COST = round(sum(_usage_cost(i) for i in range(24, 48)), 4)
