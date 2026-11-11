"""Tests against a dashboard shaped like Simon's real /view/rooms reply (values invented)."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kubu_cloud.api import KubuAuthError
from custom_components.kubu_cloud.const import CONF_HOME_ID, DOMAIN

HOME = "h" * 32
HUB = "t" * 32
WIN = "e1" + "0" * 30
DOOR = "e2" + "0" * 30

LOGIN = {"id": "u" * 32, "homes": [{"id": HOME, "name": "Home"}], "idToken": "x", "expiresIn": 3600}


def dash(window="secure", door="locked", win_online=True):
    return {
        "homeName": "Home",
        "homes": [{"id": HOME, "name": "Home", "status": "unsecure"}],
        "armStat": False,
        "things": [{"id": HUB, "name": "Kubu Hub", "macId": "A1B2C3D4E5F6", "fwVer": "5.31",
                     "hwRev": "v01", "isOnline": True, "lastConnected": "2026-11-11T08:00:00Z",
                     "nodesCount": 2}],
        "rooms": [{"id": "r1", "name": "Lounge"}, {"id": "r2", "name": "Hall"}],
        "entities": [
            {"id": WIN, "name": "Lounge window", "type": "window", "productType": "std-w",
             "status": window, "batteryStatus": "good", "isOnline": win_online, "homeId": HOME, "isDeleted": 0,
             "roomId": "r1", "updatedOn": "2026-11-11T07:59:00Z"},
            {"id": DOOR, "name": "Front door", "type": "door", "productType": "std-d",
             "status": door, "batteryStatus": "low", "isOnline": True, "homeId": HOME, "isDeleted": 0,
             "roomId": "r2", "updatedOn": "2026-11-11T07:58:00Z"},
        ],
        "ungroupedEntities": [],
        "bleNodes": [],
    }


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def _login(self):
    self.homes = LOGIN["homes"]
    self.account_id = LOGIN["id"]
    self._token = "x"
    return LOGIN


async def test_flow_and_entities(hass: HomeAssistant) -> None:
    state = {"d": dash()}

    async def _dash(self, home_id):
        d = dict(state["d"])
        if home_id is None:
            return d  # default-home reply includes hubs
        assert home_id == HOME
        d.pop("things")  # per-home reply has no hubs, like the real API
        return d

    with patch("custom_components.kubu_cloud.api.KubuClient.async_login", _login), patch(
        "custom_components.kubu_cloud.api.KubuClient.async_get_dashboard", _dash
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_EMAIL: "a@b.com", CONF_PASSWORD: "pw"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_HOME_ID] == HOME
        await hass.async_block_till_done()

        states = {s.entity_id: s.state for s in hass.states.async_all()}
        print("\n".join(f"{k} = {v}" for k, v in sorted(states.items())))

        # std-d door sensors only report lock state, so Door stays unknown for them.
        assert states["binary_sensor.front_door_door"] == "unknown"
        assert states["binary_sensor.front_door_lock"] == "off"  # locked
        assert states["binary_sensor.front_door_not_secure"] == "off"
        assert states["binary_sensor.lounge_window_window"] == "off"
        assert states["sensor.front_door_status"] == "Locked"
        assert states["sensor.front_door_battery"] == "Low"
        assert states["binary_sensor.kubu_hub_online"] == "on"
        assert states["binary_sensor.kubu_hub_sureshield_armed"] == "off"
        assert states["sensor.kubu_hub_last_connected"].startswith("2026-11-11T08:00")

        # Door unlocked then opened; window opened.
        state["d"] = dash(window="open", door="unlocked")
        coord = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
        await coord.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get("binary_sensor.front_door_lock").state == "on"
        assert hass.states.get("binary_sensor.front_door_not_secure").state == "on"
        assert hass.states.get("binary_sensor.lounge_window_window").state == "on"

        # Window shut but not yet latched: the real device reports "closed" for about
        # a minute before "secure".
        state["d"] = dash(window="closed")
        await coord.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get("binary_sensor.lounge_window_window").state == "off"
        assert hass.states.get("binary_sensor.lounge_window_not_secure").state == "on"

        # Unknown status -> raw sensor shows it, binaries unknown.
        state["d"] = dash(door="weird")
        await coord.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get("sensor.front_door_status").state == "Weird"
        assert hass.states.get("binary_sensor.front_door_lock").state == "unknown"

        # Window goes offline -> its state entities unavailable, Online/Status remain.
        state["d"] = dash(win_online=False)
        await coord.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get("binary_sensor.lounge_window_window").state == "unavailable"
        assert hass.states.get("binary_sensor.lounge_window_not_secure").state == "unavailable"
        assert hass.states.get("binary_sensor.lounge_window_online").state == "off"
        assert hass.states.get("sensor.lounge_window_status").state == "Secure"


async def test_bad_login(hass: HomeAssistant) -> None:
    async def _bad(self):
        raise KubuAuthError("no")

    with patch("custom_components.kubu_cloud.api.KubuClient.async_login", _bad):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_EMAIL: "a@b.com", CONF_PASSWORD: "pw"}
        )
        assert result["errors"] == {"base": "invalid_auth"}


async def test_auth_failure_triggers_reauth(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=HOME, title="Home",
        data={CONF_EMAIL: "a@b.com", CONF_PASSWORD: "pw", CONF_HOME_ID: HOME},
    )
    entry.add_to_hass(hass)

    async def _dash(self, home_id):
        raise KubuAuthError("expired")

    with patch("custom_components.kubu_cloud.api.KubuClient.async_get_dashboard", _dash):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == "reauth" for f in flows)


async def test_hubs_are_cached_between_polls(hass: HomeAssistant) -> None:
    calls = {"default": 0, "home": 0}

    async def _dash(self, home_id):
        d = dash()
        if home_id is None:
            calls["default"] += 1
            return d
        calls["home"] += 1
        d.pop("things")
        return d

    with patch("custom_components.kubu_cloud.api.KubuClient.async_login", _login), patch(
        "custom_components.kubu_cloud.api.KubuClient.async_get_dashboard", _dash
    ):
        entry = MockConfigEntry(
            domain=DOMAIN, unique_id=HOME, title="Home",
            data={CONF_EMAIL: "a@b.com", CONF_PASSWORD: "pw", CONF_HOME_ID: HOME},
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        coord = entry.runtime_data
        for _ in range(3):
            await coord.async_refresh()

        # Per-home dashboard every poll, default-home (hubs) only once.
        assert calls["home"] == 4
        assert calls["default"] == 1
        assert hass.states.get("binary_sensor.kubu_hub_online").state == "on"

        # Cache expiry triggers another hub fetch.
        coord._hubs_fetched -= 10_000
        await coord.async_refresh()
        assert calls["default"] == 2
