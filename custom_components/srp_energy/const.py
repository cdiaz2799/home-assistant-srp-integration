"""Constants for the SRP Energy (hourly statistics) integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "srp_energy"

# Config entry keys (mirrors the built-in srp_energy integration so users
# familiar with it feel at home).
CONF_ID: Final = "id"
CONF_IS_TOU: Final = "is_tou"

DEFAULT_NAME: Final = "SRP Energy"

# Device metadata (matches the built-in integration).
DEVICE_MANUFACTURER: Final = "srpnet.com"
DEVICE_MODEL: Final = "Service Api"

# SRP serves the Phoenix, AZ area which does NOT observe daylight saving time,
# so the hourly timestamps returned by the API are a fixed UTC-7 offset.
SRP_TIME_ZONE: Final = "America/Phoenix"

# The SRP API only exposes hourly data with a lag of ~1-2 days, so there is no
# value in polling frequently.
UPDATE_INTERVAL: Final = timedelta(hours=12)

# How far back to look on the very first run when no statistics exist yet.
# The API only returns whatever history it has; this is just an upper bound.
MAX_INITIAL_LOOKBACK_DAYS: Final = 3 * 365

# Size of each backfill request window. A multi-year first run is split into
# chunks so a single request can't time out or be rejected by SRP.
BACKFILL_CHUNK_DAYS: Final = 90

# External statistics identifiers use a ``:`` delimiter with the domain as the
# source. Suffixes are combined with the account id, e.g.
# ``srp_energy:1234_energy_consumption``.
STATISTIC_CONSUMPTION_SUFFIX: Final = "energy_consumption"
STATISTIC_COST_SUFFIX: Final = "energy_cost"
