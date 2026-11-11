"""Minimal async client for the Kubu cloud API (api-green.kubusmart.com).

Endpoints used (both observed from the official app's traffic shape):
  POST /oauth/login            {"email", "password"} -> idToken, expiresIn, homes[]
  GET  /view/rooms?homeId=...  Bearer idToken       -> things[], rooms[], entities[], ...
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

from .const import API_BASE, DEFAULT_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class KubuError(Exception):
    """Base error."""


class KubuAuthError(KubuError):
    """Credentials rejected."""


class KubuConnectionError(KubuError):
    """Cloud unreachable or returned something unexpected."""


class KubuClient:
    """Signs in with email/password and reads the home dashboard."""

    def __init__(
        self, session: aiohttp.ClientSession, email: str, password: str
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._token: str | None = None
        self._token_expiry: float = 0.0
        self._lock = asyncio.Lock()
        self.account_id: str | None = None
        self.homes: list[dict[str, Any]] = []

    async def async_login(self) -> dict[str, Any]:
        """Sign in and cache the token. Returns the raw login payload."""
        try:
            async with self._session.post(
                f"{API_BASE}/oauth/login",
                json={"email": self._email, "password": self._password},
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as resp:
                if resp.status in (400, 401, 403):
                    raise KubuAuthError(f"login rejected (HTTP {resp.status})")
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except KubuAuthError:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise KubuConnectionError(f"login failed: {err}") from err

        if not isinstance(data, dict):
            raise KubuConnectionError("login reply was not an object")
        token = data.get("idToken") or data.get("accessToken")
        if not isinstance(token, str) or not token:
            raise KubuConnectionError("login reply had no token")

        expires_in = data.get("expiresIn")
        lifetime = int(expires_in) if isinstance(expires_in, (int, float)) else 3600
        # Renew a minute early so a poll never races the expiry.
        self._token = token
        self._token_expiry = time.monotonic() + max(lifetime - 60, 60)
        self.account_id = str(data.get("id") or self._email.lower())
        self.homes = [h for h in data.get("homes") or [] if isinstance(h, dict)]
        return data

    async def _async_ensure_token(self) -> str:
        async with self._lock:
            if not self._token or time.monotonic() >= self._token_expiry:
                await self.async_login()
            assert self._token
            return self._token

    async def async_get_dashboard(self, home_id: str) -> dict[str, Any]:
        """Return /view/rooms for one home, re-signing in once on 401/403."""
        for attempt in (1, 2):
            token = await self._async_ensure_token()
            try:
                async with self._session.get(
                    f"{API_BASE}/view/rooms",
                    params={"homeId": home_id},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
                ) as resp:
                    if resp.status in (401, 403) and attempt == 1:
                        _LOGGER.debug("Token refused (HTTP %s), signing in again", resp.status)
                        self._token = None
                        continue
                    if resp.status in (401, 403):
                        raise KubuAuthError(f"dashboard refused (HTTP {resp.status})")
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
            except KubuAuthError:
                raise
            except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                raise KubuConnectionError(f"dashboard request failed: {err}") from err
            if not isinstance(data, dict):
                raise KubuConnectionError("dashboard reply was not an object")
            return data
        raise KubuAuthError("could not obtain a valid token")
