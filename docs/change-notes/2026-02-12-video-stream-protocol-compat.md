# Change Note

- Date: 2026-02-12
- Commit: pending
- Scope: fix black screen (`0 FPS`) after successful connect on newer scrcpy server

## 1) Problem / Symptom
- UI showed `Video stream connected`, but screen stayed black with `0.0 FPS`.
- Runtime log showed decoder initialized and control channel connected, but no frame output.

## 2) Root Cause
- Runtime assumed legacy video metadata shape (`name + width + height`).
- Current bundled server (`3.3.4`) may send different startup metadata and optional dummy byte.
- Server args relied on defaults for stream metadata; defaults differ across versions and can break parser expectations.

## 3) Changes Made
- `QtScrcpy/src/server/servermanager.cpp`
  - Made stream protocol explicit in server args:
    - `video=true`
    - `audio=false`
    - `control=true`
    - `send_device_meta=true`
    - `send_frame_meta=false`
    - `send_codec_meta=false`
    - `send_dummy_byte=false`
- `QtScrcpy/src/stream/videostream.cpp`
  - Added compatible device-metadata parsing:
    - supports optional dummy-byte offset
    - parses 64-byte device name metadata
    - keeps backward-compatible legacy width/height parse via heuristic
  - Added decoder `initialized(width,height)` forwarding so UI/device-size can be updated even when startup metadata lacks resolution.
- `QtScrcpy/src/ui/mainwindow.cpp`
  - Avoided writing invalid `0x0` screen size from metadata.
  - Added first-frame fallback to initialize device size when metadata has no resolution.

## 4) Validation Evidence
- User log (`F:\\down\\QtScrcpy-win-x64(10)\\log.txt`) confirms:
  - version mismatch auto-retry already worked
  - decoder initialized
  - still no frames due protocol mismatch assumptions
- This patch aligns server output mode with client parser and adds parser compatibility fallback.

## 5) Risk and Rollback
- Risk:
  - If future server versions remove these options, startup may fail with clear server-side arg error.
- Rollback:
  - Revert this commit to restore old arg/default behavior.
