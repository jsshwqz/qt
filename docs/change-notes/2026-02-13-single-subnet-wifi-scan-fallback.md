# Change Note

- Date: 2026-02-13
- Commit: pending
- Scope: Wi-Fi scan target selection (single-subnet priority with saved fallback)

## 1) Problem / Symptom
- User feedback indicated that scanning multiple NIC subnets was unnecessary in common cases and could increase scan duration.
- Desired behavior:
  - if current Wi-Fi is connected, scan that subnet first;
  - if not connected, fall back to last successful subnet;
  - keep additional fallback only as a last resort.

## 2) Root Cause
- Previous logic intentionally merged multiple subnet sources (connected Wi-Fi, saved list, configured Wi-Fi, active non-Wi-Fi), which improved coverage but could reduce scan focus/speed.
- For normal single-phone usage, a one-target strategy is more predictable and faster.

## 3) Changes Made
- `QtScrcpy/src/adb/devicediscovery.cpp`
  - `getLocalNetworkSegments()` now returns a single target subnet in priority order:
    1. connected Wi-Fi subnet;
    2. most recent saved successful subnet;
    3. configured Wi-Fi subnet;
    4. active subnet fallback;
    5. configured subnet fallback.
  - Removed multi-segment merge for this path and fixed scan target count to `1`.

## 4) Validation Evidence
- Code-level verification:
  - `kSingleTargetSegment = 1` is enforced.
  - Saved segment fallback uses only `savedSegments.first()`.
  - Priority chain matches product requirement from user feedback.
- CI trigger requirement:
  - this note is added alongside source change to satisfy `Change note gate`.

## 5) Risk and Rollback
- Known risk:
  - in rare topologies, a single-target choice may miss the device subnet on first scan.
- Mitigation:
  - fallback order preserves saved-history and active/configured subnet recovery paths.
- Rollback plan:
  - revert this commit to restore multi-subnet scan expansion behavior.

