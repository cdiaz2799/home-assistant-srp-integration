"""DataUpdateCoordinator for the SRP Energy (Hourly) integration.

The coordinator fetches SRP's hourly usage/cost data and imports it into Home
Assistant's long-term statistics via ``async_add_external_statistics`` (the same
pattern used by the core ``opower`` integration). This backfills historical
hourly buckets so they appear in the Energy Dashboard, which a regular live
sensor cannot do.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from srpenergy.client import SrpEnergyClient

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
    statistics_during_period,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CLIENT_TIMEOUT,
    CONF_ACCOUNT_ID,
    CONF_IS_TOU,
    CURRENCY_USD,
    DOMAIN,
    INCREMENTAL_OVERLAP,
    INITIAL_BACKFILL,
    MAX_REQUEST_WINDOW,
    PHOENIX_ZONE_INFO,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type SrpEnergyHourlyConfigEntry = ConfigEntry[SrpEnergyHourlyCoordinator]


@dataclass
class HourlyReading:
    """A single hour of SRP usage, normalized to a UTC on-the-hour start."""

    start: datetime
    kwh: float
    cost: float


@dataclass
class SrpLiveData:
    """Convenience values surfaced as live sensor entities."""

    yesterday_kwh: float | None = None
    yesterday_cost: float | None = None
    latest_hour_kwh: float | None = None
    latest_hour_cost: float | None = None
    latest_hour_start: datetime | None = None


def _parse_reading(row: tuple) -> HourlyReading | None:
    """Convert a raw ``usage()`` row into an :class:`HourlyReading`.

    Each row is ``(date, hour, isodate, kwh, cost)``. The ``isodate`` field uses
    a non-padded timezone offset (e.g. ``-7:00``) which is not reliably parseable,
    so we build the timestamp from the ``date`` and ``hour`` fields in Arizona
    local time instead.
    """
    date, hour, _isodate, kwh, cost = row
    try:
        local = datetime.strptime(f"{date} {hour}", "%m/%d/%Y %I:%M %p")
    except (ValueError, TypeError):
        _LOGGER.warning("Skipping SRP row with unparseable timestamp: %s", row)
        return None

    local = local.replace(tzinfo=PHOENIX_ZONE_INFO)
    start = dt_util.as_utc(local).replace(minute=0, second=0, microsecond=0)
    try:
        return HourlyReading(start=start, kwh=float(kwh), cost=float(cost))
    except (ValueError, TypeError):
        _LOGGER.warning("Skipping SRP row with non-numeric values: %s", row)
        return None


class SrpEnergyHourlyCoordinator(DataUpdateCoordinator[SrpLiveData]):
    """Fetch SRP hourly data and import it as long-term statistics."""

    config_entry: SrpEnergyHourlyConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SrpEnergyHourlyConfigEntry,
        client: SrpEnergyClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self._client = client
        self._is_tou: bool = config_entry.data[CONF_IS_TOU]
        account_id: str = config_entry.data[CONF_ACCOUNT_ID]
        self._consumption_statistic_id = f"{DOMAIN}:{account_id}_energy_consumption"
        self._cost_statistic_id = f"{DOMAIN}:{account_id}_energy_cost"
        self._name_prefix = f"SRP {account_id}"

    async def _async_update_data(self) -> SrpLiveData:
        """Fetch recent SRP data, import statistics, and return live values."""
        readings = await self._async_fetch_readings()
        if readings:
            await self._async_import_statistics(readings)
        return self._build_live_data(readings)

    async def _async_fetch_readings(self) -> list[HourlyReading]:
        """Fetch hourly readings, chunked, from the resume point to now."""
        now_local = dt_util.now(PHOENIX_ZONE_INFO)

        last_stat = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics,
            self.hass,
            1,
            self._consumption_statistic_id,
            True,
            {"sum"},
        )
        if last_stat and last_stat.get(self._consumption_statistic_id):
            last_start_ts = last_stat[self._consumption_statistic_id][0]["start"]
            start_local = (
                dt_util.utc_from_timestamp(last_start_ts).astimezone(PHOENIX_ZONE_INFO)
                - INCREMENTAL_OVERLAP
            )
        else:
            start_local = now_local - INITIAL_BACKFILL

        readings_by_start: dict[datetime, HourlyReading] = {}
        chunk_start = start_local
        while chunk_start < now_local:
            chunk_end = min(chunk_start + MAX_REQUEST_WINDOW, now_local)
            rows = await self._async_call_usage(chunk_start, chunk_end)
            for row in rows:
                reading = _parse_reading(row)
                if reading is not None:
                    readings_by_start[reading.start] = reading
            chunk_start = chunk_end + timedelta(hours=1)

        return sorted(readings_by_start.values(), key=lambda r: r.start)

    async def _async_call_usage(
        self, start: datetime, end: datetime
    ) -> list[tuple]:
        """Call the synchronous SRP client in the executor with a timeout."""
        try:
            async with asyncio.timeout(CLIENT_TIMEOUT):
                return await self.hass.async_add_executor_job(
                    self._client.usage, start, end, self._is_tou
                )
        except TimeoutError as err:
            raise UpdateFailed("Timed out fetching SRP usage data") from err
        except Exception as err:  # noqa: BLE001 - client raises bare exceptions
            raise UpdateFailed(f"Error fetching SRP usage data: {err}") from err

    async def _async_import_statistics(self, readings: list[HourlyReading]) -> None:
        """Build cumulative statistics and push them into the recorder."""
        consumption_sum, cost_sum, resume_after = await self._async_resume_point(
            readings[0].start
        )

        consumption_stats: list[StatisticData] = []
        cost_stats: list[StatisticData] = []
        for reading in readings:
            if resume_after is not None and reading.start.timestamp() <= resume_after:
                continue
            consumption_sum += reading.kwh
            cost_sum += reading.cost
            consumption_stats.append(
                StatisticData(
                    start=reading.start, state=reading.kwh, sum=consumption_sum
                )
            )
            cost_stats.append(
                StatisticData(start=reading.start, state=reading.cost, sum=cost_sum)
            )

        if not consumption_stats:
            return

        consumption_metadata = StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=f"{self._name_prefix} consumption",
            source=DOMAIN,
            statistic_id=self._consumption_statistic_id,
            unit_class="energy",
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        )
        cost_metadata = StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name=f"{self._name_prefix} cost",
            source=DOMAIN,
            statistic_id=self._cost_statistic_id,
            unit_class=None,
            unit_of_measurement=CURRENCY_USD,
        )

        async_add_external_statistics(
            self.hass, consumption_metadata, consumption_stats
        )
        async_add_external_statistics(self.hass, cost_metadata, cost_stats)

    async def _async_resume_point(
        self, first_start: datetime
    ) -> tuple[float, float, float | None]:
        """Return the running sums and the timestamp to resume after.

        When prior statistics exist we look up the cumulative sums as of the
        first reading we are about to (re)import, so re-pulling an overlap window
        continues the running total instead of restarting it.
        """
        stats = await get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            first_start,
            None,
            {self._consumption_statistic_id, self._cost_statistic_id},
            "hour",
            None,
            {"sum"},
        )
        consumption_rows = stats.get(self._consumption_statistic_id)
        if not consumption_rows:
            return 0.0, 0.0, None

        consumption_sum = consumption_rows[0]["sum"] or 0.0
        resume_after = consumption_rows[0]["start"]
        cost_rows = stats.get(self._cost_statistic_id)
        cost_sum = cost_rows[0]["sum"] if cost_rows else 0.0
        return consumption_sum, cost_sum or 0.0, resume_after

    def _build_live_data(self, readings: list[HourlyReading]) -> SrpLiveData:
        """Derive live sensor values from the most recent readings."""
        data = SrpLiveData()
        if not readings:
            # Preserve the previous values across an empty refresh.
            return self.data or data

        latest = readings[-1]
        data.latest_hour_kwh = latest.kwh
        data.latest_hour_cost = latest.cost
        data.latest_hour_start = latest.start

        today_local = dt_util.now(PHOENIX_ZONE_INFO).date()
        yesterday_local = today_local - timedelta(days=1)
        kwh_total = 0.0
        cost_total = 0.0
        found = False
        for reading in readings:
            if reading.start.astimezone(PHOENIX_ZONE_INFO).date() == yesterday_local:
                kwh_total += reading.kwh
                cost_total += reading.cost
                found = True
        if found:
            data.yesterday_kwh = round(kwh_total, 3)
            data.yesterday_cost = round(cost_total, 2)
        return data
