"""Fixtures for the SRP Energy tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.srp_energy.const import CONF_ID, DOMAIN

from .const import MOCK_CONFIG, usage_side_effect


@pytest.fixture(autouse=True)
def auto_setup(
    recorder_mock,
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable the custom integration and the recorder for every test.

    The integration depends on ``recorder``, and ``recorder_mock`` must be
    resolved before the ``hass`` fixture, so it is requested first here.
    """
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        unique_id=MOCK_CONFIG[CONF_ID],
        title=MOCK_CONFIG["name"],
    )


@pytest.fixture
def mock_srp_client() -> Generator[MagicMock]:
    """Patch SrpEnergyClient wherever it is constructed."""
    client = MagicMock()
    client.validate.return_value = True
    client.usage.side_effect = usage_side_effect
    with (
        patch(
            "custom_components.srp_energy.SrpEnergyClient",
            return_value=client,
        ),
        patch(
            "custom_components.srp_energy.config_flow.SrpEnergyClient",
            return_value=client,
        ),
    ):
        yield client
