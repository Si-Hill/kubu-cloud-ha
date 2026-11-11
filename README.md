<p align="center">
  <img src="https://raw.githubusercontent.com/Si-Hill/kubu-cloud-ha/main/custom_components/kubu_cloud/brand/logo.png" alt="Kubu" width="300">
</p>

# Kubu Cloud (Unofficial)

<p align="center">
  <img src="https://img.shields.io/badge/HOME%20ASSISTANT-2025.2%2B-41BDF5?style=for-the-badge&logo=homeassistant&logoColor=white" alt="Home Assistant 2025.2+">
  <img src="https://img.shields.io/badge/HACS-CUSTOM-orange?style=for-the-badge" alt="HACS Custom">
  <a href="https://github.com/Si-Hill/kubu-cloud-ha/releases/latest"><img src="https://img.shields.io/github/v/release/Si-Hill/kubu-cloud-ha?style=for-the-badge&label=STABLE&color=4c1" alt="Latest release"></a>
  <img src="https://img.shields.io/github/license/Si-Hill/kubu-cloud-ha?style=for-the-badge&label=LICENSE" alt="License">
  <a href="https://github.com/Si-Hill/kubu-cloud-ha/stargazers"><img src="https://img.shields.io/github/stars/Si-Hill/kubu-cloud-ha?style=for-the-badge&logo=github&label=STARS" alt="Stars"></a>
</p>

Home Assistant custom integration for **hub-connected Kubu door and window sensors** (e.g. `std-d` door and `std-w` window sensors paired to a Kubu hub). It reads their state from the Kubu cloud (`api-green.kubusmart.com`), the same data the Kubu app shows.

Not affiliated with or endorsed by Kubu. If your sensors are the Bluetooth "Retro" range, use the local Bluetooth integration [`geekyboi/kubu-home-assistant`](https://github.com/geekyboi/kubu-home-assistant) instead.

## Prerequisites

- Home Assistant 2025.2 or newer
- A Kubu account (the one you use in the Kubu app)
- Hub-connected Kubu door or window sensors (not the Bluetooth "Retro" range)

## 1. Install via HACS

Kubu Cloud is not in the HACS default store, so it needs adding as a custom repository first.

1. Open HACS, then **⋮ → Custom repositories**.
2. Add `https://github.com/Si-Hill/kubu-cloud-ha` as type **Integration**.
3. Search for **Kubu Cloud**, and click **Download**.
4. Restart Home Assistant.

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Si-Hill&repository=kubu-cloud-ha&category=integration)

The button above takes you straight to the Kubu Cloud page in HACS.

## 2. Add and sign in

1. **Settings → Devices & Services → Add Integration → Kubu Cloud**
2. Enter your Kubu email and password.
3. If your account has more than one home, pick which one to add. Each home becomes its own Home Assistant config entry.

No SSH, no manual token extraction, no YAML.

## 3. Verify

Open **Settings → Devices & Services → Kubu Cloud**. You should see a hub device and one device per sensor, and the hub's **Last connected** sensor should show a recent time. If it doesn't, check **Settings → System → Logs** for errors from `kubu_cloud`.

## Entities

| Device | Entity | Notes |
|---|---|---|
| Window sensor | Window | On = open |
| Door sensor | Door | On = open. The `std-d` door sensor reports lock state only, so this shows *unknown* for it; kept for door sensors that do report open/closed |
| Door sensor | Lock | On = unlocked |
| Door / window sensor | Not secure | On when not locked (door) or not `secure` (window; it reads `closed` for about a minute after shutting) |
| Door / window sensor | Status | Raw status text from Kubu |
| Door / window sensor | Battery | Raw battery status from Kubu |
| Door / window sensor | Last update, Online | Diagnostic |
| Hub | Online, Last connected | Diagnostic |
| Hub | SureShield armed | Read-only |

When a sensor is offline its Door/Window, Lock and Not secure entities show *unavailable* rather than a stale state.

## Options

**Settings → Devices & Services → Kubu Cloud → Configure** sets the poll interval. Default 60 s, range 30–3600 s.

## Notes

- This is cloud polling, so it needs internet access and follows whatever the Kubu cloud reports.
- Your Kubu login is stored in Home Assistant so the integration can sign in again when the session expires. If Kubu rejects it you'll be asked to re-enter it.
- Status words seen so far: doors report `locked` and `unlocked`; windows report `open`, `closed` and `secure`. Unmapped words (for example a vent or tilt position) are logged once and shown as-is on the Status sensor; the binary sensors show *unknown* for them. Please [open an issue](https://github.com/Si-Hill/kubu-cloud-ha/issues) with any new status words you see.
- The integration icon needs a recent Home Assistant version; older ones show a placeholder.

## Licence

MIT
