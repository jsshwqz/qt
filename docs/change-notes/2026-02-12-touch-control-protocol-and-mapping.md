# 2026-02-12 Touch Control Protocol and Mapping

- Date: 2026-02-12
- Commit: pending (this note is committed with the fix)
- Scope: Runtime control path (`VideoWidget -> InputHandler -> ControlStream -> ControlMessage`)

## 1) Problem / Symptom
- User observed that video stream connected, but mouse/touch control did not work.
- Log evidence:
  - `Video stream connected`
  - `Control stream connected`
  - Device list and mirror were visible, but clicks had no effect.

## 2) Root Cause
- Direct cause:
  - `InjectTouch` message serialization was missing `actionButton`, causing protocol mismatch with scrcpy 3.x touch packet layout.
  - Display coordinates were mapped twice (widget->video in `VideoWidget`, then scaled again in `InputHandler`), producing invalid device coordinates.
- Why this happened:
  - Control protocol was partially implemented against an older/incorrect touch payload shape.
  - Input mapping responsibilities were duplicated across UI and handler layers.

## 3) Changes Made
- File list:
  - `QtScrcpy/src/input/controlmessage.h`
  - `QtScrcpy/src/input/controlmessage.cpp`
  - `QtScrcpy/src/stream/controlstream.h`
  - `QtScrcpy/src/stream/controlstream.cpp`
  - `QtScrcpy/src/input/inputhandler.h`
  - `QtScrcpy/src/input/inputhandler.cpp`
  - `QtScrcpy/src/ui/videowidget.cpp`
  - `QtScrcpy/src/stream/videostream.cpp`
- Key logic change:
  - Added `actionButton` in touch message and `buttons` in scroll message serialization.
  - Updated `ControlStream::sendTouch/sendScroll` signatures and call sites.
  - Removed second coordinate scaling in `InputHandler`; now clamp to device bounds.
  - Mapped wheel position to video frame coordinates in `VideoWidget`.
  - Trimmed trailing `\0` bytes from device name metadata.
- Why this fix is minimal and sufficient:
  - Only control serialization and input mapping path were changed.
  - No decoder/rendering behavior was altered.

## 4) Validation Evidence
- Build result:
  - Local compile could not be executed in this environment (missing Visual Studio/Ninja toolchain).
- Runtime evidence used:
  - Reproduced failure mode from user log `F:\down\QtScrcpy-win-x64(11)\log.txt`.
  - Verified control path now matches scrcpy 3.x protocol field layout in source.
- Regression checks:
  - Kept ADB/device discovery flow unchanged.
  - Kept video decode path unchanged.

## 5) Risk and Rollback
- Known risk:
  - Mouse event semantics may differ across some Android vendor ROMs.
- Rollback plan:
  - Revert this commit to restore previous control behavior.
