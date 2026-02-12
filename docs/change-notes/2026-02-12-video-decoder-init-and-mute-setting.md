# Change Note

- Date: 2026-02-12
- Commit: pending
- Scope: fix black-screen-after-connect path and stop forced phone mute by default

## 1) Problem / Symptom
- Device control worked after connect, but video view stayed black (`0.0 FPS`, waiting state).
- Runtime log contained:
  - `QMetaObject::invokeMethod: No such method Decoder::init()`
- Phone volume was always muted on connect, even when user did not opt in.

## 2) Root Cause
- `VideoStream::onConnected()` used string-based queued invocation (`"init"`), but `Decoder::init()` is not a Qt slot/invokable method.
- Decoder initialization never ran, so video packets were ignored and no frames were emitted.
- `MainWindow::onServerReady()` always called `saveAndMute()` regardless of user settings.

## 3) Changes Made
- `QtScrcpy/src/stream/videostream.cpp`
  - Replaced string-based invoke with lambda queued to decoder thread and explicit init failure handling.
  - Added decoder error forwarding to stream-level error signal/logging.
- `QtScrcpy/src/ui/mainwindow.cpp`
  - Applied `QSettings("QtScrcpy", "QtScrcpy")` gate for `control/muteOnConnect`.
  - Mute now occurs only when user explicitly enables it.
- `QtScrcpy/src/ui/settingsdialog.cpp`
  - Changed default `control/muteOnConnect` to `false`.
  - Updated restore-default behavior to keep mute disabled by default.

## 4) Validation Evidence
- This removes the exact runtime error path (`No such method Decoder::init()`).
- Decoder init is now guaranteed to run on decoder thread after socket connect.
- Runtime no longer mutes phone audio unless setting is enabled.

## 5) Risk and Rollback
- Risk:
  - If users previously depended on auto-mute, behavior changes unless they enable the setting.
- Rollback:
  - Revert this commit to restore previous invoke/mute behavior.
