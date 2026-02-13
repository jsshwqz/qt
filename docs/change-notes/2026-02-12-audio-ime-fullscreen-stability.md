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
- Build failure on first attempt came from a type-name collision: `enum class AudioStream` (volume controller) vs newly added audio stream class name.

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
- `QtScrcpy/src/stream/audiostream.h/.cpp` + `QtScrcpy/src/ui/mainwindow.*`
  - Renamed stream class to `AudioPlaybackStream` to avoid conflict with existing `AudioStream` enum type used by volume control code.
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

## 6) Follow-up (2026-02-13)
- Scope: direct-input behavior (no clipboard fallback), USB scan lifecycle stabilization, ADB command overlap guard.

### 6.1 Problem / Symptom
- User requested direct input only (no clipboard-paste path).
- Runtime logs showed `Could not inject char u+XXXX` on Chinese commit text.
- USB connected sessions could still keep wireless scan UI active, and stop was not always immediate.
- Logs occasionally showed `QProcess::start: Process is already running` in ADB polling.

### 6.2 Root Cause
- IME-committed non-ASCII text was sent as `InjectText`; on some devices (e.g. Android 10) server-side char injection fails.
- `VideoWidget` previously suppressed key events when IME was visible/composing, so device-side IME could not receive direct key flow.
- Auto-scan trigger logic only checked wireless devices, not USB presence; connect flow did not force-suspend scan lifecycle.
- `AdbProcess` reused a shared `QProcess` without guarding against overlapping sync calls.

### 6.3 Changes Made
- `QtScrcpy/src/input/inputhandler.cpp`
  - Removed clipboard fallback from text path (direct-input mode only).
  - For `Qt::Key_unknown` committed text, skip non-ASCII and avoid server-side inject-char failures.
  - `handleTextInput()` now ignores non-ASCII committed text and sends direct text only for ASCII.
- `QtScrcpy/src/ui/videowidget.cpp`
  - Do not swallow key press/release during IME visibility/composition.
  - `inputMethodEvent()` forwards committed text only when ASCII; keeps non-ASCII on device-side IME key flow.
- `QtScrcpy/src/ui/mainwindow.cpp`
  - Stop wireless scan immediately when USB device is present.
  - `onScanDevices()` stop branch now also reacts to visible progress state.
  - `connectToDevice()` now forcibly stops scan, hides progress, and pauses auto-scan.
  - `showVideoView()` now restores focus to video widget.
  - `triggerAutoWirelessScan()` now skips auto-scan when USB or wireless devices are already present.
- `QtScrcpy/src/adb/adbprocess.cpp`
  - Added overlap guard in `execute()` to wait/terminate previous running process before new command start.

### 6.4 Validation Evidence
- Static checks:
  - No clipboard fallback path remains in `InputHandler` text handling.
  - IME key suppression in `VideoWidget` key handlers is removed.
  - USB-aware scan stop/skip logic present in main window device/scan lifecycle.
  - ADB overlap guard present before `m_process->start(...)`.
- Runtime expectation:
  - No forced clipboard paste behavior for text input.
  - USB-connected sessions should not keep auto wireless scan running.
  - Reduced `Process is already running` ADB warnings under refresh pressure.
