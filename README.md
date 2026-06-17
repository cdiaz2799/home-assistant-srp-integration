# SRP Energy (Hourly) for Home Assistant

A custom Home Assistant integration that imports **hourly** energy usage and
cost data from [Salt River Project (SRP)](https://www.srpnet.com/) into Home
Assistant's **Energy Dashboard**, including backfilled history.

Unlike the built-in `srp_energy` integration — which exposes only a single
daily-total sensor — this integration pushes SRP's true hourly data into Home
Assistant's long-term statistics (the same approach used by the core `opower`
integration). That means the Energy Dashboard shows hour-by-hour bars and can
display **past** usage from before the integration was installed.

## Features

- Backfills up to ~1 year of **hourly** consumption (kWh) on first setup.
- Imports both **energy (kWh)** and **cost ($)** statistics.
- Refreshes every 12 hours and re-pulls a short overlap window to capture
  SRP's late-arriving / revised readings (SRP data lags ~2 days).
- Supports standard and **Time-of-Use (TOU / EZ-3)** plans.
- Adds live convenience sensors: yesterday's energy/cost and the latest hour.

## Requirements

- Home Assistant **2025.11** or newer (uses the current recorder statistics API).
- An SRP account with online access at [srpnet.com](https://www.srpnet.com/).

## Installation

### HACS (custom repository)

1. In HACS, add this repository as a custom repository (type: *Integration*).
2. Install **SRP Energy (Hourly)** and restart Home Assistant.

### Manual

Copy `custom_components/srp_energy_hourly/` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **SRP Energy (Hourly)**.
3. Enter your **Account ID**, **Username**, and **Password**, and tick the
   **Time-of-Use** box if you are on a TOU/EZ-3 plan.

## Adding to the Energy Dashboard

After the first refresh completes:

1. Go to **Settings → Dashboards → Energy**.
2. Under **Electricity grid → Add consumption**, pick the
   `SRP <account> consumption` statistic
   (`srp_energy_hourly:<account>_energy_consumption`).
3. Optionally, choose **Use an entity tracking the total costs** and select the
   `SRP <account> cost` statistic
   (`srp_energy_hourly:<account>_energy_cost`).

You can verify the imported data under **Developer Tools → Statistics**.

## Notes & limitations

- SRP publishes usage with a delay of roughly two days; the most recent hours
  appear once SRP makes them available.
- Initial backfill depth is bounded by what SRP's API returns for your account.
- This is an unofficial integration and is not affiliated with SRP.
