"""Binary sensors for Kubu Cloud."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import KubuConfigEntry, KubuCoordinator
from .entity import KubuEntity, KubuHubEntity, KubuSensorEntity
from .model import KubuSensor

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class KubuSensorBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[KubuSensor], bool | None]
    supported_fn: Callable[[KubuSensor], bool] = lambda s: True
    # When the sensor is offline its last status is stale, so show unavailable.
    needs_online: bool = True


SENSOR_BINARIES: tuple[KubuSensorBinaryDescription, ...] = (
    # The std-d door sensor only reports lock state (this stays "unknown" for it), but
    # other Kubu door sensors may report open/closed, so the entity is kept.
    KubuSensorBinaryDescription(
        key="door",
        translation_key="door",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda s: s.is_open,
        supported_fn=lambda s: s.kind == "door",
    ),
    KubuSensorBinaryDescription(
        key="window",
        translation_key="window",
        device_class=BinarySensorDeviceClass.WINDOW,
        value_fn=lambda s: s.is_open,
        supported_fn=lambda s: s.kind != "door",
    ),
    KubuSensorBinaryDescription(
        key="lock",
        translation_key="lock",
        device_class=BinarySensorDeviceClass.LOCK,
        value_fn=lambda s: s.is_unlocked,
        supported_fn=lambda s: s.kind == "door",
    ),
    KubuSensorBinaryDescription(
        key="insecure",
        translation_key="insecure",
        device_class=BinarySensorDeviceClass.SAFETY,
        value_fn=lambda s: s.is_insecure,
    ),
    KubuSensorBinaryDescription(
        key="online",
        translation_key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.online,
        needs_online=False,
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
        new: list[BinarySensorEntity] = []
        data = coordinator.data
        for hub_id in data.hubs:
            if (key := f"hub:{hub_id}") not in known:
                known.add(key)
                new.append(KubuHubOnline(coordinator, hub_id))
        for sid, sensor in data.sensors.items():
            if (key := f"sensor:{sid}") in known:
                continue
            known.add(key)
            new.extend(
                KubuSensorBinary(coordinator, sid, d)
                for d in SENSOR_BINARIES
                if d.supported_fn(sensor)
            )
        if "home" not in known and data.armed is not None:
            known.add("home")
            new.append(KubuHomeArmed(coordinator))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class KubuSensorBinary(KubuSensorEntity, BinarySensorEntity):
    entity_description: KubuSensorBinaryDescription

    def __init__(
        self,
        coordinator: KubuCoordinator,
        sensor_id: str,
        description: KubuSensorBinaryDescription,
    ) -> None:
        super().__init__(coordinator, sensor_id, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return not (self.entity_description.needs_online and self.sensor.online is False)

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.sensor)


class KubuHubOnline(KubuHubEntity, BinarySensorEntity):
    _attr_translation_key = "hub_online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: KubuCoordinator, hub_id: str) -> None:
        super().__init__(coordinator, hub_id, "online")

    @property
    def is_on(self) -> bool | None:
        return self.hub.online


class KubuHomeArmed(KubuEntity, BinarySensorEntity):
    """SureShield armed state for the home (read-only)."""

    _attr_translation_key = "armed"

    def __init__(self, coordinator: KubuCoordinator) -> None:
        super().__init__(coordinator)
        hubs = list(coordinator.data.hubs)
        self._attr_unique_id = f"{coordinator.home_id}_armed"
        # Attach to the hub device when there is exactly one.
        if len(hubs) == 1:
            self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, hubs[0])})

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.armed
