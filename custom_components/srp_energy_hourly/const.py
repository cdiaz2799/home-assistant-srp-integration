"""Constants for the SRP Energy (Hourly) integration."""

from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

DOMAIN = "srp_energy_hourly"

# Configuration keys
CONF_ACCOUNT_ID = "account_id"
CONF_IS_TOU = "is_tou"

# SRP serves Arizona, which does not observe daylight saving time.
PHOENIX_ZONE_INFO = ZoneInfo("America/Phoenix")

# The SRP client is synchronous; cap how long we wait on a single call.
CLIENT_TIMEOUT = 30

# SRP publishes usage data with a lag of roughly two days, so we refresh a
# few times a day and always re-pull a short overlap window.
UPDATE_INTERVAL = timedelta(hours=12)

# How far back to reach on the very first refresh when no statistics exist yet.
INITIAL_BACKFILL = timedelta(days=365)

# When statistics already exist, re-pull this much recent history to capture
# late-arriving or revised readings from SRP.
INCREMENTAL_OVERLAP = timedelta(days=3)

# Request usage in chunks no larger than this to avoid client timeouts on
# large backfills.
MAX_REQUEST_WINDOW = timedelta(days=30)

ATTRIBUTION = "Powered by SRP Energy"

# Currency reported by the SRP API.
CURRENCY_USD = "USD"
