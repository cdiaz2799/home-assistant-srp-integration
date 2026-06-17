"""Test the SRP Energy (Hourly) config flow."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.srp_energy_hourly.const import (
    CONF_ACCOUNT_ID,
    CONF_IS_TOU,
    DOMAIN,
)

from .conftest import MOCK_CONFIG

from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_user_flow_success(
    recorder_mock,
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_srp_client: MagicMock,
    mock_setup_entry: MagicMock,
) -> None:
    """A valid credential set creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MOCK_CONFIG
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "SRP 123456789"
    assert result["data"][CONF_ACCOUNT_ID] == "123456789"
    assert result["data"][CONF_USERNAME] == "user@example.com"
    assert result["data"][CONF_PASSWORD] == "hunter2"
    assert result["data"][CONF_IS_TOU] is False
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_flow_invalid_auth(
    recorder_mock,
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_srp_client: MagicMock,
    mock_setup_entry: MagicMock,
) -> None:
    """Invalid credentials surface an error and do not create an entry."""
    mock_srp_client.validate.return_value = False

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MOCK_CONFIG
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_unknown_error(
    recorder_mock,
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_srp_client: MagicMock,
    mock_setup_entry: MagicMock,
) -> None:
    """An unexpected client error is reported as unknown."""
    mock_srp_client.validate.side_effect = ValueError("boom")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MOCK_CONFIG
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_duplicate_account_aborts(
    recorder_mock,
    hass: HomeAssistant,
    enable_custom_integrations,
    mock_srp_client: MagicMock,
    mock_setup_entry: MagicMock,
) -> None:
    """Configuring the same account twice aborts."""
    MockConfigEntry(
        domain=DOMAIN, unique_id="123456789", data=MOCK_CONFIG
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MOCK_CONFIG
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
