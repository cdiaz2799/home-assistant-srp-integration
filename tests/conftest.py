"""Fixtures for SRP Energy (Hourly) tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.srp_energy_hourly.const import (
    CONF_ACCOUNT_ID,
    CONF_IS_TOU,
    DOMAIN,
)

from pytest_homeassistant_custom_component.common import MockConfigEntry

ACCOUNT_ID = "123456789"

MOCK_CONFIG = {
    CONF_ACCOUNT_ID: ACCOUNT_ID,
    CONF_USERNAME: "user@example.com",
    CONF_PASSWORD: "hunter2",
    CONF_IS_TOU: False,
}


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id=ACCOUNT_ID,
        title=f"SRP {ACCOUNT_ID}",
    )


@pytest.fixture
def mock_setup_entry() -> Generator[MagicMock]:
    """Prevent the real setup from running during config-flow tests."""
    with patch(
        "custom_components.srp_energy_hourly.async_setup_entry", return_value=True
    ) as setup_entry:
        yield setup_entry


@pytest.fixture
def mock_srp_client() -> Generator[MagicMock]:
    """Mock the SrpEnergyClient used across the integration."""
    with (
        patch(
            "custom_components.srp_energy_hourly.SrpEnergyClient", autospec=True
        ) as init_client,
        patch(
            "custom_components.srp_energy_hourly.config_flow.SrpEnergyClient",
            new=init_client,
        ),
    ):
        client = init_client.return_value
        client.validate.return_value = True
        client.usage.return_value = []
        yield client
