"""Polling coordinator for one Kubu home."""

from __future__ import annotations

from datetime import timedelta
import logging
import time

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
    HUB_REFRESH_INTERVAL,
    LOCKED_STATUSES,
    OPEN_STATUSES,
    TAMPER_STATUSES,
    UNLOCKED_STATUSES,
)
from .model import KubuHome, parse_dashboard

_LOGGER = logging.getLogger(__name__)
_KNOWN = (
    OPEN_STATUSES
    | CLOSED_STATUSES
    | LOCKED_STATUSES
    | UNLOCKED_STATUSES
    | TAMPER_STATUSES
    | {"unsecure", "insecure"}
)

type KubuConfigEntry = ConfigEntry["KubuCoordinator"]


def _is_same_home(dashboard: dict, home_id: str) -> bool:
    """True if a /view/rooms reply's sensors or rooms belong to home_id."""
    items = list(dashboard.get("entities") or []) + list(dashboard.get("rooms") or [])
    ids = {i.get("homeId") for i in items if isinstance(i, dict) and i.get("homeId")}
    if ids:
        return ids == {home_id}
    homes = [h for h in dashboard.get("homes") or [] if isinstance(h, dict)]
    return len(homes) == 1 and homes[0].get("id") == home_id


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
        self._hubs: list | None = None
        self._hubs_fetched: float = 0.0

    async def _async_get_hubs(self) -> list:
        """Hub list borrowed from the default-home dashboard, cached.

        The per-home reply omits hubs. Hub details change rarely, so the extra
        request is only made every HUB_REFRESH_INTERVAL seconds. If a refresh
        fails with a connection error the last known hubs are kept.
        """
        now = time.monotonic()
        if self._hubs is not None and now - self._hubs_fetched < HUB_REFRESH_INTERVAL:
            return self._hubs
        try:
            default = await self.client.async_get_dashboard(None)
        except KubuConnectionError:
            if self._hubs is not None:
                return self._hubs
            raise
        # Only borrow them if that reply is about this same home.
        self._hubs = (
            list(default.get("things") or [])
            if _is_same_home(default, self.home_id)
            else []
        )
        self._hubs_fetched = now
        return self._hubs

    async def _async_update_data(self) -> KubuHome:
        try:
            raw = await self.client.async_get_dashboard(self.home_id)
            if not raw.get("things"):
                raw = {**raw, "things": await self._async_get_hubs()}
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
