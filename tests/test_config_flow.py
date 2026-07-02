"""Test the SRP Energy config flow."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.srp_energy.const import DOMAIN

from .const import MOCK_CONFIG


async def test_full_flow(hass: HomeAssistant, mock_srp_client: MagicMock) -> None:
    """A valid account and credentials create an entry."""
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
    assert result["title"] == MOCK_CONFIG["name"]
    assert result["data"] == MOCK_CONFIG


async def test_invalid_auth(hass: HomeAssistant, mock_srp_client: MagicMock) -> None:
    """A rejected login surfaces invalid_auth."""
    mock_srp_client.validate.return_value = False

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MOCK_CONFIG
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_invalid_account(
    hass: HomeAssistant, mock_srp_client: MagicMock
) -> None:
    """A ValueError from the client maps to invalid_account."""
    mock_srp_client.validate.side_effect = ValueError("bad account")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MOCK_CONFIG
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_account"}


async def test_unknown_error(
    hass: HomeAssistant, mock_srp_client: MagicMock
) -> None:
    """An unexpected error maps to unknown."""
    mock_srp_client.validate.side_effect = TimeoutError("boom")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MOCK_CONFIG
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_duplicate_aborts(
    hass: HomeAssistant,
    mock_srp_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Configuring the same account twice aborts."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MOCK_CONFIG
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
