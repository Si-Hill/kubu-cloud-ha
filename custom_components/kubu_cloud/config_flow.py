"""Config flow for Kubu Cloud."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import KubuAuthError, KubuClient, KubuConnectionError
from .const import (
    CONF_HOME_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

CREDS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
    }
)


async def _async_try_login(
    flow: ConfigFlow, email: str, password: str
) -> tuple[KubuClient | None, dict[str, str]]:
    client = KubuClient(async_get_clientsession(flow.hass), email, password)
    try:
        await client.async_login()
    except KubuAuthError:
        return None, {"base": "invalid_auth"}
    except KubuConnectionError:
        return None, {"base": "cannot_connect"}
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Unexpected error signing in to Kubu")
        return None, {"base": "unknown"}
    if not client.homes:
        return None, {"base": "no_homes"}
    return client, {}


class KubuCloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Sign in, then pick a home if the account has more than one."""

    VERSION = 1

    def __init__(self) -> None:
        self._email = ""
        self._password = ""
        self._client: KubuClient | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._email = user_input[CONF_EMAIL].strip()
            self._password = user_input[CONF_PASSWORD]
            self._client, errors = await _async_try_login(
                self, self._email, self._password
            )
            if not errors:
                if len(self._client.homes) == 1:
                    return await self._async_create_for_home(self._client.homes[0])
                return await self.async_step_home()
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                CREDS_SCHEMA, {CONF_EMAIL: self._email}
            ),
            errors=errors,
        )

    async def async_step_home(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._client
        homes = {h["id"]: h for h in self._client.homes if h.get("id")}
        if user_input is not None:
            return await self._async_create_for_home(homes[user_input[CONF_HOME_ID]])
        options = [
            SelectOptionDict(value=hid, label=str(h.get("name") or hid))
            for hid, h in homes.items()
        ]
        return self.async_show_form(
            step_id="home",
            data_schema=vol.Schema(
                {vol.Required(CONF_HOME_ID): SelectSelector(
                    SelectSelectorConfig(options=options)
                )}
            ),
        )

    async def _async_create_for_home(self, home: dict[str, Any]) -> ConfigFlowResult:
        await self.async_set_unique_id(home["id"])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=str(home.get("name") or "Kubu"),
            data={
                CONF_EMAIL: self._email,
                CONF_PASSWORD: self._password,
                CONF_HOME_ID: home["id"],
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        self._email = entry_data.get(CONF_EMAIL, "")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            client, errors = await _async_try_login(
                self, email, user_input[CONF_PASSWORD]
            )
            if not errors:
                if not any(h.get("id") == entry.data[CONF_HOME_ID] for h in client.homes):
                    errors = {"base": "wrong_account"}
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={
                            CONF_EMAIL: email,
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                    )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                CREDS_SCHEMA, {CONF_EMAIL: self._email}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return KubuCloudOptionsFlow()


class KubuCloudOptionsFlow(OptionsFlow):
    """Poll interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=3600)
                    )
                }
            ),
        )
