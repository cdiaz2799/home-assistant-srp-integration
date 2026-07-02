"""Data update coordinator for the SRP Energy integration.

The coordinator fetches SRP's *hourly* usage/cost data and imports it into Home
Assistant's long-term statistics (so it can back the Energy Dashboard), then
returns a small snapshot for the informational sensors.

The statistics approach is modelled on Home Assistant core's ``opower``
integration, which solves the same problem (utility data that arrives with a
delay and must be backfilled at its real timestamps).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify
from srpenergy.client import SrpEnergyClient

from .const import (
    BACKFILL_CHUNK_DAYS,
    DOMAIN,
    MAX_INITIAL_LOOKBACK_DAYS,
    SRP_TIME_ZONE,
    STATISTIC_CONSUMPTION_SUFFIX,
    STATISTIC_COST_SUFFIX,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Home Assistant is migrating statistics metadata from the ``has_mean`` boolean
# to the ``mean_type`` enum (``has_mean`` is removed in 2026.4) and added a
# required ``unit_class``. Feature-detect so this integration works across a
# range of HA versions without raising ``KeyError`` inside the recorder.
try:
    from homeassistant.components.recorder.models import StatisticMeanType

    _HAS_MEAN_TYPE = True
except ImportError:  # pragma: no cover - depends on HA version
    _HAS_MEAN_TYPE = False

try:
    from homeassistant.util.unit_conversion import EnergyConverter

    _ENERGY_UNIT_CLASS: str | None = EnergyConverter.UNIT_CLASS
except (ImportError, AttributeError):  # pragma: no cover - depends on HA version
    _ENERGY_UNIT_CLASS = "energy"

type SrpEnergyConfigEntry = ConfigEntry[SrpEnergyStatisticsCoordinator]


@dataclass
class SrpEnergySnapshot:
    """Latest values exposed to the informational sensors."""

    latest_hour_start: datetime | None = None
    latest_hour_usage: float | None = None
    latest_hour_cost: float | None = None
    latest_day: date | None = None
    latest_day_usage: float | None = None
    latest_day_cost: float | None = None


class SrpEnergyStatisticsCoordinator(DataUpdateCoordinator[SrpEnergySnapshot]):
    """Fetch SRP hourly data, import statistics, and expose a live snapshot."""

    config_entry: SrpEnergyConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SrpEnergyConfigEntry,
        client: SrpEnergyClient,
        *,
        account_id: str,
        is_tou: bool,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=UPDATE_INTERVAL,
        )
        self._client = client
        self._account_id = account_id
        self._is_tou = is_tou

        account_slug = slugify(account_id)
        self.consumption_statistic_id = (
            f"{DOMAIN}:{account_slug}_{STATISTIC_CONSUMPTION_SUFFIX}"
        )
        self.cost_statistic_id = f"{DOMAIN}:{account_slug}_{STATISTIC_COST_SUFFIX}"

    @property
    def currency(self) -> str:
        """Return the currency used for cost statistics/sensors."""
        return self.hass.config.currency

    async def _async_update_data(self) -> SrpEnergySnapshot:
        """Fetch new hourly data and import it into long-term statistics."""
        srp_tz = await self._async_srp_time_zone()

        # Determine where to resume from for each statistic.
        consumption_last_start, consumption_sum = await self._async_last_stat(
            self.consumption_statistic_id
        )
        _, cost_sum = await self._async_last_stat(self.cost_statistic_id)

        now_local = dt_util.utcnow().astimezone(srp_tz)
        if consumption_last_start is None:
            start_local = now_local - timedelta(days=MAX_INITIAL_LOOKBACK_DAYS)
        else:
            # Re-fetch from the day of the last recorded hour; already-recorded
            # hours are filtered out below.
            start_local = consumption_last_start.astimezone(srp_tz)

        try:
            records = await self.hass.async_add_executor_job(
                self._fetch_usage,
                start_local.replace(tzinfo=None),
                now_local.replace(tzinfo=None),
            )
        except Exception as err:  # noqa: BLE001 - srpenergy raises bare exceptions
            raise UpdateFailed(f"Error fetching SRP usage data: {err}") from err

        return self._process_records(
            records,
            srp_tz,
            consumption_last_start,
            consumption_sum,
            cost_sum,
        )

    def _fetch_usage(
        self, start: datetime, end: datetime
    ) -> list[tuple[Any, Any, Any, Any, Any]]:
        """Fetch usage, chunking large ranges so requests can't time out.

        Runs in the executor because the srpenergy client performs blocking
        HTTP requests.
        """
        records: list[tuple[Any, Any, Any, Any, Any]] = []
        chunk_start = start
        while chunk_start <= end:
            chunk_end = min(chunk_start + timedelta(days=BACKFILL_CHUNK_DAYS), end)
            records.extend(self._client.usage(chunk_start, chunk_end, self._is_tou))
            # ``usage`` is inclusive of both dates; step past ``chunk_end``'s day
            # to avoid re-fetching it.
            chunk_start = chunk_end + timedelta(days=1)
        return records

    def _process_records(
        self,
        records: list[tuple[Any, Any, Any, Any, Any]],
        srp_tz: Any,
        last_start: datetime | None,
        consumption_sum: float,
        cost_sum: float,
    ) -> SrpEnergySnapshot:
        """Build and import statistics, then return a live snapshot."""
        # Parse and sort by timestamp so the running sums are monotonic.
        parsed: list[tuple[datetime, float, float]] = []
        for _date, _hour, isodate, kwh, cost in records:
            start = self._parse_start(isodate, srp_tz)
            if start is None:
                continue
            parsed.append((start, max(0.0, float(kwh)), max(0.0, float(cost))))

        parsed.sort(key=lambda row: row[0])

        consumption_stats: list[StatisticData] = []
        cost_stats: list[StatisticData] = []
        seen: set[datetime] = set()
        snapshot = SrpEnergySnapshot()
        day_totals: dict[date, tuple[float, float]] = {}

        for start, usage, cost in parsed:
            # Snapshot uses every fetched hour, even ones already recorded.
            latest = snapshot.latest_hour_start
            if latest is None or start >= latest:
                snapshot.latest_hour_start = start
                snapshot.latest_hour_usage = usage
                snapshot.latest_hour_cost = cost
            local_day = start.astimezone(srp_tz).date()
            day_usage, day_cost = day_totals.get(local_day, (0.0, 0.0))
            day_totals[local_day] = (day_usage + usage, day_cost + cost)

            # Only import hours we haven't recorded yet.
            if last_start is not None and start <= last_start:
                continue
            if start in seen:
                continue
            seen.add(start)

            consumption_sum += usage
            cost_sum += cost
            consumption_stats.append(
                StatisticData(start=start, state=usage, sum=consumption_sum)
            )
            cost_stats.append(StatisticData(start=start, state=cost, sum=cost_sum))

        if day_totals:
            latest_day = max(day_totals)
            snapshot.latest_day = latest_day
            snapshot.latest_day_usage, snapshot.latest_day_cost = day_totals[latest_day]

        if consumption_stats:
            _LOGGER.debug(
                "Importing %d new hourly SRP statistics for account %s",
                len(consumption_stats),
                self._account_id,
            )
            async_add_external_statistics(
                self.hass,
                self._statistic_metadata(
                    self.consumption_statistic_id,
                    "SRP energy consumption",
                    UnitOfEnergy.KILO_WATT_HOUR,
                    _ENERGY_UNIT_CLASS,
                ),
                consumption_stats,
            )
            async_add_external_statistics(
                self.hass,
                self._statistic_metadata(
                    self.cost_statistic_id,
                    "SRP energy cost",
                    self.currency,
                    None,
                ),
                cost_stats,
            )

        return snapshot

    async def _async_last_stat(
        self, statistic_id: str
    ) -> tuple[datetime | None, float]:
        """Return the (start, sum) of the last recorded statistic, if any."""
        last_stats = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics,
            self.hass,
            1,
            statistic_id,
            True,
            {"sum"},
        )
        rows = last_stats.get(statistic_id) if last_stats else None
        if not rows:
            return None, 0.0
        row = rows[0]
        last_start = dt_util.utc_from_timestamp(row["start"])
        last_sum = float(row["sum"] or 0.0)
        return last_start, last_sum

    async def _async_srp_time_zone(self) -> Any:
        """Return the (DST-free) SRP time zone without blocking the loop."""
        if hasattr(dt_util, "async_get_time_zone"):
            return await dt_util.async_get_time_zone(SRP_TIME_ZONE)
        return await self.hass.async_add_executor_job(
            dt_util.get_time_zone, SRP_TIME_ZONE
        )

    @staticmethod
    def _parse_start(isodate: Any, srp_tz: Any) -> datetime | None:
        """Parse an SRP isodate into an hour-aligned, tz-aware UTC datetime."""
        try:
            parsed = datetime.fromisoformat(str(isodate))
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=srp_tz)
        # Arizona has no DST, so an on-the-hour local time is on-the-hour in UTC.
        return dt_util.as_utc(parsed).replace(minute=0, second=0, microsecond=0)

    @staticmethod
    def _statistic_metadata(
        statistic_id: str,
        name: str,
        unit: str | None,
        unit_class: str | None,
    ) -> StatisticMetaData:
        """Build version-compatible statistics metadata."""
        metadata: dict[str, Any] = {
            "has_sum": True,
            "name": name,
            "source": DOMAIN,
            "statistic_id": statistic_id,
            "unit_of_measurement": unit,
        }
        if _HAS_MEAN_TYPE:
            metadata["mean_type"] = StatisticMeanType.NONE
            metadata["unit_class"] = unit_class
        else:  # pragma: no cover - depends on HA version
            metadata["has_mean"] = False
        return metadata  # type: ignore[return-value]
