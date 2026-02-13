# Change Note

- Date: 2026-02-13
- Commit: pending
- Scope: Unicode input compatibility and stronger mute behavior during mirroring

## 1) Problem / Symptom
- Chinese text still could not be entered from desktop keyboard path (item 11).
- Phone-side mute expectation still not stable across devices/ROMs (item 12).

## 2) Root Cause
- Runtime log evidence showed server-side `InjectText` rejection for CJK chars:
  - `Could not inject char u+7231`
  - `Could not inject char u+6559`
  - similar warnings for other Chinese chars.
- Current text path only used scrcpy SDK text injection, which is limited for non-ASCII on some devices.
- Mute logic only targeted media stream and relied on a single shell command form; behavior varied by ROM command availability.

## 3) Changes Made
- `QtScrcpy/src/input/inputhandler.h`
  - Added signal `unicodeTextInputRequested(const QString&)`.
- `QtScrcpy/src/input/inputhandler.cpp`
  - Added non-ASCII detection.
  - For non-ASCII text, emit `unicodeTextInputRequested` instead of `sendText()`.
  - ASCII path remains unchanged (`sendText()`).
- `QtScrcpy/src/clipboard/clipboardmanager.h`
  - Added `sendUnicodeInput(const QString&)` API.
- `QtScrcpy/src/clipboard/clipboardmanager.cpp`
  - Added Unicode bridge path using control message `setClipboard(..., paste=true)`.
  - Added echo suppression (`m_suppressedEchoText`) to avoid local clipboard pollution loop from this transient input bridge.
- `QtScrcpy/src/ui/mainwindow.h`
  - Added slot `onUnicodeTextInputRequested(const QString&)`.
  - Added timer member `m_muteKeepAliveTimer`.
- `QtScrcpy/src/ui/mainwindow.cpp`
  - Connected `InputHandler::unicodeTextInputRequested` to main window handler.
  - Routed Unicode text into clipboard-based Unicode bridge.
  - Added mute keep-alive timer (1.5s) and start/stop lifecycle with connection state.
- `QtScrcpy/src/adb/volumecontroller.cpp`
  - Mute now saves and targets all main streams (music/ring/notification/alarm/system/voice).
  - Added multi-command fallback for volume get/set:
    - `media volume ...`
    - `cmd media_session volume ...`
    - `cmd audio set-stream-volume ...` (set path)
  - Added command success heuristics and zero-volume verification logs.

## 4) Validation Evidence
- Source inspection confirms:
  - non-ASCII no longer goes through raw `InjectText` path;
  - Unicode input has dedicated fallback channel;
  - mute path now has command fallback and periodic enforcement;
  - clipboard echo suppression exists for transient Unicode bridge text.
- Build verification in this environment could not be completed due missing toolchain:
  - Ninja not configured (`CMAKE_MAKE_PROGRAM-NOTFOUND` in Ninja build dirs)
  - Visual Studio generator unavailable locally.

## 5) Risk and Rollback
- Risk:
  - Unicode bridge internally uses a transient clipboard paste control message for non-ASCII text.
  - Some apps with strict input fields may still reject injected text.
- Rollback:
  - Revert this commit to restore previous direct `sendText()` only behavior and previous mute strategy.
