"""Polling coordinator for one Kubu home."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KubuAuthError, KubuClient, KubuConnectionError
from .const import (
    CLOSED_STATUSES,
    CONF_HOME_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    OPEN_STATUSES,
    TAMPER_STATUSES,
)
from .model import KubuHome, parse_dashboard

_LOGGER = logging.getLogger(__name__)
_KNOWN = OPEN_STATUSES | CLOSED_STATUSES | TAMPER_STATUSES | {"unsecure", "insecure"}

type KubuConfigEntry = ConfigEntry["KubuCoordinator"]


class KubuCoordinator(DataUpdateCoordinator[KubuHome]):
    """Fetch /view/rooms on an interval."""

    config_entry: KubuConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: KubuConfigEntry, client: KubuClient
    ) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self.home_id: str = entry.data[CONF_HOME_ID]
        self._unknown_logged: set[str] = set()

    async def _async_update_data(self) -> KubuHome:
        try:
            raw = await self.client.async_get_dashboard(self.home_id)
        except KubuAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KubuConnectionError as err:
            raise UpdateFailed(str(err)) from err

        home = parse_dashboard(self.home_id, self.config_entry.title, raw)
        for sensor in home.sensors.values():
            key = sensor.status_key
            if key and key not in _KNOWN and key not in self._unknown_logged:
                self._unknown_logged.add(key)
                _LOGGER.warning(
                    "Kubu sensor '%s' (%s) reported status '%s' which this integration "
                    "doesn't map yet; the Status sensor shows it, binary sensors show unknown",
                    sensor.name,
                    sensor.kind,
                    sensor.status,
                )
        return home
