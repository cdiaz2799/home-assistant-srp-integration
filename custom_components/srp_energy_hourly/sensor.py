"""Live sensor entities for the SRP Energy (Hourly) integration.

These are convenience entities for dashboards and automations. The Energy
Dashboard itself is fed by the long-term statistics imported in the coordinator,
not by these sensors.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CURRENCY_USD
from .coordinator import (
    SrpEnergyHourlyConfigEntry,
    SrpEnergyHourlyCoordinator,
    SrpLiveData,
)


@dataclass(frozen=True, kw_only=True)
class SrpSensorEntityDescription(SensorEntityDescription):
    """Describes an SRP live sensor."""

    value_fn: Callable[[SrpLiveData], float | datetime | None]


SENSOR_TYPES: tuple[SrpSensorEntityDescription, ...] = (
    SrpSensorEntityDescription(
        key="yesterday_energy",
        translation_key="yesterday_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda data: data.yesterday_kwh,
    ),
    SrpSensorEntityDescription(
        key="yesterday_cost",
        translation_key="yesterday_cost",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_USD,
        value_fn=lambda data: data.yesterday_cost,
    ),
    SrpSensorEntityDescription(
        key="latest_hour_energy",
        translation_key="latest_hour_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda data: data.latest_hour_kwh,
    ),
    SrpSensorEntityDescription(
        key="latest_hour_cost",
        translation_key="latest_hour_cost",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_USD,
        value_fn=lambda data: data.latest_hour_cost,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SrpEnergyHourlyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the SRP Energy (Hourly) sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        SrpEnergyHourlySensor(coordinator, entry, description)
        for description in SENSOR_TYPES
    )


class SrpEnergyHourlySensor(
    CoordinatorEntity[SrpEnergyHourlyCoordinator], SensorEntity
):
    """Representation of an SRP live sensor."""

    entity_description: SrpSensorEntityDescription
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: SrpEnergyHourlyCoordinator,
        entry: SrpEnergyHourlyConfigEntry,
        description: SrpSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_extra_state_attributes = {}

    @property
    def native_value(self) -> float | datetime | None:
        """Return the current value."""
        if self.coordinator.data is None:
            return None
        value = self.entity_description.value_fn(self.coordinator.data)
        if self.entity_description.key == "latest_hour_energy":
            start = self.coordinator.data.latest_hour_start
            self._attr_extra_state_attributes = {
                "hour_start": start.isoformat() if start else None
            }
        return value
