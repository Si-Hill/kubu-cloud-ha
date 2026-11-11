"""Sensors for Kubu Cloud."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import KubuConfigEntry, KubuCoordinator
from .entity import KubuHubEntity, KubuSensorEntity
from .model import KubuSensor

PARALLEL_UPDATES = 0


def _ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = dt_util.parse_datetime(value)
    except ValueError:
        return None
    if parsed is not None and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.UTC)
    return parsed


@dataclass(frozen=True, kw_only=True)
class KubuSensorDescription(SensorEntityDescription):
    value_fn: Callable[[KubuSensor], str | datetime | None]


SENSORS: tuple[KubuSensorDescription, ...] = (
    KubuSensorDescription(
        key="status",
        translation_key="status",
        value_fn=lambda s: s.status,
    ),
    KubuSensorDescription(
        key="battery_status",
        translation_key="battery_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.battery_status,
    ),
    KubuSensorDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: _ts(s.updated_on),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KubuConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    def _add_new() -> None:
        new: list[SensorEntity] = []
        data = coordinator.data
        for hub_id in data.hubs:
            if (key := f"hub:{hub_id}") not in known:
                known.add(key)
                new.append(KubuHubLastConnected(coordinator, hub_id))
        for sid in data.sensors:
            if (key := f"sensor:{sid}") not in known:
                known.add(key)
                new.extend(KubuSensor_(coordinator, sid, d) for d in SENSORS)
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class KubuSensor_(KubuSensorEntity, SensorEntity):  # noqa: N801
    entity_description: KubuSensorDescription

    def __init__(
        self,
        coordinator: KubuCoordinator,
        sensor_id: str,
        description: KubuSensorDescription,
    ) -> None:
        super().__init__(coordinator, sensor_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | datetime | None:
        return self.entity_description.value_fn(self.sensor)


class KubuHubLastConnected(KubuHubEntity, SensorEntity):
    _attr_translation_key = "hub_last_connected"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: KubuCoordinator, hub_id: str) -> None:
        super().__init__(coordinator, hub_id, "last_connected")

    @property
    def native_value(self) -> datetime | None:
        return _ts(self.hub.last_connected)
