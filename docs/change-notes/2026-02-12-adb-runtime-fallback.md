# Change Note

- Date: 2026-02-12
- Commit: pending
- Scope: QtScrcpy ADB runtime path fallback and availability detection

## 1) Problem / Symptom
- App showed "ADB was not detected" even when a valid ADB existed in system PATH.
- A local bundled `adb/adb.exe` path was detected, but if that binary was blocked or broken at runtime, the app stayed on this bad path and failed USB/Wi-Fi device discovery.

## 2) Root Cause
- `resolveAdbPath()` selected the first existing ADB file, but did not validate that it could actually execute.
- `checkAdbVersion()` required the command to succeed on current path only and had no fallback path migration.

## 3) Changes Made
- `QtScrcpy/src/adb/adbprocess.cpp`
  - Added runtime probe helper `isRunnableAdb()` (`adb version` with timeout) to validate executable availability.
  - Updated `resolveAdbPath()` to prefer the first runnable ADB among:
    - app dir `adb/adb.exe`
    - app dir `adb.exe`
    - app dir `platform-tools/adb.exe`
    - system PATH ADB
  - Updated `checkAdbVersion()`:
    - accept success by command exit status (`exitCode == 0`) instead of strict output string match
    - when current path fails, auto-fallback to PATH ADB if runnable, then switch internal ADB path to fallback.

## 4) Validation Evidence
- Diff reviewed for all ADB path resolution and version-check call paths.
- Local compile is blocked in this environment due missing Ninja/MSVC toolchain, so compile validation is delegated to CI.

## 5) Risk and Rollback
- Risk:
  - On machines with multiple ADB installs, path preference now favors "runnable" rather than just "first file exists".
- Rollback:
  - Revert this commit to restore prior static path behavior.
