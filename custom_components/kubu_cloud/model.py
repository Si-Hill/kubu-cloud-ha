"""Turn the Kubu /view/rooms payload into plain dataclasses (no HA imports)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import (
    CLOSED_STATUSES,
    LOCKED_STATUSES,
    OPEN_STATUSES,
    UNLOCKED_STATUSES,
)


def _str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


@dataclass(slots=True)
class KubuHub:
    id: str
    name: str
    mac: str | None
    fw: str | None
    hw: str | None
    online: bool | None
    last_connected: str | None


@dataclass(slots=True)
class KubuSensor:
    id: str
    name: str
    kind: str | None  # "door", "window", ...
    product_type: str | None  # "std-d", "std-w", ...
    status: str | None  # raw: "locked", "secure", "unsecure", ...
    battery_status: str | None
    online: bool | None
    updated_on: str | None
    room: str | None

    @property
    def status_key(self) -> str | None:
        return self.status.strip().lower() if self.status else None

    @property
    def is_open(self) -> bool | None:
        s = self.status_key
        if s is None:
            return None
        if s in OPEN_STATUSES:
            return True
        if s in CLOSED_STATUSES:
            return False
        return None

    @property
    def is_unlocked(self) -> bool | None:
        """For doors: True = unlocked (HA lock device class semantics)."""
        s = self.status_key
        if s is None or self.kind != "door":
            return None
        if s in LOCKED_STATUSES:
            return False
        if s in UNLOCKED_STATUSES:
            return True
        return None

    @property
    def is_insecure(self) -> bool | None:
        """True when not in its fully secured state (locked door / secure window).

        An unrecognised status counts as not secured: it is safer to show
        "Unsafe" than to claim a door or window is secure when we cannot tell.
        """
        s = self.status_key
        if s is None:
            return None
        if self.kind == "door":
            return s not in LOCKED_STATUSES
        return s not in {"secure", "locked"}


@dataclass(slots=True)
class KubuHome:
    id: str
    name: str
    status: str | None
    armed: bool | None
    hubs: dict[str, KubuHub] = field(default_factory=dict)
    sensors: dict[str, KubuSensor] = field(default_factory=dict)


def parse_dashboard(home_id: str, home_name: str, data: dict[str, Any]) -> KubuHome:
    """Parse a /view/rooms reply."""
    homes = [h for h in data.get("homes") or [] if isinstance(h, dict)]
    this_home = next((h for h in homes if h.get("id") == home_id), {})
    home = KubuHome(
        id=home_id,
        name=_str(data.get("homeName")) or _str(this_home.get("name")) or home_name,
        status=_str(this_home.get("status")),
        armed=_bool(data.get("armStat")),
    )

    for thing in data.get("things") or []:
        if not isinstance(thing, dict) or not _str(thing.get("id")):
            continue
        hub = KubuHub(
            id=thing["id"],
            name=_str(thing.get("name")) or "Kubu hub",
            mac=_str(thing.get("macId")),
            fw=_str(thing.get("fwVer")),
            hw=_str(thing.get("hwRev")),
            online=_bool(thing.get("isOnline")),
            last_connected=_str(thing.get("lastConnected")),
        )
        home.hubs[hub.id] = hub

    room_names: dict[str, str] = {}
    for room in data.get("rooms") or []:
        if isinstance(room, dict) and _str(room.get("id")):
            room_names[room["id"]] = _str(room.get("name")) or ""

    entities = list(data.get("entities") or []) + list(
        data.get("ungroupedEntities") or []
    )
    for ent in entities:
        if not isinstance(ent, dict) or not _str(ent.get("id")):
            continue
        if ent.get("isDeleted") not in (None, 0, False):
            continue
        sensor = KubuSensor(
            id=ent["id"],
            name=_str(ent.get("name")) or "Kubu sensor",
            kind=(_str(ent.get("type")) or "").lower() or None,
            product_type=_str(ent.get("productType")),
            status=_str(ent.get("status")),
            battery_status=_str(ent.get("batteryStatus")),
            online=_bool(ent.get("isOnline")),
            updated_on=_str(ent.get("updatedOn")),
            room=room_names.get(ent.get("roomId") or "") or None,
        )
        home.sensors[sensor.id] = sensor

    return home
