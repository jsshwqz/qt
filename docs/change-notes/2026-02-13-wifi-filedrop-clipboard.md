# Change Note

- Date: 2026-02-13
- Commit: pending
- Scope: improve Wi-Fi connect path, file drag/drop coverage, and clipboard operations

## 1) Problem / Symptom
- User asked to defer fullscreen work and prioritize three practical capabilities:
  - Wi-Fi connection should work reliably from current USB-connected state.
  - File drag/drop should work without requiring precise drop on video area only.
  - Clipboard should support clear bi-direction actions in UI.
- Existing behavior still required long subnet scans in some USB scenarios, and drag/drop was limited to `VideoWidget` hit area.

## 2) Root Cause
- Wi-Fi flow depended primarily on subnet scanning and manual IP entry, without a USB-assisted `adb tcpip` bootstrap in the main flow.
- Main window did not handle drag/drop events, so dropping on non-video regions was ignored.
- Clipboard sync had background auto-sync, but no explicit menu actions for “push local clipboard” / “pull device clipboard”, reducing operability and testability.

## 3) Changes Made
- `QtScrcpy/src/ui/mainwindow.h`
  - Added declarations for:
    - `dragEnterEvent(QDragEnterEvent*)`
    - `dropEvent(QDropEvent*)`
    - `onPasteClipboardToDevice()`
    - `onSyncClipboardFromDevice()`
    - `parseIpEndpoint(...)`
    - `prepareWirelessFromUsb(...)`
    - `resolveDeviceWifiIp(...)`
- `QtScrcpy/src/ui/mainwindow.cpp`
  - Enabled main-window level drag/drop (`setAcceptDrops(true)`) and implemented:
    - `dragEnterEvent(...)` / `dropEvent(...)` with local file validation.
  - Added Control menu actions:
    - `Paste Clipboard to Device` (`Ctrl+Shift+V`)
    - `Sync Clipboard from Device` (`Ctrl+Shift+C`)
  - Enhanced manual connect parser:
    - supports `IPv4` and `IPv4:port` input.
  - Added USB-assisted Wi-Fi bootstrap in scan flow:
    - on scan start, attempt `adb tcpip 5555` on first USB device,
    - resolve device Wi-Fi IP from shell/property output,
    - attempt `adb connect` before falling back to subnet scan.
  - Added explicit clipboard action handlers:
    - local clipboard -> device clipboard
    - request device clipboard -> local clipboard
  - Adjusted clipboard auto-sync startup to honor setting `control/clipboardSync`.

## 4) Validation Evidence
- Source-level verification confirms:
  - Main window now accepts dropped file URLs and routes to `onFilesDropped(...)`.
  - Wi-Fi helper methods exist and are invoked before subnet scan.
  - Manual connect now parses `IP:port` endpoints.
  - Clipboard actions are exposed in menu and call `ClipboardManager` APIs.
- Local full compile was not completed in this environment because existing build dirs are not runnable locally:
  - `build_qtscrcpy_local`: `CMAKE_MAKE_PROGRAM-NOTFOUND` (Ninja tool missing in current environment)
  - `build_qtscrcpy_local_vs`: Visual Studio generator unavailable on this machine

## 5) Risk and Rollback
- Risk:
  - USB-assisted Wi-Fi connect depends on ROM/network conditions; may still fall back to subnet scan on some devices.
  - New menu labels are currently English for clarity and stability.
- Rollback:
  - Revert this commit to restore previous scan-only Wi-Fi path and video-widget-only drag/drop behavior.
