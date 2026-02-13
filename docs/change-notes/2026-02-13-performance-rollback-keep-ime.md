# Change Note

- Date: 2026-02-13
- Commit: pending
- Scope: rollback non-IME runtime changes to recover smooth playback while keeping Chinese input

## 1) Problem / Symptom
- After `ac27468`, Chinese input became available, but screen playback became noticeably less smooth than the previous package.
- User requested: keep only the input method improvement and revert other runtime behavior to previous stable version.

## 2) Root Cause
- The previous patch bundled IME fix with additional runtime behavior changes:
  - continuous mute keep-alive timer (`1.5s`) in UI thread path,
  - aggressive/multi-command volume control changes.
- These non-IME additions increased command churn during mirroring and introduced regression risk for frame smoothness.

## 3) Changes Made
- `QtScrcpy/src/ui/mainwindow.h`
  - Removed `m_muteKeepAliveTimer` member.
- `QtScrcpy/src/ui/mainwindow.cpp`
  - Removed mute keep-alive timer construction and timeout loop.
  - Removed timer start/stop lifecycle hooks from connect/disconnect path.
  - Kept Unicode input bridge wiring:
    - `InputHandler::unicodeTextInputRequested`
    - `MainWindow::onUnicodeTextInputRequested`
- `QtScrcpy/src/adb/volumecontroller.cpp`
  - Restored to previous stable implementation from commit `e1670d5`.
  - Removed broad multi-stream mute + command fallback experiment.

## 4) Validation Evidence
- Code diff confirms:
  - all keep-alive timer references removed,
  - volume controller returned to previous behavior,
  - Unicode input path remains present (`inputhandler` + `clipboard` + `mainwindow` slot).
- Expected runtime behavior:
  - Chinese input remains usable.
  - Playback smoothness returns closer to previous stable release.

## 5) Risk and Rollback
- Risk:
  - mute behavior is intentionally less aggressive than the experimental branch.
- Rollback:
  - Revert this commit to re-enable aggressive mute/keep-alive behavior.
