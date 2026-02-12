# Change Note

- Date: 2026-02-12
- Commit: pending
- Scope: add runtime ADB diagnostic trace for faster field debugging

## 1) Problem / Symptom
- When users reported "command line ADB can detect device but UI cannot", diagnosis still required repeated manual back-and-forth.
- Existing `run_debug.bat` logs did not include parser-level evidence for ADB command output/parse result.

## 2) Root Cause
- Runtime diagnostic signals around ADB command execution and device parsing were insufficient.
- Packaging script did not enable a dedicated ADB diagnostic mode automatically for debug runs.

## 3) Changes Made
- `QtScrcpy/src/adb/adbprocess.cpp`
  - Added env-flag controlled diagnostics: `QT_SCRCPY_ADB_DIAG=1`.
  - Emits targeted logs for:
    - `adb start-server`
    - `adb version`
    - `adb devices`
  - Emits parsed device list count and serials.
- `.github/workflows/build-windows.yml`
  - Updated packaged `run_debug.bat` to set `QT_SCRCPY_ADB_DIAG=1` automatically.

## 4) Validation Evidence
- Code diff confirms diagnostics are guarded by env flag (no default noise in normal run).
- Packaged debug script now enables ADB diagnostics without extra user steps.

## 5) Risk and Rollback
- Risk:
  - Slightly larger debug logs when `run_debug.bat` is used.
- Rollback:
  - Revert this commit to remove diagnostic trace and env switch.
