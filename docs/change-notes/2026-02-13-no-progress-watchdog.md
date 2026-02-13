# 2026-02-13 No-progress watchdog for scan/connect

## Goal
- Prevent long "no response" states by auto-stopping workflows that show no progress for a long period.

## Changes
- File: `QtScrcpy/src/ui/mainwindow.h`
  - Added pending-operation state for `Scanning` and `Connecting`.
  - Added watchdog timer and progress timestamp fields.
- File: `QtScrcpy/src/ui/mainwindow.cpp`
  - Added a 1-second watchdog tick.
  - Added progress tracking helpers:
    - `startPendingOperation(...)`
    - `markPendingOperationProgress()`
    - `stopPendingOperation(...)`
    - `onOperationWatchdogTick()`
  - Behavior:
    - If scanning has no progress for 2 minutes: stop scan automatically and keep app responsive.
    - If connecting has no progress for 2 minutes: auto-cancel and return to device list.

## Additional mitigation
- File: `QtScrcpy/src/adb/adbprocess.cpp`
  - Reduced device metadata query blocking time:
    - `getprop` timeout changed to 8 seconds.
    - `wm size` timeout changed to 8 seconds.

## Expected effect
- Greatly reduce long UI freeze windows from stalled device state transitions.
- Provide deterministic fallback instead of requiring manual force-stop in common timeout cases.
