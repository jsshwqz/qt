# Change Note

- Date: 2026-02-13
- Commit: pending
- Scope: direct IME text path, Wi-Fi scan lifecycle, mute default behavior

## 1) Problem / Symptom
- Input method text still could not be typed into phone in direct-input mode.
- Manual Wi-Fi scan could be interrupted by USB detection, leading to poor discoverability.
- Phone-side mute-on-connect was not enabled by default in fresh settings.

## 2) Root Cause
- UI layer and input handler were filtering non-ASCII committed text, so IME commit strings were dropped before reaching control stream.
- Device-list refresh logic stopped scan whenever USB existed, without distinguishing manual scan from auto-scan.
- `control/muteOnConnect` default value remained `false`, so phone mute behavior depended on user manual setting.

## 3) Changes Made
- `QtScrcpy/src/ui/videowidget.cpp`
  - Removed ASCII-only guard in `inputMethodEvent()`.
  - Committed IME text now always forwards to `InputHandler::handleTextInput()`.
- `QtScrcpy/src/input/inputhandler.cpp`
  - Removed non-ASCII drop logic in `handleKeyPress()` (for `Qt::Key_unknown` text path).
  - Removed non-ASCII drop logic in `handleTextInput()`.
  - Direct text now always sends via control stream `sendText()`.
- `QtScrcpy/src/ui/mainwindow.h`
  - Added `m_manualScanInProgress` state flag.
- `QtScrcpy/src/ui/mainwindow.cpp`
  - Track manual scan lifecycle (`start/stop/finished/connect` all reset/set flag).
  - Keep USB-triggered scan stop behavior for auto scan only; do not interrupt active manual scan.
  - Mute setting migration:
    - if `control/muteOnConnect` missing, initialize to `true`.
    - read default as `true` in connection path.
- `QtScrcpy/src/ui/settingsdialog.cpp`
  - Settings default for `muteOnConnect` changed to `true`.
  - Restore-defaults now sets `muteOnConnect` to `true`.
- `QtScrcpy/src/adb/adbprocess.cpp`
  - Added async start guard in `executeAsync()` to skip re-entrant `QProcess::start()` when process is busy.

## 4) Validation Evidence
- Static checks:
  - No remaining non-ASCII filter in IME commit pipeline.
  - Manual scan flag referenced in device-update stop condition and scan lifecycle methods.
  - Mute default now reads/writes with `true` baseline in both runtime and settings UI.
  - Async ADB path now has a busy-state guard before `start()`.
- Runtime expectation:
  - IME commit text reaches device via control stream instead of being locally dropped.
  - User-clicked Wi-Fi scan will continue even if USB device exists.
  - Fresh users get mute-on-connect enabled without extra setting steps.

## 5) Risk and Rollback
- Risk:
  - Some devices may still reject specific Unicode injection at server side even after client forwards text.
  - Manual scans with USB connected may run longer by design.
- Rollback:
  - Revert this commit to restore prior ASCII-only IME filtering, previous scan stop policy, and mute default.
