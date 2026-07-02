"""Informational sensors for the SRP Energy integration.

These sensors surface the most recently available hourly and daily values for
convenient dashboard cards and automations. They are intentionally *not*
``total``/``total_increasing`` sensors: the Energy Dashboard is fed by the
long-term statistics imported by the coordinator, and exposing accumulating
sensors here would let the dashboard double-count usage.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DEVICE_MANUFACTURER, DEVICE_MODEL, DOMAIN
from .coordinator import (
    SrpEnergyConfigEntry,
    SrpEnergySnapshot,
    SrpEnergyStatisticsCoordinator,
)


@dataclass(frozen=True, kw_only=True)
class SrpEnergySensorEntityDescription(SensorEntityDescription):
    """Describes an SRP Energy sensor."""

    value_fn: Callable[[SrpEnergySnapshot], float | None]
    is_currency: bool = False


SENSOR_TYPES: tuple[SrpEnergySensorEntityDescription, ...] = (
    SrpEnergySensorEntityDescription(
        key="latest_hour_usage",
        translation_key="latest_hour_usage",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=lambda data: data.latest_hour_usage,
    ),
    SrpEnergySensorEntityDescription(
        key="latest_hour_cost",
        translation_key="latest_hour_cost",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        is_currency=True,
        value_fn=lambda data: data.latest_hour_cost,
    ),
    SrpEnergySensorEntityDescription(
        key="latest_day_usage",
        translation_key="latest_day_usage",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=lambda data: data.latest_day_usage,
    ),
    SrpEnergySensorEntityDescription(
        key="latest_day_cost",
        translation_key="latest_day_cost",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        is_currency=True,
        value_fn=lambda data: data.latest_day_cost,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SrpEnergyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up SRP Energy sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        SrpEnergySensor(coordinator, entry, description)
        for description in SENSOR_TYPES
    )


class SrpEnergySensor(
    CoordinatorEntity[SrpEnergyStatisticsCoordinator], SensorEntity
):
    """An informational SRP Energy sensor."""

    entity_description: SrpEnergySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SrpEnergyStatisticsCoordinator,
        entry: SrpEnergyConfigEntry,
        description: SrpEnergySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or DEFAULT_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
            entry_type=DeviceEntryType.SERVICE,
        )
        if description.is_currency:
            self._attr_native_unit_of_measurement = coordinator.currency

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator.data)
