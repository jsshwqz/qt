# Change Note

- Date: 2026-02-12
- Commit: pending
- Scope: device list parsing compatibility for ADB output

## 1) Problem / Symptom
- `adb devices -l` (and some `adb devices`) outputs could be space-aligned instead of strict tab-separated.
- QtScrcpy device list remained empty even though command line ADB clearly showed connected USB device.

## 2) Root Cause
- `AdbProcess::getDevices()` only matched lines containing `"\tdevice"` or `"\tunauthorized"`.
- Lines with whitespace-separated status (spaces) were ignored.

## 3) Changes Made
- `QtScrcpy/src/adb/adbprocess.cpp`
  - Updated parsing to use regex on generic whitespace:
    - `^\\s*(\\S+)\\s+(device|unauthorized|offline)\\b`
  - This supports both tab and space aligned output.

## 4) Validation Evidence
- Confirmed parser now accepts both forms:
  - `SERIAL<TAB>device`
  - `SERIAL    device product:...`
- Local compile is not available in this environment; CI build is used as compile/package gate.

## 5) Risk and Rollback
- Risk:
  - Low; parser is broadened to include `offline` and whitespace variants.
- Rollback:
  - Revert this commit to restore old strict-tab parsing.
