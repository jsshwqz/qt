# Change Note

- Date: 2026-02-13
- Commit: pending
- Scope: USB-assisted Wi-Fi connect reliability after `adb tcpip`

## 1) Problem / Symptom
- User feedback: USB mirroring could work, but Wi-Fi scan/USB-assisted Wi-Fi connect was unstable and often failed to find phone.
- Runtime logs repeatedly showed:
  - `Failed to resolve device Wi-Fi IP from USB device: ...`

## 2) Root Cause
- After `adb tcpip 5555`, device transport can restart briefly; immediate IP query may run during this transition and fail.
- IP route fallback previously accepted first generic IPv4 and could select non-Wi-Fi tunnel/VPN address in mixed-network environments.

## 3) Changes Made
- `QtScrcpy/src/ui/mainwindow.cpp`
  - `prepareWirelessFromUsb()` now retries Wi-Fi IP resolution (up to 12 attempts with short delay) after `adb tcpip`.
  - `resolveDeviceWifiIp()` improved priority:
    1. query `wlan0`-focused commands first;
    2. route fallback now only accepts `src` from `dev wlan0` lines;
    3. generic command parsing is used only after Wi-Fi-specific attempts.

## 4) Validation Evidence
- Source-level verification:
  - retry loop added after `tcpip` transition;
  - route parsing no longer blindly takes tunnel/VPN IPv4.
- Expected behavior:
  - significantly fewer false negatives in USB-assisted Wi-Fi preparation,
  - better subnet targeting in environments with `tun0`/VPN interfaces.

## 5) Risk and Rollback
- Known risk:
  - USB-assisted preparation may wait up to a few extra seconds while retrying.
- Mitigation:
  - bounded retry count with fixed short interval.
- Rollback plan:
  - revert this commit to restore previous immediate single-attempt resolve behavior.

