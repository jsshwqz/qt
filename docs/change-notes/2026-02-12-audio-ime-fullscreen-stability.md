# Change Note

- Date: 2026-02-12
- Commit: pending
- Scope: audio socket lifecycle + Android-version audio gating + IME/fullscreen interaction polish

## 1) Problem / Symptom
- Users could connect and control device, but PC had no sound.
- Some sessions showed unstable connect lifecycle when stream/socket order changed.
- IME experience was inconsistent for composed text input.
- Fullscreen/fit sizing did not consistently account for window chrome, causing suboptimal adaptation.

## 2) Root Cause
- Client connection flow was still effectively video/control-oriented; audio socket was not fully wired in the main window lifecycle.
- scrcpy audio forwarding requires Android 11+ (API 30+), but older devices were not explicitly gated before socket/arg setup.
- Key handling attempted direct text injection from keypress path, which is brittle for IME-composed input.
- Resize helpers used pure frame size without adding top-level non-video area.

## 3) Changes Made
- `QtScrcpy/src/server/servermanager.cpp`
  - Detect device SDK via `ro.build.version.sdk` before starting server.
  - Enable audio only for SDK >= 30; otherwise force `audio=false` and skip audio codec args.
  - Port-forward setup now branches by audio capability:
    - with audio: video -> audio -> control
    - without audio: video -> control
- `QtScrcpy/src/server/servermanager.h`
  - Added runtime fields for audio capability (`m_audioEnabled`) and detected SDK (`m_deviceSdk`).
- `QtScrcpy/src/ui/mainwindow.cpp`
  - Fully instantiated and connected `AudioStream` in UI lifecycle.
  - Updated `onServerReady(videoPort, audioPort, controlPort)` and socket open order.
  - Added runtime fallback handling when audio stream is unavailable or unsupported.
  - Ensure disconnect path also closes audio stream.
- `QtScrcpy/src/input/inputhandler.cpp`
  - Adjusted keypress text-injection rule: fallback text injection only for `Qt::Key_unknown` composed input.
  - Regular printable keys continue through keycode path for stable control semantics.
- `QtScrcpy/src/ui/videowidget.cpp`
  - Fullscreen toggle now refreshes render rect and focus.
  - `resizeToFit()` and `resizeToOriginal()` now include top-level chrome offsets.
  - Rendering hint is less expensive in fullscreen (`SmoothPixmapTransform` disabled there) for better fluidity.
  - Mouse press forces widget focus and focus-in now updates input method state.

## 4) Validation Evidence
- Static verification:
  - Signal/slot signatures aligned to 3-port ready callback.
  - Audio stream lifecycle references are present in constructor, connections, and disconnect path.
  - Server args now show `audio=true/false` by runtime capability instead of unconditional audio.
- Runtime expectation:
  - Android 11+: audio socket is opened and PCM playback attempted.
  - Android 10 and below: no audio forwarding attempted; video/control remain stable.
  - IME composed text path prefers input method commit behavior.

## 5) Risk and Rollback
- Known risk:
  - Devices where SDK query fails default to audio disabled to prioritize stability.
  - Fullscreen smooth-transform tradeoff favors FPS over scaling quality.
- Rollback plan:
  - Revert this commit to restore previous always-audio-arg behavior and pre-change UI input/resize logic.
