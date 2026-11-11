# Kubu Cloud (hub sensors, unofficial)

Home Assistant custom integration for **hub-connected Kubu door and window sensors**
(e.g. `std-d` door and `std-w` window sensors paired to a Kubu hub). It reads their state
from the Kubu cloud (`api-green.kubusmart.com`), the same data the Kubu app shows.

Not affiliated with or endorsed by Kubu. If your sensors are the Bluetooth "Retro" range,
use the local Bluetooth integration `geekyboi/kubu-home-assistant` instead.

## Install (HACS)

HACS → ⋮ → Custom repositories → add this repo as type **Integration** → install
**Kubu Cloud** → restart Home Assistant → Settings → Devices & services → Add integration →
**Kubu Cloud** → sign in with your Kubu email and password.

## Entities

Per sensor: Door / Window (open), Lock (doors; on = unlocked), Not secure, Status (raw text
from Kubu), Battery, Last update, Online.
Hub: Online, Last connected, SureShield armed.

## Notes

- Cloud polling, default every 60 s (Options: 30–3600 s).
- Your Kubu login is stored in Home Assistant so the integration can sign in again when the
  session expires. If Kubu rejects it you'll be asked to re-enter it.
- Status words seen so far: `locked`, `secure`, `unsecure`. Unmapped words are logged once
  and shown as-is on the Status sensor; open/lock binary sensors show *unknown* for them.
  Please open an issue with any new status words you see.

## Licence

MIT
