"""Base entities for Kubu Cloud."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import KubuCoordinator
from .model import KubuHub, KubuSensor

PRODUCT_NAMES = {"std-d": "Door sensor", "std-w": "Window sensor"}


def _fmt_mac(mac: str | None) -> str | None:
    if not mac or len(mac) != 12:
        return None
    return ":".join(mac[i : i + 2] for i in range(0, 12, 2)).lower()


class KubuEntity(CoordinatorEntity[KubuCoordinator]):
    """Common base."""

    _attr_has_entity_name = True


class KubuSensorEntity(KubuEntity):
    """Entity attached to one door/window sensor."""

    def __init__(self, coordinator: KubuCoordinator, sensor_id: str, key: str) -> None:
        super().__init__(coordinator)
        self._sensor_id = sensor_id
        self._attr_unique_id = f"{sensor_id}_{key}"
        s = self.sensor
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, sensor_id)},
            name=s.name,
            manufacturer=MANUFACTURER,
            model=PRODUCT_NAMES.get(s.product_type or "", s.product_type or s.kind),
            suggested_area=s.room,
        )

    @property
    def sensor(self) -> KubuSensor:
        return self.coordinator.data.sensors[self._sensor_id]

    @property
    def available(self) -> bool:
        return super().available and self._sensor_id in self.coordinator.data.sensors


class KubuHubEntity(KubuEntity):
    """Entity attached to the Kubu hub."""

    def __init__(self, coordinator: KubuCoordinator, hub_id: str, key: str) -> None:
        super().__init__(coordinator)
        self._hub_id = hub_id
        self._attr_unique_id = f"{hub_id}_{key}"
        h = self.hub
        mac = _fmt_mac(h.mac)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub_id)},
            connections={(CONNECTION_NETWORK_MAC, mac)} if mac else set(),
            name=h.name,
            manufacturer=MANUFACTURER,
            model="Kubu hub",
            sw_version=h.fw,
            hw_version=h.hw,
        )

    @property
    def hub(self) -> KubuHub:
        return self.coordinator.data.hubs[self._hub_id]

    @property
    def available(self) -> bool:
        return super().available and self._hub_id in self.coordinator.data.hubs
