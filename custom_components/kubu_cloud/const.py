"""Constants for the Kubu Cloud integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "kubu_cloud"
MANUFACTURER = "Kubu"
API_BASE = "https://api-green.kubusmart.com"

CONF_HOME_ID = "home_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 60  # seconds
MIN_SCAN_INTERVAL = 30
DEFAULT_TIMEOUT = 30
HUB_REFRESH_INTERVAL = 600  # seconds between hub-detail refreshes
UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

# Entity status strings seen from the Kubu cloud so far, plus likely siblings.
# Raw status is always exposed on the "Status" sensor; these sets only drive the
# binary sensors. Unknown strings are logged once so the mapping can be extended.
OPEN_STATUSES = {"open", "opened", "ajar", "vent", "venting"}
CLOSED_STATUSES = {"closed", "secure", "locked", "unlocked", "shut"}
LOCKED_STATUSES = {"locked"}
UNLOCKED_STATUSES = {"unlocked", "open", "opened", "closed", "ajar"}
TAMPER_STATUSES = {"tampered", "tamper", "attack", "alarm"}
