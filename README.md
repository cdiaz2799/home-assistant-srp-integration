# SRP Energy (Hourly) — Home Assistant integration

A custom Home Assistant integration for [Salt River Project (SRP)](https://www.srpnet.com/)
electricity customers that imports your **hourly** usage and cost into Home
Assistant's **long-term statistics**, so it can drive the
[Energy Dashboard](https://www.home-assistant.io/docs/energy/) with real hourly
resolution — including cost.

It uses the [`srpenergy`](https://pypi.org/project/srpenergy/) API client.

## Why this exists

The built-in `srp_energy` integration only exposes a single *daily* usage sensor
and never writes long-term statistics. SRP actually publishes **hourly** data (it
arrives with a ~1–2 day delay). A normal `total_increasing` sensor cannot
represent delayed historical hours — it only ever records the "now" value.

This integration instead imports each hour at its real timestamp using Home
Assistant's external-statistics API (the same approach the official `opower`
integration uses). That gives you:

- **`srp_energy:<account>_energy_consumption`** — hourly kWh, for the Energy Dashboard.
- **`srp_energy:<account>_energy_cost`** — hourly cost, in your HA currency.
- Four informational sensors (latest hour usage/cost, latest day usage/cost) for
  regular dashboard cards and automations.

## Installation (HACS)

1. In HACS → **Integrations** → three-dot menu → **Custom repositories**.
2. Add `https://github.com/cdiaz2799/home-assistant-srp-integration` with category
   **Integration**.
3. Install **SRP Energy (Hourly)** and restart Home Assistant.

> **Note:** This integration uses the `srp_energy` domain and therefore *overrides*
> the built-in integration of the same name. Home Assistant will log a warning that
> a custom integration is overriding a built-in one — this is expected. Do not
> configure both.

Alternatively, copy `custom_components/srp_energy` into your Home Assistant
`config/custom_components/` directory manually and restart.

## Configuration

1. **Settings → Devices & Services → Add Integration → SRP Energy**.
2. Enter:
   - **Account ID** — your SRP account number (digits only).
   - **Name** — a friendly name for the device.
   - **Username** / **Password** — your srpnet.com login.
   - **Time-of-use plan** — enable if you are on an SRP TOU rate.

On first setup the integration backfills up to ~3 years of history (whatever SRP
makes available), in 90-day chunks. Subsequent updates run every 12 hours and only
import newly available hours.

## Adding to the Energy Dashboard

1. Go to **Settings → Dashboards → Energy**.
2. Under **Electricity grid → Add consumption**, choose
   **SRP energy consumption**.
3. For cost, select **Use an entity tracking the total costs** and choose
   **SRP energy cost**.

Because SRP data lags by a day or two, the most recent day or two on the Energy
Dashboard will fill in once SRP publishes it.

## Development

```bash
pip install -r requirements_test.txt
pytest
```

CI runs [hassfest](https://developers.home-assistant.io/docs/creating_component_index),
the [HACS action](https://github.com/hacs/action), and the test suite.

## Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by Salt
River Project.
