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

# Entity status strings captured from the Kubu cloud. Raw status is always exposed
# on the "Status" sensor; these sets only drive the binary sensors. Unknown strings
# are logged once so the mapping can be extended.
#
# Confirmed by watching real sensors:
#   door sensor (std-d):   "locked", "unlocked"  (it reports the lock, never open/closed)
#   window sensor (std-w): "open" -> "closed" -> "secure" (about a minute between the
#                          last two); no vent/tilt word captured yet
# TAMPER_STATUSES are guesses, not yet seen.
OPEN_STATUSES = {"open"}
CLOSED_STATUSES = {"closed", "secure"}
LOCKED_STATUSES = {"locked"}
UNLOCKED_STATUSES = {"unlocked"}
TAMPER_STATUSES = {"tampered", "tamper", "attack", "alarm"}
