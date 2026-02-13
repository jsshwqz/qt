# Change Note

- Date: 2026-02-13
- Commit: pending
- Scope: Wi-Fi device discovery reliability on multi-NIC PCs

## 1) Problem / Symptom
- In some environments with multiple network adapters, auto Wi-Fi scan could not find device even when manual `IP` connect succeeded.
- User-reported behavior: automatic scan failed, manual phone IP connection succeeded immediately.

## 2) Root Cause
- Discovery subnet selection was too narrow:
  - only one candidate subnet was effectively prioritized from interface selection flow,
  - saved subnet pool was capped too low,
  - multi-NIC setups could pick a non-target subnet and miss the phone.

## 3) Changes Made
- `QtScrcpy/src/adb/devicediscovery.cpp`
  - Expanded saved subnet cap from `2` to `4`.
  - Reworked subnet selection strategy in `getLocalNetworkSegments()`:
    - gather multiple active Wi-Fi subnets (not just first candidate),
    - merge with saved successful subnets,
    - merge with configured Wi-Fi and active-any fallback,
    - cap final scan list to `4` subnets with de-dup.
- `QtScrcpy/src/ui/mainwindow.h`
  - Added helper declaration: `rememberNetworkSegment(const QString& ipAddress)`.
- `QtScrcpy/src/ui/mainwindow.cpp`
  - On successful manual Wi-Fi connect, remember subnet for future scan priority.
  - On successful USB-assisted Wi-Fi connect, remember subnet likewise.
  - Persist to:
    - `network/lastScanSegments`
    - `network/lastScanSegment`

## 4) Validation Evidence
- Source-level checks confirm:
  - multi-subnet merge logic now exists,
  - scan candidate list supports up to 4 subnets,
  - successful connect path updates remembered subnet list.
- Expected behavior change:
  - auto scan becomes robust on multi-network-card systems,
  - repeated use converges faster because known-good subnet is prioritized.

## 5) Risk and Rollback
- Risk:
  - scanning more subnets can increase scan time in very complex networks.
- Mitigation:
  - hard cap at 4 subnets and de-dup logic.
- Rollback:
  - revert this commit to previous single-subnet preference behavior.
